"""
File: microsoft_translator.py — module for Microsoft Translator adapter.
Author: Tuomas Lähteenmäki
Version: 0.2.10
License: MIT
Description: Robust translation provider adapter for the Microsoft Translator API.
Handles advanced features including context matching,
formality adjustment, HTML handling, service availability registry (TTL),
and security checks for suspicious output.
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
from .base import TranslationProvider
from .microsoft_registry import MicrosoftServiceRegistry
from ..errors import ErrorParser
from ..errors.providers import MICROSOFT

logger = logging.getLogger(__name__)

MS_TIMEOUT = 15


class MicrosoftTranslatorAdapter(TranslationProvider):
    """
    Microsoft Translator adapter.
    Supports:
    - text, source_lang, target_lang
    - context (built from SHL metadata)
    - formality (where supported)
    - html_format
    - service availability registry (TTL)
    - security checks
    """

    def __init__(self, api_key: Optional[str] = None):

        # Käytä annettua avainta tai lue ympäristömuuttujasta
        self.api_key = api_key or get_env_value("MICROSOFT_TRANSLATOR_KEY")

        if not self.api_key:
            raise ValueError(
                "Microsoft Translator API key must be provided as parameter or "
                "set as MICROSOFT_TRANSLATOR_KEY in ./.env/shl/.env"
            )

        self.api_key = self.api_key.strip()

        # Perus-API endpoint (v3)
        self.base_url = "https://api.cognitive.microsofttranslator.com/translate?api-version=3.0"

        # Service-level TTL registry (ei kieliparirekisteriä)
        ttl_env = float(get_config_value("ttl.microsoft_translator", "86400"))

        self.registry = MicrosoftServiceRegistry(ttl_seconds=ttl_env)

        self.error_parser = ErrorParser(
            provider=self.name,
            config=MICROSOFT,
        )

        logger.debug(
            f"MicrosoftTranslatorAdapter initialized "
            f"(api_key={mask_api_key(self.api_key)}, ttl={ttl_env}s)"
        )

    @property
    def name(self) -> str:
        return "microsoft_translator"

    @property
    def supported_features(self) -> list:
        return ["formality", "context", "html_format"]

    def translate(self, request: TranslationRequest) -> str:
        """Translate text using Microsoft Translator API."""

        # Service-level availability check (TTL)
        if not self.registry.is_available():
            raise ServiceUnavailableError(
                "Microsoft Translator marked temporarily unavailable by TTL registry"
            )

        payload = self.build_request(request)
        return self._call_api(payload, request)

    def build_request(self, request: TranslationRequest) -> Dict[str, Any]:
        """Build Microsoft Translator API payload and query params."""

        body = [
            {
                "text": request.text,
            }
        ]

        params: Dict[str, Any] = {
            "to": request.target_lang,
        }

        if request.source_lang:
            params["from"] = request.source_lang

        # Formality (where supported)
        if request.formality:
            params["formality"] = (
                "informal" if request.formality == "informal" else "formal"
            )

        # HTML vs plain text
        if request.html_format:
            params["textType"] = "html"
        else:
            params["textType"] = "plain"

        # Context metadata
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

        return {"params": params, "body": body}

    def _call_api(
        self,
        payload: Dict[str, Any],
        request: TranslationRequest,
    ) -> str:
        """Execute request against Microsoft Translator API."""
        try:
            # Build query string
            params = "&".join(
                f"{k}={v}"
                for k, v in payload["params"].items()
            )
            url = f"{self.base_url}&{params}"

            request_data = json.dumps(
                payload["body"]
            ).encode("utf-8")

            logger.debug(
                f"Microsoft Translator request to {url} "
                f"(api_key={mask_api_key(self.api_key)}, "
                f"text length={len(payload['body'][0]['text'])})"
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
                response_data = json.loads(
                    response.read().decode("utf-8")
                )

                if not response_data or not isinstance(
                    response_data,
                    list,
                ):
                    raise TranslationError(
                        "Microsoft Translator returned an empty or invalid payload"
                    )

                translations = response_data[0].get(
                    "translations",
                    [],
                )

                if not translations:
                    raise TranslationError(
                        "Microsoft Translator returned no translations array"
                    )

                translated = translations[0].get(
                    "text",
                    "",
                )

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
                            "Microsoft Translator returned unexpected HTML markup."
                        )

                # 3. Suspiciously short output
                if len(translated) < 3 and len(request.text) > 20:
                    raise TranslationError(
                        "Microsoft Translator returned suspiciously short output."
                    )

                logger.debug(
                    "Microsoft Translator translation successful"
                )

                return translated

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
                    f"Microsoft Translator HTTP error status code: {e.code}"
                )

            if normalized.code in {
                "SERVICE_UNAVAILABLE",
                "TIMEOUT",
            }:
                self.registry.mark_unavailable()

            raise self._map_normalized_error(normalized)

        except URLError as e:
            normalized = self.error_parser.parse(
                exception=e,
            )

            self.registry.mark_unavailable()

            raise self._map_normalized_error(normalized)

        except (socket.timeout, TimeoutError) as e:
            normalized = self.error_parser.parse(
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
                f"Microsoft Translator unexpected execution layer failure: "
                f"{type(e).__name__}: {e}"
            )

    @staticmethod
    def _map_normalized_error(error) -> Exception:
        """Map a normalized SHL error to existing adapter exceptions."""

        if error.code == "RATE_LIMIT_EXCEEDED":
            return RateLimitExceededError(
                error.message or "Microsoft Translator rate limit exceeded."
            )

        if error.code == "QUOTA_EXCEEDED":
            return RateLimitExceededError(
                error.message or "Microsoft Translator quota exceeded."
            )

        if error.code in {
            "TIMEOUT",
            "SERVICE_UNAVAILABLE",
        }:
            return ServiceUnavailableError(
                error.message or "Microsoft Translator service unavailable."
            )

        if error.code in {
            "AUTH_FAILED",
            "AUTH_EXPIRED",
            "AUTH_BLOCKED",
            "ACCESS_DENIED",
        }:
            return ProviderAccessError(
                error.message or "Microsoft Translator access denied."
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
            error.message or "Microsoft Translator translation failed."
        )
