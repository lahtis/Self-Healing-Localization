"""
File: shl/engine/translation/providers/deepl.py
Author: Tuomas Lähteenmäki
Version: 0.3.0
License: MIT
Description: Robust translation provider adapter for the DeepL API.
Handles advanced features including context matching, formality
adjustment, glossary mapping, registry validation, and security
checks for suspicious output.

All outbound HTTP goes through safe_urlopen for SSRF prevention,
redirect validation, and response size limits.
"""

import json
import logging
from typing import Any, NoReturn
from urllib.request import Request

from shl.utils.safe_http import safe_urlopen as urlopen
from shl.utils.safe_http_common import (
    MAX_RESPONSE_BYTES,
    SafeHTTPError,
    read_limited_response,
)

from shl._version import __version__ as SHL_VERSION
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
from ...errors.parser import ErrorParser
from ...errors.providers import DEEPL
from .base import TranslationProvider
from .deepl_registry import DeepLRegistry


logger = logging.getLogger(__name__)

DEEPL_TIMEOUT = 15


class DeepLAdapter(TranslationProvider):
    """DeepL translation adapter.

    Supports:
    - text, source_lang, target_lang
    - context (built from SHL metadata)
    - formality
    - glossary
    - registry-based language pair validation
    """

    def __init__(
        self,
        api_key: str | None = None,
        registry: DeepLRegistry | None = None,
    ):
        self.api_key = api_key or get_env_value("DEEPL_API_KEY")

        if not self.api_key:
            raise ValueError(
                "DeepL API key must be provided as parameter or "
                "set as DEEPL_API_KEY in ./.env/shl/.env"
            )

        self.api_key = self.api_key.strip()

        # Auto-detect Free vs Pro endpoint.
        if self.api_key.endswith(":fx"):
            self.base_url = "https://api-free.deepl.com/v2"
        else:
            self.base_url = "https://api.deepl.com/v2"

        # The router supplies its shared registry so a language pair
        # rejected by one request is skipped by all later requests in
        # this process. Direct adapter users retain an isolated
        # registry by default.
        self.registry = registry or DeepLRegistry()

        # Provider-independent error parser.
        self.error_parser = ErrorParser(
            provider=self.name,
            config=DEEPL,
        )

        logger.debug(
            "DeepLAdapter initialized (api_key=%s)",
            mask_api_key(self.api_key),
        )

    @property
    def name(self) -> str:
        return "deepl"

    @property
    def supported_features(self) -> list[str]:
        return ["formality", "context", "glossary", "html_format"]

    def translate(self, request: TranslationRequest) -> str:
        """Translate text using DeepL API."""

        if request.source_lang:
            if not self.registry.is_pair_supported(
                request.source_lang,
                request.target_lang,
            ):
                raise LanguageNotSupportedError(
                    f"DeepL does not support language pair "
                    f"{request.source_lang}->{request.target_lang}"
                )

        payload = self.build_request(request)
        return self._call_api(payload, request)

    def build_request(
        self,
        request: TranslationRequest,
    ) -> dict[str, Any]:
        """Build DeepL API JSON payload."""

        # Explicit annotation is required because the payload holds
        # heterogeneous value types (list, str). Without it, mypy
        # narrows the inferred type to dict[str, list[str]] based on
        # the first entry and rejects str values on later keys.
        payload: dict[str, Any] = {
            "text": [request.text],
            "target_lang": request.target_lang.upper(),
        }

        if request.source_lang:
            payload["source_lang"] = request.source_lang.upper()

        context_parts = []
        if request.domain:
            context_parts.append(f"Domain: {request.domain}")
        if request.screen:
            context_parts.append(f"Screen: {request.screen}")
        if request.component:
            context_parts.append(f"Component: {request.component}")
        if request.context_type:
            context_parts.append(f"Type: {request.context_type}")
        if request.key:
            context_parts.append(f"Key: {request.key}")

        if context_parts:
            payload["context"] = " | ".join(context_parts)

        if request.formality:
            payload["formality"] = (
                "less" if request.formality == "informal" else "more"
            )

        if request.glossary and "id" in request.glossary:
            payload["glossary_id"] = request.glossary["id"]

        if request.html_format:
            payload["tag_handling"] = "html"

        return payload

    def _raise_normalized_error(
        self,
        error,
        request: TranslationRequest | None = None,
    ) -> NoReturn:
        """Convert a normalized SHL error into the adapter's exception
        hierarchy. Always raises.
        """

        message = error.message or (
            f"DeepL request failed: {error.code}"
        )

        if error.code == "RATE_LIMIT_EXCEEDED":
            raise RateLimitExceededError(message)

        if error.code == "QUOTA_EXCEEDED":
            raise RateLimitExceededError(message)

        if error.code in {
            "TIMEOUT",
            "SERVICE_UNAVAILABLE",
        }:
            raise ServiceUnavailableError(message)

        if error.code in {
            "AUTH_FAILED",
            "AUTH_EXPIRED",
            "AUTH_BLOCKED",
            "ACCESS_DENIED",
        }:
            raise ProviderAccessError(message)

        if error.code in {
            "LANG_UNSUPPORTED",
            "LANG_PAIR_UNSUPPORTED",
        }:
            if (
                error.code == "LANG_PAIR_UNSUPPORTED"
                and request is not None
            ):
                self.registry.mark_pair_unsupported(
                    request.source_lang,
                    request.target_lang,
                )

            raise LanguageNotSupportedError(message)

        if error.code in {
            "INVALID_REQUEST",
            "TEXT_TOO_LONG",
            "REQUEST_TOO_LONG",
            "METHOD_NOT_ALLOWED",
        }:
            raise InvalidRequestError(message)

        raise TranslationError(message)

    def _call_api(
        self,
        payload: dict[str, Any],
        request: TranslationRequest,
    ) -> str:
        """Execute request against DeepL API endpoints."""
        try:
            url = f"{self.base_url}/translate"
            request_data = json.dumps(payload).encode("utf-8")

            logger.debug(
                "DeepL request to %s (api_key=%s, text length: %d)",
                url,
                mask_api_key(self.api_key),
                len(payload["text"][0]),
            )

            req = Request(
                url,
                data=request_data,
                headers={
                    "Authorization": f"DeepL-Auth-Key {self.api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": f"SHL-Client/{SHL_VERSION}",
                    "Accept": "application/json",
                },
                method="POST",
            )

            with urlopen(req, timeout=DEEPL_TIMEOUT) as response:
                raw = read_limited_response(response, MAX_RESPONSE_BYTES)
                raw_response = raw.decode("utf-8")
                status_code = response.status

            try:
                response_data = json.loads(raw_response)
            except json.JSONDecodeError:
                response_data = None

            if not isinstance(response_data, dict):
                error = self.error_parser.parse(
                    raw_response,
                    http_status=status_code,
                )
                self._raise_normalized_error(error, request)

            translations = response_data.get("translations", [])

            if not translations:
                error = self.error_parser.parse(
                    {
                        "message": (
                            "DeepL returned an empty translations "
                            "payload"
                        )
                    },
                    http_status=status_code,
                )
                self._raise_normalized_error(error, request)

            translated = translations[0].get("text")
            detected = translations[0].get(
                "detected_source_language",
                "",
            ).lower()

            # --- SECURITY CHECK: DeepL output validation ---

            # 1. Empty output. Unchanged output is intentionally
            #    accepted here; the translation router validates
            #    unchanged results using SHL language detection.
            if not translated or translated.strip() == "":
                error = self.error_parser.parse(
                    {"message": "DeepL returned empty text."},
                    http_status=status_code,
                )
                self._raise_normalized_error(error, request)

            # 2. Unexpected detected source language
            if request.source_lang:
                if detected and detected != request.source_lang.lower():
                    error = self.error_parser.parse(
                        {
                            "message": (
                                "DeepL detected unexpected source "
                                f"language '{detected}' for input "
                                f"declared as "
                                f"'{request.source_lang}'."
                            )
                        },
                        http_status=status_code,
                    )
                    self._raise_normalized_error(error, request)

            # 3. Unexpected HTML markup
            if not request.html_format:
                if "<" in translated and ">" in translated:
                    error = self.error_parser.parse(
                        {
                            "message": (
                                "DeepL returned unexpected HTML "
                                "markup."
                            )
                        },
                        http_status=status_code,
                    )
                    self._raise_normalized_error(error, request)

            # 4. Suspiciously short output
            if len(translated) < 3 and len(payload["text"][0]) > 20:
                error = self.error_parser.parse(
                    {
                        "message": (
                            "DeepL returned suspiciously short "
                            "output."
                        )
                    },
                    http_status=status_code,
                )
                self._raise_normalized_error(error, request)

            logger.debug("DeepL translation successful")
            return translated

        # safe_urlopen converts urllib's HTTPError and URLError into
        # SafeHTTPError before they leave the safe layer, so those two
        # exception types no longer need to be handled here.
        except SafeHTTPError as e:
            normalized = self.error_parser.parse(exception=e)
            self._raise_normalized_error(normalized, request)

        except TimeoutError as e:
            normalized = self.error_parser.parse(exception=e)
            self._raise_normalized_error(normalized, request)

        except OSError as e:
            normalized = self.error_parser.parse(exception=e)
            self._raise_normalized_error(normalized, request)

        except (
            RateLimitExceededError,
            ServiceUnavailableError,
            LanguageNotSupportedError,
            ProviderAccessError,
            InvalidRequestError,
            TranslationError,
        ):
            raise

        except Exception as e:
            normalized = self.error_parser.parse(exception=e)
            self._raise_normalized_error(normalized, request)
