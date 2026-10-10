"""
File: shl/engine/translation/providers/googlev3.py
Author: Tuomas Lähteenmäki
Version: 0.3.0
License: MIT
Description: Translation provider adapter for the Google Cloud
Translation Advanced v3 API. Includes secondary credentials/endpoint
failover, tracking labels, HTML/plain MIME types, glossary
configurations, and error mapping.

All outbound HTTP goes through safe_urlopen for SSRF prevention,
redirect validation, and response size limits.

PARKED — NOT wired into router.py.
Cloud Translation - Advanced (v3) does not accept simple API-key
authentication; it requires OAuth2 via a service account, which this
stdlib-only implementation does not yet provide (the api_key path
below will fail with 401/403 as written). Revive this once a
dependency decision is made for OAuth2 (e.g. google-auth) or a
manual JWT/Bearer-token flow is implemented. Until then, googlev2.py
is the active Google adapter.
"""

import json
import logging
import re
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
    """Google Cloud Translation adapter (v3 API) with failover.

    Supports:
    - Primary and backup project/key configurations
    - Text, source_lang, target_lang
    - Labels (for tracking, sanitized from SHL metadata)
    - Glossary
    - HTML format

    Parked: requires OAuth2 service-account auth, not yet implemented.
    """

    def __init__(
        self,
        project_id: str,
        api_key: str | None = None,
        location: str = "global",
        backup_project_id: str | None = None,
        backup_api_key: str | None = None,
        backup_location: str | None = None,
    ):
        if not project_id:
            raise ValueError("Google Cloud project_id cannot be empty")

        self.project_id = project_id
        self.api_key = api_key
        self.location = location

        self.endpoint = (
            f"https://translation.googleapis.com/v3/projects/"
            f"{self.project_id}/locations/{self.location}:translateText"
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
                f"https://translation.googleapis.com/v3/projects/"
                f"{self.backup_project_id}/locations/"
                f"{self.backup_location}:translateText"
            )

    @property
    def name(self) -> str:
        return "google"

    def translate(self, request: TranslationRequest) -> str:
        """Translate text using Google Cloud Translation v3 API."""

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
                "Primary Google Cloud Translation request failed (%s). "
                "Initiating failover to backup project (%s).",
                type(primary_err).__name__,
                self.backup_project_id,
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
                    "Backup Google Cloud Translation also failed: %s",
                    backup_err,
                )
                raise primary_err from backup_err

    def build_request(
        self,
        request: TranslationRequest,
    ) -> dict[str, Any]:
        """Build Google Cloud Translation v3 API JSON payload."""

        # Explicit annotation is required because the payload holds
        # heterogeneous value types (list, str, dict).
        payload: dict[str, Any] = {
            "contents": [request.text],
            "targetLanguageCode": request.target_lang,
            "mimeType": (
                "text/html" if request.html_format else "text/plain"
            ),
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
                sanitized_val = re.sub(
                    r"[^a-z0-9_-]",
                    "_",
                    str(val).lower(),
                )[:63]

                if sanitized_val:
                    labels[key] = sanitized_val

        if labels:
            payload["labels"] = labels

        if request.glossary and isinstance(request.glossary, dict):
            glossary_path = (
                request.glossary.get("id")
                or request.glossary.get("path")
            )

            if glossary_path:
                payload["glossaryConfig"] = {
                    "glossary": glossary_path
                }

        return payload

    def _call_api(
        self,
        endpoint: str,
        api_key: str | None,
        payload: dict[str, Any],
        is_backup: bool = False,
    ) -> str:
        """Low-level HTTP call executor."""

        url = endpoint
        if api_key:
            url += f"?{urlencode({'key': api_key})}"

        request_data = json.dumps(payload).encode("utf-8")
        target_type = "Backup" if is_backup else "Primary"

        logger.debug(
            "%s Google Cloud Translation request to %s",
            target_type,
            endpoint,
        )

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": f"SHL-Client/{SHL_VERSION}",
            "Accept": "application/json",
        }

        req = Request(url, data=request_data, headers=headers)

        try:
            with urlopen(req, timeout=GOOGLE_TIMEOUT) as response:
                raw = read_limited_response(
                    response,
                    MAX_RESPONSE_BYTES,
                )
                response_data = json.loads(raw.decode("utf-8"))

            translations = response_data.get("translations", [])

            if not translations:
                raise TranslationError(
                    "Google API returned an empty translations array"
                )

            translated = translations[0].get("translatedText")

            if translated is not None:
                logger.debug(
                    "%s Google Cloud translation successful",
                    target_type,
                )
                return translated

            raise TranslationError(
                "Google Cloud API response missing 'translatedText'"
            )

        # safe_urlopen converts urllib's HTTPError and URLError into
        # SafeHTTPError before they leave the safe layer. The HTTP
        # status and response body are preserved on the error object.
        except SafeHTTPError as e:
            self._raise_from_safe_http_error(e)

        except TimeoutError as e:
            raise ServiceUnavailableError(
                "Google Cloud API timeout"
            ) from e

        except OSError as e:
            raise ServiceUnavailableError(
                f"Google Cloud network error: {e}"
            ) from e

        except TranslationError:
            raise

        except Exception as e:
            raise TranslationError(
                f"Google Cloud unexpected error: "
                f"{type(e).__name__}: {e}"
            ) from e

    def _raise_from_safe_http_error(
        self,
        error: SafeHTTPError,
    ) -> NoReturn:
        """Map a SafeHTTPError to the adapter's exception hierarchy.

        SafeHTTPError carries status_code and response_body, so the
        same status-based mapping used for raw HTTPError can be
        applied here.
        """

        # Transport-level failure (no HTTP status involved).
        if error.status_code is None:
            if error.kind == "timeout":
                raise ServiceUnavailableError(
                    "Google Cloud API timeout"
                ) from error

            raise ServiceUnavailableError(
                f"Google Cloud network error: {error}"
            ) from error

        # Extract the provider error message if the body is JSON.
        error_message = ""
        if error.response_body:
            try:
                error_body = json.loads(error.response_body)
                error_message = (
                    error_body.get("error", {}).get("message", "")
                )
            except (json.JSONDecodeError, AttributeError):
                pass

        code = error.status_code

        if code in (401, 403):
            raise ProviderAccessError(
                "Google Cloud: Authentication or permission error"
            ) from error

        if code == 429:
            raise RateLimitExceededError(
                "Google Cloud: Quota exceeded"
            ) from error

        if code >= 500:
            raise ServiceUnavailableError(
                f"Google Cloud: Server error {code}"
            ) from error

        if code == 400:
            if "language" in error_message.lower():
                raise LanguageNotSupportedError(
                    "Google Cloud: Language not supported"
                ) from error

            raise InvalidRequestError(
                f"Google Cloud: Bad request ({code}) - {error_message}"
            ) from error

        raise TranslationError(
            f"Google Cloud HTTP error {code}"
        ) from error
