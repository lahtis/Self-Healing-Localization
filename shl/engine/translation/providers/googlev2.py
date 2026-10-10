"""
File: shl/engine/translation/providers/googlev2.py
Author: Tuomas Lähteenmäki
Version: 0.3.0
License: MIT
Description: Translation provider adapter for the Google Cloud
Translation Basic (v2) API. Dependency-free (stdlib urllib only).
Includes secondary API key failover, plain/HTML format support,
error mapping, registry validation, and security checks for
suspicious output.

All outbound HTTP goes through safe_urlopen for SSRF prevention,
redirect validation, and response size limits.
"""

import json
import logging
from typing import Any, NoReturn
from urllib.parse import urlencode
from urllib.request import Request

from shl.utils.safe_http import safe_urlopen as urlopen
from shl.utils.safe_http_common import (
    MAX_RESPONSE_BYTES,
    SafeHTTPError,
    read_limited_response,
)

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
GOOGLE_V2_ENDPOINT = (
    "https://translation.googleapis.com/language/translate/v2"
)


class GoogleV2Adapter(TranslationProvider):
    """Google Cloud Translation Basic (v2) adapter.

    Includes built-in secondary API key failover: if the primary key
    fails with an access, rate limit, or service error, the adapter
    retries with the backup key (if configured).
    """

    def __init__(
        self,
        api_key: str | None = None,
        backup_api_key: str | None = None,
    ):
        self.api_key = api_key or get_env_value("GOOGLE_API_KEY")
        self.backup_api_key = (
            backup_api_key
            or get_env_value("GOOGLE_BACKUP_API_KEY")
        )

        if not self.api_key:
            raise ValueError(
                "Google Cloud Translation API key must be provided as "
                "parameter or set as GOOGLE_API_KEY in ./.env/shl/.env"
            )

        self.api_key = self.api_key.strip()

        if self.backup_api_key:
            self.backup_api_key = self.backup_api_key.strip()

        self.has_backup = (
            bool(self.backup_api_key)
            and self.backup_api_key != self.api_key
        )

        # Runtime language pair registry (validation + learning).
        self.registry = GoogleRegistry()

        # Provider-independent error parser.
        self.error_parser = ErrorParser(
            provider=self.name,
            config=GOOGLE,
        )

        logger.debug(
            "GoogleV2Adapter initialized (api_key=%s, has_backup=%s)",
            mask_api_key(self.api_key),
            self.has_backup,
        )

    @property
    def name(self) -> str:
        return "google"

    @property
    def supported_features(self) -> list[str]:
        return ["html_format"]

    def translate(self, request: TranslationRequest) -> str:
        """Translate text using Google Cloud Translation Basic v2 API.

        Attempts the primary key first, and falls back to a backup key
        on failure.
        """

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
                "Primary Google Cloud Translation request failed (%s). "
                "Initiating failover to backup API key.",
                type(primary_err).__name__,
            )

            try:
                return self._call_api(
                    api_key=self.backup_api_key,
                    payload=payload,
                    is_backup=True,
                )

            except Exception as backup_err:
                logger.error(
                    "Backup Google Cloud Translation also failed: %s",
                    backup_err,
                )
                raise primary_err from backup_err

    def build_request(
        self,
        request: TranslationRequest,
    ) -> dict[str, Any]:
        """Build Google Cloud Translation Basic (v2) API JSON payload."""

        # Explicit annotation is required because the payload holds
        # heterogeneous value types (list, str). Without it, mypy
        # narrows the inferred type based on the first entry.
        payload: dict[str, Any] = {
            "q": [request.text],
            "target": request.target_lang,
            "format": "html" if request.html_format else "text",
        }

        if request.source_lang:
            payload["source"] = request.source_lang

        return payload

    def _raise_normalized_error(self, error) -> NoReturn:
        """Convert a normalized SHL error into the adapter's exception
        hierarchy. Always raises.
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
        payload: dict[str, Any],
        is_backup: bool = False,
    ) -> str:
        """Low-level HTTP call executor."""

        url = (
            f"{GOOGLE_V2_ENDPOINT}?"
            f"{urlencode({'key': api_key})}"
        )

        request_data = json.dumps(payload).encode("utf-8")
        target_type = "Backup" if is_backup else "Primary"

        logger.debug(
            "%s Google translation request (api_key=%s)",
            target_type,
            mask_api_key(api_key),
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

            with urlopen(req, timeout=GOOGLE_TIMEOUT) as response:
                raw = read_limited_response(
                    response,
                    MAX_RESPONSE_BYTES,
                )
                raw_response = raw.decode("utf-8")
                status_code = response.status

            try:
                response_data = json.loads(raw_response)
            except json.JSONDecodeError:
                error = self.error_parser.parse(
                    raw_response,
                    http_status=status_code,
                )
                self._raise_normalized_error(error)

            if not isinstance(response_data, dict):
                error = self.error_parser.parse(
                    raw_response,
                    http_status=status_code,
                )
                self._raise_normalized_error(error)

            if "error" in response_data:
                error = self.error_parser.parse(
                    response_data,
                    http_status=status_code,
                )
                self._raise_normalized_error(error)

            translations = (
                response_data.get("data", {})
                .get("translations", [])
            )

            if not translations:
                raise TranslationError(
                    "Google Translate returned empty translations "
                    "payload"
                )

            translated = translations[0].get("translatedText", "")

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
                        "Google Translate returned unexpected HTML "
                        "markup."
                    )

            # 4. Suspiciously short output
            if len(translated) < 3 and len(payload["q"][0]) > 20:
                raise TranslationError(
                    "Google Translate returned suspiciously short "
                    "output."
                )

            logger.debug("Google Translate success")
            return translated

        # safe_urlopen converts urllib's HTTPError and URLError into
        # SafeHTTPError before they leave the safe layer, so those two
        # exception types no longer need to be handled here.
        except SafeHTTPError as e:
            error = self.error_parser.parse(exception=e)
            self._raise_normalized_error(error)

        except TimeoutError as e:
            error = self.error_parser.parse(exception=e)
            self._raise_normalized_error(error)

        except OSError as e:
            error = self.error_parser.parse(exception=e)
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
            error = self.error_parser.parse(exception=e)
            self._raise_normalized_error(error)
