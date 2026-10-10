"""
File: shl/engine/translation/providers/mymemory_registry.py
Author: Tuomas Lähteenmäki
Version: 0.3.0
License: MIT
Description:
    Manages localized language validation and runtime learning for
    unsupported MyMemory language pairs to avoid wasteful network API
    calls.

    This module performs no HTTP calls. It only tracks which pairs
    MyMemory has rejected at runtime.
"""

import logging
import time


logger = logging.getLogger(__name__)


# Complete ISO / regional language code mapping supported by MyMemory.
# A frozenset is more performant than a list and explicitly immutable.
STANDARD_ISO_CODES = frozenset({
    "af", "sq", "ar", "hy", "az", "eu", "be", "bn", "bs", "bg",
    "ca", "ceb", "zh-cn", "zh-tw", "hr", "cs", "da", "nl", "en",
    "eo", "et", "tl", "fi", "fr", "gl", "ka", "de", "el", "gu",
    "ht", "ha", "he", "hi", "hmn", "hu", "is", "ig", "id", "ga",
    "it", "ja", "jw", "kn", "kk", "km", "ko", "ku", "ky", "lo",
    "la", "lv", "lt", "lb", "mk", "mg", "ms", "ml", "mt", "mi",
    "mr", "mn", "my", "ne", "no", "ny", "ps", "fa", "pl", "pt",
    "pt-br", "pa", "ro", "ru", "sm", "gd", "sr", "st", "sn", "sd",
    "si", "sk", "sl", "so", "es", "su", "sw", "sv", "tg", "ta",
    "te", "th", "tr", "uk", "ur", "uz", "vi", "cy", "xh", "yi",
    "yo", "zu",
})


class MyMemoryRegistry:
    """Runtime language pair support tracking and blacklisting for
    MyMemory.

    A pair is considered supported if both language codes appear in
    the local ISO set and the pair is not currently blacklisted by a
    prior runtime failure.
    """

    def __init__(self, cache_ttl: float = 86400.0):
        # Runtime blacklist:
        # (source, target) -> expiry timestamp
        self._unsupported_pairs_cache: dict[
            tuple[str, str], float
        ] = {}
        self.cache_ttl = cache_ttl

    def is_pair_supported(
        self,
        source_lang: str,
        target_lang: str,
    ) -> bool:
        """Validate a pair using local ISO codes and the runtime
        blacklist. Zero network overhead.
        """

        src = source_lang.lower().strip()
        tgt = target_lang.lower().strip()
        pair = (src, tgt)
        now = time.time()

        # 1. Check the runtime blacklist.
        if pair in self._unsupported_pairs_cache:
            expiry = self._unsupported_pairs_cache[pair]

            if now < expiry:
                logger.debug(
                    "MyMemory pair %s is currently blacklisted.",
                    pair,
                )
                return False

            # TTL expired; allow the pair to be tested again.
            del self._unsupported_pairs_cache[pair]

        # 2. Local fallback verification against supported code set.
        return src in STANDARD_ISO_CODES and tgt in STANDARD_ISO_CODES

    def mark_pair_unsupported(
        self,
        source_lang: str,
        target_lang: str,
    ) -> None:
        """Blacklist an unmappable language pair for the TTL duration."""
        pair = (
            source_lang.lower().strip(),
            target_lang.lower().strip(),
        )
        self._unsupported_pairs_cache[pair] = (
            time.time() + self.cache_ttl
        )

        logger.warning(
            "Blacklisted MyMemory language pair %s for %.1f seconds "
            "due to API error.",
            pair,
            self.cache_ttl,
        )

    def clear_blacklist(self) -> None:
        """Reset the runtime tracking cache."""
        self._unsupported_pairs_cache.clear()
