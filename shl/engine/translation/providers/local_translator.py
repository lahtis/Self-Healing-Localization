"""
File: shl/engine/translation/providers/local_translator.py
Author: Tuomas Lähteenmäki
Version: 0.3.3
License: MIT
Description: Translation provider adapter for the SHL local translation
API. Builds metadata-aware translation requests, supports formality,
context, glossary, honorifics, and HTML handling, validates language
pairs through the local provider registry, and validates translation
responses for unexpected or suspicious output.

The local service is a LibreTranslate-compatible endpoint. The request
uses the LibreTranslate API shape (q, source, target, format) and the
response is read from translatedText.

Placeholders such as {} and {name} are protected with PlaceholderProtector
before the request is sent to LibreTranslate and restored afterwards.
This keeps them intact even when LibreTranslate would otherwise interpret
{} as an emoji or strip it.

Supported languages are loaded from a cache (local_languages_cache.json)
on first use. The cache is refreshed from the local service's
/languages endpoint when stale or missing. If the service cannot be
reached, the stale cache is used; if no cache exists at all, all
languages are assumed to be supported.

All outbound HTTP goes through safe_local_urlopen for SSRF prevention,
redirect blocking, and response size limits. The configured
`providers.local.url` hostname must appear in the allowlist defined in
shl/utils/safe_local_http.py (_ALLOWED_LOCAL_HOSTS). The default
`https://localhost` is already allowed.
"""

import json
import logging
import re
from typing import Any
from urllib.request import Request

from urllib.error import URLError, HTTPError

from shl.utils.safe_local_http import safe_local_urlopen as urlopen

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
from ..placeholder import (
    PlaceholderProtector,
    PlaceholderIntegrityError,
)
from .base import TranslationProvider, TranslationResult
from .local_translator_registry import LocalRegistry
from ..local_languages_cache import get_local_supported_languages
from ...errors.parser import ErrorParser
from ...errors.providers import LOCAL


logger = logging.getLogger(__name__)

LOCAL_TRANSLATOR_TIMEOUT = 15

# Default placeholder pattern: matches {name}, {}, {0}, etc.
_DEFAULT_PLACEHOLDER_PATTERN = r"\{[^{}]*\}"


