"""
File: local_translator_registry.py — Engine pair-support registry for the local_translator server.
Author: Tuomas Lähteenmäki
Version: 0.2.10
License: MIT
Description:
    Runtime registry of (source_lang, target_lang) support status.
    Registry state is shared between LocalRegistry instances so that
    runtime language-pair knowledge survives adapter recreation.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


@dataclass
class PairStatus:
    supported: bool = True
    last_checked: float = field(default_factory=time.time)
    failure_count: int = 0


class LocalRegistry:
    _shared_status: Dict[str, Dict[Tuple[str, str], PairStatus]] = {}

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
        source_lang: Optional[str],
        target_lang: str,
    ) -> Tuple[str, str]:
        return (
            (source_lang or "auto").strip().lower(),
            target_lang.strip().lower(),
        )

    def is_supported(
        self,
        engine: str,
        source_lang: Optional[str],
        target_lang: str,
    ) -> bool:
        pair = self._pair_key(source_lang, target_lang)
        status = self._status.get(engine, {}).get(pair)

        if status is None:
            return True

        if not status.supported:
            if time.time() - status.last_checked > self._retry_after_seconds:
                status.supported = True
                status.failure_count = 0
                status.last_checked = time.time()
                return True

        return status.supported

    def mark_failure(
        self,
        engine: str,
        source_lang: Optional[str],
        target_lang: str,
    ) -> None:
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
        source_lang: Optional[str],
        target_lang: str,
    ) -> None:
        pair = self._pair_key(source_lang, target_lang)
        engine_map = self._status.setdefault(engine, {})

        engine_map[pair] = PairStatus(
            supported=True,
            last_checked=time.time(),
            failure_count=0,
        )

    def clear(self, engine: Optional[str] = None) -> None:
        """Clear runtime registry state for one engine or all engines."""
        if engine is None:
            self._status.clear()
            return

        self._status.pop(engine, None)
