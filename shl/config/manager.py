from __future__ import annotations

import json
import os
import threading
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

__all__ = ["ConfigManager"]


class ConfigManager:
    """
    SHL-konfiguraationhallinta – 0-riippuvuutta, säieturvallinen.

    Hakee konfiguraation projektin juuresta (oletus: ./config.json).
    Tukee .env-tiedostoa (oletus: ./.env) ympäristömuuttujille.

    Provider-konfiguraatio voi sisältää esimerkiksi:

    {
        "MyMemory": {
            "enabled": true,
            "allow": [],
            "deny": ["html"]
        },
        "DeepL": {
            "enabled": true,
            "allow": [],
            "deny": ["html"]
        },
        "Google": {
            "enabled": true,
            "allow": [],
            "deny": ["html"]
        }
    }

    Fallbackit muodostetaan automaattisesti käytössä olevista
    muista providereista. Provider ei voi olla oman itsensä fallback.

    Jos aktiivisia vaihtoehtoisia providereita ei ole, ConfigManager
    ei tee fallback-käännöstä. Mahdollinen base_lang-fallback kuuluu
    routerin/runtime-logiikan vastuulle eikä sitä tallenneta
    käännöstiedostoon.

    Attributes:
        path: Polku config.json-tiedostoon.
        check_interval: Tiedoston tarkistusväli sekunteina.
        env_path: Polku .env-tiedostoon.
                  None = älä lataa .env-tiedostoa.
    """

    def __init__(
        self,
        path: Union[str, Path] = "shl-config.json"
        check_interval: float = 1.0,
        env_path: Optional[Union[str, Path]] = ".env",
    ):
        self.path = Path(path)
        self.check_interval = check_interval
        self.env_path = Path(env_path) if env_path else None

        self._lock = threading.RLock()
        self._config: Dict[str, Any] = {}

        self._last_mtime: float = 0.0
        self._last_env_mtime: float = 0.0

        self._stop_event = threading.Event()
        self._watcher: Optional[threading.Thread] = None

        self._callbacks: List[
            Callable[[Dict[str, Any]], None]
        ] = []

        # Lataa .env ennen JSON-konfiguraatiota.
        if self.env_path:
            self._load_env()

        # Pakota ensimmäinen konfiguraation lataus.
        self.reload(force=True)

        # Käynnistä tiedostojen valvonta.
        self.start_watcher()

    # ------------------------------------------------------------------
    # .env
    # ------------------------------------------------------------------

    def _load_env(self) -> bool:
        """
        Lataa .env-tiedoston ympäristömuuttujiksi.

        Returns:
            True, jos tiedosto ladattiin onnistuneesti.
            False, jos tiedostoa ei ole tai lataus epäonnistui.
        """
        if not self.env_path or not self.env_path.exists():
            return False

        try:
            with open(self.env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()

                    if not line or line.startswith("#"):
                        continue

                    if "=" not in line:
                        continue

                    key, value = line.split("=", 1)

                    key = key.strip()
                    value = value.strip()

                    if not key:
                        continue

                    # Poista ympäröivät lainausmerkit.
                    if (
                        len(value) >= 2
                        and value.startswith('"')
                        and value.endswith('"')
                    ):
                        value = value[1:-1]

                    elif (
                        len(value) >= 2
                        and value.startswith("'")
                        and value.endswith("'")
                    ):
                        value = value[1:-1]

                    os.environ[key] = value

            self._last_env_mtime = self.env_path.stat().st_mtime

            print(f"[Config] Loaded .env from {self.env_path}")
            return True

        except Exception as exc:
            print(f"[Config] Failed to load .env: {exc}")
            return False

    def _check_env_reload(self) -> bool:
        """
        Tarkistaa, onko .env muuttunut, ja lataa sen tarvittaessa.

        Returns:
            True, jos .env ladattiin uudelleen.
        """
        if not self.env_path or not self.env_path.exists():
            return False

        try:
            mtime = self.env_path.stat().st_mtime

            if mtime <= self._last_env_mtime:
                return False

            return self._load_env()

        except OSError as exc:
            print(f"[Config] .env check failed: {exc}")
            return False

    def get_env(
        self,
        key: str,
        default: Optional[str] = None,
    ) -> Optional[str]:
        """
        Hakee arvon ympäristömuuttujista.

        Args:
            key: Ympäristömuuttujan nimi.
            default: Oletusarvo.

        Returns:
            Arvo tai default.
        """
        return os.environ.get(key, default)

    # ------------------------------------------------------------------
    # JSON-konfiguraatio
    # ------------------------------------------------------------------

    def reload(self, force: bool = False) -> bool:
        """
        Lataa konfiguraation uudelleen JSON-tiedostosta.

        Jos uusi tiedosto on virheellinen, nykyinen toimiva
        konfiguraatio säilytetään.

        Args:
            force: Pakota lataus aikaleimasta riippumatta.

        Returns:
            True, jos uusi konfiguraatio ladattiin.
            False, jos muutosta ei ollut tai lataus epäonnistui.
        """
        try:
            if not self.path.exists():
                raise FileNotFoundError(
                    f"Config file not found: {self.path}"
                )

            mtime = self.path.stat().st_mtime

            if not force and mtime <= self._last_mtime:
                return False

            with open(self.path, "r", encoding="utf-8") as f:
                new_config = json.load(f)

            if not isinstance(new_config, dict):
                raise ValueError(
                    "Configuration root must be a JSON object."
                )

            # Varmista, ettei ulkopuolinen koodi pääse muuttamaan
            # sisäistä konfiguraatiota.
            new_config = deepcopy(new_config)

            with self._lock:
                self._config = new_config
                self._last_mtime = mtime

                callback_config = deepcopy(self._config)

            # Callbackit suoritetaan lukon ulkopuolella.
            for callback in list(self._callbacks):
                try:
                    callback(callback_config)
                except Exception as exc:
                    print(f"[Config] Callback error: {exc}")

            print(f"[Config] Reloaded from {self.path}")
            return True

        except Exception as exc:
            print(
                "[Config] Reload failed → "
                f"keeping previous config. Error: {exc}"
            )
            return False

    # ------------------------------------------------------------------
    # Yleinen konfiguraation haku
    # ------------------------------------------------------------------

    def get(self) -> Dict[str, Any]:
        """
        Palauttaa kopion koko konfiguraatiosta.

        Returns:
            Syväkopio konfiguraatiosta.
        """
        with self._lock:
            return deepcopy(self._config)

    def get_value(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        """
        Hakee arvon juuritasolta.

        Args:
            key: Juuritason avain.
            default: Oletusarvo.

        Returns:
            Arvo tai default.
        """
        with self._lock:
            return deepcopy(
                self._config.get(key, default)
            )

    # ------------------------------------------------------------------
    # Provider-konfiguraatio
    # ------------------------------------------------------------------

    def get_provider(
        self,
        name: str,
    ) -> Dict[str, Any]:
        """
        Hakee providerin konfiguraation.

        Args:
            name: Providerin nimi.

        Returns:
            Syväkopio providerin konfiguraatiosta.
        """
        with self._lock:
            provider = self._config.get(name)

            if not isinstance(provider, dict):
                return {}

            return deepcopy(provider)

    def get_provider_setting(
        self,
        name: str,
        key: str,
        default: Any = None,
    ) -> Any:
        """
        Hakee tietyn asetuksen providerilta.

        Args:
            name: Providerin nimi.
            key: Asetuksen nimi.
            default: Oletusarvo.

        Returns:
            Asetuksen arvo tai default.
        """
        with self._lock:
            provider = self._config.get(name)

            if not isinstance(provider, dict):
                return default

            return deepcopy(
                provider.get(key, default)
            )

    def is_enabled(
        self,
        provider_name: str,
    ) -> bool:
        """
        Tarkistaa, onko provider käytössä.
        """
        return bool(
            self.get_provider_setting(
                provider_name,
                "enabled",
                default=False,
            )
        )

    # ------------------------------------------------------------------
    # Allow / deny
    # ------------------------------------------------------------------

    def is_allowed(
        self,
        provider_name: str,
        item: str,
        default: bool = True,
    ) -> bool:
        """
        Tarkistaa, soveltuuko tietty kohde providerille.

        Järjestys:

        1. deny-listalla oleva kohde → False
        2. tyhjä allow-lista → default
        3. allow-listalla oleva kohde → True
        4. muuten → False

        Args:
            provider_name: Providerin nimi.
            item: Tarkistettava kohde, esimerkiksi "html".
            default: Oletusarvo tyhjälle allow-listalle.

        Returns:
            True, jos kohde on sallittu.
        """
        with self._lock:
            provider = self._config.get(provider_name)

            if not isinstance(provider, dict):
                return default

            deny_list = provider.get("deny", [])
            allow_list = provider.get("allow", [])

            if not isinstance(deny_list, list):
                deny_list = []

            if not isinstance(allow_list, list):
                allow_list = []

            if item in deny_list:
                return False

            if not allow_list:
                return default

            return item in allow_list

    def get_allowed_items(
        self,
        provider_name: str,
    ) -> Dict[str, List[str]]:
        """
        Palauttaa providerin allow- ja deny-listat.

        Returns:
            {
                "allow": [...],
                "deny": [...]
            }
        """
        with self._lock:
            provider = self._config.get(provider_name)

            if not isinstance(provider, dict):
                return {
                    "allow": [],
                    "deny": [],
                }

            allow = provider.get("allow", [])
            deny = provider.get("deny", [])

            if not isinstance(allow, list):
                allow = []

            if not isinstance(deny, list):
                deny = []

            return {
                "allow": deepcopy(allow),
                "deny": deepcopy(deny),
            }

    # ------------------------------------------------------------------
    # Provider-listat
    # ------------------------------------------------------------------

    def get_provider_list(self) -> List[str]:
        """
        Palauttaa kaikki providerit.

        Vain sanakirjana olevat juuritason osiot huomioidaan.
        """
        with self._lock:
            return [
                name
                for name, config in self._config.items()
                if isinstance(config, dict)
            ]

    def get_enabled_providers(self) -> List[str]:
        """
        Palauttaa käytössä olevat providerit.

        Järjestys säilyy config.json:n mukaisena.
        """
        with self._lock:
            return [
                name
                for name, config in self._config.items()
                if (
                    isinstance(config, dict)
                    and config.get("enabled", False) is True
                )
            ]

    def get_fallback_providers(
        self,
        current_provider: Optional[str] = None,
    ) -> List[str]:
        """
        Palauttaa mahdolliset fallback-providerit.

        Kaikki käytössä olevat muut providerit ovat mahdollisia
        fallbackeja. Nykyinen provider jätetään aina pois.

        Args:
            current_provider:
                Provider, jota parhaillaan käytetään.
                Tätä ei koskaan palauteta fallbackiksi.

        Returns:
            Lista mahdollisista fallback-providereista.
        """
        with self._lock:
            return [
                name
                for name, config in self._config.items()
                if (
                    isinstance(config, dict)
                    and config.get("enabled", False) is True
                    and name != current_provider
                )
            ]

    # ------------------------------------------------------------------
    # Callbackit
    # ------------------------------------------------------------------

    def on_reload(
        self,
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        """
        Rekisteröi callbackin onnistuneen reloadin jälkeen.

        Callback saa parametrikseen kopion uudesta konfiguraatiosta.
        """
        if not callable(callback):
            raise TypeError("callback must be callable")

        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)

    def remove_reload_callback(
        self,
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        """
        Poistaa aiemmin rekisteröidyn reload-callbackin.
        """
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    # ------------------------------------------------------------------
    # Watcher
    # ------------------------------------------------------------------

    def start_watcher(self) -> None:
        """
        Käynnistää taustalangan, joka tarkkailee config.json- ja
        .env-tiedostoja.
        """
        with self._lock:
            if (
                self._watcher
                and self._watcher.is_alive()
            ):
                return

            self._stop_event.clear()

            self._watcher = threading.Thread(
                target=self._watch,
                daemon=True,
                name="SHLConfigWatcher",
            )

            self._watcher.start()

        print(
            "[Config] Watcher started "
            f"(interval: {self.check_interval}s)"
        )

    def _watch(self) -> None:
        """
        Watcher-säikeen pääsilmukka.
        """
        while not self._stop_event.is_set():
            try:
                self._check_env_reload()
                self.reload()
            except Exception as exc:
                print(f"[Config] Watcher error: {exc}")

            self._stop_event.wait(
                timeout=self.check_interval
            )

    def stop_watcher(self) -> None:
        """
        Pysäyttää watcher-säikeen.
        """
        self._stop_event.set()

        watcher = self._watcher

        if watcher and watcher.is_alive():
            watcher.join(timeout=2.0)

            if watcher.is_alive():
                print(
                    "[Config] Watcher thread "
                    "did not stop in time."
                )
            else:
                print("[Config] Watcher stopped.")

        self._watcher = None

    def close(self) -> None:
        """
        Sulkee ConfigManagerin ja pysäyttää watcherin.
        """
        self.stop_watcher()

    def __enter__(self) -> "ConfigManager":
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_value: Any,
        traceback: Any,
    ) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------------

    def print_config(self) -> None:
        """
        Tulostaa nykyisen konfiguraation luettavassa muodossa.

        Älä käytä tätä, jos konfiguraatio sisältää salaisia arvoja.
        """
        config = self.get()

        print("\n" + "=" * 50)
        print("SHL CONFIGURATION")
        print("=" * 50)

        for name, provider in config.items():
            if not isinstance(provider, dict):
                continue

            print(f"\n{name}:")

            if "enabled" in provider:
                print(
                    f"  enabled: "
                    f"{provider.get('enabled')}"
                )

            if "allow" in provider:
                print(
                    f"  allow: "
                    f"{provider.get('allow')}"
                )

            if "deny" in provider:
                print(
                    f"  deny: "
                    f"{provider.get('deny')}"
                )

        print("=" * 50 + "\n")
