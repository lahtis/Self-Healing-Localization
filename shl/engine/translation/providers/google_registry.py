"""
File: shl/engine/translation/providers/google_registry.py
Author: Tuomas Lähteenmäki
Version: 0.3.0
License: MIT
Description:
    Manages localized language validation and runtime learning for
    unsupported Google Cloud Translation language pairs to avoid
    wasteful network API calls.

    Uses ISO 639-1 / BCP-47 standard language code mapping.

    This module performs no HTTP calls. It only tracks which pairs
    Google has rejected at runtime.
"""

import logging
import time


logger = logging.getLogger(__name__)


# Local fallback set of Google Cloud Translation language codes.
# Used for fast pre-validation before making a network request.
# The Google API remains the final authority for actual support.
_STANDARD_ISO_CODES_RAW = frozenset({
    "af", "am", "ar", "az", "be", "bg", "bn", "bs", "ca", "ceb",
    "co", "cs", "cy", "da", "de", "el", "en", "eo", "es", "et",
    "eu", "fa", "fi", "fr", "fy", "ga", "gd", "gl", "gu", "ha",
    "haw", "he", "hi", "hmn", "hr", "ht", "hu", "hy", "id", "ig",
    "is", "it", "ja", "jv", "ka", "kk", "km", "kn", "ko", "ku",
    "ky", "la", "lb", "lo", "lt", "lv", "mg", "mi", "mk", "ml",
    "mn", "mr", "ms", "mt", "my", "ne", "nl", "no", "ny", "or",
    "pa", "pl", "ps", "pt", "pt-BR", "pt-PT", "ro", "ru", "rw",
    "sd", "si", "sk", "sl", "sm", "sn", "so", "sq", "sr", "st",
    "su", "sv", "sw", "ta", "te", "tg", "th", "tk", "tl", "tr",
    "tt", "ug", "uk", "ur", "uz", "vi", "xh", "yi", "yo", "zh",
    "zh-CN", "zh-TW", "zu",
})

STANDARD_ISO_CODES = frozenset(
    code.lower() for code in _STANDARD_ISO_CODES_RAW
)


class GoogleRegistry:
    """Runtime language pair support tracking and blacklisting for
    Google Cloud Translation.

    A pair is considered supported if both language codes appear in
    the local ISO set and the pair is not currently blacklisted by a
    prior runtime failure. The local set is a fast pre-filter; the
    Google API remains the final authority.
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

        src = source_lang.strip().lower()
        tgt = target_lang.strip().lower()
        pair = (src, tgt)
        now = time.time()

        # 1. Check the runtime blacklist.
        if pair in self._unsupported_pairs_cache:
            expiry = self._unsupported_pairs_cache[pair]

            if now < expiry:
                logger.debug(
                    "Google Translate pair %s is currently blacklisted.",
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
            source_lang.strip().lower(),
            target_lang.strip().lower(),
        )
        self._unsupported_pairs_cache[pair] = (
            time.time() + self.cache_ttl
        )

        logger.warning(
            "Blacklisted Google Translate language pair %s for %.1f "
            "seconds due to API error.",
            pair,
            self.cache_ttl,
        )

    def clear_blacklist(self) -> None:
        """Reset the runtime tracking cache."""
        self._unsupported_pairs_cache.clear()
