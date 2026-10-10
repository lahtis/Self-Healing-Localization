"""
File: shl/engine/translation/providers/libretranslate_mirrors.py
Author: Tuomas Lähteenmäki
Version: 0.3.0
License: MIT
Description: LibreTranslate mirror pool management for SHL.

Owns a pool of LibreTranslate mirrors, tracks their health and
latency, and selects the best one per request based on weight and
recent latency.

All outbound HTTP goes through safe_urlopen for SSRF prevention,
redirect validation, and response size limits.
"""

import json
import logging
import os
import time
from typing import Any
from urllib.request import Request

from shl.utils.safe_http import safe_urlopen as urlopen
from shl.utils.safe_http_common import (
    MAX_RESPONSE_BYTES,
    SafeHTTPError,
    read_limited_response,
)

from shl._version import __version__ as SHL_VERSION
from shl.utils.lang_utils import base_language


logger = logging.getLogger(__name__)


# Mirror statuses
MIRROR_STATUS_UNKNOWN = "unknown"
MIRROR_STATUS_AVAILABLE = "available"
MIRROR_STATUS_UNAVAILABLE = "unavailable"
MIRROR_STATUS_DEGRADED = "degraded"


# Default mirror list
DEFAULT_MIRRORS = [
    {
        "url": "https://libretranslate.com",
        "weight": 5,
        "api_key_env": "LIBRETRANSLATE_API_KEY",
    },
    {"url": "https://libretranslate.de", "weight": 4},
]


class LibreTranslateMirror:
    """A single LibreTranslate mirror instance."""

    def __init__(
        self,
        url: str,
        weight: int = 1,
        api_key_env: str | None = None,
        timeout: int = 5,
    ):
        if not url:
            raise ValueError("Mirror URL cannot be empty")

        self.url = url.rstrip("/")
        self.weight = weight
        self.api_key_env = api_key_env
        self.timeout = timeout

        # State initialization
        self.status = MIRROR_STATUS_UNKNOWN
        self.last_check = 0.0
        self.last_latency = 0.0
        self.last_error = ""
        self.supported_languages: dict[str, str] = {}

    def is_available(self) -> bool:
        """Return True if the mirror is believed available.

        A mirror with UNKNOWN status is treated as available so it
        gets a chance to prove itself on the next request.
        """
        if self.status == MIRROR_STATUS_AVAILABLE:
            return True
        if self.status == MIRROR_STATUS_UNKNOWN:
            return True
        return False

    def get_api_key(self) -> str | None:
        """Return the API key from the environment, if configured."""
        if self.api_key_env:
            return os.environ.get(self.api_key_env)
        return None

    def test(self) -> bool:
        """Test availability and latency of the mirror.

        Returns True if the mirror is operational and responsive.

        This method never raises: any failure marks the mirror as
        unavailable and is recorded in ``last_error`` for diagnostics.
        That is intentional for a health check — the caller must be
        able to probe every mirror without exception handling.
        """
        try:
            start_time = time.time()
            url = f"{self.url}/languages"

            req = Request(
                url,
                headers={
                    "User-Agent": f"SHL-Client/{SHL_VERSION}",
                    "Accept": "application/json",
                },
            )

            with urlopen(req, timeout=self.timeout) as response:
                raw = read_limited_response(
                    response,
                    MAX_RESPONSE_BYTES,
                )
                data = json.loads(raw.decode("utf-8"))

            # Normalize supported languages to base_language format.
            self.supported_languages = {
                base_language(lang["code"]): lang["name"]
                for lang in data
                if isinstance(lang, dict)
                and "code" in lang
                and "name" in lang
            }

            self.last_latency = (time.time() - start_time) * 1000
            self.status = MIRROR_STATUS_AVAILABLE
            self.last_check = time.time()
            self.last_error = ""

            logger.debug(
                "Mirror %s available: %d languages",
                self.url,
                len(self.supported_languages),
            )
            return True

        except SafeHTTPError as e:
            self._mark_unavailable(f"HTTP: {e}")
            return False

        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            self._mark_unavailable(f"Invalid response: {e}")
            return False

        except Exception as e:
            # Health checks must not raise. Any unexpected failure is
            # recorded and the mirror is marked unavailable.
            self._mark_unavailable(
                f"{type(e).__name__}: {e}"
            )
            return False

    def _mark_unavailable(self, reason: str) -> None:
        """Mark the mirror unavailable and record the reason."""
        self.status = MIRROR_STATUS_UNAVAILABLE
        self.last_check = time.time()
        self.last_error = reason
        logger.debug("Mirror %s unavailable: %s", self.url, reason)

    def to_dict(self) -> dict[str, Any]:
        """Return mirror metadata as a dictionary for stats or persistence."""
        return {
            "url": self.url,
            "weight": self.weight,
            "status": self.status,
            "last_check": self.last_check,
            "last_latency": self.last_latency,
            "last_error": self.last_error,
            "supported_languages_count": len(
                self.supported_languages
            ),
        }


