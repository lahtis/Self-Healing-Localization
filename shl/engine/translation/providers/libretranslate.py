"""
LibreTranslate translation adapter.
"""

from __future__ import annotations

import json
import logging
import os
import socket
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from shl._version import __version__ as SHL_VERSION

from ..exceptions import (
    InvalidRequestError,
    LanguageNotSupportedError,
    ProviderAccessError,
    RateLimitExceededError,
    ServiceUnavailableError,
    TranslationError,
)
from ..metadata import TranslationRequest
from ..providers.base import TranslationProvider
from .libretranslate_registry import LibreTranslateRegistry

logger = logging.getLogger(__name__)


LIBRETRANSLATE_TIMEOUT = 15
LIBRETRANSLATE_LANGUAGES_TIMEOUT = 10
LIBRETRANSLATE_DEFAULT_URL = "https://libretranslate.com"
LIBRETRANSLATE_DEFAULT_API_KEY = ""


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
        or os.environ.get("LIBRETRANSLATE_URL")
        or LIBRETRANSLATE_DEFAULT_URL
    ).rstrip("/")

    resolved_api_key = (
        api_key
        or os.environ.get("LIBRETRANSLATE_API_KEY")
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

    try:
        with urlopen(
            request,
            timeout=timeout,
        ) as response:
            payload = json.loads(
                response.read().decode("utf-8")
            )

    except HTTPError as error:
        if error.code in (401, 403):
            raise ProviderAccessError(
                "LibreTranslate: access denied "
                "when retrieving supported languages"
            ) from error

        if error.code == 429:
            raise RateLimitExceededError(
                "LibreTranslate: rate limit exceeded "
                "when retrieving supported languages"
            ) from error

        if error.code >= 500:
            raise ServiceUnavailableError(
                "LibreTranslate: server error "
                f"{error.code} from /languages"
            ) from error

        raise TranslationError(
            "LibreTranslate: HTTP error "
            f"{error.code} from /languages"
        ) from error

    except URLError as error:
        if isinstance(
            error.reason,
            (socket.timeout, TimeoutError),
        ):
            raise ServiceUnavailableError(
                "LibreTranslate: timeout "
                "when retrieving supported languages"
            ) from error

        raise ServiceUnavailableError(
            "LibreTranslate: network error "
            f"when retrieving supported languages: {error.reason}"
        ) from error

    except (socket.timeout, TimeoutError) as error:
        raise ServiceUnavailableError(
            "LibreTranslate: timeout "
            "when retrieving supported languages"
        ) from error

    except json.JSONDecodeError as error:
        raise TranslationError(
            "LibreTranslate: invalid JSON response "
            "from /languages"
        ) from error

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
            or os.environ.get("LIBRETRANSLATE_URL")
            or LIBRETRANSLATE_DEFAULT_URL
        ).rstrip("/")

        self.api_key = (
            api_key
            or os.environ.get("LIBRETRANSLATE_API_KEY")
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
                self._mask_api_key(self.api_key),
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
                response_data = json.loads(
                    response.read().decode("utf-8")
                )

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

            raise ServiceUnavailableError(
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

            if error.code == 403:
                raise ProviderAccessError(
                    "LibreTranslate: access denied "
                    "(invalid or banned API key)"
                ) from error

            if error.code == 429:
                raise RateLimitExceededError(
                    "LibreTranslate: rate limit exceeded"
                ) from error

            if error.code >= 500:
                raise ServiceUnavailableError(
                    f"LibreTranslate: server error {error.code}"
                ) from error

            if error.code == 404:
                raise LanguageNotSupportedError(
                    "LibreTranslate: language not supported "
                    f"(HTTP {error.code})"
                ) from error

            if error.code == 400:
                if "language" in error_body.lower():
                    raise LanguageNotSupportedError(
                        "LibreTranslate: language not supported "
                        f"(HTTP {error.code})"
                    ) from error

                raise InvalidRequestError(
                    f"LibreTranslate: bad request {error.code}"
                ) from error

            raise TranslationError(
                f"LibreTranslate: HTTP error {error.code}"
            ) from error

        except URLError as error:
            if isinstance(
                error.reason,
                (socket.timeout, TimeoutError),
            ):
                raise ServiceUnavailableError(
                    "LibreTranslate: request timeout"
                ) from error

            raise ServiceUnavailableError(
                "LibreTranslate: network error "
                f"{error.reason}"
            ) from error

        except (socket.timeout, TimeoutError) as error:
            raise ServiceUnavailableError(
                "LibreTranslate: request timeout"
            ) from error

        except (
            RateLimitExceededError,
            ServiceUnavailableError,
            LanguageNotSupportedError,
            ProviderAccessError,
            InvalidRequestError,
            TranslationError,
        ):
            raise

        except json.JSONDecodeError as error:
            raise TranslationError(
                "LibreTranslate: invalid JSON response"
            ) from error

        except Exception as error:
            raise TranslationError(
                "LibreTranslate: unexpected error "
                f"{type(error).__name__}: {error}"
            ) from error

    @staticmethod
    def _mask_api_key(
        key: Optional[str],
    ) -> str:
        """Mask API key for safe logging."""
        if not key:
            return "(not set)"

        if len(key) <= 8:
            return "*" * len(key)

        return (
            key[:4]
            + "*" * (len(key) - 8)
            + key[-4:]
        )
