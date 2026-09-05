"""
File: yandex.py — module for Yandex Translate adapter.
Author: Tuomas Lähteenmäki
Version: 0.2.10
License: MIT
Description: Robust translation provider adapter for the Yandex Cloud Translate API.
Handles advanced features including HTML formatting, glossary mapping,
registry validation, and security checks for suspicious output.
"""

import json
import logging
import socket
from typing import Dict, Any, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from shl._version import __version__ as SHL_VERSION
from shl.config import get_config_value
from shl.utils.env_loader import get_env_value, mask_api_key

from ...errors.parser import ErrorParser
from ...errors.providers import YANDEX
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
from .yandex_registry import YandexRegistry

logger = logging.getLogger(__name__)

YANDEX_TIMEOUT = 15
YANDEX_TRANSLATE_URL = "https://translate.api.cloud.yandex.net/translate/v2/translate"


class YandexAdapter(TranslationProvider):
    """
    Yandex Cloud Translate adapter.
    Supports:
    - text, source_lang, target_lang
    - folderId configuration
    - glossary mapping
    - html_format
    - (speller)
    - (exact)
    - (model)
    - registry validation
    - security checks
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        folder_id: Optional[str] = None,
    ):
        self.api_key = api_key or get_env_value("YANDEX_API_KEY")
        self.folder_id = folder_id or get_config_value(
            "providers.yandex.folder_id"
        )

        if not self.api_key:
            raise ValueError(
                "Yandex API key must be provided as parameter or "
                "set as YANDEX_API_KEY in ./.env/shl/.env"
            )

        if not self.folder_id:
            raise ValueError(
                "Yandex Folder ID must be provided as parameter or "
                "set as providers.yandex.folder_id in shl-config.json"
            )

        self.api_key = self.api_key.strip()
        self.folder_id = self.folder_id.strip()

        # Runtime language pair registry
        self.registry = YandexRegistry()

        # Centralized error parser
        self.error_parser = ErrorParser(
            provider=self.name,
            config=YANDEX,
        )

        logger.debug(
            f"YandexAdapter initialized "
            f"(api_key={mask_api_key(self.api_key)}, "
            f"folder_id={self.folder_id})"
        )

    @property
    def name(self) -> str:
        return "yandex"

    @property
    def supported_features(self) -> list:
        return ["glossary", "html_format"]

    def translate(self, request: TranslationRequest) -> str:
        """Translate text using Yandex Cloud Translate API."""

        # Pre-validate language pair using registry
        if request.source_lang:
            if not self.registry.is_pair_supported(
                request.source_lang,
                request.target_lang,
            ):
                raise LanguageNotSupportedError(
                    f"Yandex does not support language pair "
                    f"{request.source_lang}->{request.target_lang}"
                )

        payload = self.build_request(request)
        return self._call_api(payload, request)

    def build_request(
        self,
        request: TranslationRequest,
    ) -> Dict[str, Any]:
        """Build Yandex Cloud Translate API JSON payload."""
        payload = {
            "folderId": self.folder_id,
            "texts": [request.text],
            "targetLanguageCode": request.target_lang.lower(),
        }

        if request.source_lang:
            payload["sourceLanguageCode"] = request.source_lang.lower()

        if request.html_format:
            payload["format"] = "HTML"

        if request.glossary and "id" in request.glossary:
            # Yandex uses glossaryConfig for glossary configuration.
            payload["glossaryConfig"] = {
                "glossaryPairs": request.glossary.get("pairs", [])
            }

        return payload

    def _call_api(
        self,
        payload: Dict[str, Any],
        request: TranslationRequest,
    ) -> str:
        """Execute request against Yandex Cloud Translate API endpoint."""
        try:
            request_data = json.dumps(payload).encode("utf-8")

            logger.debug(
                f"Yandex request to {YANDEX_TRANSLATE_URL} "
                f"(api_key={mask_api_key(self.api_key)}, "
                f"text length: {len(payload['texts'][0])})"
            )

            req = Request(
                YANDEX_TRANSLATE_URL,
                data=request_data,
                headers={
                    "Authorization": f"Api-Key {self.api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": f"SHL-Client/{SHL_VERSION}",
                },
                method="POST",
            )

            with urlopen(req, timeout=YANDEX_TIMEOUT) as response:
                response_data = json.loads(
                    response.read().decode("utf-8")
                )
                translations = response_data.get("translations", [])

                if not translations:
                    raise TranslationError(
                        "Yandex returned an empty translations payload"
                    )

                translated = translations[0].get("text")

                # Yandex may not return the detected language in all responses.
                detected = translations[0].get(
                    "detectedLanguageCode",
                    "",
                ).lower()

                # --- SECURITY CHECK: Yandex output validation ---

                # 1. Empty or unchanged output
                if not translated or translated.strip() == "":
                    raise TranslationError(
                        "Yandex returned empty text."
                    )

                if translated.strip() == payload["texts"][0].strip():
                    raise TranslationError(
                        "Yandex returned unchanged text."
                    )

                # 2. Unexpected detected source language
                if request.source_lang and detected:
                    if detected != request.source_lang.lower():
                        raise TranslationError(
                            f"Yandex detected unexpected source language "
                            f"'{detected}' for input declared as "
                            f"'{request.source_lang}'."
                        )

                # 3. Unexpected HTML markup
                if not request.html_format:
                    if "<" in translated and ">" in translated:
                        raise TranslationError(
                            "Yandex returned unexpected HTML markup."
                        )

                # 4. Suspiciously short output
                if (
                    len(translated) < 3
                    and len(payload["texts"][0]) > 20
                ):
                    raise TranslationError(
                        "Yandex returned suspiciously short output."
                    )

                logger.debug("Yandex translation successful")
                return translated

        except HTTPError as e:
            try:
                error_body = e.read().decode(
                    "utf-8",
                    errors="replace",
                )
            except Exception:
                error_body = ""

            normalized = self.error_parser.parse(
                error_body,
                http_status=e.code,
            )

            if normalized is None:
                raise TranslationError(
                    f"Yandex HTTP error status code: {e.code}"
                ) from e

            if normalized.code in {
                "LANG_UNSUPPORTED",
                "LANG_PAIR_UNSUPPORTED",
            }:
                if request.source_lang:
                    self.registry.mark_pair_unsupported(
                        request.source_lang,
                        request.target_lang,
                    )

            raise self._map_normalized_error(
                normalized
            ) from e

        except URLError as e:
            normalized = self.error_parser.parse(
                exception=e,
            )

            if normalized is None:
                raise ServiceUnavailableError(
                    f"Yandex socket pipeline failure: {e.reason}"
                ) from e

            raise self._map_normalized_error(
                normalized
            ) from e

        except (socket.timeout, TimeoutError) as e:
            normalized = self.error_parser.parse(
                exception=e,
            )

            if normalized is None:
                raise ServiceUnavailableError(
                    "Yandex connection timeout reached"
                ) from e

            raise self._map_normalized_error(
                normalized
            ) from e

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
                f"Yandex unexpected execution layer failure: "
                f"{type(e).__name__}: {e}"
            ) from e

    def _map_normalized_error(self, error) -> Exception:
        """Map a normalized SHL error to the existing Yandex exceptions."""

        if error.code == "RATE_LIMIT_EXCEEDED":
            return RateLimitExceededError(
                error.message
                or "Yandex rate limit exceeded"
            )

        if error.code == "QUOTA_EXCEEDED":
            return RateLimitExceededError(
                error.message
                or "Yandex quota exceeded"
            )

        if error.code in {
            "TIMEOUT",
            "SERVICE_UNAVAILABLE",
        }:
            return ServiceUnavailableError(
                error.message
                or "Yandex service unavailable"
            )

        if error.code in {
            "AUTH_FAILED",
            "AUTH_EXPIRED",
            "AUTH_BLOCKED",
            "ACCESS_DENIED",
        }:
            return ProviderAccessError(
                error.message
                or "Yandex access denied"
            )

        if error.code in {
            "LANG_UNSUPPORTED",
            "LANG_PAIR_UNSUPPORTED",
        }:
            return LanguageNotSupportedError(
                error.message
                or "Yandex does not support the requested language"
            )

        if error.code in {
            "INVALID_REQUEST",
            "TEXT_TOO_LONG",
            "REQUEST_TOO_LONG",
            "METHOD_NOT_ALLOWED",
        }:
            return InvalidRequestError(
                error.message
                or "Yandex rejected the request"
            )

        return TranslationError(
            error.message
            or f"Yandex translation error: {error.code}"
        )
