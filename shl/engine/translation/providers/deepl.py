"""
File: deepl.py — module for DeepL translation adapter.
Author: Tuomas Lähteenmäki
Version: 0.2.4
License: MIT
Description: Robust translation provider adapter for the DeepL API.
Handles advanced features including context matching,
formality adjustment, glossary mapping, registry validation,
and security checks for suspicious output.
"""

import json
import logging
import os
import socket
from typing import Dict, Any, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from shl._version import __version__ as SHL_VERSION
from shl.utils.env_loader import load_shl_env, mask_api_key
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
        # Lataa .env-tiedosto ./env/shl/-kansiosta (jos ei jo ladattu)
        load_shl_env()

        # Käytä annettua avainta tai lue ympäristömuuttujasta
        self.api_key = api_key or os.getenv("DEEPL_API_KEY")

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

        logger.debug(f"DeepLAdapter initialized (api_key={mask_api_key(self.api_key)})")

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

    def _call_api(self, payload: Dict[str, Any], request: TranslationRequest) -> str:
        """Execute request against DeepL API endpoints."""
        try:
            url = f"{self.base_url}/translate"
            request_data = json.dumps(payload).encode("utf-8")

            logger.debug(
                f"DeepL request to {url} (api_key={mask_api_key(self.api_key)}, "
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
            )

            with urlopen(req, timeout=DEEPL_TIMEOUT) as response:
                response_data = json.loads(response.read().decode("utf-8"))
                translations = response_data.get("translations", [])

                if not translations:
                    raise TranslationError(
                        "DeepL returned an empty translations payload"
                    )

                translated = translations[0].get("text")
                detected = translations[0].get("detected_source_language", "").lower()

                # --- SECURITY CHECK: DeepL output validation ---

                # 1. Empty or unchanged output
                if not translated or translated.strip() == "":
                    raise TranslationError("DeepL returned empty text.")

                if translated.strip() == payload["text"][0].strip():
                    raise TranslationError("DeepL returned unchanged text.")

                # 2. Unexpected detected source language
                if request.source_lang:
                    if detected and detected != request.source_lang.lower():
                        raise TranslationError(
                            f"DeepL detected unexpected source language '{detected}' "
                            f"for input declared as '{request.source_lang}'."
                        )

                # 3. Unexpected HTML markup
                if not request.html_format:
                    if "<" in translated and ">" in translated:
                        raise TranslationError("DeepL returned unexpected HTML markup.")

                # 4. Suspiciously short output
                if len(translated) < 3 and len(payload["text"][0]) > 20:
                    raise TranslationError("DeepL returned suspiciously short output.")

                logger.debug("DeepL translation successful")
                return translated

        except HTTPError as e:
            code = e.code

            # Access / auth / billing
            if code in (401, 403):
                raise ProviderAccessError(
                    "DeepL: Invalid or unauthorized API token initialization"
                )
            elif code == 402:
                raise ProviderAccessError(
                    "DeepL: Billing issue or payment required (HTTP 402)"
                )

            # Timeouts / availability / gateway
            elif code == 408:
                raise ServiceUnavailableError(
                    "DeepL: Request timeout (HTTP 408)"
                )
            elif code in (500, 502, 503, 504):
                raise ServiceUnavailableError(
                    f"DeepL: Remote endpoint or gateway issue ({code})"
                )

            # Rate limits / quotas
            elif code == 429:
                raise RateLimitExceededError(
                    "DeepL: Maximum burst request cadence exceeded (HTTP 429)"
                )
            elif code == 456:
                raise RateLimitExceededError(
                    "DeepL: Periodic character quota limit reached (HTTP 456)"
                )

            # Request / payload / configuration errors
            elif code == 400:
                if request.source_lang:
                    self.registry.mark_pair_unsupported(
                        request.source_lang,
                        request.target_lang,
                    )
                raise InvalidRequestError(
                    f"DeepL: Invalid request configuration parameters ({code})"
                )

            elif code in (409, 413, 415, 422):
                if request.source_lang:
                    self.registry.mark_pair_unsupported(
                        request.source_lang,
                        request.target_lang,
                    )
                raise InvalidRequestError(
                    f"DeepL: Request payload or configuration not acceptable ({code})"
                )

            else:
                raise TranslationError(
                    f"DeepL HTTP error status code: {code}"
                )

        except URLError as e:
            if isinstance(e.reason, (socket.timeout, TimeoutError)):
                raise ServiceUnavailableError("DeepL network timeout reached")
            raise ServiceUnavailableError(
                f"DeepL socket pipeline failure: {e.reason}"
            )

        except (socket.timeout, TimeoutError):
            raise ServiceUnavailableError("DeepL connection timeout reached")

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
                f"DeepL unexpected execution layer failure: "
                f"{type(e).__name__}: {e}"
            )
