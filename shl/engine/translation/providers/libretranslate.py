"""
File: shl/engine/translation/providers/libretranslate.py
Author: Tuomas Lähteenmäki
Version: 0.3.0
License: MIT
Description: Robust translation provider adapter for the LibreTranslate
API. Handles translation requests, supported-language discovery,
language-pair registry validation, configurable API endpoints, API
authentication, error classification, and security checks for
suspicious translation results.

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
from shl.config import get_config_value
from shl.utils.env_loader import get_env_value, mask_api_key

from ..exceptions import (
    InvalidRequestError,
    LanguageNotSupportedError,
    ProviderAccessError,
    RateLimitExceededError,
    ServiceUnavailableError,
    TranslationError,
)
from ..metadata import TranslationRequest
from ...errors import codes
from ...errors.parser import ErrorParser
from ...errors.providers import LIBRETRANSLATE
from ..providers.base import TranslationProvider
from .libretranslate_registry import LibreTranslateRegistry


logger = logging.getLogger(__name__)


LIBRETRANSLATE_TIMEOUT = 15
LIBRETRANSLATE_LANGUAGES_TIMEOUT = 10
LIBRETRANSLATE_DEFAULT_URL = "https://libretranslate.com"
LIBRETRANSLATE_DEFAULT_API_KEY = ""


def _raise_normalized_error(error) -> NoReturn:
    """Convert a normalized SHL error into the LibreTranslate adapter
    exception hierarchy. Always raises.
    """

    message = error.message or (
        f"LibreTranslate request failed: {error.code}"
    )

    if error.code == codes.RATE_LIMIT_EXCEEDED:
        raise RateLimitExceededError(message)

    if error.code == codes.QUOTA_EXCEEDED:
        raise RateLimitExceededError(message)

    if error.code in {
        codes.TIMEOUT,
        codes.SERVICE_UNAVAILABLE,
    }:
        raise ServiceUnavailableError(message)

    if error.code in {
        codes.AUTH_FAILED,
        codes.AUTH_EXPIRED,
        codes.AUTH_BLOCKED,
        codes.ACCESS_DENIED,
    }:
        raise ProviderAccessError(message)

    if error.code in {
        codes.LANG_UNSUPPORTED,
        codes.LANG_PAIR_UNSUPPORTED,
    }:
        raise LanguageNotSupportedError(message)

    if error.code in {
        codes.INVALID_REQUEST,
        codes.TEXT_TOO_LONG,
        codes.REQUEST_TOO_LONG,
        codes.METHOD_NOT_ALLOWED,
    }:
        raise InvalidRequestError(message)

    raise TranslationError(message)


def get_supported_languages(
    base_url: str | None = None,
    api_key: str | None = None,
    timeout: float = LIBRETRANSLATE_LANGUAGES_TIMEOUT,
) -> list[dict[str, Any]]:
    """Fetch supported languages from the LibreTranslate /languages
    endpoint.

    Returns:
        A list of dictionaries returned by LibreTranslate.

    Raises:
        Adapter-specific exceptions on any failure.
    """

    resolved_base_url = (
        base_url
        or get_config_value(
            "providers.libretranslate.url",
            LIBRETRANSLATE_DEFAULT_URL,
        )
    ).rstrip("/")

    resolved_api_key = (
        api_key
        or get_env_value("LIBRETRANSLATE_API_KEY")
        or LIBRETRANSLATE_DEFAULT_API_KEY
    )

    url = f"{resolved_base_url}/languages"

    if resolved_api_key:
        url = (
            f"{url}?"
            f"{urlencode({'api_key': resolved_api_key})}"
        )

    request = Request(
        url=url,
        headers={
            "Accept": "application/json",
            "User-Agent": f"SHL/{SHL_VERSION}",
        },
        method="GET",
    )

    error_parser = ErrorParser(
        provider="libretranslate",
        config=LIBRETRANSLATE,
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            raw = read_limited_response(response, MAX_RESPONSE_BYTES)
            raw_response = raw.decode("utf-8")
            status_code = response.status

        try:
            payload = json.loads(raw_response)
        except json.JSONDecodeError:
            error = error_parser.parse(
                raw_response,
                http_status=status_code,
            )
            _raise_normalized_error(error)

    # safe_urlopen converts urllib's HTTPError and URLError into
    # SafeHTTPError before they leave the safe layer. The HTTP status
    # and response body are preserved on the error object.
    except SafeHTTPError as error:
        if error.status_code is None:
            # Transport-level failure with no HTTP status.
            normalized_error = error_parser.parse(
                {},
                exception=error,
            )
            _raise_normalized_error(normalized_error)

        try:
            response_data = json.loads(error.response_body or "")
        except (json.JSONDecodeError, TypeError):
            response_data = {}

        if not isinstance(response_data, dict):
            response_data = {}

        normalized_error = error_parser.parse(
            response_data,
            http_status=error.status_code,
        )

        _raise_normalized_error(normalized_error)

    except TimeoutError as error:
        normalized_error = error_parser.parse(
            {},
            exception=error,
        )
        _raise_normalized_error(normalized_error)

    except OSError as error:
        normalized_error = error_parser.parse(
            {},
            exception=error,
        )
        _raise_normalized_error(normalized_error)

    except (
        RateLimitExceededError,
        ServiceUnavailableError,
        LanguageNotSupportedError,
        ProviderAccessError,
        InvalidRequestError,
        TranslationError,
    ):
        raise

    if not isinstance(payload, list):
        raise TranslationError(
            "LibreTranslate: /languages returned an unexpected "
            "response format"
        )

    return payload


class LibreTranslateAdapter(TranslationProvider):
    """LibreTranslate translation adapter."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        cache_ttl: float = 86400.0,
    ):
        self.base_url = (
            base_url
            or get_config_value(
                "providers.libretranslate.url",
                LIBRETRANSLATE_DEFAULT_URL,
            )
        ).rstrip("/")

        self.api_key = (
            api_key
            or get_env_value("LIBRETRANSLATE_API_KEY")
            or LIBRETRANSLATE_DEFAULT_API_KEY
        )

        self.registry = LibreTranslateRegistry(cache_ttl=cache_ttl)

        self.error_parser = ErrorParser(
            provider=self.name,
            config=LIBRETRANSLATE,
        )

        logger.debug(
            "LibreTranslateAdapter initialized "
            "(base_url=%s, api_key=%s)",
            self.base_url,
            mask_api_key(self.api_key),
        )

    @property
    def name(self) -> str:
        return "libretranslate"

    @property
    def supported_features(self) -> list[str]:
        return []

    def supports_feature(self, feature: str) -> bool:
        return feature.lower() in self.supported_features

    def translate(self, request: TranslationRequest) -> str:
        """Translate text using LibreTranslate API."""

        source = request.source_lang
        target = request.target_lang

        if not self.registry.is_pair_supported(source, target):
            raise LanguageNotSupportedError(
                f"LibreTranslate: language pair "
                f"'{source}' -> '{target}' is not supported "
                "according to the local registry"
            )

        payload = self.build_request(request)

        try:
            return self._call_api(payload)

        except LanguageNotSupportedError:
            self.registry.mark_pair_unsupported(source, target)
            raise

    def build_request(
        self,
        request: TranslationRequest,
    ) -> dict[str, Any]:
        """Build LibreTranslate API request."""

        # Explicit annotation is required because the payload holds
        # heterogeneous value types (str, and possibly None for
        # source_lang).
        payload: dict[str, Any] = {
            "q": request.text,
            "source": request.source_lang,
            "target": request.target_lang,
            "format": "text",
        }

        if self.api_key:
            payload["api_key"] = self.api_key

        return payload

    def _call_api(self, payload: dict[str, Any]) -> str:
        """Call LibreTranslate /translate."""

        source = payload.get("source", "")
        target = payload.get("target", "")
        base_url = self.base_url

        try:
            url = f"{base_url}/translate"

            request_data = json.dumps(payload).encode("utf-8")

            logger.debug(
                "LibreTranslate request: %s->%s (api_key=%s)",
                source,
                target,
                mask_api_key(self.api_key),
            )

            request = Request(
                url=url,
                data=request_data,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": f"SHL/{SHL_VERSION}",
                    "Accept": "application/json",
                },
                method="POST",
            )

            with urlopen(
                request,
                timeout=LIBRETRANSLATE_TIMEOUT,
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
                normalized_error = self.error_parser.parse(
                    raw_response,
                    http_status=status_code,
                )
                _raise_normalized_error(normalized_error)

            if not isinstance(response_data, dict):
                raise TranslationError(
                    "LibreTranslate: unexpected response format"
                )

            translated = response_data.get("translatedText")

            if (
                isinstance(translated, str)
                and translated
                and translated != payload["q"]
            ):
                logger.debug(
                    "LibreTranslate success: %s",
                    translated[:100],
                )
                return translated

            raise TranslationError(
                "LibreTranslate returned empty or unmodified text"
            )

        # safe_urlopen converts urllib's HTTPError and URLError into
        # SafeHTTPError before they leave the safe layer.
        except SafeHTTPError as error:
            if error.status_code is None:
                normalized_error = self.error_parser.parse(
                    {},
                    exception=error,
                )
                _raise_normalized_error(normalized_error)

            logger.debug(
                "LibreTranslate error details: %s",
                error.response_body or "",
            )

            try:
                response_data = json.loads(
                    error.response_body or ""
                )
            except (json.JSONDecodeError, TypeError):
                response_data = {}

            if not isinstance(response_data, dict):
                response_data = {}

            normalized_error = self.error_parser.parse(
                response_data,
                http_status=error.status_code,
            )

            _raise_normalized_error(normalized_error)

        except TimeoutError as error:
            normalized_error = self.error_parser.parse(
                {},
                exception=error,
            )
            _raise_normalized_error(normalized_error)

        except OSError as error:
            normalized_error = self.error_parser.parse(
                {},
                exception=error,
            )
            _raise_normalized_error(normalized_error)

        except (
            RateLimitExceededError,
            ServiceUnavailableError,
            LanguageNotSupportedError,
            ProviderAccessError,
            InvalidRequestError,
            TranslationError,
        ):
            raise

        except Exception as error:
            normalized_error = self.error_parser.parse(
                {},
                exception=error,
            )
            _raise_normalized_error(normalized_error)
