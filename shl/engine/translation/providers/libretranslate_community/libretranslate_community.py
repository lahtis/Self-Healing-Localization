"""
File: libretranslate_community.py — LibreTranslate Community translation adapter.
Author: Tuomas Lähteenmäki
Version: 0.2.13
License: MIT
Description: Translation provider adapter for LibreTranslate Community
             endpoints. Tries configured Community endpoints in order
             and returns the first successful translation.
"""

import json
import logging
import socket
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request
from shl.utils.safe_http import safe_urlopen as urlopen

from shl._version import __version__ as SHL_VERSION
from shl.utils.env_loader import get_env_value, mask_api_key

from ...exceptions import (
    InvalidRequestError,
    LanguageNotSupportedError,
    ProviderAccessError,
    RateLimitExceededError,
    ServiceUnavailableError,
    TranslationError,
)
from ...metadata import TranslationRequest
from ....errors.parser import ErrorParser
from ....errors.providers import LIBRETRANSLATE
from ..base import TranslationProvider

from .endpoints import LIBRETRANSLATE_COMMUNITY_ENDPOINTS
from .libretranslate_community_registry import (
    LibreTranslateCommunityRegistry,
)

logger = logging.getLogger(__name__)

LIBRETRANSLATE_COMMUNITY_TIMEOUT = 15