class LocalTranslatorAdapter(TranslationProvider):
    """Translation adapter for the SHL local translation API."""

    def __init__(
        self,
        api_key: str | None = None,
        registry: LocalRegistry | None = None,
    ):
        self.api_key = api_key or get_env_value(
            "LOCAL_TRANSLATOR_API_KEY"
        )

        if not self.api_key:
            raise ValueError(
                "Local translator API key must be provided as parameter "
                "or set as LOCAL_TRANSLATOR_API_KEY in ~/.config/shl/.env"
            )

        self.api_key = self.api_key.strip()

        self.base_url = get_config_value(
            "providers.local.url",
            "https://localhost",
        ).rstrip("/")

        self.registry = registry or LocalRegistry.shared()

        self.supported_languages: set[str] = set(
            get_local_supported_languages(self.base_url)
        )

        if self.supported_languages:
            logger.info(
                "Local service supports %d languages",
                len(self.supported_languages),
            )
        else:
            logger.info(
                "Local service language list unknown; assuming all supported",
            )

        self.error_parser = ErrorParser(
            provider=self.name,
            config=LOCAL,
        )

        logger.debug(
            "local_translator_adapter initialized (api_key=%s)",
            mask_api_key(self.api_key),
        )

    @property
    def name(self) -> str:
        return "local"

    @property
    def supported_features(self) -> list[str]:
        return [
            "formality",
            "context",
            "glossary",
            "honorific",
            "html_format",
        ]

    def translate(self, request: TranslationRequest) -> str:
        """Translate text using Local API. Backward-compatible str return."""
        return self.translate_with_metadata(request).text

    def translate_with_metadata(
        self,
        request: TranslationRequest,
    ) -> TranslationResult:
        """Translate text using Local API and return full metadata."""

        if (
            self.supported_languages
            and request.target_lang.lower() not in self.supported_languages
        ):
            self.registry.mark_failure(
                self.name,
                request.source_lang,
                request.target_lang,
            )
            raise LanguageNotSupportedError(
                f"Local does not support target language: "
                f"{request.target_lang}"
            )

        if not self.registry.is_supported(
            self.name,
            request.source_lang,
            request.target_lang,
        ):
            raise LanguageNotSupportedError(
                f"Local does not support language pair "
                f"{request.source_lang or 'auto'}->{request.target_lang}"
            )

        # Protect placeholders before sending to LibreTranslate.
        # LibreTranslate would otherwise turn {} into an emoji or drop it.
        protector: PlaceholderProtector | None = None
        protected_text = request.text

        if re.search(_DEFAULT_PLACEHOLDER_PATTERN, request.text):
            protector = PlaceholderProtector(
                pattern=_DEFAULT_PLACEHOLDER_PATTERN
            )
            protected_text = protector.protect(request.text)

        payload = self.build_request(request, protected_text)
        result = self._call_api(payload, request, protector)

        return result

    def build_request(
        self,
        request: TranslationRequest,
        text: str | None = None,
    ) -> dict[str, Any]:
        """Build LibreTranslate-compatible JSON payload.

        Field names are read from providers.local.request so the same
        adapter can serve different local translation services.
        """

        request_config = get_config_value(
            "providers.local.request",
            {},
        )

        if not isinstance(request_config, dict):
            request_config = {}

        text_field = request_config.get("text_field", "q")
        source_field = request_config.get("source_field", "source")
        target_field = request_config.get("target_field", "target")
        format_field = request_config.get("format_field", "format")
        format_value = request_config.get("format_value", "text")

        payload: dict[str, Any] = {
            text_field: text if text is not None else request.text,
            target_field: request.target_lang.lower(),
        }

        if format_field:
            payload[format_field] = format_value

        if request.source_lang:
            payload[source_field] = request.source_lang.lower()

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
            payload["formality"] = request.formality

        if request.honorific:
            payload["honorific"] = request.honorific

        if request.glossary:
            payload["glossary"] = request.glossary

        return payload

    def _call_api(
        self,
        payload: dict[str, Any],
        request: TranslationRequest,
        protector: PlaceholderProtector | None = None,
    ) -> TranslationResult:
        """Execute request against LibreTranslate API."""

        try:
            url = f"{self.base_url}/translate"
            request_data = json.dumps(payload).encode("utf-8")

            logger.debug(
                "Local request to %s (api_key=%s, text length: %d)",
                url,
                mask_api_key(self.api_key),
                len(payload["q"]),
            )

            req = Request(
                url,
                data=request_data,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": f"SHL-Client/{SHL_VERSION}",
                    "Accept": "application/json",
                },
                method="POST",
            )

            with urlopen(
                req,
                timeout=LOCAL_TRANSLATOR_TIMEOUT,
            ) as response:
                response_data = json.loads(
                    response.read().decode("utf-8")
                )

                translated = response_data.get("translatedText")

                if not translated or translated.strip() == "":
                    raise TranslationError(
                        "Local returned empty text."
                    )

                # Restore placeholders BEFORE further validation,
                # because the protected tokens must be compared against
                # the original text.
                if protector is not None:
                    try:
                        protector.validate(translated)
                    except PlaceholderIntegrityError as error:
                        raise TranslationError(
                            f"Local lost a placeholder: {error}"
                        ) from error

                    translated = protector.restore(translated)

                if translated.strip() == request.text.strip():
                    raise TranslationError(
                        "Local returned unchanged text."
                    )

                detected_info = response_data.get("detectedLanguage")
                detected = ""

                if isinstance(detected_info, dict):
                    detected = str(
                        detected_info.get("language", "")
                    ).lower()
                elif isinstance(detected_info, str):
                    detected = detected_info.lower()

                if request.source_lang and detected:
                    if detected != request.source_lang.lower():
                        raise TranslationError(
                            f"Local detected unexpected source language "
                            f"'{detected}' for input declared as "
                            f"'{request.source_lang}'."
                        )

                if not request.html_format:
                    if "<" in translated and ">" in translated:
                        raise TranslationError(
                            "Local returned unexpected HTML markup."
                        )

                if (
                    len(translated) < 3
                    and len(request.text) > 20
                ):
                    raise TranslationError(
                        "Local returned suspiciously short output."
                    )

                self.registry.mark_success(
                    self.name,
                    request.source_lang,
                    request.target_lang,
                )

                engine = response_data.get("engine")
                fallback = bool(response_data.get("fallback", False))
                confidence = response_data.get("confidence")

                logger.debug(
                    "Local translation successful "
                    "(engine=%s, fallback=%s)",
                    engine,
                    fallback,
                )

                return TranslationResult(
                    text=translated,
                    provider=self.name,
                    engine=engine,
                    fallback=fallback,
                    confidence=confidence,
                )

        except HTTPError as e:
            response_body = None

            try:
                response_body = e.read().decode(
                    "utf-8",
                    errors="replace",
                )
            except Exception:
                response_body = None

            normalized = self.error_parser.parse(
                response_body,
                http_status=e.code,
            )

            if normalized is None:
                raise TranslationError(
                    f"Local HTTP error status code: {e.code}"
                )

            if normalized.code in {
                "LANG_UNSUPPORTED",
                "LANG_PAIR_UNSUPPORTED",
            }:
                self.registry.mark_failure(
                    self.name,
                    request.source_lang,
                    request.target_lang,
                )

            raise self._map_normalized_error(normalized)

        except URLError as e:
            normalized = self.error_parser.parse(
                exception=e,
            )

            raise self._map_normalized_error(normalized)

        except TimeoutError as e:
            normalized = self.error_parser.parse(
                exception=e,
            )

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

            raise TranslationError(
                f"Local unexpected execution layer failure: "
                f"{type(e).__name__}: {e}"
            )

    @staticmethod
    def _map_normalized_error(error) -> Exception:
        """Map a normalized SHL error to the existing adapter exceptions."""

        if error.code == "RATE_LIMIT_EXCEEDED":
            return RateLimitExceededError(
                error.message or "Local rate limit exceeded."
            )

        if error.code == "QUOTA_EXCEEDED":
            return RateLimitExceededError(
                error.message or "Local quota exceeded."
            )

        if error.code in {
            "TIMEOUT",
            "SERVICE_UNAVAILABLE",
        }:
            return ServiceUnavailableError(
                error.message or "Local service unavailable."
            )

        if error.code in {
            "AUTH_FAILED",
            "AUTH_EXPIRED",
            "AUTH_BLOCKED",
            "ACCESS_DENIED",
        }:
            return ProviderAccessError(
                error.message or "Local access denied."
            )

        if error.code in {
            "LANG_UNSUPPORTED",
            "LANG_PAIR_UNSUPPORTED",
        }:
            return LanguageNotSupportedError(
                error.message or "Local language is not supported."
            )

        if error.code in {
            "INVALID_REQUEST",
            "TEXT_TOO_LONG",
            "REQUEST_TOO_LONG",
            "METHOD_NOT_ALLOWED",
        }:
            return InvalidRequestError(
                error.message or "Local request is invalid."
            )

        return TranslationError(
            error.message or "Local translation failed."
        )
