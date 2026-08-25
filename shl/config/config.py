"""
file: config/config.py - SHL configuration loader
Author: Tuomas Lähteenmäki
Version: 0.2.6
License: MIT
Description: Loads SHL configuration from the project root.
Creates the default configuration automatically if the file does not exist.
Supports thread-safe hot reload and automatic recovery from corrupted
configuration files.
"""

import json
import logging
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path.cwd()
CONFIG_PATH = PROJECT_ROOT / "shl-config.json"
BACKUP_PATH = CONFIG_PATH.with_suffix(".json.bak")

_config_cache: Dict[str, Any] = {}
_config_lock = threading.RLock()

_config_mtime: float = 0.0
_config_loaded = False

_watcher: Optional[threading.Thread] = None
_stop_event = threading.Event()


def _create_default_config() -> dict:
    """Create the default SHL configuration."""
    return {
        "ttl": {
            "local": 86400,
            "mymemory": 86400,
            "libretranslate": 86400,
            "deepl": 86400,
            "google": 86400,
            "microsoft_translator": 86400,
            "papago": 86400,
            "yandex": 86400
        },
        "cache": {
            "cache_persist": False,
            "cache_persist_path": ".shl_cache.json",
            "ttl": 3600,
            "max_size": 10000
        },
        "reload": {
            "enabled": True,
            "check_interval": 1.0
        },
        "providers": {
            "local": {
                "url": "https://localhost:8000"
            },
            "libretranslate": {
                "url": "https://libretranslate.com"
            },
            "yandex": {
                "folder_id": None
            }
        }
    }


def _write_config(config: Dict[str, Any]) -> bool:
    """
    Write configuration to disk.

    Uses a temporary file and replaces the target atomically to avoid
    leaving a partially written configuration file.
    """
    temp_path = CONFIG_PATH.with_suffix(".json.tmp")

    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(
                config,
                f,
                indent=4,
                ensure_ascii=False,
            )
            f.write("\n")

        temp_path.replace(CONFIG_PATH)

        return True

    except Exception as exc:
        logger.error(
            "Failed to write config %s: %s",
            CONFIG_PATH,
            exc,
        )

        try:
            if temp_path.exists():
                temp_path.unlink()
        except OSError:
            pass

        return False


def _get_recovery_config() -> Dict[str, Any]:
    """
    Return the last known valid configuration.

    Falls back to the default configuration if no valid configuration
    has been loaded yet.
    """
    with _config_lock:
        if _config_loaded and _config_cache:
            return deepcopy(_config_cache)

    return _create_default_config()


def _backup_broken_config() -> bool:
    """
    Back up the corrupted configuration.

    Only one backup file is maintained. An existing backup is replaced.
    """
    if not CONFIG_PATH.exists():
        return False

    try:
        CONFIG_PATH.replace(BACKUP_PATH)

        logger.warning(
            "Backed up broken config to %s",
            BACKUP_PATH,
        )

        return True

    except OSError as exc:
        logger.error(
            "Failed to back up broken config %s: %s",
            CONFIG_PATH,
            exc,
        )
        return False


def _recover_config() -> bool:
    """
    Recover from a corrupted configuration file.

    The last known valid in-memory configuration is preferred.
    Defaults are used only if no valid configuration has been loaded yet.
    """
    recovery_config = _get_recovery_config()

    if not _backup_broken_config():
        logger.error(
            "Configuration recovery aborted because the broken "
            "configuration could not be backed up."
        )
        return False

    if not _write_config(recovery_config):
        logger.error(
            "Failed to write recovered configuration to %s",
            CONFIG_PATH,
        )

        return False

    try:
        mtime = CONFIG_PATH.stat().st_mtime
    except OSError as exc:
        logger.error(
            "Failed to read recovered config timestamp: %s",
            exc,
        )
        return False

    with _config_lock:
        _config_cache = deepcopy(recovery_config)
        _config_mtime = mtime
        _config_loaded = True

    logger.warning(
        "Recovered configuration at %s",
        CONFIG_PATH,
    )

    return True


