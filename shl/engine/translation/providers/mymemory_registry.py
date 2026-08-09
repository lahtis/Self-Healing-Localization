"""
File: providers/mymemory_registry.py — Registry for MyMemory language support.
Author: Tuomas Lähteenmäki
License: MIT
Description: Manages localized language validation and runtime learning for unsupported
             MyMemory language pairs to avoid wasteful network API calls.
"""

import time
import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

# Complete ISO / regional language code mapping supported by MyMemory
# frozenset is more performant and explicitly immutable
STANDARD_ISO_CODES = frozenset({
    "af", "sq", "ar", "hy", "az", "eu", "be", "bn", "bs", "bg", "ca", "ceb",
    "zh-cn", "zh-tw", "hr", "cs", "da", "nl", "en", "eo", "et", "tl", "fi",
    "fr", "gl", "ka", "de", "el", "gu", "ht", "ha", "he", "hi", "hmn", "hu",
    "is", "ig", "id", "ga", "it", "ja", "jw", "kn", "kk", "km", "ko", "ku",
    "ky", "lo", "la", "lv", "lt", "lb", "mk", "mg", "ms", "ml", "mt", "mi",
    "mr", "mn", "my", "ne", "no", "ny", "ps", "fa", "pl", "pt", "pt-br", "pa",
    "ro", "ru", "sm", "gd", "sr", "st", "sn", "sd", "si", "sk", "sl", "so",
    "es", "su", "sw", "sv", "tg", "ta", "te", "th", "tr", "uk", "ur", "uz",
    "vi", "cy", "xh", "yi", "yo", "zu"
})


class MyMemoryRegistry:
    """Handles runtime language pair support tracking and blacklisting for MyMemory."""

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
                logger.debug(f"MyMemory pair {pair} is currently blacklisted.")
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
        logger.warning(f"Blacklisted MyMemory language pair {pair} for {self.cache_ttl} seconds due to API error.")

    def clear_blacklist(self) -> None:
        """Resets the runtime tracking cache."""
        self._unsupported_pairs_cache.clear()
