"""
MyMemory translation adapter.
"""

import json
import logging
import time
from typing import Optional, Dict, Any
from urllib.request import Request, urlopen
from urllib.parse import quote
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
MYMEMORY_TIMEOUT = 10
MYMEMORY_DEFAULT_EMAIL = ""


class MyMemoryAdapter(TranslationProvider):
    """
    MyMemory translation adapter.

    Supports only basic translation (text + languages).
    All SHL metadata (key, context_type, domain, screen, component, source_id)
    is kept as internal metadata for caching, logging, and future routing.
    """

    def __init__(self, email: Optional[str] = None):
        self.email = email or MYMEMORY_DEFAULT_EMAIL

    @property
    def name(self) -> str:
        return "mymemory"

    def translate(self, request: TranslationRequest) -> str:
        """
        Translate text using MyMemory API.

        Only uses:
        - request.text -> q
        - request.source_lang -> langpair
        - request.target_lang -> langpair

        All other metadata fields are ignored for the API call.
        """
        payload = self.build_request(request)
        result = self._call_api(payload)
        return result

    def build_request(self, request: TranslationRequest) -> Dict[str, Any]:
        """Build MyMemory API request."""
        payload = {
            "q": request.text,
            "langpair": f"{request.source_lang}|{request.target_lang}",
        }
        if self.email:
            payload["de"] = self.email
        return payload

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
                    raise RateLimitExceededError(f"MyMemory: quota reached: {response_warning}")

                if response_status == 403:
                    raise ProviderAccessError("MyMemory: Access denied")
                if response_status == 429:
                    raise RateLimitExceededError("MyMemory: Rate limit exceeded")
                if response_status >= 500:
                    raise ServiceUnavailableError(f"MyMemory: Server error {response_status}")
                if response_status == 404:
                    raise LanguageNotSupportedError("MyMemory: Language not supported")
                if response_status == 400:
                    if "language" in str(response_data).lower():
                        raise LanguageNotSupportedError("MyMemory: Language not supported")
                    raise InvalidRequestError(f"MyMemory: Bad request {response_status}")
                if response_status != 200:
                    raise TranslationError(f"MyMemory: Unexpected status {response_status}")

                translated = response_details.get("translatedText")

                if translated and translated != payload["q"]:
                    logger.debug(f"MyMemory success: '{translated[:100]}...'")
                    return translated

                logger.warning("MyMemory returned empty or same text")
                return payload["q"]

        except HTTPError as e:
            if e.code == 403:
                raise ProviderAccessError("MyMemory HTTP 403")
            elif e.code == 429:
                raise RateLimitExceededError("MyMemory HTTP 429")
            elif e.code >= 500:
                raise ServiceUnavailableError(f"MyMemory HTTP {e.code}")
            elif e.code == 404:
                raise LanguageNotSupportedError("MyMemory language not supported")
            elif e.code == 400:
                try:
                    error_body = e.read().decode("utf-8")
                    if "language" in error_body.lower():
                        raise LanguageNotSupportedError("MyMemory language not supported")
                except Exception:
                    pass
                raise InvalidRequestError("MyMemory HTTP 400")
            else:
                raise TranslationError(f"MyMemory HTTP {e.code}")

        except URLError as e:
            raise ServiceUnavailableError(f"MyMemory network error: {e.reason}")
        except TimeoutError:
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
