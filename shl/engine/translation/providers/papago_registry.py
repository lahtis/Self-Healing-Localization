"""
File: shl/engine/translation/providers/papago_registry.py
Author: Tuomas Lähteenmäki
Version: 0.3.0
License: MIT
Description:
    Runtime blacklist tracking for Papago language pairs.

    Static support is determined by the caller (from provider_cache);
    this registry only handles dynamic learning of unsupported pairs
    with a TTL-based blacklist.

    This module performs no HTTP calls. It only tracks which pairs
    Papago has rejected at runtime.
"""

import logging
import time


logger = logging.getLogger(__name__)


class PapagoRegistry:
    """Runtime language pair support tracking and blacklisting for
    Papago.

    Unlike the other provider registries, static language support is
    not decided here — the caller passes a ``static_supported`` flag.
    This registry only tracks pairs that Papago rejected at runtime.
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
        static_supported: bool,
    ) -> bool:
        """Check if Papago supports the language pair.

        Args:
            source_lang: Source language code.
            target_lang: Target language code.
            static_supported: Boolean from provider_cache indicating
                whether Papago supports this pair statically. The
                registry trusts this value and only adds a runtime
                blacklist check on top.

        Returns:
            False if the pair is currently blacklisted, otherwise
            the value of ``static_supported``.
        """

        src = source_lang.strip().lower()
        tgt = target_lang.strip().lower()
        pair = (src, tgt)
        now = time.time()

        # 1. Runtime blacklist check.
        if pair in self._unsupported_pairs_cache:
            expiry = self._unsupported_pairs_cache[pair]

            if now < expiry:
                logger.debug(
                    "Papago pair %s is currently blacklisted.",
                    pair,
                )
                return False

            # TTL expired; allow the pair to be tested again.
            del self._unsupported_pairs_cache[pair]

        # 2. Static support check (supplied by the caller).
        return static_supported

    def mark_pair_unsupported(
        self,
        source_lang: str,
        target_lang: str,
    ) -> None:
        """Blacklist a Papago language pair for the TTL duration."""
        pair = (
            source_lang.strip().lower(),
            target_lang.strip().lower(),
        )
        self._unsupported_pairs_cache[pair] = (
            time.time() + self.cache_ttl
        )

        logger.warning(
            "Papago: Blacklisted language pair %s for %.1f seconds "
            "due to API error.",
            pair,
            self.cache_ttl,
        )

    def clear_blacklist(self) -> None:
        """Clear all runtime Papago blacklist entries."""
        self._unsupported_pairs_cache.clear()