def load_config(force: bool = False) -> bool:
    """
    Load SHL configuration.

    Keeps the previous valid configuration if loading fails.
    Automatically recovers from a corrupted configuration file.
    """
    global _config_cache
    global _config_mtime
    global _config_loaded

    if not CONFIG_PATH.exists():
        new_config = _create_default_config()

        if _write_config(new_config):
            try:
                mtime = CONFIG_PATH.stat().st_mtime
            except OSError:
                mtime = 0.0

            with _config_lock:
                _config_cache = deepcopy(new_config)
                _config_mtime = mtime
                _config_loaded = True

            logger.info(
                "Created default config at %s",
                CONFIG_PATH,
            )

            return True

        if not _config_loaded:
            with _config_lock:
                _config_cache = deepcopy(new_config)
                _config_loaded = True

        return False

    try:
        mtime = CONFIG_PATH.stat().st_mtime

        with _config_lock:
            current_mtime = _config_mtime
            already_loaded = _config_loaded

        if not force and already_loaded and mtime <= current_mtime:
            return False

        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            new_config = json.load(f)

        if not isinstance(new_config, dict):
            raise ValueError(
                "Configuration root must be a JSON object."
            )

        with _config_lock:
            _config_cache = deepcopy(new_config)
            _config_mtime = mtime
            _config_loaded = True

        logger.debug(
            "Loaded configuration from %s",
            CONFIG_PATH,
        )

        return True

    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.error(
            "Invalid configuration %s: %s",
            CONFIG_PATH,
            exc,
        )

        return _recover_config()

    except Exception as exc:
        logger.error(
            "Unexpected error while loading config %s: %s",
            CONFIG_PATH,
            exc,
        )

        return False


def _get_reload_settings() -> Tuple[bool, float]:
    """
    Read reload settings directly from the configuration file.

    This allows reload.enabled and reload.check_interval to be changed
    while the application is running.
    """
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)

        if not isinstance(config, dict):
            raise ValueError(
                "Configuration root must be a JSON object."
            )

        reload_config = config.get("reload", {})

        if not isinstance(reload_config, dict):
            reload_config = {}

        enabled = bool(
            reload_config.get("enabled", True)
        )

        try:
            check_interval = max(
                float(
                    reload_config.get(
                        "check_interval",
                        1.0,
                    )
                ),
                0.1,
            )
        except (TypeError, ValueError):
            check_interval = 1.0

        return enabled, check_interval

    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.warning(
            "Failed to read reload settings: %s",
            exc,
        )

        return True, 1.0


def _watch_config() -> None:
    """Watch the configuration file for changes."""
    while not _stop_event.is_set():
        try:
            enabled, interval = _get_reload_settings()

            if CONFIG_PATH.exists():
                mtime = CONFIG_PATH.stat().st_mtime

                with _config_lock:
                    current_mtime = _config_mtime

                if enabled and mtime > current_mtime:
                    load_config()

            else:
                load_config()

            _stop_event.wait(interval)

        except Exception as exc:
            logger.error(
                "Config watcher error: %s",
                exc,
            )
            _stop_event.wait(1.0)

def start_config_watcher() -> None:
    """Start the configuration hot-reload watcher."""
    global _watcher

    with _config_lock:
        if _watcher and _watcher.is_alive():
            return

        _stop_event.clear()

        _watcher = threading.Thread(
            target=_watch_config,
            daemon=True,
            name="SHLConfigWatcher",
        )
        _watcher.start()

    logger.debug("Config watcher started")


def stop_config_watcher() -> None:
    """Stop the configuration hot-reload watcher."""
    global _watcher

    _stop_event.set()

    watcher = _watcher

    if watcher and watcher.is_alive():
        watcher.join(timeout=2.0)

        if watcher.is_alive():
            logger.warning(
                "Config watcher did not stop within timeout."
            )
        else:
            logger.debug("Config watcher stopped.")

    _watcher = None


def get_ttl(provider: str, default=None):
    """Return the TTL configured for a provider."""
    with _config_lock:
        ttl_section = _config_cache.get("ttl", {})

        if not isinstance(ttl_section, dict):
            return default

        return ttl_section.get(provider, default)


def get_config_value(
    key: str,
    default=None,
):
    """Get a configuration value using a dotted key path."""
    with _config_lock:
        keys = key.split(".")
        value = _config_cache

        for key_part in keys:
            if isinstance(value, dict) and key_part in value:
                value = value[key_part]
            else:
                return default

        return value


def get_cache_config() -> dict:
    """
    Return cache configuration with defaults.

    Supports both 'persist' and 'cache_persist' keys.
    """
    with _config_lock:
        cache = _config_cache.get("cache", {})

        if not isinstance(cache, dict):
            cache = {}

        return {
            "persist": cache.get(
                "persist",
                cache.get(
                    "cache_persist",
                    False,
                ),
            ),
            "persist_path": cache.get(
                "persist_path",
                cache.get(
                    "cache_persist_path",
                    ".shl_cache.json",
                ),
            ),
            "ttl": cache.get(
                "ttl",
                3600,
            ),
            "max_size": cache.get(
                "max_size",
                10000,
            ),
        }


load_config()
start_config_watcher()