class LibreTranslateMirrorManager:
    """Manages pool distribution, routing, and health checks for
    LibreTranslate mirrors.
    """

    def __init__(
        self,
        mirrors: list[dict[str, Any]] | None = None,
        test_interval: int = 300,  # 5 minutes
        max_failures: int = 3,
    ):
        self.mirrors: list[LibreTranslateMirror] = []
        self.test_interval = test_interval
        self.max_failures = max_failures

        if mirrors is None:
            mirrors = self._load_mirrors_from_env()

        self._load_mirrors(mirrors)

    def _load_mirrors_from_env(self) -> list[dict[str, Any]]:
        """Load unique mirror configurations from .env and environment
        variables.
        """
        found_urls: set[str] = set()
        mirrors: list[dict[str, Any]] = []

        # 1. Parse local .env file if it exists.
        env_file = os.path.join(os.getcwd(), ".env")

        if os.path.exists(env_file):
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()

                        if line.startswith("LIBRETRANSLATE_MIRROR_"):
                            _, value = line.split("=", 1)
                            clean_url = (
                                value.strip().strip('"').strip("'")
                            )

                            if clean_url and clean_url not in found_urls:
                                found_urls.add(clean_url)
                                mirrors.append({"url": clean_url})
            except OSError as e:
                logger.warning(
                    "Error reading .env for mirrors: %s",
                    e,
                )

        # 2. Check active process environment variables.
        for key, value in os.environ.items():
            if key.startswith("LIBRETRANSLATE_MIRROR_"):
                clean_url = value.strip().strip('"').strip("'")

                if clean_url and clean_url not in found_urls:
                    found_urls.add(clean_url)
                    mirrors.append({"url": clean_url})

        # 3. Fallback to hardcoded defaults if nothing custom was found.
        if not mirrors:
            mirrors = DEFAULT_MIRRORS

        return mirrors

    def _load_mirrors(
        self,
        mirrors: list[dict[str, Any]],
    ) -> None:
        """Instantiate LibreTranslateMirror objects from raw config."""
        self.mirrors = []

        for mirror_data in mirrors:
            if isinstance(mirror_data, str):
                mirror_data = {"url": mirror_data}

            url = mirror_data.get("url")
            if not url:
                continue

            self.mirrors.append(
                LibreTranslateMirror(
                    url=url,
                    weight=mirror_data.get("weight", 1),
                    api_key_env=mirror_data.get("api_key_env"),
                    timeout=mirror_data.get("timeout", 5),
                )
            )

    def get_best_mirror(
        self,
        force_test: bool = False,
    ) -> LibreTranslateMirror | None:
        """Select the optimal mirror based on status, weight, and
        latency.
        """
        for mirror in self.mirrors:
            if force_test or (
                time.time() - mirror.last_check
                > self.test_interval
            ):
                mirror.test()

        available = [m for m in self.mirrors if m.is_available()]

        if not available:
            # Re-test failed targets if the pool appears exhausted.
            for mirror in self.mirrors:
                mirror.test()
            available = [m for m in self.mirrors if m.is_available()]

        if not available:
            logger.warning("No LibreTranslate mirrors available")
            return None

        # Primary sort by weight (descending), secondary by recent
        # latency (faster responses first).
        available.sort(
            key=lambda m: (
                m.weight,
                -m.last_latency if m.last_latency > 0 else 0,
            ),
            reverse=True,
        )
        return available[0]

    def get_mirror_for_language(
        self,
        target_lang: str,
        source_lang: str = "en",
    ) -> LibreTranslateMirror | None:
        """Return the highest-priority mirror that supports the pair."""
        target = base_language(target_lang)
        source = base_language(source_lang)

        # Re-verify stale mirrors if necessary.
        for mirror in self.mirrors:
            if (
                time.time() - mirror.last_check
                > self.test_interval
            ):
                mirror.test()

        sorted_mirrors = sorted(
            self.mirrors,
            key=lambda m: (
                m.weight,
                -m.last_latency if m.last_latency > 0 else 0,
            ),
            reverse=True,
        )

        # 1. Look through currently available mirrors.
        for mirror in sorted_mirrors:
            if mirror.is_available():
                if (
                    target in mirror.supported_languages
                    and source in mirror.supported_languages
                ):
                    return mirror

        # 2. Fallback: force a global retry if nothing eligible
        #    supports the pair.
        for mirror in self.mirrors:
            mirror.test()

            if mirror.is_available():
                if (
                    target in mirror.supported_languages
                    and source in mirror.supported_languages
                ):
                    return mirror

        return None

    def update_mirror_status(
        self,
        url: str,
        available: bool,
    ) -> None:
        """Overwrite a specific mirror's runtime status."""
        clean_url = url.rstrip("/")

        for mirror in self.mirrors:
            if mirror.url == clean_url:
                mirror.status = (
                    MIRROR_STATUS_AVAILABLE
                    if available
                    else MIRROR_STATUS_UNAVAILABLE
                )
                mirror.last_check = time.time()
                break

    def get_mirror_stats(self) -> list[dict[str, Any]]:
        """Return current per-mirror performance metrics."""
        return [m.to_dict() for m in self.mirrors]

    def clear_cache(self) -> None:
        """Reset internal availability cache and status flags."""
        for mirror in self.mirrors:
            mirror.status = MIRROR_STATUS_UNKNOWN
            mirror.last_check = 0.0
            mirror.supported_languages = {}
