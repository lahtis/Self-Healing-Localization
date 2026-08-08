"""
File: cache.py — module for Translation cache for SHL.
Author: Tuomas Lähteenmäki
Version: 0.2.0
License: MIT
Description:
 - Translation cache for SHL.
"""

import hashlib
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Default TTL for translation cache (1 hour)
TRANSLATION_CACHE_TTL = 3600


class TranslationCache:
    """Translation cache to reduce API calls"""

    def __init__(self, ttl: int = TRANSLATION_CACHE_TTL, max_size: int = 10000):
        self.cache: dict[str, tuple] = {}
        self.ttl = ttl
        self.max_size = max_size

    def _generate_key(self, text: str, source_lang: str, target_lang: str) -> str:
        raw_key = f"{text}:{source_lang}:{target_lang}"
        return hashlib.md5(raw_key.encode("utf-8")).hexdigest()

    def get(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        key = self._generate_key(text, source_lang, target_lang)

        if key in self.cache:
            cached_text, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                logger.debug(f"Cache hit: '{text[:50]}...'")
                return cached_text
            del self.cache[key]

        return None

    def set(self, text: str, translated: str, source_lang: str, target_lang: str) -> None:
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache, key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]

        key = self._generate_key(text, source_lang, target_lang)
        self.cache[key] = (translated, time.time())

    def clear(self) -> None:
        self.cache.clear()

    def size(self) -> int:
        return len(self.cache)
