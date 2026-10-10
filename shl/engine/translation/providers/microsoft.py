"""
File: shl/engine/translation/providers/microsoft.py
Author: Tuomas Lähteenmäki
Version: 0.3.0
License: MIT
Description: Robust translation provider adapter for the Microsoft
Translator API. Handles advanced features including context matching,
formality adjustment, HTML handling, service availability registry
(TTL), and security checks for suspicious output.

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
from .microsoft_registry import MicrosoftServiceRegistry
from ...errors.parser import ErrorParser
from ...errors.providers import MICROSOFT


logger = logging.getLogger(__name__)

MS_TIMEOUT = 15


class MicrosoftTranslatorAdapter(TranslationProvider):
    """Microsoft Translator adapter.

    Supports:
    - text, source_lang, target_lang
    - context (built from SHL metadata)
    - formality (where supported)
    - html_format
    - service availability registry (TTL)
    - security checks for suspicious output
    """

    def __init__(self, api_key: str | None = None):

        # Use the supplied key or read from environment.
        self.api_key = api_key or get_env_value(
            "MICROSOFT_TRANSLATOR_KEY"
        )

        if not self.api_key:
            raise ValueError(
                "Microsoft Translator API key must be provided as "
                "parameter or set as MICROSOFT_TRANSLATOR_KEY in "
                "./.env/shl/.env"
            )

        self.api_key = self.api_key.strip()

        # Base API endpoint (v3).
        self.base_url = (
            "https://api.cognitive.microsofttranslator.com/"
            "translate?api-version=3.0"
        )

        # Service-level TTL registry (not a language-pair registry).
        ttl_env = float(
            get_config_value(
                "ttl.microsoft_translator",
                "86400",
            )
        )

        self.registry = MicrosoftServiceRegistry(ttl_seconds=ttl_env)

        self.error_parser = ErrorParser(
            provider=self.name,
            config=MICROSOFT,
        )

        logger.debug(
            "MicrosoftTranslatorAdapter initialized "
            "(api_key=%s, ttl=%ss)",
            mask_api_key(self.api_key),
            ttl_env,
        )

    @property
    def name(self) -> str:
        return "microsoft_translator"

    @property
    def supported_features(self) -> list[str]:
        return ["formality", "context", "html_format"]

    def translate(self, request: TranslationRequest) -> str:
        """Translate text using Microsoft Translator API."""

        # Service-level availability check (TTL).
        if not self.registry.is_available():
            raise ServiceUnavailableError(
                "Microsoft Translator marked temporarily unavailable "
                "by TTL registry"
            )

        payload = self.build_request(request)
        return self._call_api(payload, request)

    def build_request(
        self,
        request: TranslationRequest,
    ) -> dict[str, Any]:
        """Build Microsoft Translator API payload and query params."""

        body = [
            {
                "text": request.text,
            }
        ]

        # Explicit annotation is required because params holds a mix
        # of str values and possibly None for optional fields.
        params: dict[str, Any] = {
            "to": request.target_lang,
        }

        if request.source_lang:
            params["from"] = request.source_lang

        # Formality (where supported).
        if request.formality:
            params["formality"] = (
                "informal"
                if request.formality == "informal"
                else "formal"
            )

        # HTML vs plain text.
        if request.html_format:
            params["textType"] = "html"
        else:
            params["textType"] = "plain"

        # Context metadata.
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
            body[0]["context"] = " | ".join(context_parts)

        # Explicit annotation: params is dict[str, Any], body is
        # list[dict[str, str]]. The return value mixes both.
        payload: dict[str, Any] = {
            "params": params,
            "body": body,
        }
        return payload

    def _call_api(
        self,
        payload: dict[str, Any],
        request: TranslationRequest,
    ) -> str:
        """Execute request against Microsoft Translator API."""
        try:
            # Build query string.
            params = "&".join(
                f"{k}={v}"
                for k, v in payload["params"].items()
            )
            url = f"{self.base_url}&{params}"

            request_data = json.dumps(
                payload["body"]
            ).encode("utf-8")

            logger.debug(
                "Microsoft Translator request to %s "
                "(api_key=%s, text length=%d)",
                url,
                mask_api_key(self.api_key),
                len(payload["body"][0]["text"]),
            )

            req = Request(
                url,
                data=request_data,
                headers={
                    "Ocp-Apim-Subscription-Key": self.api_key,
                    "Content-Type": "application/json",
                    "User-Agent": f"SHL-Client/{SHL_VERSION}",
                    "Accept": "application/json",
                },
                method="POST",
            )

            with urlopen(req, timeout=MS_TIMEOUT) as response:
                raw = read_limited_response(
                    response,
                    MAX_RESPONSE_BYTES,
                )
                response_data = json.loads(raw.decode("utf-8"))

            if not response_data or not isinstance(
                response_data,
                list,
            ):
                raise TranslationError(
                    "Microsoft Translator returned an empty or "
                    "invalid payload"
                )

            translations = response_data[0].get(
                "translations",
                [],
            )

            if not translations:
                raise TranslationError(
                    "Microsoft Translator returned no translations "
                    "array"
                )

            translated = translations[0].get("text", "")

            # --- SECURITY CHECKS ---

            # 1. Empty or unchanged output
            if not translated or translated.strip() == "":
                raise TranslationError(
                    "Microsoft Translator returned empty text."
                )

            if translated.strip() == request.text.strip():
                raise TranslationError(
                    "Microsoft Translator returned unchanged text."
                )

            # 2. Unexpected HTML markup when html_format=False
            if not request.html_format:
                if "<" in translated and ">" in translated:
                    raise TranslationError(
                        "Microsoft Translator returned unexpected "
                        "HTML markup."
                    )

            # 3. Suspiciously short output
            if len(translated) < 3 and len(request.text) > 20:
                raise TranslationError(
                    "Microsoft Translator returned suspiciously "
                    "short output."
                )

            logger.debug(
                "Microsoft Translator translation successful"
            )
            return translated

        # safe_urlopen converts urllib's HTTPError and URLError into
        # SafeHTTPError before they leave the safe layer. The HTTP
        # status and response body are preserved on the error object.
        except SafeHTTPError as e:
            if e.status_code is None:
                # Transport-level failure, no HTTP status.
                self.registry.mark_unavailable()
                normalized = self.error_parser.parse(
                    {},
                    exception=e,
                )
                raise self._map_normalized_error(normalized)

            normalized = self.error_parser.parse(
                e.response_body,
                http_status=e.status_code,
            )

            if normalized is None:
                raise TranslationError(
                    f"Microsoft Translator HTTP error status code: "
                    f"{e.status_code}"
                )

            if normalized.code in {
                "SERVICE_UNAVAILABLE",
                "TIMEOUT",
            }:
                self.registry.mark_unavailable()

            raise self._map_normalized_error(normalized)

        except TimeoutError as e:
            normalized = self.error_parser.parse(
                {},
                exception=e,
            )

            self.registry.mark_unavailable()

            raise self._map_normalized_error(normalized)

        except OSError as e:
            normalized = self.error_parser.parse(
                {},
                exception=e,
            )

            self.registry.mark_unavailable()

            raise self._map_normalized_error(normalized)

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

            self.registry.mark_unavailable()

            raise TranslationError(
                f"Microsoft Translator unexpected execution layer "
                f"failure: {type(e).__name__}: {e}"
            )

    @staticmethod
    def _map_normalized_error(error) -> Exception:
        """Map a normalized SHL error to existing adapter exceptions.

        Note: unlike most adapters, this method returns an exception
        instead of raising it. The caller decides when to raise.
        """
        if error.code == "RATE_LIMIT_EXCEEDED":
            return RateLimitExceededError(
                error.message
                or "Microsoft Translator rate limit exceeded."
            )

        if error.code == "QUOTA_EXCEEDED":
            return RateLimitExceededError(
                error.message
                or "Microsoft Translator quota exceeded."
            )

        if error.code in {
            "TIMEOUT",
            "SERVICE_UNAVAILABLE",
        }:
            return ServiceUnavailableError(
                error.message
                or "Microsoft Translator service unavailable."
            )

        if error.code in {
            "AUTH_FAILED",
            "AUTH_EXPIRED",
            "AUTH_BLOCKED",
            "ACCESS_DENIED",
        }:
            return ProviderAccessError(
                error.message
                or "Microsoft Translator access denied."
            )

        if error.code in {
            "LANG_UNSUPPORTED",
            "LANG_PAIR_UNSUPPORTED",
        }:
            return LanguageNotSupportedError(
                error.message
                or "Microsoft Translator language is not supported."
            )

        if error.code in {
            "INVALID_REQUEST",
            "TEXT_TOO_LONG",
            "REQUEST_TOO_LONG",
            "METHOD_NOT_ALLOWED",
        }:
            return InvalidRequestError(
                error.message
                or "Microsoft Translator request is invalid."
            )

        return TranslationError(
            error.message
            or "Microsoft Translator translation failed."
        )
