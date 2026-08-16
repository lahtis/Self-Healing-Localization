"""
File: papago.py — module for Papago translation adapter.
Author: Tuomas Lähteenmäki
Version: 0.2.4
License: MIT
Description: Robust translation provider adapter for the Naver Papago API.
Handles language pair validation, honorific support, glossary mapping,
registry validation, and security checks for suspicious output.
"""

import json
import logging
import os
import socket
from typing import Dict, Any, Optional, Union
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

logger = logging.getLogger(__name__)

PAPAGO_TIMEOUT = 15
PAPAGO_ENDPOINT = "https://papago.apigw.ntruss.com/nmt/v1/translation"


class PapagoRegistry:
    """
    Lightweight runtime registry for supported Papago language pairs.
    Can be extended later with dynamic discovery if needed.
    """

    # Officially supported pairs (simplified, bidirectional where applicable)
    SUPPORTED_PAIRS = {
        # Korean
        ("ko", "en"), ("en", "ko"),
        ("ko", "ja"), ("ja", "ko"),
        ("ko", "zh-cn"), ("zh-cn", "ko"),
        ("ko", "zh-tw"), ("zh-tw", "ko"),
        ("ko", "vi"), ("vi", "ko"),
        ("ko", "th"), ("th", "ko"),
        ("ko", "id"), ("id", "ko"),
        ("ko", "fr"), ("fr", "ko"),
        ("ko", "es"), ("es", "ko"),
        ("ko", "ru"), ("ru", "ko"),
        ("ko", "de"), ("de", "ko"),
        ("ko", "it"), ("it", "ko"),
        # English
        ("en", "ja"), ("ja", "en"),
        ("en", "zh-cn"), ("zh-cn", "en"),
        ("en", "zh-tw"), ("zh-tw", "en"),
        ("en", "vi"), ("vi", "en"),
        ("en", "th"), ("th", "en"),
        ("en", "id"), ("id", "en"),
        ("en", "fr"), ("fr", "en"),
        ("en", "es"), ("es", "en"),
        ("en", "ru"), ("ru", "en"),
        ("en", "de"), ("de", "en"),
        # Japanese
        ("ja", "zh-cn"), ("zh-cn", "ja"),
        ("ja", "zh-tw"), ("zh-tw", "ja"),
        ("ja", "vi"), ("vi", "ja"),
        ("ja", "th"), ("th", "ja"),
        ("ja", "id"), ("id", "ja"),
        ("ja", "fr"), ("fr", "ja"),
        # Chinese
        ("zh-cn", "zh-tw"), ("zh-tw", "zh-cn"),
    }

    def __init__(self):
        self._unsupported = set()

    def _normalize(self, lang: str) -> str:
        if not lang:
            return ""
        lang = lang.lower().replace("_", "-")
        # Common aliases
        aliases = {
            "zh": "zh-cn",
            "zh-hans": "zh-cn",
            "zh-hant": "zh-tw",
            "jp": "ja",
            "kr": "ko",
        }
        return aliases.get(lang, lang)

    def is_pair_supported(self, source: str, target: str) -> bool:
        source = self._normalize(source)
        target = self._normalize(target)

        if not source or source == "auto":
            # Allow auto-detect
            return True

        pair = (source, target)
        if pair in self._unsupported:
            return False
        return pair in self.SUPPORTED_PAIRS

    def mark_pair_unsupported(self, source: str, target: str) -> None:
        source = self._normalize(source)
        target = self._normalize(target)
        self._unsupported.add((source, target))


