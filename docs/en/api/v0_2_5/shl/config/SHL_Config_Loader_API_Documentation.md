# Config (SHL Configuration Loader) API Documentation

## Overview

`config.py` loads the SHL configuration from the project root. It automatically creates a default configuration if the configuration file does not exist or is corrupted.

---

## Module Metadata

| Field | Value |
|-------|-------|
| **File** | `config.py` |
| **Description** | SHL configuration loader |
| **Author** | Tuomas Lähteenmäki |
| **License** | MIT |
| **Version** | `0.2.5` |

---

## Dependencies and Imports

### Standard Library

- `json`
- `pathlib.Path`

---

## Module Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `PROJECT_ROOT` | `Path.cwd()` | The current working directory at import time. |
| `CONFIG_PATH` | `PROJECT_ROOT / "shl-config.json"` | Path to the configuration file. |
| `_config_cache` | `{}` | In-memory cache for the loaded configuration dictionary. |

---

## Module-Level Side Effect

`load_config()` is called automatically when the module is imported. This means the configuration is loaded (or created with defaults) at import time.

---

## Functions

### `_create_default_config() -> dict`

Creates the default configuration dictionary. This is an internal function.

#### Returns

- `dict` — The default configuration with the following structure:

```json
{
  "ttl": {
    "mymemory": 10,
    "libretranslate": 8,
    "deepl": 5,
    "google": 5,
    "microsoft_translator": 5,
    "papago": 5
  },
  "cache": {
    "cache_persist": false,
    "cache_persist_path": ".shl_cache.json",
    "ttl": 3600,
    "max_size": 10000
  }
}
```

---

### `load_config()`

Loads the configuration from the project root. Creates defaults if the file is missing or broken.

#### Behavior

1. Checks if `CONFIG_PATH` exists.
   - If it exists, attempts to open and parse it as JSON into `_config_cache`.
   - If parsing fails (any `Exception`), prints an error message to stdout and falls through to default creation.
2. If the file does not exist or parsing failed:
   - Calls `_create_default_config()` and assigns the result to `_config_cache`.
   - Attempts to write the default config to `CONFIG_PATH` as JSON with `indent=4` and `ensure_ascii=False`.
   - Prints a confirmation message on success or an error message on failure.

---

### `get_ttl(provider: str, default=None)`

Retrieves the TTL value for a specific provider from the configuration.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `provider` | `str` | — | Provider name (e.g., `"mymemory"`, `"deepl"`, `"google"`). |
| `default` | `Any` | `None` | Value to return if the provider is not found. |

#### Behavior

- Reads the `"ttl"` section from `_config_cache`.
- Returns `ttl_section.get(provider, default)`.

#### Returns

- `Any` — The configured TTL for the provider, or `default`.

---

### `get_config_value(key: str, default=None)`

Retrieves a value from the configuration. Supports dot-notation for nested keys.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `key` | `str` | — | Configuration key, using `.` as a nested path separator. |
| `default` | `Any` | `None` | Value to return if the key path is not found. |

#### Behavior

1. Splits `key` on `.` into individual key segments.
2. Traverses `_config_cache` dictionary level by level.
3. If any segment is missing or the current value is not a `dict`, returns `default`.
4. Returns the final value if all segments exist.

#### Examples

| Key | Resolves To |
|-----|-------------|
| `"ttl"` | The entire `"ttl"` dictionary. |
| `"ttl.deepl"` | `5` (from default config). |
| `"cache.max_size"` | `10000` (from default config). |
| `"nonexistent.key"` | `default` |

#### Returns

- `Any` — The configuration value at the nested key path, or `default`.

---

### `get_cache_config() -> dict`

Returns the cache configuration with default fallbacks.

#### Behavior

- Reads the `"cache"` section from `_config_cache`.
- Returns a dictionary with the following keys and fallback logic:

| Key | Fallback Chain |
|-----|----------------|
| `"persist"` | `cache.get("persist")` → `cache.get("cache_persist")` → `False` |
| `"persist_path"` | `cache.get("persist_path")` → `cache.get("cache_persist_path")` → `".shl_cache.json"` |
| `"ttl"` | `cache.get("ttl")` → `3600` |
| `"max_size"` | `cache.get("max_size")` → `10000` |

#### Returns

- `dict` — A normalized cache configuration dictionary.

---

## Default Configuration

If `shl-config.json` does not exist, the following default configuration is created automatically:

```json
{
  "ttl": {
    "mymemory": 10,
    "libretranslate": 8,
    "deepl": 5,
    "google": 5,
    "microsoft_translator": 5,
    "papago": 5
  },
  "cache": {
    "cache_persist": false,
    "cache_persist_path": ".shl_cache.json",
    "ttl": 3600,
    "max_size": 10000
  }
}
```

---

## Usage Example

```python
from shl.config.config import get_ttl, get_config_value, get_cache_config

# Get provider TTL
ttl = get_ttl("deepl", default=5)

# Get nested config value
max_size = get_config_value("cache.max_size", default=10000)

# Get normalized cache config
cache_cfg = get_cache_config()
print(cache_cfg["persist"])      # False
print(cache_cfg["persist_path"]) # .shl_cache.json
print(cache_cfg["ttl"])          # 3600
print(cache_cfg["max_size"])     # 10000
```

---

## Version

**Module version:** `0.2.5`

**Author:** Tuomas Lähteenmäki

**License:** MIT
