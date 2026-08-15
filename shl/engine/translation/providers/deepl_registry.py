"""
File: providers/deepl_registry.py — Registry for DeepL translation language support.
Author: Tuomas Lähteenmäki
License: MIT
Description: Manages localized language validation and runtime learning for unsupported
             DeepL language pairs to avoid wasteful network API calls.
             Uses ISO 639-1 / BCP-47 standard language code mapping.
"""

import time
import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

# DeepL-documented supported languages (ISO 639-1 + BCP-47 variants)
DEEPL_SUPPORTED_LANGUAGES_RAW = frozenset({
    "bg", "cs", "da", "de", "el",
    "en", "en-US", "en-GB",
    "es", "et", "fi", "fr", "hu", "id",
    "it", "ja", "ko", "lt", "lv", "nb",
    "nl", "pl",
    "pt", "pt-BR", "pt-PT",
    "ro", "ru", "sk", "sl", "sv",
    "tr", "uk",
    "zh", "zh-CN", "zh-TW"
})

DEEPL_SUPPORTED_LANGUAGES = frozenset(
    code.lower() for code in DEEPL_SUPPORTED_LANGUAGES_RAW
)


class DeepLRegistry:
    """
    Handles runtime language pair support tracking and blacklisting for DeepL.
    Prevents repeated network calls for unsupported language pairs.
    """

    def __init__(self, cache_ttl: float = 86400.0):
        # Dynamic memory cache for failed language pairs: (source, target) -> expiry_timestamp
        self._unsupported_pairs_cache: Dict[Tuple[str, str], float] = {}
        self.cache_ttl = cache_ttl

    def is_pair_supported(self, source_lang: str, target_lang: str) -> bool:
        """
        Validates if the language pair is supported using local DeepL language codes
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
                logger.debug(f"DeepL pair {pair} is currently blacklisted.")
                return False
            else:
                # TTL expired → allow re-testing
                del self._unsupported_pairs_cache[pair]

        # 2. Local DeepL language support validation
        return src in DEEPL_SUPPORTED_LANGUAGES and tgt in DEEPL_SUPPORTED_LANGUAGES

    def mark_pair_unsupported(self, source_lang: str, target_lang: str) -> None:
        """Blacklists an unmappable language pair for the duration of the TTL."""
        pair = (source_lang.strip().lower(), target_lang.strip().lower())
        self._unsupported_pairs_cache[pair] = time.time() + self.cache_ttl
        logger.warning(
            f"Blacklisted DeepL language pair {pair} for {self.cache_ttl} seconds due to API error."
        )

    def clear_blacklist(self) -> None:
        """Resets the runtime tracking cache."""
        self._unsupported_pairs_cache.clear()

