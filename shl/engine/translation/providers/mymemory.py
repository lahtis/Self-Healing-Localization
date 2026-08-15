"""
MyMemory translation adapter.
"""

import os
import json
import logging
import socket
from typing import Dict, Any
from urllib.request import Request, urlopen
from urllib.parse import quote
from urllib.error import URLError, HTTPError

from shl._version import __version__ as SHL_VERSION
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
MYMEMORY_DEFAULT_EMAIL = os.getenv("MYMEMORY_EMAIL", "")

# Shared registry instance
_registry = MyMemoryRegistry()


class MyMemoryAdapter(TranslationProvider):
    """
    MyMemory translation adapter.
    """

    def __init__(self, email: str | None = None, cache_ttl: float | None = None):
        self.email = email or MYMEMORY_DEFAULT_EMAIL

        if cache_ttl is not None:
            _registry.cache_ttl = cache_ttl

    @property
    def name(self) -> str:
        return "mymemory"

    def translate(self, request: TranslationRequest) -> str:
        """
        Translate text using MyMemory API.
        """

        src = (request.source_lang or "").lower().strip()
        tgt = request.target_lang.lower().strip()

        # Fast-fail using registry
        if not _registry.is_pair_supported(src, tgt):
            raise LanguageNotSupportedError(
                f"MyMemory: Kielipari '{src}|{tgt}' ei ole tuettu tai se on väliaikaisesti estetty."
            )

        payload = self.build_request(request)

        try:
            return self._call_api(payload)
        except LanguageNotSupportedError:
            _registry.mark_pair_unsupported(src, tgt)
            raise

    def build_request(self, request: TranslationRequest) -> Dict[str, Any]:
        """Build MyMemory API request."""
        src = (request.source_lang or "").lower().strip()
        tgt = request.target_lang.lower().strip()

        payload = {
            "q": request.text,
            "langpair": f"{src}|{tgt}",
        }

        if self.email:
            payload["de"] = self.email

        return payload

    def _call_api(self, payload: Dict[str, Any]) -> str:
        """Call MyMemory API with the built payload."""
        try:
            url = (
                f"https://api.mymemory.translated.net/get?"
                f"q={quote(payload['q'])}&langpair={payload['langpair']}"
            )

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

                # --- QUOTA / RATE LIMIT ---
                if quota_reached or "quota" in response_warning.lower():
                    raise RateLimitExceededError(
                        f"MyMemory: Quota reached: {response_warning}"
                    )

                # --- STATUS HANDLING ---
                if response_status == 403:
                    raise ProviderAccessError("MyMemory: Access denied")
                if response_status == 429:
                    raise RateLimitExceededError("MyMemory: Rate limit exceeded")
                if response_status >= 500:
                    raise ServiceUnavailableError(f"MyMemory: Server error {response_status}")
                if response_status == 404:
                    raise LanguageNotSupportedError("MyMemory: Language not supported")
                if response_status == 400:
                    body = json.dumps(response_data).lower()
                    if "language" in body or "invalid" in body:
                        raise LanguageNotSupportedError("MyMemory: Language not supported")
                    raise InvalidRequestError(f"MyMemory: Bad request {response_status}")
                if response_status != 200:
                    raise TranslationError(f"MyMemory: Unexpected status {response_status}")

                translated = response_details.get("translatedText")
                match_quality = float(response_details.get("match", 0))

                # --- SECURITY CHECKS ---

                # 1. Empty or unchanged
                if not translated or translated.strip() == "":
                    raise TranslationError("MyMemory returned empty text.")

                if translated.strip() == payload["q"].strip():
                    raise TranslationError("MyMemory returned unchanged text.")

                # 2. Weak match quality
                if match_quality < 0.1:
                    raise TranslationError(
                        f"MyMemory returned suspiciously weak match quality ({match_quality})."
                    )

                # 3. Suspiciously short output
                if len(translated) < 3 and len(payload["q"]) > 20:
                    raise TranslationError("MyMemory returned suspiciously short output.")

                logger.debug(f"MyMemory success: '{translated[:100]}...'")
                return translated

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
                    body = e.read().decode("utf-8").lower()
                    if "language" in body or "invalid" in body:
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

