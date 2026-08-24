"""
File: providers/yandex_registry.py — Registry for Yandex translation language support.
Author: Tuomas Lähteenmäki
Version: 0.2.6
License: MIT
Description: Manages localized language validation and runtime learning for unsupported
             Yandex Cloud Translate language pairs to avoid wasteful network API calls.
             Uses ISO 639-1 / BCP-47 standard language code mapping.
"""

import time
import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

# Yandex Cloud Translate laajasti tuetut kielet (ISO 639-1 / keskeiset koodit)
YANDEX_SUPPORTED_LANGUAGES_RAW = frozenset({
    "af", "am", "ar", "az", "ba", "be", "bg", "bn", "bs", "ca", 
    "ceb", "cs", "cy", "da", "de", "el", "en", "eo", "es", "et", 
    "eu", "fa", "fi", "fr", "ga", "gd", "gl", "gu", "he", "hi", 
    "hr", "ht", "hu", "hy", "id", "is", "it", "ja", "jv", "ka", 
    "kk", "km", "kn", "ko", "ky", "la", "lb", "lo", "lt", "lv", 
    "mg", "mhr", "mi", "mk", "ml", "mn", "mr", "mrj", "ms", "mt", 
    "my", "ne", "nl", "no", "pa", "pap", "pl", "pt", "ro", "ru", 
    "sah", "si", "sk", "sl", "sq", "sr", "su", "sv", "sw", "ta", 
    "te", "tg", "th", "tl", "tr", "tt", "udm", "uk", "ur", "uz", 
    "vi", "xh", "yi", "zh"
})

YANDEX_SUPPORTED_LANGUAGES = frozenset(
    code.lower() for code in YANDEX_SUPPORTED_LANGUAGES_RAW
)


class YandexRegistry:
    """
    Handles runtime language pair support tracking and blacklisting for Yandex.
    Prevents repeated network calls for unsupported language pairs.
    """

    def __init__(self, cache_ttl: float = 86400.0):
        # Dynamic memory cache for failed language pairs: (source, target) -> expiry_timestamp
        self._unsupported_pairs_cache: Dict[Tuple[str, str], float] = {}
        self.cache_ttl = cache_ttl

    def is_pair_supported(self, source_lang: str, target_lang: str) -> bool:
        """
        Validates if the language pair is supported using local Yandex language codes
        and the runtime error blacklist. Zero network overhead.
        """
        src = source_lang.strip().lower()
        tgt = target_lang.strip().lower()
        pair = (src, tgt)
        now = time.time()

        # 1. Check runtime blacklist
        if pair in self._unsupported_pairs_cache:
            expiry = self._unsupported_pairs_cache[pair]
            if now < expiry:
                logger.debug(f"Yandex pair {pair} is currently blacklisted.")
                return False
            else:
                # TTL expired → allow re-testing
                del self._unsupported_pairs_cache[pair]

        # 2. Local Yandex language support validation
        return src in YANDEX_SUPPORTED_LANGUAGES and tgt in YANDEX_SUPPORTED_LANGUAGES

    def mark_pair_unsupported(self, source_lang: str, target_lang: str) -> None:
        """Blacklists an unmappable language pair for the duration of the TTL."""
        pair = (source_lang.strip().lower(), target_lang.strip().lower())
        self._unsupported_pairs_cache[pair] = time.time() + self.cache_ttl
        logger.warning(
            f"Blacklisted Yandex language pair {pair} for {self.cache_ttl} seconds due to API error."
        )

    def clear_blacklist(self) -> None:
        """Resets the runtime tracking cache."""
        self._unsupported_pairs_cache.clear()
