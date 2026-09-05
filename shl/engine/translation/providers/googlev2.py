"""
File: googlev2.py — Google Cloud Translation adapter (Basic v2, API-key auth).
Author: Tuomas Lähteenmäki
Version: 0.2.10
License: MIT
Description: Translation provider adapter for the Google Cloud Translation Basic (v2) API.
             Dependency-free (stdlib urllib only). Includes secondary API key failover,
             plain/HTML format support, error mapping, registry validation, and security
             checks for suspicious output.
"""

import json
import logging
import socket
from typing import Dict, Any, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from shl._version import __version__ as SHL_VERSION
from shl.utils.env_loader import get_env_value, mask_api_key
from ..exceptions import (
    TranslationError,
    ServiceUnavailableError,
    RateLimitExceededError,
    LanguageNotSupportedError,
    ProviderAccessError,
    InvalidRequestError,
)
from ..metadata import TranslationRequest
from ...errors.parser import ErrorParser
from ...errors.providers import GOOGLE
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
        api_key: Optional[str] = None,
        backup_api_key: Optional[str] = None,
    ):
        # Use provided keys or read from environment variables
        self.api_key = api_key or get_env_value("GOOGLE_API_KEY")
        self.backup_api_key = (
            backup_api_key
            or get_env_value("GOOGLE_BACKUP_API_KEY")
        )

        if not self.api_key:
            raise ValueError(
                "Google Cloud Translation API key must be provided as parameter or "
                "set as GOOGLE_API_KEY in ./.env/shl/.env"
            )

        self.api_key = self.api_key.strip()

        if self.backup_api_key:
            self.backup_api_key = self.backup_api_key.strip()

        self.has_backup = (
            bool(self.backup_api_key)
            and self.backup_api_key != self.api_key
        )

        # Runtime language pair registry (validation + learning)
        self.registry = GoogleRegistry()

        # Provider-independent error parser
        self.error_parser = ErrorParser(
            provider=self.name,
            config=GOOGLE,
        )

        logger.debug(
            f"GoogleV2Adapter initialized "
            f"(api_key={mask_api_key(self.api_key)}, "
            f"has_backup={self.has_backup})"
        )

    @property
    def name(self) -> str:
        return "google"

    @property
    def supported_features(self) -> list:
        return ["html_format"]

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
            return self._call_api(
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
                f"Primary Google Cloud Translation request failed "
                f"({type(primary_err).__name__}). "
                "Initiating failover to backup API key."
            )

            try:
                return self._call_api(
                    api_key=self.backup_api_key,
                    payload=payload,
                    is_backup=True,
                )

            except Exception as backup_err:
                logger.error(
                    f"Backup Google Cloud Translation also failed: "
                    f"{backup_err}"
                )
                raise primary_err from backup_err

    def build_request(
        self,
        request: TranslationRequest,
    ) -> Dict[str, Any]:
        """Build Google Cloud Translation Basic (v2) API JSON payload."""
        payload: Dict[str, Any] = {
            "q": [request.text],
            "target": request.target_lang,
            "format": "html" if request.html_format else "text",
        }

        if request.source_lang:
            payload["source"] = request.source_lang

        return payload

    def _raise_normalized_error(self, error) -> None:
        """
        Convert a normalized SHL error into the existing adapter
        exception hierarchy.
        """

        message = error.message or (
            f"Google Translate request failed: {error.code}"
        )

        if error.code == "RATE_LIMIT_EXCEEDED":
            raise RateLimitExceededError(message)

        if error.code == "QUOTA_EXCEEDED":
            raise RateLimitExceededError(message)

        if error.code in {
            "TIMEOUT",
            "SERVICE_UNAVAILABLE",
        }:
            raise ServiceUnavailableError(message)

        if error.code in {
            "AUTH_FAILED",
            "AUTH_EXPIRED",
            "AUTH_BLOCKED",
            "ACCESS_DENIED",
        }:
            raise ProviderAccessError(message)

        if error.code in {
            "LANG_UNSUPPORTED",
            "LANG_PAIR_UNSUPPORTED",
        }:
            raise LanguageNotSupportedError(message)

        if error.code in {
            "INVALID_REQUEST",
            "TEXT_TOO_LONG",
            "REQUEST_TOO_LONG",
            "METHOD_NOT_ALLOWED",
        }:
            raise InvalidRequestError(message)

        raise TranslationError(message)

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

        logger.debug(
            f"{target_type} Google translation request "
            f"(api_key={mask_api_key(api_key)})"
        )

        try:
            req = Request(
                url,
                data=request_data,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": f"SHL-Client/{SHL_VERSION}",
                    "Accept": "application/json",
                },
                method="POST",
            )

            with urlopen(
                req,
                timeout=GOOGLE_TIMEOUT,
            ) as response:

                raw_response = response.read().decode("utf-8")

                try:
                    response_data = json.loads(raw_response)
                except json.JSONDecodeError:
                    error = self.error_parser.parse(
                        raw_response,
                        http_status=response.status,
                    )
                    self._raise_normalized_error(error)

                if not isinstance(response_data, dict):
                    error = self.error_parser.parse(
                        raw_response,
                        http_status=response.status,
                    )
                    self._raise_normalized_error(error)

                if "error" in response_data:
                    error = self.error_parser.parse(
                        response_data,
                        http_status=response.status,
                    )
                    self._raise_normalized_error(error)

                translations = response_data.get(
                    "data",
                    {},
                ).get(
                    "translations",
                    [],
                )

                if not translations:
                    raise TranslationError(
                        "Google Translate returned empty "
                        "translations payload"
                    )

                translated = translations[0].get(
                    "translatedText",
                    "",
                )

                detected = translations[0].get(
                    "detectedSourceLanguage",
                    "",
                ).lower()

                # --- SECURITY CHECK: Google output validation ---

                # 1. Empty or unchanged output
                if not translated or translated.strip() == "":
                    raise TranslationError(
                        "Google Translate returned empty text."
                    )

                if translated.strip() == payload["q"][0].strip():
                    raise TranslationError(
                        "Google Translate returned unchanged text."
                    )

                # 2. Unexpected detected source language
                if "source" in payload:
                    declared = payload["source"].lower()

                    if detected and detected != declared:
                        raise TranslationError(
                            f"Google detected unexpected source language "
                            f"'{detected}' for input declared as "
                            f"'{declared}'."
                        )

                # 3. Unexpected HTML markup
                if payload["format"] == "text":
                    if "<" in translated and ">" in translated:
                        raise TranslationError(
                            "Google Translate returned unexpected "
                            "HTML markup."
                        )

                # 4. Suspiciously short output
                if len(translated) < 3 and len(payload["q"][0]) > 20:
                    raise TranslationError(
                        "Google Translate returned suspiciously "
                        "short output."
                    )

                logger.debug("Google Translate success")
                return translated

        except HTTPError as e:
            response_data = None

            try:
                raw_body = e.read().decode("utf-8")

                if raw_body:
                    response_data = json.loads(raw_body)

            except (UnicodeDecodeError, json.JSONDecodeError):
                response_data = None

            if response_data is None:
                response_data = {}

            error = self.error_parser.parse(
                response_data,
                http_status=e.code,
            )

            self._raise_normalized_error(error)

        except URLError as e:
            if isinstance(
                e.reason,
                (socket.timeout, TimeoutError),
            ):
                error = self.error_parser.parse(
                    {},
                    exception=TimeoutError(
                        "Google Translate network timeout reached"
                    ),
                )
            else:
                error = self.error_parser.parse(
                    {},
                    exception=ConnectionError(
                        f"Google Translate socket failure: {e.reason}"
                    ),
                )

            self._raise_normalized_error(error)

        except (socket.timeout, TimeoutError) as e:
            error = self.error_parser.parse(
                {},
                exception=e,
            )
            self._raise_normalized_error(error)

        except (
            RateLimitExceededError,
            ServiceUnavailableError,
            LanguageNotSupportedError,
            ProviderAccessError,
            InvalidRequestError,
            TranslationError,
        ):
            raise

        except Exception as e:
            error = self.error_parser.parse(
                {},
                exception=e,
            )
            self._raise_normalized_error(error)
