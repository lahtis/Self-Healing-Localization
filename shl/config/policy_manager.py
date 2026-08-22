"""
file: policy_manager.py - SHL policy manager
Author: Tuomas Lähteenmäki
License: MIT
Version: 0.2.5

Policy-konfiguraatio projektin juuresta (CWD).
"""

from __future__ import annotations

import json
import os
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

__all__ = ["ConfigManager"]

DEFAULT_POLICY_PATH = Path.cwd() / "shl-policy-config.json"


class ConfigManager:
    """
    SHL-policy konfiguraationhallinta – 0-riippuvuutta, säieturvallinen.
    """

    def __init__(
        self,
        path: Optional[Union[str, Path]] = None,
        check_interval: float = 1.0,
        env_path: Optional[Union[str, Path]] = ".env",
    ):
        self.path = Path(path) if path else DEFAULT_POLICY_PATH
        self.check_interval = check_interval
        self.env_path = Path(env_path) if env_path else None

        self._lock = threading.RLock()
        self._config: Dict[str, Any] = {}

        self._last_mtime: float = 0.0
        self._last_env_mtime: float = 0.0

        self._stop_event = threading.Event()
        self._watcher: Optional[threading.Thread] = None

        self._callbacks: List[Callable[[Dict[str, Any]], None]] = []

        # Debug: näytä mistä etsitään (self on nyt olemassa!)
        print(f"[PolicyManager] Config path: {self.path}")
        print(f"[PolicyManager] CWD: {Path.cwd()}")
        print(f"[PolicyManager] File exists: {self.path.exists()}")

        if self.env_path:
            self._load_env()

        self.reload(force=True)
        self.start_watcher()

    def _load_env(self) -> bool:
        if not self.env_path or not self.env_path.exists():
            return False
        try:
            with open(self.env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    if not key:
                        continue
                    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "\u0027"):
                        value = value[1:-1]
                    os.environ[key] = value
            self._last_env_mtime = self.env_path.stat().st_mtime
            print(f"[Config] Loaded .env from {self.env_path}")
            return True
        except Exception as exc:
            print(f"[Config] Failed to load .env: {exc}")
            return False

    def _check_env_reload(self) -> bool:
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

    def get_env(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return os.environ.get(key, default)

    def reload(self, force: bool = False) -> bool:
        try:
            if not self.path.exists():
                self._create_default_config()

            mtime = self.path.stat().st_mtime
            if not force and mtime <= self._last_mtime:
                return False

            with open(self.path, "r", encoding="utf-8") as f:
                new_config = json.load(f)

            if not isinstance(new_config, dict):
                raise ValueError("Configuration root must be a JSON object.")

            new_config = deepcopy(new_config)

            with self._lock:
                self._config = new_config
                self._last_mtime = mtime
                callback_config = deepcopy(self._config)

            for callback in list(self._callbacks):
                try:
                    callback(callback_config)
                except Exception as exc:
                    print(f"[Config] Callback error: {exc}")

            print(f"[Config] Reloaded from {self.path}")
            return True

        except Exception as exc:
            print(f"[Config] Reload failed → keeping previous config. Error: {exc}")
            return False

    def _create_default_config(self) -> None:
        default_config = {
            "MyMemory": {
                "enabled": True,
                "allow": [],
                "deny": ["html"],
                "timeout": 10,
                "requires_env": ["MYMEMORY_EMAIL"],
                "priority": 1
            },
            "LibreTranslate": {
                "enabled": True,
                "allow": [],
                "deny": ["html"],
                "timeout": 8,
                "requires_env": [],
                "priority": 2
            },
            "DeepL": {
                "enabled": False,
                "allow": [],
                "deny": [],
                "timeout": 5,
                "requires_env": ["DEEPL_API_KEY"],
                "priority": 3
            },
            "Google": {
                "enabled": False,
                "allow": [],
                "deny": [],
                "timeout": 5,
                "requires_env": ["GOOGLE_API_KEY"],
                "priority": 4
            },
            "MicrosoftTranslator": {
                "enabled": False,
                "allow": [],
                "deny": [],
                "timeout": 5,
                "requires_env": ["MICROSOFT_TRANSLATOR_KEY"],
                "priority": 5
            },
            "Papago": {
                "enabled": False,
                "allow": [],
                "deny": ["html"],
                "timeout": 5,
                "requires_env": ["NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET"],
                "priority": 6
            }
        }

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)

        print(f"[Config] Created default config at {self.path}")

    def get(self) -> Dict[str, Any]:
        with self._lock:
            return deepcopy(self._config)

    def get_value(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return deepcopy(self._config.get(key, default))

    def get_provider(self, name: str) -> Dict[str, Any]:
        with self._lock:
            provider = self._config.get(name)
            if not isinstance(provider, dict):
                return {}
            return deepcopy(provider)

    def get_provider_setting(self, name: str, key: str, default: Any = None) -> Any:
        with self._lock:
            provider = self._config.get(name)
            if not isinstance(provider, dict):
                return default
            return deepcopy(provider.get(key, default))

    def is_enabled(self, provider_name: str) -> bool:
        return bool(self.get_provider_setting(provider_name, "enabled", default=False))

    def is_available(self, provider_name: str) -> bool:
        if not self.is_enabled(provider_name):
            return False
        requires = self.get_provider_setting(provider_name, "requires_env", default=[])
        if not isinstance(requires, list):
            return True
        return all(self.get_env(key) for key in requires)

    def get_timeout(self, provider_name: str, default: float = 10.0) -> float:
        return float(self.get_provider_setting(provider_name, "timeout", default=default))

    def get_enabled_providers(self) -> List[str]:
        with self._lock:
            return [
                name for name, config in self._config.items()
                if isinstance(config, dict) and config.get("enabled", False) is True
            ]

    def get_available_providers(self) -> List[str]:
        with self._lock:
            providers = []
            for name, config in self._config.items():
                if not isinstance(config, dict):
                    continue
                if not config.get("enabled", False):
                    continue
                requires = config.get("requires_env", [])
                if isinstance(requires, list) and requires:
                    if not all(self.get_env(key) for key in requires):
                        continue
                priority = config.get("priority", 999)
                providers.append((priority, name))
            providers.sort(key=lambda x: x[0])
            return [name for _, name in providers]

    def get_fallback_providers(self, current_provider: Optional[str] = None) -> List[str]:
        with self._lock:
            return [
                name for name, config in self._config.items()
                if isinstance(config, dict) and config.get("enabled", False) is True and name != current_provider
            ]

    def on_reload(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        if not callable(callback):
            raise TypeError("callback must be callable")
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)

    def remove_reload_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    def start_watcher(self) -> None:
        with self._lock:
            if self._watcher and self._watcher.is_alive():
                return
            self._stop_event.clear()
            self._watcher = threading.Thread(target=self._watch, daemon=True, name="SHLConfigWatcher")
            self._watcher.start()
        print(f"[Config] Watcher started (interval: {self.check_interval}s)")

    def _watch(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._check_env_reload()
                self.reload()
            except Exception as exc:
                print(f"[Config] Watcher error: {exc}")
            self._stop_event.wait(timeout=self.check_interval)

    def stop_watcher(self) -> None:
        self._stop_event.set()
        watcher = self._watcher
        if watcher and watcher.is_alive():
            watcher.join(timeout=2.0)
            if watcher.is_alive():
                print("[Config] Watcher thread did not stop in time.")
            else:
                print("[Config] Watcher stopped.")
        self._watcher = None

    def close(self) -> None:
        self.stop_watcher()

    def __enter__(self) -> "ConfigManager":
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.close()

