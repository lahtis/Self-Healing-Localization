"""
LibreTranslate translation adapter.
"""

import json
import logging
import time
from typing import Optional, Dict, Any
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

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

SHL_VERSION = "0.3.0"
LIBRETRANSLATE_TIMEOUT = 15
LIBRETRANSLATE_DEFAULT_URL = "https://libretranslate.com"
LIBRETRANSLATE_DEFAULT_API_KEY = ""

# Language list cache (24 hours)
_language_cache: dict[str, tuple] = {}
LANGUAGE_CACHE_TTL = 86400


class LibreTranslateAdapter(TranslationProvider):
    """LibreTranslate translation adapter."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.base_url = (base_url or LIBRETRANSLATE_DEFAULT_URL).rstrip("/")
        self.api_key = api_key or LIBRETRANSLATE_DEFAULT_API_KEY

    @property
    def name(self) -> str:
        return "libretranslate"

    def translate(self, request: TranslationRequest) -> str:
        """
        Translate text using LibreTranslate API.

        Uses:
        - request.text -> q
        - request.source_lang -> source
        - request.target_lang -> target
        - (future) request.html_format -> format
        """
        payload = self.build_request(request)
        result = self._call_api(payload)
        return result

    def build_request(self, request: TranslationRequest) -> Dict[str, Any]:
        """Build LibreTranslate API request."""
        payload = {
            "q": request.text,
            "source": request.source_lang,
            "target": request.target_lang,
            "format": "text",  # Default
        }

        # Future: Support HTML format
        # if request.html_format:
        #     payload["format"] = "html"

        if self.api_key:
            payload["api_key"] = self.api_key

        return payload

    def _call_api(self, payload: Dict[str, Any]) -> str:
        """Call LibreTranslate API with the built payload."""
        try:
            url = f"{self.base_url}/translate"
            request_data = json.dumps(payload).encode("utf-8")

            logger.debug(
                f"LibreTranslate request: {payload.get('source')}->{payload.get('target')}"
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

                logger.warning("LibreTranslate returned empty or same text")
                return payload["q"]

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
                raise LanguageNotSupportedError("LibreTranslate: Language not supported")
            elif e.code == 400:
                if "language" in error_body.lower():
                    raise LanguageNotSupportedError("LibreTranslate: Language not supported")
                raise InvalidRequestError(f"LibreTranslate: Bad request {e.code}")
            else:
                raise TranslationError(f"LibreTranslate HTTP {e.code}")

        except URLError as e:
            raise ServiceUnavailableError(f"LibreTranslate network error: {e.reason}")
        except TimeoutError:
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


# ---------------------------------------------------------------------------
# Language list support (separate from translation)
# ---------------------------------------------------------------------------

def get_supported_languages(base_url: Optional[str] = None) -> Dict[str, str]:
    """
    Fetch supported languages from a LibreTranslate instance.
    Results are cached for 24 hours.
    """
    _base_url = (base_url or LIBRETRANSLATE_DEFAULT_URL).rstrip("/")

    cache_key = _base_url

    if cache_key in _language_cache:
        languages, timestamp = _language_cache[cache_key]
        if time.time() - timestamp < LANGUAGE_CACHE_TTL:
            return languages

    try:
        url = f"{_base_url}/languages"
        req = Request(
            url,
            headers={
                "User-Agent": f"SHL-Client/{SHL_VERSION}",
                "Accept": "application/json",
            },
        )

        with urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            languages = {
                lang["code"]: lang["name"]
                for lang in data
                if "code" in lang and "name" in lang
            }

            _language_cache[cache_key] = (languages, time.time())
            logger.info(f"Fetched {len(languages)} supported languages from LibreTranslate")
            return languages

    except Exception as e:
        logger.warning(f"Failed to fetch language list from LibreTranslate: {e}")
        return {}
