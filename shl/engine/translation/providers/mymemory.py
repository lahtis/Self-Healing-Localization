"""
File: mymemory.py — module for MyMemory translation adapter.
Author: Tuomas Lähteenmäki
Version: 0.2.10
License: MIT
Description: Robust translation provider adapter for the MyMemory API.
Handles optional email-based quota enhancement, optional private
translation memory access, registry validation, and security checks
for suspicious output.
"""

import json
import logging
import socket
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

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
from .base import TranslationProvider
from .mymemory_registry import MyMemoryRegistry
from ...errors.parser import ErrorParser
from ...errors.providers import MYMEMORY


logger = logging.getLogger(__name__)


MYMEMORY_TIMEOUT = 10
MYMEMORY_DEFAULT_URL = "https://api.mymemory.translated.net/get"


# Shared registry instance.
_registry = MyMemoryRegistry()


class MyMemoryAdapter(TranslationProvider):
    """
    MyMemory translation adapter.

    Supports:
    - source and target language selection
    - optional email for increased quota
    - optional API key for private translation memory
    - Bearer authentication for API key access
    - runtime language-pair registry
    - security checks for suspicious output
    """

    def __init__(
        self,
        email: Optional[str] = None,
        api_key: Optional[str] = None,
        cache_ttl: Optional[float] = None,
    ):
        """
        Initialize the MyMemory adapter.

        Email and API key are both optional. If omitted, they are read
        from the SHL environment configuration.
        """
        self.email = email or get_env_value(
            "MYMEMORY_EMAIL",
            "",
        )

        self.api_key = api_key or get_env_value(
            "MYMEMORY_API_KEY",
            "",
        )

        if self.email:
            self.email = self.email.strip()

        if self.api_key:
            self.api_key = self.api_key.strip()

        if cache_ttl is not None:
            _registry.cache_ttl = cache_ttl

        self.error_parser = ErrorParser(
            provider=self.name,
            config=MYMEMORY,
        )

        logger.debug(
            "MyMemoryAdapter initialized "
            "(email_configured=%s, api_key=%s)",
            bool(self.email),
            mask_api_key(self.api_key),
        )

    @property
    def name(self) -> str:
        return "mymemory"

    @property
    def supported_features(self) -> list:
        return []

    def translate(
        self,
        request: TranslationRequest,
    ) -> str:
        """
        Translate text using the MyMemory API.
        """
        source = (
            request.source_lang or ""
        ).lower().strip()

        target = request.target_lang.lower().strip()

        # Fast-fail using the local registry.
        if not _registry.is_pair_supported(
            source,
            target,
        ):
            raise LanguageNotSupportedError(
                f"MyMemory: language pair '{source}|{target}' "
                "is not supported or is temporarily blocked."
            )

        payload = self.build_request(request)

        try:
            return self._call_api(payload)

        except LanguageNotSupportedError:
            _registry.mark_pair_unsupported(
                source,
                target,
            )
            raise

    def build_request(
        self,
        request: TranslationRequest,
    ) -> Dict[str, Any]:
        """Build the MyMemory API request."""
        source = (
            request.source_lang or ""
        ).lower().strip()

        target = request.target_lang.lower().strip()

        payload: Dict[str, Any] = {
            "q": request.text,
            "langpair": f"{source}|{target}",
        }

        # Optional email. MyMemory can use this to provide
        # a higher request quota.
        if self.email:
            payload["de"] = self.email

        # Optional API key. The key is used for private
        # translation memory access and is sent through
        # the Authorization header.
        if self.api_key:
            payload["key"] = self.api_key

        return payload

    def _call_api(
        self,
        payload: Dict[str, Any],
    ) -> str:
        """
        Call the MyMemory API with the built GET request.

        The optional email is sent as the `de` query parameter.
        The optional API key is sent using Bearer authentication
        and is never included in the URL.
        """
        try:
            query_params = {
                "q": payload["q"],
                "langpair": payload["langpair"],
            }

            if payload.get("de"):
                query_params["de"] = payload["de"]

            url = (
                f"{MYMEMORY_DEFAULT_URL}?"
                f"{urlencode(query_params)}"
            )

            headers = {
                "User-Agent": f"SHL-Client/{SHL_VERSION}",
                "Accept": "application/json",
            }

            # Use Bearer authentication for private
            # translation memory access.
            if payload.get("key"):
                headers["Authorization"] = (
                    f"Bearer {payload['key']}"
                )

            # Never log the complete URL because it may contain
            # user-provided text and the optional email address.
            logger.debug(
                "MyMemory request: langpair=%s, "
                "email_configured=%s, api_key_configured=%s",
                payload["langpair"],
                bool(payload.get("de")),
                bool(payload.get("key")),
            )

            request = Request(
                url,
                headers=headers,
                method="GET",
            )

            with urlopen(
                request,
                timeout=MYMEMORY_TIMEOUT,
            ) as response:
                response_data = json.loads(
                    response.read().decode("utf-8")
                )

            if not isinstance(response_data, dict):
                raise TranslationError(
                    "MyMemory returned an invalid response payload."
                )

            response_status = response_data.get(
                "responseStatus"
            )

            response_details = response_data.get(
                "responseData",
                {},
            )

            if not isinstance(response_details, dict):
                raise TranslationError(
                    "MyMemory returned an invalid "
                    "responseData payload."
                )

            quota_reached = response_data.get(
                "quotaReached",
                False,
            )

            response_warning = response_details.get(
                "warning",
                "",
            )

            # --- QUOTA / RATE LIMIT ---

            if (
                quota_reached
                or "quota" in str(
                    response_warning
                ).lower()
            ):
                raise RateLimitExceededError(
                    "MyMemory: quota reached: "
                    f"{response_warning}"
                )

            # --- STATUS HANDLING ---

            if response_status != 200:
                normalized = self.error_parser.parse(
                    response_data,
                    http_status=response_status,
                )

                if normalized is not None:
                    raise self._map_normalized_error(
                        normalized
                    )

                raise TranslationError(
                    "MyMemory: unexpected status "
                    f"{response_status}"
                )

            translated = response_details.get(
                "translatedText"
            )

            try:
                match_quality = float(
                    response_details.get(
                        "match",
                        0,
                    )
                )
            except (TypeError, ValueError):
                match_quality = 0.0

            # --- SECURITY CHECKS ---

            # 1. Empty or unchanged output.
            if (
                not isinstance(translated, str)
                or not translated.strip()
            ):
                raise TranslationError(
                    "MyMemory returned empty text."
                )

            if (
                translated.strip()
                == payload["q"].strip()
            ):
                raise TranslationError(
                    "MyMemory returned unchanged text."
                )

            # 2. Weak match quality.
            if match_quality < 0.1:
                raise TranslationError(
                    "MyMemory returned suspiciously weak "
                    f"match quality ({match_quality})."
                )

            # 3. Suspiciously short output.
            if (
                len(translated) < 3
                and len(payload["q"]) > 20
            ):
                raise TranslationError(
                    "MyMemory returned suspiciously "
                    "short output."
                )

            logger.debug(
                "MyMemory translation successful "
                "(match=%s, private_memory=%s)",
                match_quality,
                bool(payload.get("key")),
            )

            return translated

        except HTTPError as error:
            response_body = None

            try:
                response_body = error.read().decode(
                    "utf-8",
                    errors="replace",
                )
            except Exception:
                response_body = None

            normalized = self.error_parser.parse(
                response_body,
                http_status=error.code,
            )

            if normalized is None:
                raise TranslationError(
                    f"MyMemory HTTP {error.code}"
                ) from error

            raise self._map_normalized_error(
                normalized
            ) from error

        except URLError as error:
            normalized = self.error_parser.parse(
                exception=error,
            )

            raise self._map_normalized_error(
                normalized
            ) from error

        except (
            socket.timeout,
            TimeoutError,
        ) as error:
            normalized = self.error_parser.parse(
                exception=error,
            )

            raise self._map_normalized_error(
                normalized
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
                "MyMemory returned invalid JSON"
            ) from error

        except Exception as error:
            raise TranslationError(
                "MyMemory unexpected error: "
                f"{type(error).__name__}: {error}"
            ) from error

    @staticmethod
    def _map_normalized_error(error) -> Exception:
        """Map a normalized SHL error to existing adapter exceptions."""

        if error.code == "RATE_LIMIT_EXCEEDED":
            return RateLimitExceededError(
                error.message or "MyMemory rate limit exceeded."
            )

        if error.code == "QUOTA_EXCEEDED":
            return RateLimitExceededError(
                error.message or "MyMemory quota exceeded."
            )

        if error.code in {
            "TIMEOUT",
            "SERVICE_UNAVAILABLE",
        }:
            return ServiceUnavailableError(
                error.message or "MyMemory service unavailable."
            )

        if error.code in {
            "AUTH_FAILED",
            "AUTH_EXPIRED",
            "AUTH_BLOCKED",
            "ACCESS_DENIED",
        }:
            return ProviderAccessError(
                error.message or "MyMemory access denied."
            )

        if error.code in {
            "LANG_UNSUPPORTED",
            "LANG_PAIR_UNSUPPORTED",
        }:
            return LanguageNotSupportedError(
                error.message or "MyMemory language is not supported."
            )

        if error.code in {
            "INVALID_REQUEST",
            "TEXT_TOO_LONG",
            "REQUEST_TOO_LONG",
            "METHOD_NOT_ALLOWED",
        }:
            return InvalidRequestError(
                error.message or "MyMemory request is invalid."
            )

        return TranslationError(
            error.message or "MyMemory translation failed."
        )
