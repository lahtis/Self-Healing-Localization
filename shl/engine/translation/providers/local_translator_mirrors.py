"""
File: shl/engine/translation/providers/local_translator_mirrors.py
Author: Tuomas Lähteenmäki
Version: 0.3.0
License: MIT
Description: Local mirror pool manager for the Local translator
server.

Owns a pool of mirror endpoints and selects a healthy one per request
based on weight and recent latency. Mirror definitions (URL, weight,
timeout, API key) are injected from config — nothing here is hardcoded,
per the "no hardcoded configurable behaviour" decision.

This module performs no HTTP calls. It only selects which mirror the
caller should use; the actual request goes through the caller's
safe_local_urlopen path.
"""

import random
import time
from dataclasses import dataclass


@dataclass
class MirrorConfig:
    """One Local mirror endpoint, as loaded from config."""

    url: str
    weight: float = 1.0
    timeout_seconds: float = 10.0
    api_key: str | None = None


@dataclass
class MirrorHealth:
    healthy: bool = True
    last_checked: float = 0.0
    last_latency_ms: float | None = None
    consecutive_failures: int = 0


class LocalMirrorManager:
    """Selects a healthy mirror weighted by config weight and latency.

    A mirror that has failed repeatedly is marked unhealthy and skipped
    until its cool-down elapses. A slow high-weight mirror may still be
    chosen over a fast low-weight one, and an untested mirror is treated
    as neutral rather than preferred.

    Language-pair support is intentionally NOT checked here — that is
    the registry's job (see local_translator_registry.py). This class
    only answers "which mirror", never "can this mirror handle this
    pair".
    """

    def __init__(
        self,
        mirrors: list[MirrorConfig],
        unhealthy_after_failures: int = 3,
        health_recheck_seconds: int = 300,
    ):
        if not mirrors:
            raise ValueError(
                "LocalMirrorManager requires at least one mirror"
            )

        self._mirrors = mirrors
        self._health: dict[str, MirrorHealth] = {
            m.url: MirrorHealth() for m in mirrors
        }
        self._unhealthy_after_failures = unhealthy_after_failures
        self._health_recheck_seconds = health_recheck_seconds

    def _eligible_mirrors(self) -> list[MirrorConfig]:
        now = time.time()
        eligible = []

        for m in self._mirrors:
            health = self._health[m.url]

            if health.healthy:
                eligible.append(m)
            elif now - health.last_checked > self._health_recheck_seconds:
                # Cool-down elapsed — give it another chance rather
                # than permanently blacklisting a mirror that
                # recovered.
                eligible.append(m)

        # Last resort: if nothing is eligible, try everything rather
        # than fail outright.
        return eligible or list(self._mirrors)

    def select(self) -> MirrorConfig:
        """Pick a mirror using weight divided by recent latency."""

        candidates = self._eligible_mirrors()

        def score(m: MirrorConfig) -> float:
            health = self._health[m.url]

            # A mirror that has never been measured gets a neutral
            # penalty of 1.0 so it is neither preferred nor penalized.
            # A measured mirror is floored at 1.0 ms so latency never
            # approaches zero and blows up the score.
            if health.last_latency_ms is None:
                latency_penalty = 1.0
            else:
                latency_penalty = max(health.last_latency_ms, 1.0)

            return m.weight / latency_penalty

        weights = [max(score(m), 0.001) for m in candidates]

        return random.choices(candidates, weights=weights, k=1)[0]

    def record_success(
        self,
        mirror: MirrorConfig,
        latency_ms: float,
    ) -> None:
        """Mark a mirror as healthy and record its latency."""
        health = self._health[mirror.url]
        health.healthy = True
        health.consecutive_failures = 0
        health.last_latency_ms = latency_ms
        health.last_checked = time.time()

    def record_failure(self, mirror: MirrorConfig) -> None:
        """Record a failure; mark unhealthy after the threshold."""
        health = self._health[mirror.url]
        health.consecutive_failures += 1
        health.last_checked = time.time()

        if health.consecutive_failures >= self._unhealthy_after_failures:
            health.healthy = False
