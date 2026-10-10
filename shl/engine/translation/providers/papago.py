"""
File: shl/engine/translation/providers/papago.py
Author: Tuomas Lähteenmäki
Version: 0.3.0
License: MIT
Description: Robust translation provider adapter for the Naver Papago
API. Handles language pair validation, honorific support, glossary
mapping, registry validation (TTL-based), and security checks for
suspicious output.

All outbound HTTP goes through safe_urlopen for SSRF prevention,
redirect validation, and response size limits.
"""

import json
import logging
from typing import Any
from urllib.request import Request

from shl.utils.safe_http import safe_urlopen as urlopen
from shl.utils.safe_http_common import (
    MAX_RESPONSE_BYTES,
    SafeHTTPError,
    read_limited_response,
)

from shl._version import __version__ as SHL_VERSION
from shl.config import get_config_value
from shl.utils.env_loader import get_env_value, mask_api_key
from ..exceptions import (
    TranslationError,
    ServiceUnavailableError,
    RateLimitExceededError,
    LanguageNotSupportedError,
    ProviderAccessError,
    InvalidRequestError,
)
from ..metadata import TranslationRequest
from .base import TranslationProvider
from .papago_registry import PapagoRegistry
from ...errors.parser import ErrorParser
from ...errors.providers import PAPAGO


logger = logging.getLogger(__name__)

PAPAGO_TIMEOUT = 15
PAPAGO_ENDPOINT = (
    "https://papago.apigw.ntruss.com/nmt/v1/translation"
)


