"""
LibreTranslate mirror management for SHL.
"""

import json
import logging
import time
from typing import List, Dict, Optional, Any
from urllib.request import Request, urlopen
from urllib.error import URLError

logger = logging.getLogger(__name__)

# Peilin tilat
MIRROR_STATUS_UNKNOWN = "unknown"
MIRROR_STATUS_AVAILABLE = "available"
MIRROR_STATUS_UNAVAILABLE = "unavailable"
MIRROR_STATUS_DEGRADED = "degraded"

# Oletuspeililista (voidaan ylikirjoittaa .env-tiedostossa tai konfiguraatiossa)
DEFAULT_MIRRORS = [
    {"url": "https://libretranslate.com", "weight": 5, "api_key_env": "LIBRETRANSLATE_API_KEY"},
    {"url": "https://libretranslate.de", "weight": 4},
    {"url": "https://translate.mentality.rip", "weight": 3},
    {"url": "https://translate.astian.org", "weight": 2},
]


class LibreTranslateMirror:
    """Yksittäinen LibreTranslate-peili."""

    def __init__(
        self,
        url: str,
        weight: int = 1,
        api_key_env: Optional[str] = None,
        timeout: int = 5,
    ):
        self.url = url.rstrip("/")
        self.weight = weight
        self.api_key_env = api_key_env
        self.timeout = timeout

        # Tila
        self.status = MIRROR_STATUS_UNKNOWN
        self.last_check = 0.0
        self.last_latency = 0.0
        self.last_error = ""
        self.supported_languages: Dict[str, str] = {}

    def is_available(self) -> bool:
        """Onko peili saatavilla (välimuistin perusteella)."""
        if self.status == MIRROR_STATUS_AVAILABLE:
            return True
        if self.status == MIRROR_STATUS_UNKNOWN:
            # Tuntematon peili katsotaan käytettäväksi, mutta testataan ennen käyttöä
            return True
        return False

    def get_api_key(self) -> Optional[str]:
        """Hae API-avain ympäristömuuttujasta."""
        if self.api_key_env:
            import os
            return os.environ.get(self.api_key_env)
        return None

    def test(self) -> bool:
        """
        Testaa peilin saatavuus ja nopeus.

        Palauttaa True, jos peili on käytettävissä.
        """
        try:
            start_time = time.time()
            url = f"{self.url}/languages"
            req = Request(
                url,
                headers={
                    "User-Agent": "SHL-Client/0.3.0",
                    "Accept": "application/json",
                },
            )

            with urlopen(req, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
                self.supported_languages = {
                    lang["code"]: lang["name"]
                    for lang in data
                    if "code" in lang and "name" in lang
                }

                self.last_latency = (time.time() - start_time) * 1000  # ms
                self.status = MIRROR_STATUS_AVAILABLE
                self.last_check = time.time()
                self.last_error = ""
                logger.debug(f"Mirror {self.url} available: {len(self.supported_languages)} languages")
                return True

        except Exception as e:
            self.status = MIRROR_STATUS_UNAVAILABLE
            self.last_check = time.time()
            self.last_error = str(e)
            logger.debug(f"Mirror {self.url} unavailable: {e}")
            return False

    def to_dict(self) -> Dict[str, Any]:
        """Muunna sanakirjaksi tallennusta varten."""
        return {
            "url": self.url,
            "weight": self.weight,
            "status": self.status,
            "last_check": self.last_check,
            "last_latency": self.last_latency,
            "last_error": self.last_error,
            "supported_languages_count": len(self.supported_languages),
        }


class LibreTranslateMirrorManager:
    """Hallitsee LibreTranslate-peilejä."""

    def __init__(
        self,
        mirrors: Optional[List[Dict[str, Any]]] = None,
        test_interval: int = 300,  # 5 minuuttia
        max_failures: int = 3,
    ):
        self.mirrors: List[LibreTranslateMirror] = []
        self.test_interval = test_interval
        self.max_failures = max_failures
        self._current_mirror_index = 0

        # Lataa peilit
        if mirrors is None:
            mirrors = self._load_mirrors_from_env()
        self._load_mirrors(mirrors)

    def _load_mirrors_from_env(self) -> List[Dict[str, Any]]:
        """Lataa peilit ympäristömuuttujista."""
        import os
        mirrors = []

        # Lue .env-tiedosto (jos olemassa)
        env_file = os.path.join(os.getcwd(), ".env")
        if os.path.exists(env_file):
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("LIBRETRANSLATE_MIRROR_"):
                            key, value = line.split("=", 1)
                            # LIBRETRANSLATE_MIRROR_1=https://libretranslate.de
                            mirrors.append({"url": value.strip().strip('"').strip("'")})
            except Exception:
                pass

        # Ympäristömuuttujat
        for key, value in os.environ.items():
            if key.startswith("LIBRETRANSLATE_MIRROR_"):
                mirrors.append({"url": value})

        # Oletuspeilit
        if not mirrors:
            mirrors = DEFAULT_MIRRORS

        return mirrors

    def _load_mirrors(self, mirrors: List[Dict[str, Any]]) -> None:
        """Luo peilioliot listasta."""
        self.mirrors = []
        for mirror_data in mirrors:
            self.mirrors.append(
                LibreTranslateMirror(
                    url=mirror_data.get("url"),
                    weight=mirror_data.get("weight", 1),
                    api_key_env=mirror_data.get("api_key_env"),
                    timeout=mirror_data.get("timeout", 5),
                )
            )

    def get_best_mirror(self, force_test: bool = False) -> Optional[LibreTranslateMirror]:
        """
        Hae paras peili saatavuuden ja painon perusteella.

        Args:
            force_test: Testataanko peilit ennen valintaa.

        Returns:
            Paras peili tai None.
        """
        # Testaa peilit, jos aika on kulunut
        for mirror in self.mirrors:
            if force_test or (time.time() - mirror.last_check > self.test_interval):
                mirror.test()

        # Suodatetaan käytettävissä olevat peilit
        available = [m for m in self.mirrors if m.is_available()]

        if not available:
            # Kaikki peilit epäonnistuivat, yritä testata uudelleen
            for mirror in self.mirrors:
                mirror.test()
            available = [m for m in self.mirrors if m.is_available()]

        if not available:
            logger.warning("No LibreTranslate mirrors available")
            return None

        # Järjestä peilit painon mukaan (korkein ensin)
        available.sort(key=lambda m: (m.weight, -m.last_latency if m.last_latency > 0 else 0), reverse=True)

        # Palauta paras
        best = available[0]
        logger.debug(f"Best mirror: {best.url} (weight={best.weight}, latency={best.last_latency:.0f}ms)")
        return best

    def get_mirror_for_language(
        self,
        target_lang: str,
        source_lang: str = "en",
    ) -> Optional[LibreTranslateMirror]:
        """
        Hae peili, joka tukee kieliparia.

        Returns:
            Sopiva peili tai None.
        """
        target = target_lang.lower()
        source = source_lang.lower()

        # Testaa kaikki peilit, jos aika on kulunut
        for mirror in self.mirrors:
            if time.time() - mirror.last_check > self.test_interval:
                mirror.test()

        # Etsi peili, joka tukee kieliparia
        for mirror in sorted(self.mirrors, key=lambda m: (m.weight, -m.last_latency if m.last_latency > 0 else 0), reverse=True):
            if mirror.is_available():
                if target in mirror.supported_languages and source in mirror.supported_languages:
                    return mirror

        # Jos mikään peili ei tue kieliparia, yritä uudelleentestaus
        for mirror in self.mirrors:
            mirror.test()
            if mirror.is_available():
                if target in mirror.supported_languages and source in mirror.supported_languages:
                    return mirror

        return None

    def update_mirror_status(self, url: str, available: bool) -> None:
        """Päivitä yksittäisen peilin tila."""
        for mirror in self.mirrors:
            if mirror.url == url:
                mirror.status = MIRROR_STATUS_AVAILABLE if available else MIRROR_STATUS_UNAVAILABLE
                mirror.last_check = time.time()
                break

    def get_mirror_stats(self) -> List[Dict[str, Any]]:
        """Hae tilastot kaikista peileistä."""
        return [m.to_dict() for m in self.mirrors]

    def clear_cache(self) -> None:
        """Tyhjennä peilien välimuisti."""
        for mirror in self.mirrors:
            mirror.status = MIRROR_STATUS_UNKNOWN
            mirror.last_check = 0.0
            mirror.supported_languages = {}
