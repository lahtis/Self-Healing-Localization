"""
File: papago.py — module for Papago translation adapter.
Author: Tuomas Lähteenmäki
Version: 0.2.10
License: MIT
Description: Robust translation provider adapter for the Naver Papago API.
Handles language pair validation, honorific support, glossary mapping,
registry validation (TTL-based), and security checks for suspicious output.
"""

import json
import logging
import socket
from typing import Dict, Any, Optional, Set, Tuple
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

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
from ..errors import ErrorParser
from ..errors.providers import PAPAGO

logger = logging.getLogger(__name__)

PAPAGO_TIMEOUT = 15
PAPAGO_ENDPOINT = "https://papago.apigw.ntruss.com/nmt/v1/translation"


class PapagoAdapter(TranslationProvider):
    """
    Papago translation adapter (Naver Cloud).

    Supports:
    - text, source_lang, target_lang
    - honorific (direct bool/str or via formality)
    - glossary (glossaryKey)
    - registry validation (TTL-based blacklist)
    - security checks
    """

    # Staattisesti tuetut kieliparit
    SUPPORTED_PAIRS: Set[Tuple[str, str]] = {
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
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        # Käytä annettuja tunnisteita tai lue ympäristömuuttujista
        self.client_id = client_id or get_env_value("NAVER_CLIENT_ID")
        self.client_secret = client_secret or get_env_value("NAVER_CLIENT_SECRET")

        if not self.client_id or not self.client_secret:
            raise ValueError(
                "Papago client_id and client_secret must be provided as parameters or "
                "set as NAVER_CLIENT_ID and NAVER_CLIENT_SECRET in ./.env/shl/.env"
            )

        self.client_id = self.client_id.strip()
        self.client_secret = self.client_secret.strip()
        self.base_url = PAPAGO_ENDPOINT

        # TTL-based registry
        ttl_env = float(get_config_value("ttl.papago", "86400"))
        self.registry = PapagoRegistry(cache_ttl=ttl_env)

        self.error_parser = ErrorParser(
            provider=self.name,
            config=PAPAGO,
        )

        logger.debug(
            f"PapagoAdapter initialized "
            f"(client_id={mask_api_key(self.client_id)}, ttl={ttl_env}s)"
        )

    @property
    def name(self) -> str:
        return "papago"

    @property
    def supported_features(self) -> list:
        return ["honorific", "glossary", "formality"]

    def translate(self, request: TranslationRequest) -> str:
        """Translate text using Papago API."""

        # Pre-validate language pair
        if request.source_lang and request.source_lang.lower() != "auto":
            src = request.source_lang.lower()
            tgt = request.target_lang.lower()

            # 1. Staattinen tuki
            if (src, tgt) not in self.SUPPORTED_PAIRS:
                raise LanguageNotSupportedError(
                    f"Papago does not support language pair "
                    f"{request.source_lang}->{request.target_lang}"
                )

            # 2. TTL-blacklist check
            if not self.registry.is_pair_supported(
                request.source_lang,
                request.target_lang,
                static_supported=True,
            ):
                raise ServiceUnavailableError(
                    f"Papago pair {request.source_lang}->{request.target_lang} "
                    "temporarily unavailable"
                )

        payload = self.build_request(request)
        return self._call_api(payload, request)

    def build_request(self, request: TranslationRequest) -> Dict[str, Any]:
        """Build Papago API JSON payload."""
        source = (request.source_lang or "auto").lower()
        target = request.target_lang.lower()

        payload: Dict[str, Any] = {
            "source": source,
            "target": target,
            "text": request.text,
        }

        # --- Honorific support ---
        honorific_value = None

        if hasattr(request, "honorific") and request.honorific is not None:
            if isinstance(request.honorific, bool):
                honorific_value = "true" if request.honorific else "false"
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

        # Glossary support
        if request.glossary and "id" in request.glossary:
            payload["glossaryKey"] = request.glossary["id"]

        return payload

    def _call_api(
        self,
        payload: Dict[str, Any],
        request: TranslationRequest,
    ) -> str:
        """Execute request against Papago API endpoint."""
        try:
            url = self.base_url
            request_data = json.dumps(payload).encode("utf-8")

            logger.debug(
                f"Papago request to {url} "
                f"(client_id={mask_api_key(self.client_id)}, "
                f"text length: {len(payload['text'])})"
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
                response_data = json.loads(
                    response.read().decode("utf-8")
                )

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

        except HTTPError as e:
            try:
                error_body = e.read().decode(
                    "utf-8",
                    errors="replace",
                )
            except Exception:
                error_body = ""

            normalized = self.error_parser.parse(
                error_body,
                http_status=e.code,
            )

            if normalized is None:
                raise TranslationError(
                    f"Papago HTTP error status code: {e.code}"
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

            raise self._map_normalized_error(
                normalized
            ) from e

        except URLError as e:
            normalized = self.error_parser.parse(
                exception=e,
            )

            raise self._map_normalized_error(
                normalized
            ) from e

        except (socket.timeout, TimeoutError) as e:
            normalized = self.error_parser.parse(
                exception=e,
            )

            raise self._map_normalized_error(
                normalized
            ) from e

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
        """Map a normalized SHL error to existing Papago exceptions."""

        if error.code == "RATE_LIMIT_EXCEEDED":
            return RateLimitExceededError(
                error.message
                or "Papago rate limit exceeded."
            )

        if error.code == "QUOTA_EXCEEDED":
            return RateLimitExceededError(
                error.message
                or "Papago quota exceeded."
            )

        if error.code in {
            "TIMEOUT",
            "SERVICE_UNAVAILABLE",
        }:
            return ServiceUnavailableError(
                error.message
                or "Papago service unavailable."
            )

        if error.code in {
            "AUTH_FAILED",
            "AUTH_EXPIRED",
            "AUTH_BLOCKED",
            "ACCESS_DENIED",
        }:
            return ProviderAccessError(
                error.message
                or "Papago access denied."
            )

        if error.code in {
            "LANG_UNSUPPORTED",
            "LANG_PAIR_UNSUPPORTED",
        }:
            return LanguageNotSupportedError(
                error.message
                or "Papago language is not supported."
            )

        if error.code in {
            "INVALID_REQUEST",
            "TEXT_TOO_LONG",
            "REQUEST_TOO_LONG",
            "METHOD_NOT_ALLOWED",
        }:
            return InvalidRequestError(
                error.message
                or "Papago request is invalid."
            )

        return TranslationError(
            error.message
            or "Papago translation failed."
        )
