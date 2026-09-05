"""
File: local_translator.py — module for local translation adapter.
Author: Tuomas Lähteenmäki
Version: 0.2.10
License: MIT
Description: Translation provider adapter for the SHL local translation API.
Builds metadata-aware translation requests, supports formality, context,
glossary, honorifics, and HTML handling, validates language pairs through
the local provider registry, and validates translation responses for
unexpected or suspicious output.
"""

import json
import logging
import socket
from typing import Dict, Any, Optional
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
from .base import TranslationProvider, TranslationResult
from .local_translator_registry import LocalRegistry
from ...errors.parser import ErrorParser
from ...errors.providers import LOCAL

logger = logging.getLogger(__name__)

LOCAL_TRANSLATOR_TIMEOUT = 15


class LocalTranslatorAdapter(TranslationProvider):
    """
    local_translator adapter.
    Supports:
    - text, source_lang, target_lang
    - context (built from SHL metadata)
    - formality
    - glossary
    - honorifics
    - all features
    - registry validation
    - security checks
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        registry: Optional[LocalRegistry] = None,
    ):
        self.api_key = api_key or get_env_value("LOCAL_TRANSLATOR_API_KEY")

        if not self.api_key:
            raise ValueError(
                "Local translator API key must be provided as parameter or "
                "set as LOCAL_TRANSLATOR_API_KEY in ./.env/shl/.env"
            )

        self.api_key = self.api_key.strip()

        self.base_url = get_config_value(
            "providers.local.url",
            "https://localhost",
        ).rstrip("/")

        # Use a shared registry when one is not explicitly supplied.
        self.registry = registry or LocalRegistry.shared()

        self.error_parser = ErrorParser(
            provider=self.name,
            config=LOCAL,
        )

        logger.debug(
            f"local_translator_adapter initialized "
            f"(api_key={mask_api_key(self.api_key)})"
        )

    @property
    def name(self) -> str:
        return "local"

    @property
    def supported_features(self) -> list:
        return ["formality", "context", "glossary", "honorific", "html_format"]

    def translate(self, request: TranslationRequest) -> str:
        """Translate text using Local API. Backward-compatible str return."""
        return self.translate_with_metadata(request).text

    def translate_with_metadata(
        self,
        request: TranslationRequest,
    ) -> TranslationResult:
        """Translate text using Local API and return full metadata."""

        if not self.registry.is_supported(
            self.name,
            request.source_lang,
            request.target_lang,
        ):
            raise LanguageNotSupportedError(
                f"Local does not support language pair "
                f"{request.source_lang or 'auto'}->{request.target_lang}"
            )

        payload = self.build_request(request)
        return self._call_api(payload, request)

    def build_request(
        self,
        request: TranslationRequest,
    ) -> Dict[str, Any]:
        """Build local translator API JSON payload."""
        payload = {
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
            payload["formality"] = request.formality

        if request.honorific:
            payload["honorific"] = request.honorific

        if request.glossary:
            payload["glossary"] = request.glossary

        if request.html_format:
            payload["html_format"] = True

        return payload

    def _call_api(
        self,
        payload: Dict[str, Any],
        request: TranslationRequest,
    ) -> TranslationResult:
        """Execute request against Local API endpoints."""

        try:
            url = f"{self.base_url}/translate"
            request_data = json.dumps(payload).encode("utf-8")

            logger.debug(
                f"Local request to {url} "
                f"(api_key={mask_api_key(self.api_key)}, "
                f"text length: {len(payload['text'][0])})"
            )

            req = Request(
                url,
                data=request_data,
                headers={
                    "Authorization": f"Local-Auth-Key {self.api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": f"SHL-Client/{SHL_VERSION}",
                    "Accept": "application/json",
                },
                method="POST",
            )

            with urlopen(req, timeout=LOCAL_TRANSLATOR_TIMEOUT) as response:
                response_data = json.loads(
                    response.read().decode("utf-8")
                )
                translations = response_data.get("translations", [])

                if not translations:
                    raise TranslationError(
                        "Local returned an empty translations payload"
                    )

                translated = translations[0].get("text")
                detected = (
                    translations[0].get(
                        "detected_source_language"
                    ) or ""
                ).lower()

                engine = response_data.get("engine")
                fallback = bool(response_data.get("fallback", False))
                confidence = response_data.get("confidence")

                if not translated or translated.strip() == "":
                    raise TranslationError("Local returned empty text.")

                if translated.strip() == payload["text"][0].strip():
                    raise TranslationError(
                        "Local returned unchanged text."
                    )

                if request.source_lang:
                    if detected and detected != request.source_lang.lower():
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

                if len(translated) < 3 and len(payload["text"][0]) > 20:
                    raise TranslationError(
                        "Local returned suspiciously short output."
                    )

                self.registry.mark_success(
                    self.name,
                    request.source_lang,
                    request.target_lang,
                )

                logger.debug(
                    f"Local translation successful "
                    f"(engine={engine}, fallback={fallback})"
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

        except (socket.timeout, TimeoutError) as e:
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
