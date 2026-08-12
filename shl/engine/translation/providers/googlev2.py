"""
File: googlev2.py — Google Cloud Translation adapter (Basic v2, API-key auth).
Author: Tuomas Lähteenmäki
Version: 0.2.0
License: MIT
Description: Translation provider adapter for the Google Cloud Translation Basic (v2) API.
             Dependency-free (stdlib urllib only). Includes secondary API key failover,
             plain/HTML format support, and error mapping. Does not require a GCP project ID
             or service account — Basic API is authenticated purely via API key.
             Currently the active Google adapter wired into router.py.
"""

import json
import logging
import socket
from typing import Dict, Any, Optional
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

logger = logging.getLogger(__name__)

GOOGLE_TIMEOUT = 15
GOOGLE_V2_ENDPOINT = "https://translation.googleapis.com/language/translate/v2"


class GoogleV2Adapter(TranslationProvider):
    """
    Google Cloud Translation Basic (v2) adapter with built-in secondary API key failover.

    Cloud Translation - Advanced (v3) does not support API-key authentication and
    requires OAuth2 service account credentials, which would pull in an extra
    dependency and break this package's dependency-free design. Basic (v2) supports
    simple API-key auth and needs no GCP project ID, so it is used here instead.
    See googleV3.py for the parked Advanced-API implementation.
    """

    def __init__(
        self,
        api_key: str,
        backup_api_key: Optional[str] = None,
    ):
        if not api_key:
            raise ValueError("Google Cloud Translation API key cannot be empty")

        self.api_key = api_key
        self.backup_api_key = backup_api_key
        self.has_backup = bool(backup_api_key) and backup_api_key != api_key

    @property
    def name(self) -> str:
        return "google"

    def translate(self, request: TranslationRequest) -> str:
        """
        Translate text using Google Cloud Translation Basic v2 API.
        Attempts the primary key first, and falls back to a backup key on failure.
        """
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

        # Huom: v2 Basic ei tue labels- tai glossaryConfig-kenttiä (Advanced/v3-ominaisuuksia).
        # Jos TranslationRequest sisältää glossary-metadataa, se jätetään tässä huomiotta.

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
