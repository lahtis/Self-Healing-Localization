"""
File: local_translator.py — module for local translation adapter.
Author: Tuomas Lähteenmäki
Version: 0.2.6
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

    def __init__(self, api_key: Optional[str] = None):
  
        # Käytä annettua avainta tai lue ympäristömuuttujasta
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

        # Runtime language pair registry
        self.registry = LocalRegistry()

        logger.debug(f"local_translator_adapter initialized (api_key={mask_api_key(self.api_key)})")

    @property
    def name(self) -> str:
        return "local"

    @property
    def supported_features(self) -> list:
        return ["formality", "context", "glossary", "honorific", "html_format"]

    def translate(self, request: TranslationRequest) -> str:
        """Translate text using Local API. Backward-compatible str-paluu."""
        return self.translate_with_metadata(request).text

    def translate_with_metadata(self, request: TranslationRequest) -> TranslationResult:
        """Translate text using Local API and palauta täysi metadata.
        """

        # Pre-validate language pair using registry
        if request.source_lang:
            if not self.registry.is_pair_supported(
                request.source_lang,
                request.target_lang,
            ):
                raise LanguageNotSupportedError(
                    f"Local does not support language pair "
                    f"{request.source_lang}->{request.target_lang}"
                )

        payload = self.build_request(request)
        return self._call_api(payload, request)

    def build_request(self, request: TranslationRequest) -> Dict[str, Any]:
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

    def _call_api(self, payload: Dict[str, Any], request: TranslationRequest) -> TranslationResult:
        """Execute request against Local API endpoints.

        Odotettu vastausmuoto palvelimelta:
        {
            "translations": [{"text": "...", "detected_source_language": "FI"}],
            "engine": "local",
            "fallback": true | false,
            "confidence": 0.0-1.0  (valinnainen)
        }
        `engine`, `fallback` ja `confidence` ovat kaikki valinnaisia -
        jos palvelin ei ilmoita niitä, ne jäävät None/False-oletuksiin.
        """
        try:
            url = f"{self.base_url}/translate"
            request_data = json.dumps(payload).encode("utf-8")

            logger.debug(
                f"Local request to {url} (api_key={mask_api_key(self.api_key)}, "
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
                response_data = json.loads(response.read().decode("utf-8"))
                translations = response_data.get("translations", [])

                if not translations:
                    raise TranslationError(
                        "Local returned an empty translations payload"
                    )

                translated = translations[0].get("text")
                detected = (translations[0].get("detected_source_language") or "").lower()

                engine = response_data.get("engine")
                fallback = bool(response_data.get("fallback", False))
                confidence = response_data.get("confidence")

                # --- SECURITY CHECK: Local output validation ---

                # 1. Empty or unchanged output
                if not translated or translated.strip() == "":
                    raise TranslationError("Local returned empty text.")

                if translated.strip() == payload["text"][0].strip():
                    raise TranslationError("Local returned unchanged text.")

                # 2. Unexpected detected source language
                if request.source_lang:
                    if detected and detected != request.source_lang.lower():
                        raise TranslationError(
                            f"Local detected unexpected source language '{detected}' "
                            f"for input declared as '{request.source_lang}'."
                        )

                # 3. Unexpected HTML markup
                if not request.html_format:
                    if "<" in translated and ">" in translated:
                        raise TranslationError("Local returned unexpected HTML markup.")

                # 4. Suspiciously short output
                if len(translated) < 3 and len(payload["text"][0]) > 20:
                    raise TranslationError("Local returned suspiciously short output.")

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
            code = e.code

            # Access / auth / billing
            if code in (401, 403):
                raise ProviderAccessError(
                    "Local: Invalid or unauthorized API token initialization"
                )
            elif code == 402:
                raise ProviderAccessError(
                    "Local: Billing issue or payment required (HTTP 402)"
                )

            # Timeouts / availability / gateway
            elif code == 408:
                raise ServiceUnavailableError(
                    "Local: Request timeout (HTTP 408)"
                )
            elif code in (500, 502, 503, 504):
                raise ServiceUnavailableError(
                    f"Local: Remote endpoint or gateway issue ({code})"
                )

            # Rate limits / quotas
            elif code == 429:
                raise RateLimitExceededError(
                    "Local: Maximum burst request cadence exceeded (HTTP 429)"
                )
            elif code == 456:
                raise RateLimitExceededError(
                    "Local: Periodic character quota limit reached (HTTP 456)"
                )

            # Request / payload / configuration errors
            elif code == 400:
                if request.source_lang:
                    self.registry.mark_pair_unsupported(
                        request.source_lang,
                        request.target_lang,
                    )
                raise InvalidRequestError(
                    f"Local: Invalid request configuration parameters ({code})"
                )

            elif code in (409, 413, 415, 422):
                if request.source_lang:
                    self.registry.mark_pair_unsupported(
                        request.source_lang,
                        request.target_lang,
                    )
                raise InvalidRequestError(
                    f"Local: Request payload or configuration not acceptable ({code})"
                )

            else:
                raise TranslationError(
                    f"Local HTTP error status code: {code}"
                )

        except URLError as e:
            if isinstance(e.reason, (socket.timeout, TimeoutError)):
                raise ServiceUnavailableError("Local network timeout reached")
            raise ServiceUnavailableError(
                f"Local socket pipeline failure: {e.reason}"
            )

        except (socket.timeout, TimeoutError):
            raise ServiceUnavailableError("Local connection timeout reached")

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