class LibreTranslateCommunityAdapter(TranslationProvider):
    """
    LibreTranslate Community translation provider.

    The provider uses a static list of LibreTranslate-compatible
    Community endpoints and tries them in order until one succeeds.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
    ):
        self.api_key = (
            api_key
            or get_env_value(
                "LIBRETRANSLATE_COMMUNITY_API_KEY"
            )
            or ""
        )

        self.endpoints = [
            str(endpoint).rstrip("/")
            for endpoint in LIBRETRANSLATE_COMMUNITY_ENDPOINTS
            if endpoint
        ]

        self.registry = LibreTranslateCommunityRegistry()

        self.error_parser = ErrorParser(
            provider=self.name,
            config=LIBRETRANSLATE,
        )

        logger.debug(
            "LibreTranslateCommunityAdapter initialized "
            "(endpoints=%d, api_key=%s)",
            len(self.endpoints),
            mask_api_key(self.api_key),
        )

    @property
    def name(self) -> str:
        return "libretranslate_community"

    @property
    def supported_features(self) -> List[str]:
        return []

    def supports_feature(
        self,
        feature: str,
    ) -> bool:
        return feature.lower() in self.supported_features

    def translate(
        self,
        request: TranslationRequest,
    ) -> str:
        """Translate text using LibreTranslate Community endpoints."""

        if not self.endpoints:
            raise ServiceUnavailableError(
                "LibreTranslate Community: "
                "no endpoints configured"
            )

        if not self.registry.is_pair_supported(
            request.source_lang,
            request.target_lang,
        ):
            logger.debug(
                "LibreTranslate Community does not support "
                "language pair '%s' -> '%s'.",
                request.source_lang,
                request.target_lang,
            )
            raise LanguageNotSupportedError(
                "LibreTranslate Community does not support "
                f"'{request.source_lang}' -> "
                f"'{request.target_lang}'."
            )

        payload = self.build_request(request)

        last_error = None

        for endpoint in self.endpoints:
            try:
                logger.debug(
                    "LibreTranslate Community trying endpoint: %s",
                    endpoint,
                )

                return self._call_api(
                    endpoint,
                    payload,
                    request,
                )

            except LanguageNotSupportedError as error:
                logger.debug(
                    "LibreTranslate Community endpoint does not "
                    "support '%s' -> '%s': %s",
                    request.source_lang,
                    request.target_lang,
                    error,
                )

                last_error = error
                continue

            except (
                ServiceUnavailableError,
                RateLimitExceededError,
            ) as error:
                logger.debug(
                    "LibreTranslate Community endpoint unavailable "
                    "or rate limited: %s: %s",
                    endpoint,
                    error,
                )

                last_error = error
                continue

            except ProviderAccessError as error:
                logger.debug(
                    "LibreTranslate Community endpoint access "
                    "failure: %s: %s",
                    endpoint,
                    error,
                )

                last_error = error
                continue

            except TranslationError as error:
                logger.debug(
                    "LibreTranslate Community endpoint failed: "
                    "%s: %s",
                    endpoint,
                    error,
                )

                last_error = error
                continue

        if last_error is not None:
            raise last_error

        raise ServiceUnavailableError(
            "LibreTranslate Community: "
            "all endpoints failed"
        )

    def build_request(
        self,
        request: TranslationRequest,
    ) -> Dict[str, Any]:
        """Build LibreTranslate Community API request."""

        payload: Dict[str, Any] = {
            "q": request.text,
            "source": request.source_lang,
            "target": request.target_lang,
            "format": "text",
        }

        if self.api_key:
            payload["api_key"] = self.api_key

        return payload

    def _raise_normalized_error(
        self,
        error,
        request: Optional[TranslationRequest] = None,
    ) -> None:
        """
        Convert a normalized SHL error into the existing adapter
        exception hierarchy.
        """

        message = error.message or (
            f"LibreTranslate Community request failed: "
            f"{error.code}"
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
            if (
                error.code == "LANG_PAIR_UNSUPPORTED"
                and request is not None
            ):
                self.registry.mark_pair_unsupported(
                    request.source_lang,
                    request.target_lang,
                )

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
        endpoint: str,
        payload: Dict[str, Any],
        request: TranslationRequest,
    ) -> str:
        """Execute request against one LibreTranslate Community endpoint."""

        try:
            url = f"{endpoint}/translate"
            request_data = json.dumps(payload).encode("utf-8")

            logger.debug(
                "LibreTranslate Community request to %s "
                "(api_key=%s, text length: %d)",
                url,
                mask_api_key(self.api_key),
                len(payload["q"]),
            )

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
                timeout=LIBRETRANSLATE_COMMUNITY_TIMEOUT,
            ) as response:

                raw_response = response.read().decode(
                    "utf-8"
                )

                response_data = self.error_parser._decode_payload(
                    raw_response
                )

                if response_data is None:
                    error = self.error_parser.parse(
                        raw_response,
                        http_status=response.status,
                    )
                    self._raise_normalized_error(
                        error,
                        request,
                    )

                translated = response_data.get(
                    "translatedText"
                )

                # Empty output is a provider error.
                # Unchanged output is NOT an error here.
                # The translation router must validate it using
                # SHL language detection.
                if not isinstance(translated, str):
                    error = self.error_parser.parse(
                        {
                            "message": (
                                "LibreTranslate Community returned "
                                "an invalid translation payload."
                            )
                        },
                        http_status=response.status,
                    )
                    self._raise_normalized_error(
                        error,
                        request,
                    )

                if not translated.strip():
                    error = self.error_parser.parse(
                        {
                            "message": (
                                "LibreTranslate Community returned "
                                "empty text."
                            )
                        },
                        http_status=response.status,
                    )
                    self._raise_normalized_error(
                        error,
                        request,
                    )

                logger.debug(
                    "LibreTranslate Community translation successful "
                    "(endpoint=%s)",
                    endpoint,
                )

                return translated

        except HTTPError as e:
            response_data = None

            try:
                raw_body = e.read().decode("utf-8")

                if raw_body:
                    response_data = json.loads(raw_body)

            except (
                UnicodeDecodeError,
                json.JSONDecodeError,
            ):
                response_data = None

            if response_data is None:
                response_data = {}

            error = self.error_parser.parse(
                response_data,
                http_status=e.code,
            )

            if error is None:
                error = self.error_parser.parse(
                    {},
                    http_status=e.code,
                )

            self._raise_normalized_error(
                error,
                request,
            )

        except URLError as e:
            if isinstance(
                e.reason,
                (socket.timeout, TimeoutError),
            ):
                error = self.error_parser.parse(
                    {},
                    exception=TimeoutError(
                        "LibreTranslate Community "
                        "network timeout reached"
                    ),
                )
            else:
                error = self.error_parser.parse(
                    {},
                    exception=ConnectionError(
                        "LibreTranslate Community socket "
                        f"pipeline failure: {e.reason}"
                    ),
                )

            self._raise_normalized_error(
                error,
                request,
            )

        except (
            socket.timeout,
            TimeoutError,
        ) as e:
            error = self.error_parser.parse(
                {},
                exception=e,
            )

            self._raise_normalized_error(
                error,
                request,
            )

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

            self._raise_normalized_error(
                error,
                request,
            )
