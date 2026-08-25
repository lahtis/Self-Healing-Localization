"""
File: mymemory.py — module for MyMemory translation adapter.
Author: Tuomas Lähteenmäki
Version: 0.2.6
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

            if response_status in (401, 403):
                raise ProviderAccessError(
                    "MyMemory: access denied"
                )

            if response_status == 429:
                raise RateLimitExceededError(
                    "MyMemory: rate limit exceeded"
                )

            if (
                isinstance(response_status, int)
                and response_status >= 500
            ):
                raise ServiceUnavailableError(
                    "MyMemory: server error "
                    f"{response_status}"
                )

            if response_status == 404:
                raise LanguageNotSupportedError(
                    "MyMemory: language not supported"
                )

            if response_status == 400:
                body = json.dumps(
                    response_data
                ).lower()

                if (
                    "language" in body
                    or "invalid" in body
                ):
                    raise LanguageNotSupportedError(
                        "MyMemory: language not supported"
                    )

                raise InvalidRequestError(
                    "MyMemory: bad request "
                    f"{response_status}"
                )

            if response_status != 200:
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
            if error.code in (401, 403):
                raise ProviderAccessError(
                    f"MyMemory HTTP {error.code}"
                ) from error

            if error.code == 429:
                raise RateLimitExceededError(
                    "MyMemory HTTP 429"
                ) from error

            if error.code >= 500:
                raise ServiceUnavailableError(
                    f"MyMemory HTTP {error.code}"
                ) from error

            if error.code == 404:
                raise LanguageNotSupportedError(
                    "MyMemory: language not supported"
                ) from error

            if error.code == 400:
                try:
                    body = error.read().decode(
                        "utf-8",
                        errors="replace",
                    ).lower()
                except Exception:
                    body = ""

                if (
                    "language" in body
                    or "invalid" in body
                ):
                    raise LanguageNotSupportedError(
                        "MyMemory: language not supported"
                    ) from error

                raise InvalidRequestError(
                    "MyMemory HTTP 400"
                ) from error

            raise TranslationError(
                f"MyMemory HTTP {error.code}"
            ) from error

        except URLError as error:
            if isinstance(
                error.reason,
                (socket.timeout, TimeoutError),
            ):
                raise ServiceUnavailableError(
                    "MyMemory timeout"
                ) from error

            raise ServiceUnavailableError(
                "MyMemory network error: "
                f"{error.reason}"
            ) from error

        except (
            socket.timeout,
            TimeoutError,
        ) as error:
            raise ServiceUnavailableError(
                "MyMemory timeout"
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
