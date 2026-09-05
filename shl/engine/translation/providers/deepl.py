"""
File: deepl.py — module for DeepL translation adapter.
Author: Tuomas Lähteenmäki
Version: 0.2.10
License: MIT
Description: Robust translation provider adapter for the DeepL API.
Handles advanced features including context matching,
formality adjustment, glossary mapping, registry validation,
and security checks for suspicious output.
"""

import json
import logging
import socket
from typing import Dict, Any, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

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
    """
    DeepL translation adapter.
    Supports:
    - text, source_lang, target_lang
    - context (built from SHL metadata)
    - formality
    - glossary
    - registry validation
    - security checks
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or get_env_value("DEEPL_API_KEY")

        if not self.api_key:
            raise ValueError(
                "DeepL API key must be provided as parameter or "
                "set as DEEPL_API_KEY in ./.env/shl/.env"
            )

        self.api_key = self.api_key.strip()

        # Auto-detect Free vs Pro endpoint
        if self.api_key.endswith(":fx"):
            self.base_url = "https://api-free.deepl.com/v2"
        else:
            self.base_url = "https://api.deepl.com/v2"

        # Runtime language pair registry
        self.registry = DeepLRegistry()

        # Provider-independent error parser
        self.error_parser = ErrorParser(
            provider=self.name,
            config=DEEPL,
        )

        logger.debug(
            f"DeepLAdapter initialized "
            f"(api_key={mask_api_key(self.api_key)})"
        )

    @property
    def name(self) -> str:
        return "deepl"

    @property
    def supported_features(self) -> list:
        return ["formality", "context", "glossary", "html_format"]

    def translate(self, request: TranslationRequest) -> str:
        """Translate text using DeepL API."""

        # Pre-validate language pair using registry
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

    def build_request(self, request: TranslationRequest) -> Dict[str, Any]:
        """Build DeepL API JSON payload."""
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
    ) -> None:
        """
        Convert a normalized SHL error into the existing adapter
        exception hierarchy.
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
        payload: Dict[str, Any],
        request: TranslationRequest,
    ) -> str:
        """Execute request against DeepL API endpoints."""
        try:
            url = f"{self.base_url}/translate"
            request_data = json.dumps(payload).encode("utf-8")

            logger.debug(
                f"DeepL request to {url} "
                f"(api_key={mask_api_key(self.api_key)}, "
                f"text length: {len(payload['text'][0])})"
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
                raw_response = response.read().decode("utf-8")

                response_data = self.error_parser._decode_payload(
                    raw_response
                )

                if response_data is None:
                    error = self.error_parser.parse(
                        raw_response,
                        http_status=response.status,
                    )
                    self._raise_normalized_error(error)

                translations = response_data.get(
                    "translations",
                    [],
                )

                if not translations:
                    error = self.error_parser.parse(
                        {
                            "message": (
                                "DeepL returned an empty "
                                "translations payload"
                            )
                        },
                        http_status=response.status,
                    )
                    self._raise_normalized_error(error)

                translated = translations[0].get("text")
                detected = translations[0].get(
                    "detected_source_language",
                    "",
                ).lower()

                # --- SECURITY CHECK: DeepL output validation ---

                # 1. Empty or unchanged output
                if not translated or translated.strip() == "":
                    error = self.error_parser.parse(
                        {
                            "message": "DeepL returned empty text."
                        },
                        http_status=response.status,
                    )
                    self._raise_normalized_error(error)

                if translated.strip() == payload["text"][0].strip():
                    error = self.error_parser.parse(
                        {
                            "message": (
                                "DeepL returned unchanged text."
                            )
                        },
                        http_status=response.status,
                    )
                    self._raise_normalized_error(error)

                # 2. Unexpected detected source language
                if request.source_lang:
                    if (
                        detected
                        and detected != request.source_lang.lower()
                    ):
                        error = self.error_parser.parse(
                            {
                                "message": (
                                    "DeepL detected unexpected source "
                                    f"language '{detected}' for input "
                                    f"declared as "
                                    f"'{request.source_lang}'."
                                )
                            },
                            http_status=response.status,
                        )
                        self._raise_normalized_error(error)

                # 3. Unexpected HTML markup
                if not request.html_format:
                    if "<" in translated and ">" in translated:
                        error = self.error_parser.parse(
                            {
                                "message": (
                                    "DeepL returned unexpected "
                                    "HTML markup."
                                )
                            },
                            http_status=response.status,
                        )
                        self._raise_normalized_error(error)

                # 4. Suspiciously short output
                if len(translated) < 3 and len(
                    payload["text"][0]
                ) > 20:
                    error = self.error_parser.parse(
                        {
                            "message": (
                                "DeepL returned suspiciously "
                                "short output."
                            )
                        },
                        http_status=response.status,
                    )
                    self._raise_normalized_error(error)

                logger.debug("DeepL translation successful")
                return translated

        except HTTPError as e:
            response_data = None

            try:
                raw_body = e.read().decode("utf-8")

                if raw_body:
                    response_data = json.loads(raw_body)
            except (UnicodeDecodeError, json.JSONDecodeError):
                response_data = None

            if response_data is None:
                response_data = {}

            error = self.error_parser.parse(
                response_data,
                http_status=e.code,
            )

            if error is None:
                error = self.error_parser.parse(
                    {},
                    http_status=e.code,
                )

            self._raise_normalized_error(error)

        except URLError as e:
            if isinstance(
                e.reason,
                (socket.timeout, TimeoutError),
            ):
                error = self.error_parser.parse(
                    {},
                    exception=TimeoutError(
                        "DeepL network timeout reached"
                    ),
                )
            else:
                error = self.error_parser.parse(
                    {},
                    exception=ConnectionError(
                        f"DeepL socket pipeline failure: {e.reason}"
                    ),
                )

            self._raise_normalized_error(error)

        except (socket.timeout, TimeoutError) as e:
            error = self.error_parser.parse(
                {},
                exception=e,
            )
            self._raise_normalized_error(error)

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
            error = self.error_parser.parse(
                {},
                exception=e,
            )
            self._raise_normalized_error(error)
