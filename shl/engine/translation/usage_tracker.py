"""
file: usage_tracker.py — Translation character usage and quota manager.
Author: Tuomas Lähteenmäki
License: MIT
Description: Tracks character usage per provider, enforces maximum quotas,
             and provides statistics for local localization budgets.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

SHL_DIR = Path(__file__).resolve().parents[2]
USAGE_CACHE_FILE = SHL_DIR / "usage_stats.json"


class UsageTracker:
    """
    Manages translation character limits, live decrementing quotas,
    and provider-specific usage statistics.
    """

    def __init__(self, config: Dict[str, Any] = None):
        # Oletusasetukset: seuranta päällä, oletusbudjetti per provider (esim. 100 000 merkkiä)
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.default_max_chars = self.config.get("max_chars", 100000)
        
        # Provider-kohtaiset maksimit voidaan määritellä erikseen
        self.provider_max_chars = self.config.get("provider_max_chars", {})

        # Lataa olemassa olevat tilastot levyltä
        self.stats = self._load_stats()

    def _load_stats(self) -> Dict[str, Any]:
        """Lataa tallennetut käyttötilastot tiedostosta."""
        if USAGE_CACHE_FILE.exists():
            try:
                with USAGE_CACHE_FILE.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                logger.warning("Could not read usage stats cache, resetting stats.")
        
        return {"providers": {}}

    def _save_stats(self) -> None:
        """Tallentaa tilastot levylle."""
        if not self.enabled:
            return
        try:
            USAGE_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with USAGE_CACHE_FILE.open("w", encoding="utf-8") as f:
                json.dump(self.stats, f, indent=4, ensure_ascii=False)
        except OSError as e:
            logger.error(f"Failed to save usage stats: {e}")

    def track_and_consume(self, provider_name: str, text: str) -> int:
        """
        Laskee tekstin merkit, tarkistaa budjetin, vähentää sen jäljellä olevasta
        ja päivittää tilastot. Palauttaa käytettyjen merkkien määrän.
        """
        if not self.enabled:
            return len(text)

        char_count = len(text)
        if char_count == 0:
            return 0

        providers_stats = self.stats.setdefault("providers", {})
        prov_stat = providers_stats.setdefault(provider_name, {
            "used_chars": 0,
            "requests_count": 0
        })

        # Määritä maksimi tälle providerille
        max_chars = self.provider_max_chars.get(provider_name, self.default_max_chars)
        current_used = prov_stat["used_chars"]
        remaining = max_chars - current_used

        # Tarkistetaan riittääkö budjetti
        if char_count > remaining:
            raise ValueError(
                f"Translation quota exceeded for provider '{provider_name}'. "
                f"Attempted to use {char_count} chars, but only {max_chars - current_used} remaining "
                f"(Max quota: {max_chars}, Total used: {current_used})."
            )

        # Päivitetään tilastot
        prov_stat["used_chars"] += char_count
        prov_stat["requests_count"] += 1

        self._save_stats()
        logger.debug(f"Tracked {char_count} chars for provider '{provider_name}'. Remaining quota: {max_chars - prov_stat['used_chars']}")

        return char_count

    def get_provider_stats(self, provider_name: str) -> Dict[str, Any]:
        """Palauttaa tietyn providerin statistiikan (käytetyt, maksimi, jäljellä)."""
        providers_stats = self.stats.get("providers", {})
        prov_stat = providers_stats.get(provider_name, {"used_chars": 0, "requests_count": 0})
        
        max_chars = self.provider_max_chars.get(provider_name, self.default_max_chars)
        used = prov_stat["used_chars"]
        remaining = max(0, max_chars - used)

        return {
            "provider": provider_name,
            "enabled": self.enabled,
            "max_chars": max_chars,
            "used_chars": used,
            "remaining_chars": remaining,
            "requests_count": prov_stat["requests_count"],
            "quota_exhausted": remaining == 0
        }

    def get_all_stats(self) -> Dict[str, Any]:
        """Palauttaa kaikkien providerien statistiikan kerralla."""
        providers_stats = self.stats.get("providers", {})
        all_res = {}
        
        # Kerätään kaikkien tiedossa olevien tai konfiguroitujen providerien tiedot
        all_providers = set(list(providers_stats.keys()) + list(self.provider_max_chars.keys()))
        for prov in all_providers:
            all_res[prov] = self.get_provider_stats(prov)

        return {
            "enabled": self.enabled,
            "providers": all_res
        }

    def reset_quota(self, provider_name: Optional[str] = None) -> None:
        """Nollaa laskurin joko tietyltä providerilta tai kaikilta."""
        if provider_name:
            if provider_name in self.stats.get("providers", {}):
                self.stats["providers"][provider_name] = {"used_chars": 0, "requests_count": 0}
        else:
            self.stats["providers"] = {}
        self._save_stats()
