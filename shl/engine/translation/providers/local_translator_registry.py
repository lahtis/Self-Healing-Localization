"""
File: shl/engine/translation/providers/local_translator_registry.py
Author: Tuomas Lähteenmäki
Version: 0.3.0
License: MIT
Description:
    Runtime registry of (source_lang, target_lang) support status.

    Registry state is shared between LocalRegistry instances so that
    runtime language-pair knowledge survives adapter recreation.

    This module performs no HTTP calls. It only tracks which pairs the
    caller has observed to work or fail.
"""

import time
from dataclasses import dataclass, field


@dataclass
class PairStatus:
    """Support status for a single (source, target) language pair."""

    supported: bool = True
    last_checked: float = field(default_factory=time.time)
    failure_count: int = 0


class LocalRegistry:
    """Shared runtime registry of language-pair support per engine.

    All instances share the same underlying state, so adapters can be
    recreated without losing runtime knowledge about which pairs work.
    """

    _shared_status: dict[
        str, dict[tuple[str, str], PairStatus]
    ] = {}

    def __init__(
        self,
        blacklist_threshold: int = 3,
        retry_after_seconds: int = 3600,
    ):
        self._status = LocalRegistry._shared_status
        self._blacklist_threshold = blacklist_threshold
        self._retry_after_seconds = retry_after_seconds

    @classmethod
    def shared(
        cls,
        blacklist_threshold: int = 3,
        retry_after_seconds: int = 3600,
    ) -> "LocalRegistry":
        """Return a registry using the shared runtime state."""
        return cls(
            blacklist_threshold=blacklist_threshold,
            retry_after_seconds=retry_after_seconds,
        )

    def _pair_key(
        self,
        source_lang: str | None,
        target_lang: str,
    ) -> tuple[str, str]:
        """Normalize a language pair into a stable key."""
        return (
            (source_lang or "auto").strip().lower(),
            target_lang.strip().lower(),
        )

    def is_supported(
        self,
        engine: str,
        source_lang: str | None,
        target_lang: str,
    ) -> bool:
        """Return whether the engine is believed to support the pair.

        An unknown pair is treated as supported (optimistic). A pair
        blacklisted by repeated failures is re-enabled after the
        retry window elapses.
        """
        pair = self._pair_key(source_lang, target_lang)
        status = self._status.get(engine, {}).get(pair)

        if status is None:
            return True

        if not status.supported:
            if (
                time.time() - status.last_checked
                > self._retry_after_seconds
            ):
                status.supported = True
                status.failure_count = 0
                status.last_checked = time.time()
                return True

        return status.supported

    def mark_failure(
        self,
        engine: str,
        source_lang: str | None,
        target_lang: str,
    ) -> None:
        """Record a failure; blacklist after the threshold."""
        pair = self._pair_key(source_lang, target_lang)
        engine_map = self._status.setdefault(engine, {})
        status = engine_map.setdefault(pair, PairStatus())

        status.failure_count += 1
        status.last_checked = time.time()

        if status.failure_count >= self._blacklist_threshold:
            status.supported = False

    def mark_success(
        self,
        engine: str,
        source_lang: str | None,
        target_lang: str,
    ) -> None:
        """Reset failure state and mark the pair as supported."""
        pair = self._pair_key(source_lang, target_lang)
        engine_map = self._status.setdefault(engine, {})

        engine_map[pair] = PairStatus(
            supported=True,
            last_checked=time.time(),
            failure_count=0,
        )

    def clear(self, engine: str | None = None) -> None:
        """Clear runtime registry state for one engine or all engines."""
        if engine is None:
            self._status.clear()
            return

        self._status.pop(engine, None)
