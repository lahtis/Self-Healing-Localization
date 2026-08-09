"""
MyMemory translation adapter.
"""

import os
import json
import logging
import time
import socket
from typing import Optional, Dict, Any
from urllib.request import Request, urlopen
from urllib.parse import quote
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
from .mymemory_registry import MyMemoryRegistry

logger = logging.getLogger(__name__)

MYMEMORY_TIMEOUT = 10
# Read email from environment variable to unlock larger daily limits (10k words vs 1k anonymous)
MYMEMORY_DEFAULT_EMAIL = os.getenv("MYMEMORY_EMAIL", "")

# Shared module-level registry instance to persist state across adapter instantiations
_registry = MyMemoryRegistry()


class MyMemoryAdapter(TranslationProvider):
    """
    MyMemory translation adapter.
    """

    def __init__(self, email: Optional[str] = None, cache_ttl: Optional[float] = None):
        self.email = email or MYMEMORY_DEFAULT_EMAIL
        
        # Jos käyttäjä määrittää koodissa oman TTL:n, päivitetään se jaetulle rekisterille
        if cache_ttl is not None:
            _registry.cache_ttl = cache_ttl

    @property
    def name(self) -> str:
        return "mymemory"

    def translate(self, request: TranslationRequest) -> str:
        """
        Translate text using MyMemory API.
        """
        src = request.source_lang.lower().strip()
        tgt = request.target_lang.lower().strip()

        # Fast-fail intercept using the isolated registry component
        if not _registry.is_pair_supported(src, tgt):
            raise LanguageNotSupportedError(
                f"MyMemory: Kielipari '{src}|{tgt}' ei ole tuettu tai se on väliaikaisesti estetty."
            )

        payload = self.build_request(request)
        
        try:
            result = self._call_api(payload)
            return result
        except LanguageNotSupportedError:
            # Otetaan kiinni API:n palauttama kielivirhe ja opetetaan se rekisterille lennosta
            _registry.mark_pair_unsupported(src, tgt)
            raise

    def build_request(self, request: TranslationRequest) -> Dict[str, Any]:
        """Build MyMemory API request."""
        return {
            "q": request.text,
            "langpair": f"{request.source_lang.lower().strip()}|{request.target_lang.lower().strip()}",
            "src_raw": request.source_lang,
            "tgt_raw": request.target_lang,
            "de": self.email if self.email else None
        }

    def _call_api(self, payload: Dict[str, Any]) -> str:
        """Call MyMemory API with the built payload."""
        try:
            url = f"https://api.mymemory.translated.net/get?q={quote(payload['q'])}&langpair={payload['langpair']}"
            if payload.get("de"):
                url += f"&de={quote(payload['de'])}"

            logger.debug(f"MyMemory request: {url[:120]}...")

            req = Request(
                url,
                headers={
                    "User-Agent": f"SHL-Client/{SHL_VERSION}",
                    "Accept": "application/json",
                },
            )

            with urlopen(req, timeout=MYMEMORY_TIMEOUT) as response:
                response_data = json.loads(response.read().decode("utf-8"))

                response_status = response_data.get("responseStatus")
                response_details = response_data.get("responseData", {})

                quota_reached = response_data.get("quotaReached", False)
                response_warning = response_details.get("warning", "")

                if quota_reached or "quota" in response_warning.lower():
                    raise RateLimitExceededError(f"MyMemory: Quota reached: {response_warning}")

                if response_status == 403:
                    raise ProviderAccessError("MyMemory: Access denied")
                if response_status == 429:
                    raise RateLimitExceededError("MyMemory: Rate limit exceeded")
                if response_status >= 500:
                    raise ServiceUnavailableError(f"MyMemory: Server error {response_status}")
                if response_status == 404:
                    raise LanguageNotSupportedError("MyMemory: Language not supported")
                if response_status == 400:
                    if "language" in str(response_data).lower() or "invalid" in str(response_data).lower():
                        raise LanguageNotSupportedError("MyMemory: Language not supported")
                    raise InvalidRequestError(f"MyMemory: Bad request {response_status}")
                if response_status != 200:
                    raise TranslationError(f"MyMemory: Unexpected status {response_status}")

                translated = response_details.get("translatedText")

                if translated and translated != payload["q"]:
                    logger.debug(f"MyMemory success: '{translated[:100]}...'")
                    return translated

                raise TranslationError("MyMemory returned empty or unmodified text")

        except HTTPError as e:
            if e.code == 403:
                raise ProviderAccessError("MyMemory HTTP 403")
            elif e.code == 429:
                raise RateLimitExceededError("MyMemory HTTP 429")
            elif e.code >= 500:
                raise ServiceUnavailableError(f"MyMemory HTTP {e.code}")
            elif e.code == 404:
                raise LanguageNotSupportedError("MyMemory: Language not supported")
            elif e.code == 400:
                try:
                    error_body = e.read().decode("utf-8")
                    if "language" in error_body.lower() or "invalid" in error_body.lower():
                        raise LanguageNotSupportedError("MyMemory: Language not supported")
                except Exception:
                    pass
                raise InvalidRequestError("MyMemory HTTP 400")
            else:
                raise TranslationError(f"MyMemory HTTP {e.code}")

        except URLError as e:
            if isinstance(e.reason, (socket.timeout, TimeoutError)):
                raise ServiceUnavailableError("MyMemory timeout")
            raise ServiceUnavailableError(f"MyMemory network error: {e.reason}")
            
        except (socket.timeout, TimeoutError):
            raise ServiceUnavailableError("MyMemory timeout")
            
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
            raise TranslationError(f"MyMemory unexpected error: {type(e).__name__}: {e}")
