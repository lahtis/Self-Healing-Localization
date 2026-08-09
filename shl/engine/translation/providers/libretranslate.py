"""
LibreTranslate translation adapter.
"""

import json
import logging
import time
import socket
from typing import Optional, Dict, Any
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
from .libretranslate_registry import LibreTranslateRegistry  # <-- Tuodaan uusi rekisteri

logger = logging.getLogger(__name__)

LIBRETRANSLATE_TIMEOUT = 15
LIBRETRANSLATE_DEFAULT_URL = "https://libretranslate.com"
LIBRETRANSLATE_DEFAULT_API_KEY = ""


class LibreTranslateAdapter(TranslationProvider):
    """LibreTranslate translation adapter."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        cache_ttl: float = 86400.0,  # <-- Sallitaan TTL:n määritys (oletus 24h)
    ):
        self.base_url = (base_url or LIBRETRANSLATE_DEFAULT_URL).rstrip("/")
        self.api_key = api_key or LIBRETRANSLATE_DEFAULT_API_KEY
        # Alustetaan rekisteri instanssitasolle varmuuskerrokseksi ja oppimista varten
        self.registry = LibreTranslateRegistry(cache_ttl=cache_ttl)

    @property
    def name(self) -> str:
        return "libretranslate"

    def translate(self, request: TranslationRequest) -> str:
        """
        Translate text using LibreTranslate API.
        """
        source = request.source_lang
        target = request.target_lang

        # FAST-FAIL: Tarkistetaan varmuuskerros ennen verkon kuormittamista
        if not self.registry.is_pair_supported(source, target):
            raise LanguageNotSupportedError(
                f"LibreTranslate: Kielipari '{source}' -> '{target}' ei ole tuettu (rekisteritarkistus)."
            )

        payload = self.build_request(request)
        
        try:
            result = self._call_api(payload)
            return result
        except LanguageNotSupportedError:
            # Jos _call_api heitti kielivirheen, merkitään pari muistiin ja välitetään virhe eteenpäin
            self.registry.mark_pair_unsupported(source, target)
            raise

    def build_request(self, request: TranslationRequest) -> Dict[str, Any]:
        """Build LibreTranslate API request."""
        payload = {
            "q": request.text,
            "source": request.source_lang,
            "target": request.target_lang,
            "format": "text",
        }

        if self.api_key:
            payload["api_key"] = self.api_key

        return payload

    def _call_api(self, payload: Dict[str, Any]) -> str:
        """Call LibreTranslate API with the built payload."""
        source = payload.get("source", "")
        target = payload.get("target", "")

        try:
            url = f"{self.base_url}/translate"
            request_data = json.dumps(payload).encode("utf-8")

            logger.debug(
                f"LibreTranslate request: {source}->{target} "
                f"(api_key={self._mask_api_key(self.api_key)})"
            )

            req = Request(
                url,
                data=request_data,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": f"SHL-Client/{SHL_VERSION}",
                    "Accept": "application/json",
                },
            )

            with urlopen(req, timeout=LIBRETRANSLATE_TIMEOUT) as response:
                response_data = json.loads(response.read().decode("utf-8"))
                translated = response_data.get("translatedText")

                if translated and translated != payload["q"]:
                    logger.debug(f"LibreTranslate success: '{translated[:100]}...'")
                    return translated

                raise ServiceUnavailableError("LibreTranslate returned empty or unmodified text")

        except HTTPError as e:
            try:
                error_body = e.read().decode("utf-8")
                logger.debug(f"LibreTranslate error details: {error_body}")
            except Exception:
                error_body = ""

            if e.code == 403:
                raise ProviderAccessError("LibreTranslate: Access denied (banned/invalid API key)")
            elif e.code == 429:
                raise RateLimitExceededError("LibreTranslate: Rate limit exceeded")
            elif e.code >= 500:
                raise ServiceUnavailableError(f"LibreTranslate: Server error {e.code}")
            elif e.code == 404:
                raise LanguageNotSupportedError(f"LibreTranslate: Language not supported (HTTP {e.code})")
            elif e.code == 400:
                if "language" in error_body.lower():
                    raise LanguageNotSupportedError(f"LibreTranslate: Language not supported (HTTP {e.code})")
                raise InvalidRequestError(f"LibreTranslate: Bad request {e.code}")
            else:
                raise TranslationError(f"LibreTranslate HTTP {e.code}")

        except URLError as e:
            if isinstance(e.reason, (socket.timeout, TimeoutError)):
                raise ServiceUnavailableError("LibreTranslate timeout")
            raise ServiceUnavailableError(f"LibreTranslate network error: {e.reason}")
            
        except (socket.timeout, TimeoutError):
            raise ServiceUnavailableError("LibreTranslate timeout")
            
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
            raise TranslationError(f"LibreTranslate unexpected error: {type(e).__name__}: {e}")

    @staticmethod
    def _mask_api_key(key: str) -> str:
        """Mask API key for safe logging."""
        if not key:
            return "(not set)"
        if len(key) <= 8:
            return "*" * len(key)
        return key[:4] + "*" * (len(key) - 8) + key[-4:]
