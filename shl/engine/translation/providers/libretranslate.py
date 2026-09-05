"""
File: libretranslater.py — LibreTranslate translation adapter.
Author: Tuomas Lähteenmäki
Version: 0.2.10
License: MIT
Description: Robust translation provider adapter for the LibreTranslate API.
             Handles translation requests, supported-language discovery,
             language-pair registry validation, configurable API endpoints,
             mirror support, API authentication, error classification,
             and security checks for suspicious translation results.
"""

import json
import logging
import socket
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

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
from ..errors import ErrorParser
from ..errors.providers import LIBRETRANSLATE
from ..providers.base import TranslationProvider
from .libretranslate_registry import LibreTranslateRegistry

logger = logging.getLogger(__name__)


LIBRETRANSLATE_TIMEOUT = 15
LIBRETRANSLATE_LANGUAGES_TIMEOUT = 10
LIBRETRANSLATE_DEFAULT_URL = "https://libretranslate.com"
LIBRETRANSLATE_DEFAULT_API_KEY = ""


def _raise_normalized_error(error) -> None:
    """
    Convert a normalized SHL error into the existing
    LibreTranslate adapter exception hierarchy.
    """

    message = error.message or (
        f"LibreTranslate request failed: {error.code}"
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


def get_supported_languages(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: float = LIBRETRANSLATE_LANGUAGES_TIMEOUT,
) -> List[Dict[str, Any]]:
    """
    Fetch supported languages from the LibreTranslate /languages endpoint.

    Returns:
        A list of dictionaries returned by LibreTranslate.
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
        url = f"{url}?{urlencode({'api_key': resolved_api_key})}"

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
        with urlopen(
            request,
            timeout=timeout,
        ) as response:
            raw_response = response.read().decode("utf-8")

            try:
                payload = json.loads(raw_response)
            except json.JSONDecodeError:
                error = error_parser.parse(
                    raw_response,
                    http_status=response.status,
                )
                _raise_normalized_error(error)

    except HTTPError as error:
        try:
            error_body = error.read().decode(
                "utf-8",
                errors="replace",
            )
        except Exception:
            error_body = ""

        try:
            response_data = json.loads(error_body)
        except json.JSONDecodeError:
            response_data = {}

        normalized_error = error_parser.parse(
            response_data,
            http_status=error.code,
        )

        _raise_normalized_error(normalized_error)

    except URLError as error:
        if isinstance(
            error.reason,
            (socket.timeout, TimeoutError),
        ):
            normalized_error = error_parser.parse(
                {},
                exception=TimeoutError(
                    "LibreTranslate: timeout "
                    "when retrieving supported languages"
                ),
            )
        else:
            normalized_error = error_parser.parse(
                {},
                exception=ConnectionError(
                    "LibreTranslate: network error "
                    f"when retrieving supported languages: {error.reason}"
                ),
            )

        _raise_normalized_error(normalized_error)

    except (socket.timeout, TimeoutError) as error:
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
            "LibreTranslate: /languages returned "
            "an unexpected response format"
        )

    return payload


class LibreTranslateAdapter(TranslationProvider):
    """LibreTranslate translation adapter."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        cache_ttl: float = 86400.0,
        mirror_manager: Optional[Any] = None,
        mirrors: Optional[List[Dict[str, Any]]] = None,
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

        self.registry = LibreTranslateRegistry(
            cache_ttl=cache_ttl
        )

        self.mirror_manager = mirror_manager

        if self.mirror_manager is None and mirrors is not None:
            from .libretranslate_mirrors import (
                LibreTranslateMirrorManager,
            )

            self.mirror_manager = LibreTranslateMirrorManager(
                mirrors=mirrors
            )

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
        """
        Translate text using LibreTranslate API.
        """

        source = request.source_lang
        target = request.target_lang

        if not self.registry.is_pair_supported(
            source,
            target,
        ):
            raise LanguageNotSupportedError(
                "LibreTranslate: language pair "
                f"'{source}' -> '{target}' is not supported "
                "according to the local registry"
            )

        payload = self.build_request(request)

        try:
            return self._call_api(payload)

        except LanguageNotSupportedError:
            self.registry.mark_pair_unsupported(
                source,
                target,
            )
            raise

    def build_request(
        self,
        request: TranslationRequest,
    ) -> Dict[str, Any]:
        """Build LibreTranslate API request."""

        payload: Dict[str, Any] = {
            "q": request.text,
            "source": request.source_lang,
            "target": request.target_lang,
            "format": "text",
        }

        if self.api_key:
            payload["api_key"] = self.api_key

        return payload

    def _get_translation_base_url(self) -> str:
        """
        Resolve the URL used for translation.

        If a mirror manager is available, use its best mirror.
        Otherwise use the configured base URL.
        """

        if self.mirror_manager is not None:
            mirror = self.mirror_manager.get_best_mirror()

            if mirror is not None and getattr(
                mirror,
                "url",
                None,
            ):
                return mirror.url.rstrip("/")

        return self.base_url

    def _call_api(
        self,
        payload: Dict[str, Any],
    ) -> str:
        """Call LibreTranslate /translate."""

        source = payload.get("source", "")
        target = payload.get("target", "")
        base_url = self._get_translation_base_url()

        try:
            url = f"{base_url}/translate"

            request_data = json.dumps(
                payload
            ).encode("utf-8")

            logger.debug(
                "LibreTranslate request: %s->%s "
                "(api_key=%s)",
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
                raw_response = response.read().decode("utf-8")

                try:
                    response_data = json.loads(raw_response)
                except json.JSONDecodeError:
                    normalized_error = self.error_parser.parse(
                        raw_response,
                        http_status=response.status,
                    )
                    _raise_normalized_error(normalized_error)

            translated = response_data.get(
                "translatedText"
            )

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
                "LibreTranslate returned empty "
                "or unmodified text"
            )

        except HTTPError as error:
            try:
                error_body = error.read().decode(
                    "utf-8",
                    errors="replace",
                )
            except Exception:
                error_body = ""

            logger.debug(
                "LibreTranslate error details: %s",
                error_body,
            )

            try:
                response_data = json.loads(error_body)
            except json.JSONDecodeError:
                response_data = {}

            normalized_error = self.error_parser.parse(
                response_data,
                http_status=error.code,
            )

            _raise_normalized_error(normalized_error)

        except URLError as error:
            if isinstance(
                error.reason,
                (socket.timeout, TimeoutError),
            ):
                normalized_error = self.error_parser.parse(
                    {},
                    exception=TimeoutError(
                        "LibreTranslate: request timeout"
                    ),
                )
            else:
                normalized_error = self.error_parser.parse(
                    {},
                    exception=ConnectionError(
                        "LibreTranslate: network error "
                        f"{error.reason}"
                    ),
                )

            _raise_normalized_error(normalized_error)

        except (socket.timeout, TimeoutError) as error:
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
