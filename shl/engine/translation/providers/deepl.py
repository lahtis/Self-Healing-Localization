"""
File: deepl.py — module for DeepL translation adapter.
Author: Tuomas Lähteenmäki
Version: 0.2.0
License: MIT
Description: Robust translation provider adapter for the DeepL API.
             Handles advanced features including context matching, 
             formality adjustment, and glossary mapping.
"""

import json
import logging
import socket
from typing import Dict, Any, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from .. import __version__ as SHL_VERSION
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

logger = logging.getLogger(__name__)

DEEPL_TIMEOUT = 15


class DeepLAdapter(TranslationProvider):
    """
    DeepL translation adapter.

    Supports:
    - text, source_lang, target_lang (all providers)
    - context (built from SHL metadata)
    - formality
    - glossary
    """

    def __init__(
        self,
        api_key: str,
        use_free_api: bool = True,
    ):
        if not api_key:
            raise ValueError("DeepL API key cannot be empty")
            
        self.api_key = api_key
        self.base_url = (
            "https://api-free.deepl.com/v2" if use_free_api else "https://api.deepl.com/v2"
        )

    @property
    def name(self) -> str:
        return "deepl"

    def translate(self, request: TranslationRequest) -> str:
        """
        Translate text using DeepL API.
        """
        payload = self.build_request(request)
        return self._call_api(payload)

    def build_request(self, request: TranslationRequest) -> Dict[str, Any]:
        """Build DeepL API JSON payload."""
        payload = {
            "text": [request.text],
            "target_lang": request.target_lang.upper(),
        }

        # Source language is optional in DeepL (auto-detects if omitted)
        if request.source_lang:
            payload["source_lang"] = request.source_lang.upper()

        # Build structural context parameter from SHL metadata
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

        # Handle formality matching criteria
        if request.formality:
            payload["formality"] = "less" if request.formality == "informal" else "more"

        # Glossary support (requires a configured glossary_id string)
        if request.glossary and "id" in request.glossary:
            payload["glossary_id"] = request.glossary["id"]

        # HTML markup structural parsing flags
        if request.html_format:
            payload["tag_handling"] = "html"

        return payload

    def _call_api(self, payload: Dict[str, Any]) -> str:
        """Execute request against DeepL API endpoints."""
        try:
            url = f"{self.base_url}/translate"
            request_data = json.dumps(payload).encode("utf-8")

            logger.debug(f"DeepL request to {url} (text length: {len(payload['text'][0])})")

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
                    raise TranslationError("DeepL returned an empty translations payload")

                translated = translations[0].get("text")

                # Verify if translated text changed to prevent falling through silently
                if translated and translated != payload["text"][0]:
                    logger.debug("DeepL translation successful")
                    return translated

                raise TranslationError("DeepL returned empty or unmodified text output")

        except HTTPError as e:
            if e.code in (401, 403):
                raise ProviderAccessError("DeepL: Invalid or unauthorized API token initialization")
            elif e.code == 429:
                raise RateLimitExceededError("DeepL: Maximum burst request cadence exceeded")
            elif e.code == 456:
                raise RateLimitExceededError("DeepL: Periodic character quota limit reached")
            elif e.code >= 500:
                raise ServiceUnavailableError(f"DeepL: Remote endpoint issue {e.code}")
            elif e.code == 400:
                raise InvalidRequestError(f"DeepL: Invalid request configuration parameters ({e.code})")
            else:
                raise TranslationError(f"DeepL HTTP error status code: {e.code}")

        except URLError as e:
            if isinstance(e.reason, (socket.timeout, TimeoutError)):
                raise ServiceUnavailableError("DeepL network timeout reached")
            raise ServiceUnavailableError(f"DeepL socket pipeline failure: {e.reason}")
            
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
            raise TranslationError(f"DeepL unexpected execution layer failure: {type(e).__name__}: {e}")
