"""
File: providers/google_registry.py — Registry for Google Cloud Translation language support.
Author: Tuomas Lähteenmäki
License: MIT
Description: Manages localized language validation and runtime learning for unsupported
             Google Cloud Translation language pairs to avoid wasteful network API calls.
             Uses ISO 639-1 / BCP-47 standard language code mapping.
"""

import time
import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

# Local fallback set of Google Cloud Translation language codes.
# Used for fast pre-validation before making a network request.
# The Google API remains the final authority for actual support.

STANDARD_ISO_CODES_RAW = frozenset({
    "af", "am", "ar", "az", "be", "bg", "bn", "bs", "ca", "ceb", "co", "cs", "cy", "da",
    "de", "el", "en", "eo", "es", "et", "eu", "fa", "fi", "fr", "fy", "ga", "gd", "gl",
    "gu", "ha", "haw", "he", "hi", "hmn", "hr", "ht", "hu", "hy", "id", "ig", "is", "it",
    "ja", "jv", "ka", "kk", "km", "kn", "ko", "ku", "ky", "la", "lb", "lo", "lt", "lv",
    "mg", "mi", "mk", "ml", "mn", "mr", "ms", "mt", "my", "ne", "nl", "no", "ny", "or",
    "pa", "pl", "ps", "pt", "pt-BR", "pt-PT", "ro", "ru", "rw", "sd", "si", "sk", "sl",
    "sm", "sn", "so", "sq", "sr", "st", "su", "sv", "sw", "ta", "te", "tg", "th", "tk",
    "tl", "tr", "tt", "ug", "uk", "ur", "uz", "vi", "xh", "yi", "yo", "zh", "zh-CN", "zh-TW", "zu"
})

STANDARD_ISO_CODES = frozenset(
    code.lower()
    for code in STANDARD_ISO_CODES_RAW
)


class GoogleRegistry:
    """Handles runtime language pair support tracking and blacklisting for Google Cloud Translation."""

    def __init__(self, cache_ttl: float = 86400.0):
        # Dynamic memory cache for failed language pairs: (source, target) -> expiry_timestamp
        self._unsupported_pairs_cache: Dict[Tuple[str, str], float] = {}
        self.cache_ttl = cache_ttl

    def is_pair_supported(self, source_lang: str, target_lang: str) -> bool:
        """
        Validates if the language pair is supported using local ISO codes 
        and the runtime error blacklist. Zero network overhead.
        """
        src = source_lang.strip().lower()
        tgt = target_lang.strip().lower()
        pair = (src, tgt)
        now = time.time()

        # 1. Check if temporarily blacklisted due to prior runtime API failure
        if pair in self._unsupported_pairs_cache:
            expiry = self._unsupported_pairs_cache[pair]
            if now < expiry:
                logger.debug(f"Google Translate pair {pair} is currently blacklisted.")
                return False
            else:
                # TTL expired, evict from blacklist to allow re-testing
                del self._unsupported_pairs_cache[pair]

        # 2. Local fallback verification against complete supported code set
        return src in STANDARD_ISO_CODES and tgt in STANDARD_ISO_CODES

    def mark_pair_unsupported(self, source_lang: str, target_lang: str) -> None:
        """Blacklists an unmappable language pair for the duration of the TTL."""
        pair = (source_lang.strip().lower(), target_lang.strip().lower())
        self._unsupported_pairs_cache[pair] = time.time() + self.cache_ttl
        logger.warning(
            f"Blacklisted Google Translate language pair {pair} for {self.cache_ttl} seconds due to API error."
        )

    def clear_blacklist(self) -> None:
        """Resets the runtime tracking cache."""
        self._unsupported_pairs_cache.clear()
