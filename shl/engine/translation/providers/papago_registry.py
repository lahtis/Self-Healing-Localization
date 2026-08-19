"""
Papago language pair registry.
Author: Tuomas Lähteenmäki
License: MIT

Provides runtime blacklist tracking for Papago language pairs.
Static support is determined by provider_cache; this registry only
handles dynamic learning of unsupported pairs (TTL-based).
"""

import time
import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


class PapagoRegistry:
    """Tracks runtime Papago language pair support using TTL-based blacklist."""

    def __init__(self, cache_ttl: float = 86400.0):
        # (source, target) -> expiry_timestamp
        self._unsupported_pairs_cache: Dict[Tuple[str, str], float] = {}
        self.cache_ttl = cache_ttl

    def is_pair_supported(self, source_lang: str, target_lang: str, static_supported: bool) -> bool:
        """
        Check if Papago supports the language pair.

        static_supported:
            Boolean from provider_cache (Papago supports this pair statically).

        Runtime blacklist:
            If Papago has previously failed for this pair, it is temporarily blocked.
        """

        src = source_lang.strip().lower()
        tgt = target_lang.strip().lower()
        pair = (src, tgt)
        now = time.time()

        # 1. Runtime blacklist check
        if pair in self._unsupported_pairs_cache:
            expiry = self._unsupported_pairs_cache[pair]
            if now < expiry:
                logger.debug(f"Papago pair {pair} is currently blacklisted.")
                return False
            else:
                # TTL expired → remove from blacklist
                del self._unsupported_pairs_cache[pair]

        # 2. Static support check (from provider_cache)
        return static_supported

    def mark_pair_unsupported(self, source_lang: str, target_lang: str) -> None:
        """Blacklist Papago language pair for TTL duration."""
        pair = (source_lang.strip().lower(), target_lang.strip().lower())
        self._unsupported_pairs_cache[pair] = time.time() + self.cache_ttl
        logger.warning(
            f"Papago: Blacklisted language pair {pair} for {self.cache_ttl} seconds due to API error."
        )

    def clear_blacklist(self) -> None:
        """Clear all runtime Papago blacklist entries."""
        self._unsupported_pairs_cache.clear()

