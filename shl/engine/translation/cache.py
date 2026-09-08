"""
File: cache.py — Translation cache for SHL.
Author: Tuomas Lähteenmäki
Version: 0.2.5-persist
License: MIT
Description: Memory-backed translation cache with optional disk persistence.
             Prevents duplicate remote API calls with TTL, max_size eviction,
             and optional JSON persistence for warm starts and debugging.
"""

import hashlib
import json
import logging
import time
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

TRANSLATION_CACHE_TTL = 3600


class TranslationCache:
    """
    Translation cache with optional disk persistence.

    Args:
        ttl: Time-to-live in seconds (default 3600 = 1h).
        max_size: Maximum number of entries before eviction (default 10000).
        persist: Save cache to disk for warm starts (default False).
        persist_path: Path for persistence file. Default: <CWD>/.shl_cache.json
    """

    def __init__(
        self,
        ttl: int = TRANSLATION_CACHE_TTL,
        max_size: int = 10000,
        persist: bool = True,
        persist_path: Optional[str] = None,
    ):
        self.cache: dict[str, tuple] = {}
        self.ttl = ttl
        self.max_size = max_size
        self.persist = persist
        self.persist_path = Path(persist_path) if persist_path else Path.cwd() / ".shl_cache.json"
        self._lock = threading.RLock()
        self._dirty = False
        self._last_save = 0.0

        if self.persist:
            self._load_from_disk()

    # ------------------------------------------------------------------
    # KEY GENERATION (existing MD5 logic preserved)
    # ------------------------------------------------------------------

    def _generate_key(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        formality: Optional[str] = None,
        context_type: Optional[str] = None,
    ) -> str:
        """Create a unique deterministic MD5 hex digest."""
        raw_key = f"{text}:{source_lang}:{target_lang}:{formality or ''}:{context_type or ''}"
        return hashlib.md5(raw_key.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # DISK PERSISTENCE (new)
    # ------------------------------------------------------------------

    def _load_from_disk(self) -> None:
        """Load cache entries from disk on startup."""
        if not self.persist_path.exists():
            return

        try:
            with self.persist_path.open("r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                return

            now = time.time()
            loaded = 0
            with self._lock:
                for key, entry in data.items():
                    if not isinstance(entry, list) or len(entry) != 2:
                        continue
                    cached_text, timestamp = entry
                    if cached_text is None:
                        continue
                    if now - timestamp > self.ttl:
                        continue  # Expired, skip
                    self.cache[key] = (cached_text, timestamp)
                    loaded += 1

            if loaded:
                logger.info(f"Loaded {loaded} entries from {self.persist_path}")

        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load cache from disk: {e}")

    def save_to_disk(self) -> bool:
        """
        Save current cache to disk.

        Returns:
            True if successful.
        """
        if not self.persist:
            return False

        try:
            with self._lock:
                data = {}
                for key, (text, timestamp) in self.cache.items():
                    data[key] = [text, timestamp]

            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            with self.persist_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self._dirty = False
            self._last_save = time.time()
            logger.info(f"Saved {len(data)} entries to {self.persist_path}")
            return True

        except OSError as e:
            logger.error(f"Failed to save cache to disk: {e}")
            return False

    def _maybe_save(self, min_interval: float = 2.0) -> None:
        """Save to disk if enough time has passed since the last save."""
        now = time.time()
        if now - self._last_save >= min_interval:
            self.save_to_disk()
        return False

    # ------------------------------------------------------------------
    # PUBLIC API (existing logic preserved)
    # ------------------------------------------------------------------

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

        with self._lock:
            if key in self.cache:
                cached_text, timestamp = self.cache[key]
                if time.time() - timestamp < self.ttl:
                    logger.debug(f"Cache hit: '{text[:50]}...'")
                    return cached_text

                # Evict stale entry
                del self.cache[key]
                self._dirty = True

        return None

    def set(
        self,
        text: str,
        translated: Optional[str],
        source_lang: str,
        target_lang: str,
        formality: Optional[str] = None,
        context_type: Optional[str] = None,
    ) -> None:
        """Commit a successful translation into the cache."""
        if translated is None:
            logger.debug(
                "CACHE SKIP: translation failed for text=%r source=%s target=%s",
                text,
                source_lang,
                target_lang,
            )
            return

        with self._lock:
            logger.info(
            "CACHE SET: text=%r translated=%r source=%s target=%s",
            text,
            translated,
            source_lang,
            target_lang,
            )

            if len(self.cache) >= self.max_size:
                self._evict_stale_or_oldest()

            key = self._generate_key(text, source_lang, target_lang, formality, context_type)
            self.cache[key] = (translated, time.time())
            self._dirty = True

            if self.persist:
                self._maybe_save()

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
        with self._lock:
            self.cache.clear()
            self._dirty = True

        if self.persist and self.persist_path.exists():
            try:
                self.persist_path.unlink()
            except OSError:
                pass

        logger.info("Translation cache fully cleared")

    def size(self) -> int:
        """Return the current cumulative index assignment count."""
        with self._lock:
            return len(self.cache)

    def is_dirty(self) -> bool:
        """Return True if cache has changes not yet saved to disk."""
        return self._dirty

    # ------------------------------------------------------------------
    # CONTEXT MANAGER (new)
    # ------------------------------------------------------------------

    def __enter__(self) -> "TranslationCache":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Auto-save to disk on exit if persist is enabled and dirty."""
        if self.persist and self._dirty:
            self.save_to_disk()

