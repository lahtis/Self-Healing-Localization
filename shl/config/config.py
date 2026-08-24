"""
file: config.py - SHL configuration loader
Author: Tuomas Lähteenmäki
License: MIT
Version: 0.2.5

Lataa konfiguraation projektin juuresta.
Luo oletuskonfiguraation automaattisesti jos tiedostoa ei ole.
"""

import json
from pathlib import Path

PROJECT_ROOT = Path.cwd()
CONFIG_PATH = PROJECT_ROOT / "shl-config.json"

_config_cache = {}


def _create_default_config() -> dict:
    """Luo oletuskonfiguraation."""
    return {
        "ttl": {
            "mymemory": 10,
            "libretranslate": 8,
            "deepl": 5,
            "google": 5,
            "microsoft_translator": 5,
            "papago": 5
        },
        "cache": {
            "cache_persist": False,
            "cache_persist_path": ".shl_cache.json",
            "ttl": 3600,
            "max_size": 10000
        },
        "providers": {
            "yandex": {
                "folder_id": None
            }
        }
    }


def load_config():
    """Lataa konfiguraation projektin juuresta. Luo oletukset jos puuttuu."""
    global _config_cache

    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                _config_cache = json.load(f)
            return
        except Exception as e:
            print(f"[Config] Failed to load {CONFIG_PATH}: {e}")

    # Tiedostoa ei ole tai se on rikkinäinen — luo oletukset
    _config_cache = _create_default_config()
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(_config_cache, f, indent=4, ensure_ascii=False)
        print(f"[Config] Created default config at {CONFIG_PATH}")
    except Exception as e:
        print(f"[Config] Failed to create config: {e}")


load_config()


def get_ttl(provider: str, default=None):
    ttl_section = _config_cache.get("ttl", {})
    return ttl_section.get(provider, default)


def get_config_value(key: str, default=None):
    """Hakee arvon konfiguraatiosta. Tukee pisteellisiä avaimia (nested)."""
    keys = key.split(".")
    value = _config_cache
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default
    return value


def get_cache_config() -> dict:
    """
    Palauttaa cache-konfiguraation oletusarvoilla.
    Tukee sekä 'persist' että 'cache_persist' -avaimia.
    """
    cache = _config_cache.get("cache", {})
    return {
        "persist": cache.get("persist", cache.get("cache_persist", False)),
        "persist_path": cache.get("persist_path", cache.get("cache_persist_path", ".shl_cache.json")),
        "ttl": cache.get("ttl", 3600),
        "max_size": cache.get("max_size", 10000),
    }

