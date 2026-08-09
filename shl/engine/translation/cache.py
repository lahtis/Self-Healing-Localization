"""
File: cache.py — module for Translation cache for SHL.
Author: Tuomas Lähteenmäki
Version: 0.2.0
License: MIT
Description: Memory-backed in-memory translation cache for SHL client requests.
             Prevents duplicate remote API calls by caching distinct language-pair hashes
             with maximum limit evictions and configurable TTL enforcement.
"""

import hashlib
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Default TTL for translation cache (1 hour)
TRANSLATION_CACHE_TTL = 3600


class TranslationCache:
    """Translation cache layer designed to intercept and optimize repeated provider calls."""

    def __init__(self, ttl: int = TRANSLATION_CACHE_TTL, max_size: int = 10000):
        self.cache: dict[str, tuple] = {}
        self.ttl = ttl
        self.max_size = max_size

    def _generate_key(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        formality: Optional[str] = None,
        context_type: Optional[str] = None,
    ) -> str:
        """Create a unique deterministic MD5 hex digest representing the transaction footprint."""
        raw_key = f"{text}:{source_lang}:{target_lang}:{formality or ''}:{context_type or ''}"
        return hashlib.md5(raw_key.encode("utf-8")).hexdigest()

    def get(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        formality: Optional[str] = None,
        context_type: Optional[str] = None,
    ) -> Optional[str]:
        """
        Retrieve localized strings from memory if signature is fresh.
        Returns None if cache is missing or contents have expired past TTL boundary.
        """
        key = self._generate_key(text, source_lang, target_lang, formality, context_type)

        if key in self.cache:
            cached_text, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                logger.debug(f"Cache hit: '{text[:50]}...'")
                return cached_text

            # Evict localized text block explicitly if stale
            del self.cache[key]

        return None

    def set(
        self,
        text: str,
        translated: str,
        source_lang: str,
        target_lang: str,
        formality: Optional[str] = None,
        context_type: Optional[str] = None,
    ) -> None:
        """Commit an evaluated translation string into the tracking dictionary."""
        if len(self.cache) >= self.max_size:
            self._evict_stale_or_oldest()

        key = self._generate_key(text, source_lang, target_lang, formality, context_type)
        self.cache[key] = (translated, time.time())

    def _evict_stale_or_oldest(self) -> None:
        """Internal memory maintenance subroutine to free tracking indices."""
        now = time.time()
        stale_keys = [k for k, v in self.cache.items() if now - v[1] >= self.ttl]

        if stale_keys:
            for k in stale_keys:
                del self.cache[k]
            logger.debug(f"Evicted {len(stale_keys)} expired strings from cache memory footprint")
        else:
            oldest_key = min(self.cache, key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]

    def clear(self) -> None:
        """Flush all structural references inside the local context map."""
        self.cache.clear()
        logger.info("Translation cache fully cleared")

    def size(self) -> int:
        """Return the current cumulative index assignment count."""
        return len(self.cache)
