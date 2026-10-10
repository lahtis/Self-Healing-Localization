"""
File: shl/engine/translation/providers/yandex_registry.py
Author: Tuomas Lähteenmäki
Version: 0.3.0
License: MIT
Description:
    Manages localized language validation and runtime learning for
    unsupported Yandex Cloud Translate language pairs to avoid wasteful
    network API calls.

    The supported-language set lives in yandex_languages.py as the
    single source of truth; this module only adds runtime blacklist
    tracking on top.

    This module performs no HTTP calls. It only tracks which pairs
    Yandex has rejected at runtime.
"""

import logging
import time

from .yandex_languages import YANDEX_SUPPORTED_LANGUAGES_RAW


logger = logging.getLogger(__name__)


# Normalize the shared language set once at import time.
YANDEX_SUPPORTED_LANGUAGES = frozenset(
    code.lower() for code in YANDEX_SUPPORTED_LANGUAGES_RAW
)


class YandexRegistry:
    """Runtime language pair support tracking and blacklisting for
    Yandex Cloud Translate.

    A pair is considered supported if both language codes appear in
    the shared Yandex language set and the pair is not currently
    blacklisted by a prior runtime failure.
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
        """Validate a pair using local Yandex language codes and the
        runtime blacklist. Zero network overhead.
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
                    "Yandex pair %s is currently blacklisted.",
                    pair,
                )
                return False

            # TTL expired; allow the pair to be tested again.
            del self._unsupported_pairs_cache[pair]

        # 2. Local Yandex language support validation.
        return (
            src in YANDEX_SUPPORTED_LANGUAGES
            and tgt in YANDEX_SUPPORTED_LANGUAGES
        )

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
            "Blacklisted Yandex language pair %s for %.1f seconds "
            "due to API error.",
            pair,
            self.cache_ttl,
        )

    def clear_blacklist(self) -> None:
        """Reset the runtime tracking cache."""
        self._unsupported_pairs_cache.clear()
