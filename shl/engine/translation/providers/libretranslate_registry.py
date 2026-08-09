"""
File: providers/libretranslate_registry.py — Registry for LibreTranslate language support.
Author: Tuomas Lähteenmäki
License: MIT
Description: Manages localized language validation and runtime learning for unsupported
             LibreTranslate language pairs to avoid wasteful network API calls.
             Uses strict Argos OpenNMT index mapping (pb, zh, zt).
"""

import time
import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

# Complete language code mapping officially supported by standard LibreTranslate instances.
# Strictly matches the official argosmin-index constraints (e.g., 'pb', 'zh', 'zt').
STANDARD_ISO_CODES = frozenset({
    "ar", "az", "bg", "bn", "ca", "cs", "da", "de", "el", "en", "eo", "es",
    "et", "eu", "fa", "fi", "fr", "ga", "gl", "he", "hi", "hu", "id", "it",
    "ja", "ko", "ky", "lt", "lv", "ms", "nb", "nl", "pb", "pl", "pt", "ro",
    "ru", "sk", "sl", "sq", "sv", "th", "tl", "tr", "uk", "ur", "vi", "zh", "zt"
})


class LibreTranslateRegistry:
    """Handles runtime language pair support tracking and blacklisting for LibreTranslate."""

    def __init__(self, cache_ttl: float = 86400.0):
        # Dynamic memory cache for failed language pairs: (source, target) -> expiry_timestamp
        self._unsupported_pairs_cache: Dict[Tuple[str, str], float] = {}
        self.cache_ttl = cache_ttl

    def is_pair_supported(self, source_lang: str, target_lang: str) -> bool:
        """
        Validates if the language pair is supported using local ISO codes 
        and the runtime error blacklist. Zero network overhead.
        """
        src = source_lang.lower().strip()
        tgt = target_lang.lower().strip()
        pair = (src, tgt)
        now = time.time()

        # 1. Check if temporarily blacklisted due to prior runtime API failure
        if pair in self._unsupported_pairs_cache:
            expiry = self._unsupported_pairs_cache[pair]
            if now < expiry:
                logger.debug(f"LibreTranslate pair {pair} is currently blacklisted.")
                return False
            else:
                # TTL expired, evict from blacklist to allow re-testing
                del self._unsupported_pairs_cache[pair]

        # 2. Local fallback verification against complete supported code set
        return src in STANDARD_ISO_CODES and tgt in STANDARD_ISO_CODES

    def mark_pair_unsupported(self, source_lang: str, target_lang: str) -> None:
        """Blacklists an unmappable language pair for the duration of the TTL."""
        pair = (source_lang.lower().strip(), target_lang.lower().strip())
        self._unsupported_pairs_cache[pair] = time.time() + self.cache_ttl
        logger.warning(f"Blacklisted LibreTranslate language pair {pair} for {self.cache_ttl} seconds due to API error.")

    def clear_blacklist(self) -> None:
        """Resets the runtime tracking cache."""
        self._unsupported_pairs_cache.clear()
