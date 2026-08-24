"""
File: Local_translater_mirror.py — Local mirror pool manager for the Local_translator server.
Author: Tuomas Lähteenmäki
Version: 0.2.6
License: MIT
Description: Owns a pool of Local mirror endpoints and selects a
healthy one per request based on weight and recent latency. Mirror
definitions (URL, weight, timeout, API key) are injected from config.py -
nothing here is hardcoded, per the "no hardcoded configurable behaviour"
decision.
"""
import random
import time
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class MirrorConfig:
    """One Local mirror endpoint, as loaded from config.py."""
    url: str
    weight: float = 1.0
    timeout_seconds: float = 10.0
    api_key: Optional[str] = None


@dataclass
class MirrorHealth:
    healthy: bool = True
    last_checked: float = 0.0
    last_latency_ms: Optional[float] = None
    consecutive_failures: int = 0


class LocalMirrorManager:
    """
    Selects a mirror = healthy mirrors, weighted by (config weight / recent
    latency), so a fast high-weight mirror wins more often but a slow one is
    still tried if it's the only option left.

    Language-pair support is intentionally NOT checked here - that's the
    registry's job (see registry.py). This class only answers "which mirror",
    never "can this mirror handle this pair".
    """

    def __init__(
        self,
        mirrors: List[MirrorConfig],
        unhealthy_after_failures: int = 3,
        health_recheck_seconds: int = 300,
    ):
        if not mirrors:
            raise ValueError("LocalMirrorManager requires at least one mirror")
        self._mirrors = mirrors
        self._health: Dict[str, MirrorHealth] = {m.url: MirrorHealth() for m in mirrors}
        self._unhealthy_after_failures = unhealthy_after_failures
        self._health_recheck_seconds = health_recheck_seconds

    def _eligible_mirrors(self) -> List[MirrorConfig]:
        now = time.time()
        eligible = []
        for m in self._mirrors:
            health = self._health[m.url]
            if health.healthy:
                eligible.append(m)
            elif now - health.last_checked > self._health_recheck_seconds:
                # cool-down elapsed - give it another chance rather than
                # permanently blacklisting a mirror that recovered
                eligible.append(m)
        return eligible or list(self._mirrors)  # last resort: everything

    def select(self) -> MirrorConfig:
        """Pick a mirror using weight / latency scoring."""
        candidates = self._eligible_mirrors()

        def score(m: MirrorConfig) -> float:
            health = self._health[m.url]
            latency_penalty = health.last_latency_ms or 1.0
            return m.weight / max(latency_penalty, 1.0)

        weights = [max(score(m), 0.001) for m in candidates]
        return random.choices(candidates, weights=weights, k=1)[0]

    def record_success(self, mirror: MirrorConfig, latency_ms: float) -> None:
        health = self._health[mirror.url]
        health.healthy = True
        health.consecutive_failures = 0
        health.last_latency_ms = latency_ms
        health.last_checked = time.time()

    def record_failure(self, mirror: MirrorConfig) -> None:
        health = self._health[mirror.url]
        health.consecutive_failures += 1
        health.last_checked = time.time()
        if health.consecutive_failures >= self._unhealthy_after_failures:
            health.healthy = False
