"""
File: shl/engine/translation/providers/libretranslate_registry.py
Author: Tuomas Lähteenmäki
Version: 0.3.0
License: MIT
Description:
    Manages localized language validation and runtime learning for
    unsupported LibreTranslate language pairs to avoid wasteful
    network API calls.

    Uses strict Argos OpenNMT index mapping (pb, zh, zt).

    This module performs no HTTP calls. It only tracks which pairs
    LibreTranslate has rejected at runtime.
"""

import logging
import time


logger = logging.getLogger(__name__)


# Complete language code mapping officially supported by standard
# LibreTranslate instances. Strictly matches the official
# argosmin-index constraints (e.g. 'pb', 'zh', 'zt').
STANDARD_ISO_CODES = frozenset({
    "ar", "az", "bg", "bn", "ca", "cs", "da", "de", "el", "en",
    "eo", "es", "et", "eu", "fa", "fi", "fr", "ga", "gl", "he",
    "hi", "hu", "id", "it", "ja", "ko", "ky", "lt", "lv", "ms",
    "nb", "nl", "pb", "pl", "pt", "ro", "ru", "sk", "sl", "sq",
    "sv", "th", "tl", "tr", "uk", "ur", "vi", "zh", "zt",
})


class LibreTranslateRegistry:
    """Runtime language pair support tracking and blacklisting for
    LibreTranslate.

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
                    "LibreTranslate pair %s is currently blacklisted.",
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
            "Blacklisted LibreTranslate language pair %s for %.1f "
            "seconds due to API error.",
            pair,
            self.cache_ttl,
        )

    def clear_blacklist(self) -> None:
        """Reset the runtime tracking cache."""
        self._unsupported_pairs_cache.clear()
