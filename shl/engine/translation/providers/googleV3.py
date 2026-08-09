"""
File: googleV3.py — Google Cloud Translation adapter (Advanced v3, service-account auth).
Author: Tuomas Lähteenmäki
Version: 0.3.0
License: MIT
Description: Translation provider adapter for the Google Cloud Translation Advanced v3 API.
             Includes secondary credentials/endpoint failover mechanism, tracking labels,
             HTML/plain MIME types, glossary configurations, and error mapping.

PARKED — NOT wired into router.py.
Cloud Translation - Advanced (v3) does not accept simple API-key authentication;
it requires OAuth2 via a service account, which this stdlib-only implementation does
not yet provide (the api_key/_call_api path below will fail with 401/403 as written).
Revive this once a dependency decision is made for OAuth2 (e.g. google-auth) or a manual
JWT/Bearer-token flow is implemented. Until then, googleV2.py is the active Google adapter.
"""

import json
import logging
import re
import socket
from typing import Dict, Any, Optional
from urllib.parse import urlencode
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

GOOGLE_TIMEOUT = 15


class GoogleV3Adapter(TranslationProvider):
    """
    Google Cloud Translation adapter (v3 API) with built-in secondary backup failover.

    Supports:
    - Primary and backup project/key configurations
    - Text, source_lang, target_lang (all providers)
    - Labels (for tracking, sanitized from SHL metadata)
    - Glossary
    - HTML format
    """

    def __init__(
        self,
        project_id: str,
        api_key: Optional[str] = None,
        location: str = "global",
        backup_project_id: Optional[str] = None,
        backup_api_key: Optional[str] = None,
        backup_location: Optional[str] = None,
    ):
        if not project_id:
            raise ValueError("Google Cloud project_id cannot be empty")

        self.project_id = project_id
        self.api_key = api_key
        self.location = location

        self.endpoint = (
            f"https://translation.googleapis.com/v3/projects/{self.project_id}"
            f"/locations/{self.location}:translateText"
        )

        self.backup_project_id = backup_project_id or project_id
        self.backup_api_key = backup_api_key or api_key
        self.backup_location = backup_location or location
        self.has_backup = bool(
            backup_project_id or backup_api_key or backup_location
        ) and (
            (self.backup_project_id != self.project_id)
            or (self.backup_api_key != self.api_key)
            or (self.backup_location != self.location)
        )

        if self.has_backup:
            self.backup_endpoint = (
                f"https://translation.googleapis.com/v3/projects/{self.backup_project_id}"
                f"/locations/{self.backup_location}:translateText"
            )

    @property
    def name(self) -> str:
        return "google"

    def translate(self, request: TranslationRequest) -> str:
        payload = self.build_request(request)

        try:
            return self._call_api(
                endpoint=self.endpoint,
                api_key=self.api_key,
                payload=payload,
                is_backup=False,
            )
        except (
            ProviderAccessError,
            RateLimitExceededError,
            ServiceUnavailableError,
        ) as primary_err:
            if not self.has_backup:
                raise primary_err

            logger.warning(
                f"Primary Google Cloud Translation request failed ({type(primary_err).__name__}). "
                f"Initiating failover to backup project ({self.backup_project_id})."
            )

            try:
                return self._call_api(
                    endpoint=self.backup_endpoint,
                    api_key=self.backup_api_key,
                    payload=payload,
                    is_backup=True,
                )
            except Exception as backup_err:
                logger.error(
                    f"Backup Google Cloud Translation also failed: {backup_err}"
                )
                raise primary_err from backup_err

    def build_request(self, request: TranslationRequest) -> Dict[str, Any]:
        payload = {
            "contents": [request.text],
            "targetLanguageCode": request.target_lang,
            "mimeType": "text/html" if request.html_format else "text/plain",
        }

        if request.source_lang:
            payload["sourceLanguageCode"] = request.source_lang

        labels = {}
        for key, val in [
            ("domain", request.domain),
            ("screen", request.screen),
            ("component", request.component),
            ("context_type", request.context_type),
        ]:
            if val:
                sanitized_val = re.sub(r"[^a-z0-9_-]", "_", str(val).lower())[:63]
                if sanitized_val:
                    labels[key] = sanitized_val

        if labels:
            payload["labels"] = labels

        if request.glossary and isinstance(request.glossary, dict):
            glossary_path = request.glossary.get("id") or request.glossary.get("path")
            if glossary_path:
                payload["glossaryConfig"] = {"glossary": glossary_path}

        return payload

    def _call_api(
        self,
        endpoint: str,
        api_key: Optional[str],
        payload: Dict[str, Any],
        is_backup: bool = False,
    ) -> str:
        url = endpoint
        if api_key:
            url += f"?{urlencode({'key': api_key})}"

        request_data = json.dumps(payload).encode("utf-8")
        target_type = "Backup" if is_backup else "Primary"
        logger.debug(f"{target_type} Google Cloud Translation request to {endpoint}")

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": f"SHL-Client/{SHL_VERSION}",
            "Accept": "application/json",
        }

        req = Request(url, data=request_data, headers=headers)

        try:
            with urlopen(req, timeout=GOOGLE_TIMEOUT) as response:
                response_data = json.loads(response.read().decode("utf-8"))

            translations = response_data.get("translations", [])
            if not translations:
                raise TranslationError("Google API returned an empty translations array")

            translated = translations[0].get("translatedText")

            if translated is not None:
                logger.debug(f"{target_type} Google Cloud translation successful")
                return translated

            raise TranslationError("Google Cloud API response missing 'translatedText'")

        except HTTPError as e:
            error_message = ""
            try:
                error_body = json.loads(e.read().decode("utf-8"))
                error_message = error_body.get("error", {}).get("message", "")
            except Exception:
                pass

            if e.code in (401, 403):
                raise ProviderAccessError("Google Cloud: Authentication or permission error") from e
            elif e.code == 429:
                raise RateLimitExceededError("Google Cloud: Quota exceeded") from e
            elif e.code >= 500:
                raise ServiceUnavailableError(f"Google Cloud: Server error {e.code}") from e
            elif e.code == 400:
                if "language" in error_message.lower():
                    raise LanguageNotSupportedError("Google Cloud: Language not supported") from e
                raise InvalidRequestError(f"Google Cloud: Bad request ({e.code}) - {error_message}") from e
            else:
                raise TranslationError(f"Google Cloud HTTP error {e.code}") from e

        except (URLError, socket.timeout, TimeoutError) as e:
            if isinstance(e, URLError) and not isinstance(e.reason, (socket.timeout, TimeoutError)):
                raise ServiceUnavailableError(f"Google Cloud network error: {e.reason}") from e
            raise ServiceUnavailableError("Google Cloud API timeout") from e

        except TranslationError:
            raise
        except Exception as e:
            raise TranslationError(f"Google Cloud unexpected error: {type(e).__name__}: {e}") from e
