"""
LibreTranslate mirror management for SHL.
file: libretranslate_mirrors.py
"""

import json
import logging
import os
import time
from typing import List, Dict, Optional, Any
from urllib.request import Request, urlopen
from urllib.error import URLError

from .. import __version__ as SHL_VERSION
from shl.utils.lang_utils import base_language

logger = logging.getLogger(__name__)

# Mirror statuses
MIRROR_STATUS_UNKNOWN = "unknown"
MIRROR_STATUS_AVAILABLE = "available"
MIRROR_STATUS_UNAVAILABLE = "unavailable"
MIRROR_STATUS_DEGRADED = "degraded"

# Default mirror list
DEFAULT_MIRRORS = [
    {"url": "https://libretranslate.com", "weight": 5, "api_key_env": "LIBRETRANSLATE_API_KEY"},
    {"url": "https://libretranslate.de", "weight": 4},
    {"url": "https://translate.mentality.rip", "weight": 3},
    {"url": "https://translate.astian.org", "weight": 2},
]


class LibreTranslateMirror:
    """Represents a single LibreTranslate mirror instance."""

    def __init__(
        self,
        url: str,
        weight: int = 1,
        api_key_env: Optional[str] = None,
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
        self.supported_languages: Dict[str, str] = {}

    def is_available(self) -> bool:
        """Check if the mirror is available based on cached status."""
        if self.status == MIRROR_STATUS_AVAILABLE:
            return True
        if self.status == MIRROR_STATUS_UNKNOWN:
            return True
        return False

    def get_api_key(self) -> Optional[str]:
        """Retrieve the API key from environment variables."""
        if self.api_key_env:
            return os.environ.get(self.api_key_env)
        return None

    def test(self) -> bool:
        """
        Test the availability and latency of the mirror.
        Returns True if the mirror is operational and responsive.
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
                data = json.loads(response.read().decode("utf-8"))
                
                # Normalize supported languages to base_language format
                self.supported_languages = {
                    base_language(lang["code"]): lang["name"]
                    for lang in data
                    if isinstance(lang, dict) and "code" in lang and "name" in lang
                }

                self.last_latency = (time.time() - start_time) * 1000  # in ms
                self.status = MIRROR_STATUS_AVAILABLE
                self.last_check = time.time()
                self.last_error = ""
                logger.debug(f"Mirror {self.url} available: {len(self.supported_languages)} languages")
                return True

        except (URLError, Exception) as e:
            self.status = MIRROR_STATUS_UNAVAILABLE
            self.last_check = time.time()
            self.last_error = str(e)
            logger.debug(f"Mirror {self.url} unavailable: {e}")
            return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert mirror metadata to a dictionary for persistence or stats."""
        return {
            "url": self.url,
            "weight": self.weight,
            "status": self.status,
            "last_check": self.last_check,
            "last_latency": self.last_latency,
            "last_error": self.last_error,
            "supported_languages_count": len(self.supported_languages),
        }


class LibreTranslateMirrorManager:
    """Manages pool distribution, routing, and health checks for LibreTranslate mirrors."""

    def __init__(
        self,
        mirrors: Optional[List[Dict[str, Any]]] = None,
        test_interval: int = 300,  # 5 minutes
        max_failures: int = 3,
    ):
        self.mirrors: List[LibreTranslateMirror] = []
        self.test_interval = test_interval
        self.max_failures = max_failures

        # Load mirrors from dynamic sources
        if mirrors is None:
            mirrors = self._load_mirrors_from_env()
        self._load_mirrors(mirrors)

    def _load_mirrors_from_env(self) -> List[Dict[str, Any]]:
        """Load unique mirror configurations from .env file and environment variables."""
        found_urls = set()
        mirrors = []

        # 1. Parse local .env file if it exists
        env_file = os.path.join(os.getcwd(), ".env")
        if os.path.exists(env_file):
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("LIBRETRANSLATE_MIRROR_"):
                            _, value = line.split("=", 1)
                            clean_url = value.strip().strip('"').strip("'")
                            if clean_url and clean_url not in found_urls:
                                found_urls.add(clean_url)
                                mirrors.append({"url": clean_url})
            except Exception as e:
                logger.warning(f"Error reading .env for mirrors: {e}")

        # 2. Check active process environment variables
        for key, value in os.environ.items():
            if key.startswith("LIBRETRANSLATE_MIRROR_"):
                clean_url = value.strip().strip('"').strip("'")
                if clean_url and clean_url not in found_urls:
                    found_urls.add(clean_url)
                    mirrors.append({"url": clean_url})

        # 3. Fallback to hardcoded defaults if no custom mirrors are discovered
        if not mirrors:
            mirrors = DEFAULT_MIRRORS

        return mirrors

    def _load_mirrors(self, mirrors: List[Dict[str, Any]]) -> None:
        """Safely instantiate LibreTranslateMirror instances from a raw list."""
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

    def get_best_mirror(self, force_test: bool = False) -> Optional[LibreTranslateMirror]:
        """Select the optimal mirror based on status, weight, and latency boundaries."""
        for mirror in self.mirrors:
            if force_test or (time.time() - mirror.last_check > self.test_interval):
                mirror.test()

        available = [m for m in self.mirrors if m.is_available()]

        if not available:
            # Re-test failed targets if the pool appears completely exhausted
            for mirror in self.mirrors:
                mirror.test()
            available = [m for m in self.mirrors if m.is_available()]

        if not available:
            logger.warning("No LibreTranslate mirrors available")
            return None

        # Primary sorting by weight (descending), secondary by negative latency (faster responses first)
        available.sort(key=lambda m: (m.weight, -m.last_latency if m.last_latency > 0 else 0), reverse=True)
        return available[0]

    def get_mirror_for_language(
        self,
        target_lang: str,
        source_lang: str = "en",
    ) -> Optional[LibreTranslateMirror]:
        """Find the highest priority mirror supporting the requested language pair."""
        target = base_language(target_lang)
        source = base_language(source_lang)

        # Re-verify stale mirrors if necessary
        for mirror in self.mirrors:
            if time.time() - mirror.last_check > self.test_interval:
                mirror.test()

        sorted_mirrors = sorted(
            self.mirrors,
            key=lambda m: (m.weight, -m.last_latency if m.last_latency > 0 else 0),
            reverse=True,
        )

        # 1. Look through currently available mirrors
        for mirror in sorted_mirrors:
            if mirror.is_available():
                if target in mirror.supported_languages and source in mirror.supported_languages:
                    return mirror

        # 2. Fallback: Force global retry if no available mirrors support the pair
        for mirror in self.mirrors:
            mirror.test()
            if mirror.is_available():
                if target in mirror.supported_languages and source in mirror.supported_languages:
                    return mirror

        return None

    def update_mirror_status(self, url: str, available: bool) -> None:
        """Explicitly overwrite a specific mirror's runtime status."""
        clean_url = url.rstrip("/")
        for mirror in self.mirrors:
            if mirror.url == clean_url:
                mirror.status = MIRROR_STATUS_AVAILABLE if available else MIRROR_STATUS_UNAVAILABLE
                mirror.last_check = time.time()
                break

    def get_mirror_stats(self) -> List[Dict[str, Any]]:
        """Collect current structural performance metrics across the cluster."""
        return [m.to_dict() for m in self.mirrors]

    def clear_cache(self) -> None:
        """Reset internal availability cache and forced status tracking flags."""
        for mirror in self.mirrors:
            mirror.status = MIRROR_STATUS_UNKNOWN
            mirror.last_check = 0.0
            mirror.supported_languages = {}
