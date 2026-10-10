"""
File: shl/engine/translation/providers/libretranslate_community/libretranslate_community.py
Author: Tuomas Lähteenmäki
Version: 0.3.0
License: MIT
Description: Translation provider adapter for LibreTranslate Community
endpoints. Tries configured Community endpoints in order and returns
the first successful translation.

All outbound HTTP goes through safe_urlopen for SSRF prevention,
redirect validation, and response size limits.
"""

import json
import logging
from typing import Any, NoReturn
from urllib.request import Request

from shl.utils.safe_http import safe_urlopen as urlopen
from shl.utils.safe_http_common import (
    MAX_RESPONSE_BYTES,
    SafeHTTPError,
    read_limited_response,
)

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

from .endpoints import load_endpoints
from .libretranslate_community_registry import (
    LibreTranslateCommunityRegistry,
)


logger = logging.getLogger(__name__)

LIBRETRANSLATE_COMMUNITY_TIMEOUT = 15


class LibreTranslateCommunityAdapter(TranslationProvider):
    """LibreTranslate Community translation provider.

    Endpoints are resolved by load_endpoints(), which honours the
    user override file (<cwd>/libretranslate_endpoints.json) and
    falls back to library defaults when the file is absent. Endpoints
    are tried in order until one succeeds.
    """

    def __init__(
        self,
        api_key: str | None = None,
    ):
        self.api_key = (
            api_key
            or get_env_value("LIBRETRANSLATE_COMMUNITY_API_KEY")
            or ""
        )

        # Load endpoints via the resolver so the user override file
        # (<cwd>/libretranslate_endpoints.json) is honoured, and the
        # file is created from defaults on first call.
        self.endpoints = load_endpoints()

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
    def supported_features(self) -> list[str]:
        return []

    def supports_feature(self, feature: str) -> bool:
        return feature.lower() in self.supported_features

    def translate(self, request: TranslationRequest) -> str:
        """Translate text using LibreTranslate Community endpoints."""

        if not self.endpoints:
            raise ServiceUnavailableError(
                "LibreTranslate Community: no endpoints configured"
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

        last_error: Exception | None = None

        for endpoint in self.endpoints:
            try:
                logger.debug(
                    "LibreTranslate Community trying endpoint: %s",
                    endpoint,
                )
                return self._call_api(endpoint, payload, request)

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
            "LibreTranslate Community: all endpoints failed"
        )

    def build_request(
        self,
        request: TranslationRequest,
    ) -> dict[str, Any]:
        """Build LibreTranslate Community API request."""

        # Explicit annotation is required because the payload holds
        # a mix of str values and an optional api_key.
        payload: dict[str, Any] = {
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
        request: TranslationRequest | None = None,
    ) -> NoReturn:
        """Convert a normalized SHL error into the adapter's exception
        hierarchy. Always raises.
        """

        message = error.message or (
            f"LibreTranslate Community request failed: {error.code}"
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
        payload: dict[str, Any],
        request: TranslationRequest,
    ) -> str:
        """Execute request against one LibreTranslate Community
        endpoint.
        """

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
                self._raise_normalized_error(error, request)

            if not isinstance(response_data, dict):
                error = self.error_parser.parse(
                    raw_response,
                    http_status=status_code,
                )
                self._raise_normalized_error(error, request)

            translated = response_data.get("translatedText")

            # Empty output is a provider error.
            # Unchanged output is NOT an error here — the translation
            # router validates unchanged results using SHL language
            # detection.
            if not isinstance(translated, str):
                error = self.error_parser.parse(
                    {
                        "message": (
                            "LibreTranslate Community returned an "
                            "invalid translation payload."
                        )
                    },
                    http_status=status_code,
                )
                self._raise_normalized_error(error, request)

            if not translated.strip():
                error = self.error_parser.parse(
                    {
                        "message": (
                            "LibreTranslate Community returned empty "
                            "text."
                        )
                    },
                    http_status=status_code,
                )
                self._raise_normalized_error(error, request)

            logger.debug(
                "LibreTranslate Community translation successful "
                "(endpoint=%s)",
                endpoint,
            )
            return translated

        # safe_urlopen converts urllib's HTTPError and URLError into
        # SafeHTTPError before they leave the safe layer. The HTTP
        # status and response body are preserved on the error object.
        except SafeHTTPError as e:
            if e.status_code is None:
                # Transport-level failure, no HTTP status.
                error = self.error_parser.parse({}, exception=e)
                self._raise_normalized_error(error, request)

            try:
                response_data = json.loads(e.response_body or "")
            except (json.JSONDecodeError, TypeError):
                response_data = {}

            if not isinstance(response_data, dict):
                response_data = {}

            error = self.error_parser.parse(
                response_data,
                http_status=e.status_code,
            )

            if error is None:
                error = self.error_parser.parse(
                    {},
                    http_status=e.status_code,
                )

            self._raise_normalized_error(error, request)

        except TimeoutError as e:
            error = self.error_parser.parse({}, exception=e)
            self._raise_normalized_error(error, request)

        except OSError as e:
            error = self.error_parser.parse({}, exception=e)
            self._raise_normalized_error(error, request)

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
            error = self.error_parser.parse({}, exception=e)
            self._raise_normalized_error(error, request)
