"""
File: googlev2.py — Google Cloud Translation adapter (Basic v2, API-key auth).
Author: Tuomas Lähteenmäki
Version: 0.2.4
License: MIT
Description: Translation provider adapter for the Google Cloud Translation Basic (v2) API.
             Dependency-free (stdlib urllib only). Includes secondary API key failover,
             plain/HTML format support, error mapping, registry validation, and security
             checks for suspicious output.
"""

import json
import logging
import socket
from typing import Dict, Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
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
from .google_registry import GoogleRegistry

logger = logging.getLogger(__name__)

GOOGLE_TIMEOUT = 15
GOOGLE_V2_ENDPOINT = "https://translation.googleapis.com/language/translate/v2"


class GoogleV2Adapter(TranslationProvider):
    """
    Google Cloud Translation Basic (v2) adapter with built-in secondary API key failover.
    """

    def __init__(
        self,
        api_key: str,
        backup_api_key: str = None,
    ):
        if not api_key:
            raise ValueError("Google Cloud Translation API key cannot be empty")

        self.api_key = api_key.strip()
        self.backup_api_key = backup_api_key.strip() if backup_api_key else None
        self.has_backup = bool(self.backup_api_key) and self.backup_api_key != self.api_key

        # Runtime language pair registry (validation + learning)
        self.registry = GoogleRegistry()

    @property
    def name(self) -> str:
        return "google"

    def translate(self, request: TranslationRequest) -> str:
        """
        Translate text using Google Cloud Translation Basic v2 API.
        Attempts the primary key first, and falls back to a backup key on failure.
        """

        # Pre-validate language pair using registry
        if request.source_lang:
            if not self.registry.is_pair_supported(
                request.source_lang,
                request.target_lang,
            ):
                raise LanguageNotSupportedError(
                    f"Google Translate does not support language pair "
                    f"{request.source_lang}->{request.target_lang}"
                )

        payload = self.build_request(request)

        try:
            return self._call_api(api_key=self.api_key, payload=payload, is_backup=False)
        except (
            ProviderAccessError,
            RateLimitExceededError,
            ServiceUnavailableError,
        ) as primary_err:

            if not self.has_backup:
                raise primary_err

            logger.warning(
                f"Primary Google Cloud Translation request failed ({type(primary_err).__name__}). "
                "Initiating failover to backup API key."
            )

            try:
                return self._call_api(api_key=self.backup_api_key, payload=payload, is_backup=True)
            except Exception as backup_err:
                logger.error(f"Backup Google Cloud Translation also failed: {backup_err}")
                raise primary_err from backup_err

    def build_request(self, request: TranslationRequest) -> Dict[str, Any]:
        """Build Google Cloud Translation Basic (v2) API JSON payload."""
        payload: Dict[str, Any] = {
            "q": [request.text],
            "target": request.target_lang,
            "format": "html" if request.html_format else "text",
        }

        if request.source_lang:
            payload["source"] = request.source_lang

        return payload

    def _call_api(
        self,
        api_key: str,
        payload: Dict[str, Any],
        is_backup: bool = False,
    ) -> str:
        """Low-level HTTP call executor via urllib."""
        url = f"{GOOGLE_V2_ENDPOINT}?{urlencode({'key': api_key})}"

        request_data = json.dumps(payload).encode("utf-8")
        target_type = "Backup" if is_backup else "Primary"
        logger.debug(f"{target_type} Google translation request")

        try:
            req = Request(
                url,
                data=request_data,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": f"SHL-Client/{SHL_VERSION}",
                    "Accept": "application/json",
                },
            )

            with urlopen(req, timeout=GOOGLE_TIMEOUT) as response:
                response_data = json.loads(response.read().decode("utf-8"))

                if "error" in response_data:
                    return self._handle_api_error(response_data["error"], payload)

                translations = response_data.get("data", {}).get("translations", [])
                if not translations:
                    raise TranslationError("Google Translate returned empty translations payload")

                translated = translations[0].get("translatedText", "")
                detected = translations[0].get("detectedSourceLanguage", "").lower()

                # --- SECURITY CHECK: Google output validation ---

                # 1. Empty or unchanged output
                if not translated or translated.strip() == "":
                    raise TranslationError("Google Translate returned empty text.")

                if translated.strip() == payload["q"][0].strip():
                    raise TranslationError("Google Translate returned unchanged text.")

                # 2. Unexpected detected source language
                if "source" in payload:
                    declared = payload["source"].lower()
                    if detected and detected != declared:
                        raise TranslationError(
                            f"Google detected unexpected source language '{detected}' "
                            f"for input declared as '{declared}'."
                        )

                # 3. Unexpected HTML markup
                if payload["format"] == "text":
                    if "<" in translated and ">" in translated:
                        raise TranslationError("Google Translate returned unexpected HTML markup.")

                # 4. Suspiciously short output
                if len(translated) < 3 and len(payload["q"][0]) > 20:
                    raise TranslationError("Google Translate returned suspiciously short output.")

                logger.debug("Google Translate success")
                return translated

        except HTTPError as e:
            code = e.code

            # Access / auth
            if code in (401, 403):
                raise ProviderAccessError("Google Translate: Unauthorized or forbidden API key")

            # Rate limits
            elif code == 429:
                raise RateLimitExceededError("Google Translate: Rate limit exceeded (HTTP 429)")

            # Request errors
            elif code == 400:
                self._mark_unsupported_if_needed(payload)
                raise InvalidRequestError("Google Translate: Invalid request (HTTP 400)")

            elif code in (409, 413, 415, 422):
                self._mark_unsupported_if_needed(payload)
                raise InvalidRequestError(f"Google Translate: Request not acceptable ({code})")

            # Server errors
            elif code in (500, 502, 503, 504):
                raise ServiceUnavailableError(f"Google Translate: Server or gateway error ({code})")

            else:
                raise TranslationError(f"Google Translate HTTP error: {code}")

        except URLError as e:
            if isinstance(e.reason, (socket.timeout, TimeoutError)):
                raise ServiceUnavailableError("Google Translate network timeout reached")
            raise ServiceUnavailableError(f"Google Translate socket failure: {e.reason}")

        except (socket.timeout, TimeoutError):
            raise ServiceUnavailableError("Google Translate connection timeout reached")

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
                f"Google Translate unexpected execution layer failure: "
                f"{type(e).__name__}: {e}"
            )

    # --- INTERNAL HELPERS -----------------------------------------------------

    def _handle_api_error(self, error: Dict[str, Any], payload: Dict[str, Any]) -> str:
        """Handle Google API error JSON structure."""
        code = error.get("code", 0)
        message = error.get("message", "Unknown Google API error")

        if code in (401, 403):
            raise ProviderAccessError(message)

        elif code == 429:
            raise RateLimitExceededError(message)

        elif code == 400:
            self._mark_unsupported_if_needed(payload)
            raise InvalidRequestError(message)

        elif code in (409, 413, 415, 422):
            self._mark_unsupported_if_needed(payload)
            raise InvalidRequestError(message)

        elif code in (500, 502, 503, 504):
            raise ServiceUnavailableError(message)

        raise TranslationError(message)

    def _mark_unsupported_if_needed(self, payload: Dict[str, Any]) -> None:
        """Mark language pair unsupported if source language is explicitly declared."""
        if "source" in payload:
            self.registry.mark_pair_unsupported(
                payload["source"],
                payload["target"],
            )