class PapagoAdapter(TranslationProvider):
    """
    Papago translation adapter (Naver Cloud).

    Supports:
    - text, source_lang, target_lang
    - honorific (direct bool/str or via formality)
    - glossary (glossaryKey)
    - registry validation
    - security checks
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        # Lataa .env-tiedosto ./env/shl/-kansiosta (jos ei jo ladattu)
        load_shl_env()

        # Käytä annettuja tunnisteita tai lue ympäristömuuttujista
        self.client_id = client_id or os.getenv("NAVER_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("NAVER_CLIENT_SECRET")

        if not self.client_id or not self.client_secret:
            raise ValueError(
                "Papago client_id and client_secret must be provided as parameters or "
                "set as NAVER_CLIENT_ID and NAVER_CLIENT_SECRET in ./.env/shl/.env"
            )

        self.client_id = self.client_id.strip()
        self.client_secret = self.client_secret.strip()
        self.base_url = PAPAGO_ENDPOINT
        self.registry = PapagoRegistry()

        logger.debug(
            f"PapagoAdapter initialized (client_id={mask_api_key(self.client_id)})"
        )

    @property
    def name(self) -> str:
        return "papago"

    @property
    def supported_features(self) -> list:
        return ["honorific", "glossary", "formality"]

    def translate(self, request: TranslationRequest) -> str:
        """Translate text using Papago API."""

        # Pre-validate language pair
        if request.source_lang and request.source_lang.lower() != "auto":
            if not self.registry.is_pair_supported(
                request.source_lang,
                request.target_lang,
            ):
                raise LanguageNotSupportedError(
                    f"Papago does not support language pair "
                    f"{request.source_lang}->{request.target_lang}"
                )

        payload = self.build_request(request)
        return self._call_api(payload, request)

    def build_request(self, request: TranslationRequest) -> Dict[str, Any]:
        """Build Papago API JSON payload."""
        source = (request.source_lang or "auto").lower()
        target = request.target_lang.lower()

        # Normalize common codes
        source = self.registry._normalize(source)
        target = self.registry._normalize(target)

        payload: Dict[str, Any] = {
            "source": source,
            "target": target,
            "text": request.text,
        }

        # --- Honorific support ---
        # Priority:
        # 1. Explicit request.honorific (bool or str)
        # 2. Fallback to request.formality
        honorific_value = None

        # 1. Direct honorific field (recommended)
        if hasattr(request, "honorific") and request.honorific is not None:
            if isinstance(request.honorific, bool):
                honorific_value = "true" if request.honorific else "false"
            elif isinstance(request.honorific, str):
                val = request.honorific.lower().strip()
                if val in ("true", "1", "yes", "formal", "more", "polite", "honorific"):
                    honorific_value = "true"
                else:
                    honorific_value = "false"

        # 2. Fallback from formality (compatibility with DeepL-style usage)
        elif getattr(request, "formality", None):
            formality = str(request.formality).lower()
            if formality in ("formal", "more", "honorific", "polite"):
                honorific_value = "true"
            elif formality in ("informal", "less", "casual"):
                honorific_value = "false"

        if honorific_value is not None:
            payload["honorific"] = honorific_value

        # Glossary support
        if request.glossary and "id" in request.glossary:
            payload["glossaryKey"] = request.glossary["id"]

        return payload

    def _call_api(self, payload: Dict[str, Any], request: TranslationRequest) -> str:
        """Execute request against Papago API endpoint."""
        try:
            url = self.base_url
            request_data = json.dumps(payload).encode("utf-8")

            logger.debug(
                f"Papago request to {url} (client_id={mask_api_key(self.client_id)}, "
                f"text length: {len(payload['text'])})"
            )

            req = Request(
                url,
                data=request_data,
                headers={
                    "X-NCP-APIGW-API-KEY-ID": self.client_id,
                    "X-NCP-APIGW-API-KEY": self.client_secret,
                    "Content-Type": "application/json",
                    "User-Agent": f"SHL-Client/{SHL_VERSION}",
                    "Accept": "application/json",
                },
                method="POST",
            )

            with urlopen(req, timeout=PAPAGO_TIMEOUT) as response:
                response_data = json.loads(response.read().decode("utf-8"))

                # Papago response structure
                message = response_data.get("message", {})
                result = message.get("result", {})
                translated = result.get("translatedText")
                detected = result.get("srcLangType", "").lower()

                if not translated:
                    raise TranslationError(
                        "Papago returned an empty translation payload"
                    )

                # --- SECURITY CHECKS ---

                # 1. Empty or unchanged output
                if not translated or translated.strip() == "":
                    raise TranslationError("Papago returned empty text.")

                if translated.strip() == payload["text"].strip():
                    raise TranslationError("Papago returned unchanged text.")

                # 2. Unexpected detected source language
                if request.source_lang and request.source_lang.lower() != "auto":
                    expected = self.registry._normalize(request.source_lang)
                    if detected and detected != expected:
                        logger.warning(
                            f"Papago detected '{detected}' but request declared "
                            f"'{request.source_lang}'"
                        )

                # 3. Unexpected HTML markup
                if not getattr(request, "html_format", False):
                    if "<" in translated and ">" in translated:
                        raise TranslationError(
                            "Papago returned unexpected HTML markup."
                        )

                # 4. Suspiciously short output
                if len(translated) < 3 and len(payload["text"]) > 20:
                    raise TranslationError(
                        "Papago returned suspiciously short output."
                    )

                logger.debug("Papago translation successful")
                return translated

        except HTTPError as e:
            code = e.code
            try:
                error_body = e.read().decode("utf-8")
            except Exception:
                error_body = ""

            # Authentication / Authorization
            if code in (401, 403):
                raise ProviderAccessError(
                    "Papago: Invalid or unauthorized API credentials (Client ID / Secret)"
                )

            # Rate limiting / Quota
            if code == 429:
                raise RateLimitExceededError(
                    "Papago: Rate limit or quota exceeded (HTTP 429)"
                )

            # Bad request
            if code == 400:
                if request.source_lang:
                    self.registry.mark_pair_unsupported(
                        request.source_lang,
                        request.target_lang,
                    )
                raise InvalidRequestError(
                    f"Papago: Invalid request parameters (HTTP 400). Body: {error_body[:200]}"
                )

            # Server / Gateway issues
            if code in (500, 502, 503, 504):
                raise ServiceUnavailableError(
                    f"Papago: Remote endpoint or gateway issue (HTTP {code})"
                )

            raise TranslationError(
                f"Papago HTTP error status code: {code}. Body: {error_body[:200]}"
            )

        except URLError as e:
            if isinstance(e.reason, (socket.timeout, TimeoutError)):
                raise ServiceUnavailableError("Papago network timeout reached")
            raise ServiceUnavailableError(
                f"Papago socket pipeline failure: {e.reason}"
            )

        except (socket.timeout, TimeoutError):
            raise ServiceUnavailableError("Papago connection timeout reached")

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
                f"Papago unexpected execution layer failure: "
                f"{type(e).__name__}: {e}"
            )
