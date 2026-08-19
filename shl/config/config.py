import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "SHL-config.json"

_config_cache = {}

def load_config():
    global _config_cache

    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                _config_cache = json.load(f)
        except Exception:
            _config_cache = {}
    else:
        _config_cache = {}

load_config()

def get_ttl(provider: str, default=None):
    ttl_section = _config_cache.get("ttl", {})
    return ttl_section.get(provider, default)

def get_config_value(key: str, default=None):
    return _config_cache.get(key, default)