class PapagoAdapter(TranslationProvider):
    """Papago translation adapter (Naver Cloud).

    Supports:
    - text, source_lang, target_lang
    - honorific (direct bool/str or via formality)
    - glossary (glossaryKey)
    - registry validation (TTL-based blacklist)
    - security checks for suspicious output
    """

    # Statically supported language pairs.
    SUPPORTED_PAIRS: set[tuple[str, str]] = {
        # Korean
        ("ko", "en"), ("en", "ko"),
        ("ko", "ja"), ("ja", "ko"),
        ("ko", "zh-cn"), ("zh-cn", "ko"),
        ("ko", "zh-tw"), ("zh-tw", "ko"),
        ("ko", "vi"), ("vi", "ko"),
        ("ko", "th"), ("th", "ko"),
        ("ko", "id"), ("id", "ko"),
        ("ko", "fr"), ("fr", "ko"),
        ("ko", "es"), ("es", "ko"),
        ("ko", "ru"), ("ru", "ko"),
        ("ko", "de"), ("de", "ko"),
        ("ko", "it"), ("it", "ko"),
        # English
        ("en", "ja"), ("ja", "en"),
        ("en", "zh-cn"), ("zh-cn", "en"),
        ("en", "zh-tw"), ("zh-tw", "en"),
        ("en", "vi"), ("vi", "en"),
        ("en", "th"), ("th", "en"),
        ("en", "id"), ("id", "en"),
        ("en", "fr"), ("fr", "en"),
        ("en", "es"), ("es", "en"),
        ("en", "ru"), ("ru", "en"),
        ("en", "de"), ("de", "en"),
        # Japanese
        ("ja", "zh-cn"), ("zh-cn", "ja"),
        ("ja", "zh-tw"), ("zh-tw", "ja"),
        ("ja", "vi"), ("vi", "ja"),
        ("ja", "th"), ("th", "ja"),
        ("ja", "id"), ("id", "ja"),
        ("ja", "fr"), ("fr", "ja"),
        # Chinese
        ("zh-cn", "zh-tw"), ("zh-tw", "zh-cn"),
    }

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
    ):
        # Use the supplied credentials or read from environment.
        self.client_id = (
            client_id or get_env_value("NAVER_CLIENT_ID")
        )
        self.client_secret = (
            client_secret or get_env_value("NAVER_CLIENT_SECRET")
        )

        if not self.client_id or not self.client_secret:
            raise ValueError(
                "Papago client_id and client_secret must be provided "
                "as parameters or set as NAVER_CLIENT_ID and "
                "NAVER_CLIENT_SECRET in ./.env/shl/.env"
            )

        self.client_id = self.client_id.strip()
        self.client_secret = self.client_secret.strip()
        self.base_url = PAPAGO_ENDPOINT

        # TTL-based registry.
        ttl_env = float(get_config_value("ttl.papago", "86400"))
        self.registry = PapagoRegistry(cache_ttl=ttl_env)

        self.error_parser = ErrorParser(
            provider=self.name,
            config=PAPAGO,
        )

        logger.debug(
            "PapagoAdapter initialized "
            "(client_id=%s, ttl=%ss)",
            mask_api_key(self.client_id),
            ttl_env,
        )

    @property
    def name(self) -> str:
        return "papago"

    @property
    def supported_features(self) -> list[str]:
        return ["honorific", "glossary", "formality"]

    def translate(self, request: TranslationRequest) -> str:
        """Translate text using Papago API."""

        # Pre-validate language pair.
        if request.source_lang and request.source_lang.lower() != "auto":
            src = request.source_lang.lower()
            tgt = request.target_lang.lower()

            # 1. Static support.
            if (src, tgt) not in self.SUPPORTED_PAIRS:
                raise LanguageNotSupportedError(
                    f"Papago does not support language pair "
                    f"{request.source_lang}->{request.target_lang}"
                )

            # 2. TTL-blacklist check.
            if not self.registry.is_pair_supported(
                request.source_lang,
                request.target_lang,
                static_supported=True,
            ):
                raise ServiceUnavailableError(
                    f"Papago pair {request.source_lang}->"
                    f"{request.target_lang} temporarily unavailable"
                )

        payload = self.build_request(request)
        return self._call_api(payload, request)

    def build_request(
        self,
        request: TranslationRequest,
    ) -> dict[str, Any]:
        """Build Papago API JSON payload."""
        source = (request.source_lang or "auto").lower()
        target = request.target_lang.lower()

        # Explicit annotation is required because the payload holds
        # a mix of str values and optional glossary keys.
        payload: dict[str, Any] = {
            "source": source,
            "target": target,
            "text": request.text,
        }

        # --- Honorific support ---
        honorific_value = None

        if hasattr(request, "honorific") and request.honorific is not None:
            if isinstance(request.honorific, bool):
                honorific_value = (
                    "true" if request.honorific else "false"
                )
            elif isinstance(request.honorific, str):
                val = request.honorific.lower().strip()

                if val in (
                    "true",
                    "1",
                    "yes",
                    "formal",
                    "more",
                    "polite",
                    "honorific",
                ):
                    honorific_value = "true"
                else:
                    honorific_value = "false"

        elif getattr(request, "formality", None):
            formality = str(request.formality).lower()

            if formality in (
                "formal",
                "more",
                "honorific",
                "polite",
            ):
                honorific_value = "true"
            elif formality in (
                "informal",
                "less",
                "casual",
            ):
                honorific_value = "false"

        if honorific_value is not None:
            payload["honorific"] = honorific_value

        # Glossary support.
        if request.glossary and "id" in request.glossary:
            payload["glossaryKey"] = request.glossary["id"]

        return payload

    def _call_api(
        self,
        payload: dict[str, Any],
        request: TranslationRequest,
    ) -> str:
        """Execute request against Papago API endpoint."""
        try:
            url = self.base_url
            request_data = json.dumps(payload).encode("utf-8")

            logger.debug(
                "Papago request to %s (client_id=%s, text length: %d)",
                url,
                mask_api_key(self.client_id),
                len(payload["text"]),
            )

            req = Request(
                url,
                data=request_data,
                headers={
                    "X-NCP-APIGW-API-KEY-ID": self.client_id,
                    "X-NCP-APIGW-API-KEY": self.client_secret,
                    "Content-Type": "application/json",
                    "User-Agent": f"SHL-Client/{SHL_VERSION}",
                    "Accept": "application/json",
                },
                method="POST",
            )

            with urlopen(req, timeout=PAPAGO_TIMEOUT) as response:
                raw = read_limited_response(
                    response,
                    MAX_RESPONSE_BYTES,
                )
                response_data = json.loads(raw.decode("utf-8"))

            message = response_data.get("message", {})
            result = message.get("result", {})
            translated = result.get("translatedText")

            if not translated:
                raise TranslationError(
                    "Papago returned an empty translation payload"
                )

            # --- SECURITY CHECKS ---

            if not translated or translated.strip() == "":
                raise TranslationError(
                    "Papago returned empty text."
                )

            if translated.strip() == payload["text"].strip():
                raise TranslationError(
                    "Papago returned unchanged text."
                )

            if not getattr(request, "html_format", False):
                if "<" in translated and ">" in translated:
                    raise TranslationError(
                        "Papago returned unexpected HTML markup."
                    )

            if len(translated) < 3 and len(payload["text"]) > 20:
                raise TranslationError(
                    "Papago returned suspiciously short output."
                )

            logger.debug("Papago translation successful")
            return translated

        # safe_urlopen converts urllib's HTTPError and URLError into
        # SafeHTTPError before they leave the safe layer. The HTTP
        # status and response body are preserved on the error object.
        except SafeHTTPError as e:
            if e.status_code is None:
                # Transport-level failure, no HTTP status.
                normalized = self.error_parser.parse(
                    {},
                    exception=e,
                )
                raise self._map_normalized_error(normalized) from e

            normalized = self.error_parser.parse(
                e.response_body,
                http_status=e.status_code,
            )

            if normalized is None:
                raise TranslationError(
                    f"Papago HTTP error status code: {e.status_code}"
                ) from e

            if normalized.code in {
                "LANG_UNSUPPORTED",
                "LANG_PAIR_UNSUPPORTED",
            }:
                if (
                    request.source_lang
                    and request.source_lang.lower() != "auto"
                ):
                    self.registry.mark_pair_unsupported(
                        request.source_lang,
                        request.target_lang,
                    )

            raise self._map_normalized_error(normalized) from e

        except TimeoutError as e:
            normalized = self.error_parser.parse(
                {},
                exception=e,
            )
            raise self._map_normalized_error(normalized) from e

        except OSError as e:
            normalized = self.error_parser.parse(
                {},
                exception=e,
            )
            raise self._map_normalized_error(normalized) from e

        except Exception as e:
            if isinstance(
                e,
                (
                    RateLimitExceededError,
                    ServiceUnavailableError,
                    LanguageNotSupportedError,
                    ProviderAccessError,
                    InvalidRequestError,
                    TranslationError,
                ),
            ):
                raise

            raise TranslationError(
                f"Papago unexpected execution layer failure: "
                f"{type(e).__name__}: {e}"
            )

    def _map_normalized_error(self, error) -> Exception:
        """Map a normalized SHL error to existing Papago exceptions.

        Unlike most adapters, this returns an exception instead of
        raising it. The caller decides when to raise.
        """

        if error.code == "RATE_LIMIT_EXCEEDED":
            return RateLimitExceededError(
                error.message or "Papago rate limit exceeded."
            )

        if error.code == "QUOTA_EXCEEDED":
            return RateLimitExceededError(
                error.message or "Papago quota exceeded."
            )

        if error.code in {
            "TIMEOUT",
            "SERVICE_UNAVAILABLE",
        }:
            return ServiceUnavailableError(
                error.message or "Papago service unavailable."
            )

        if error.code in {
            "AUTH_FAILED",
            "AUTH_EXPIRED",
            "AUTH_BLOCKED",
            "ACCESS_DENIED",
        }:
            return ProviderAccessError(
                error.message or "Papago access denied."
            )

        if error.code in {
            "LANG_UNSUPPORTED",
            "LANG_PAIR_UNSUPPORTED",
        }:
            return LanguageNotSupportedError(
                error.message or "Papago language is not supported."
            )

        if error.code in {
            "INVALID_REQUEST",
            "TEXT_TOO_LONG",
            "REQUEST_TOO_LONG",
            "METHOD_NOT_ALLOWED",
        }:
            return InvalidRequestError(
                error.message or "Papago request is invalid."
            )

        return TranslationError(
            error.message or "Papago translation failed."
        )
