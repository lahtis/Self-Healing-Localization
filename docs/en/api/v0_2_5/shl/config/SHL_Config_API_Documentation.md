# SHL Config Loader — API Documentation

## Module Overview

A lightweight, module-level configuration cache for the SHL project. Loads `SHL-config.json` once at import time and provides simple accessor functions for TTL values and arbitrary top-level config keys.

---

## Constants

| Name | Type | Description |
|------|------|-------------|
| `PROJECT_ROOT` | `pathlib.Path` | Absolute path to the project root directory (three levels above this file). |
| `CONFIG_PATH` | `pathlib.Path` | Absolute path to `SHL-config.json`, resolved relative to `PROJECT_ROOT`. |

---

## Global Variables

| Name | Type | Description |
|------|------|-------------|
| `_config_cache` | `dict` | Internal in-memory cache of the parsed JSON configuration. Populated by `load_config()` at module import. |

---

## Functions

### `load_config()`

```python
def load_config() -> None
```

Loads or reloads the configuration file from disk into `_config_cache`.

**Behavior**
- Reads `CONFIG_PATH` as UTF-8 encoded JSON.
- If the file does not exist, `_config_cache` is set to an empty dict `{}`.
- If the file exists but is unreadable or contains invalid JSON, `_config_cache` is set to an empty dict `{}` (fail-silent).

**Side Effects**
- Mutates the module-level `_config_cache` variable.

---

### `get_ttl()`

```python
def get_ttl(provider: str, default=None) -> Any
```

Retrieves the TTL (time-to-live) value for a given provider from the `ttl` section of the configuration.

| Parameter | Type | Description |
|-----------|------|-------------|
| `provider` | `str` | Provider identifier (e.g., `"mymemory"`, `"libretranslate"`). |
| `default` | `Any` | Value returned if the provider is not found in the `ttl` section or if the section is missing. Defaults to `None`. |

**Returns**
- The TTL value associated with `provider`, or `default` if not found.

**Example**
```python
>>> get_ttl("mymemory", default=3600)
86400
>>> get_ttl("unknown_provider", default=300)
300
```

---

### `get_config_value()`

```python
def get_config_value(key: str, default=None) -> Any
```

Retrieves an arbitrary top-level configuration value by key.

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | `str` | Top-level key in the configuration JSON. |
| `default` | `Any` | Value returned if the key is not present. Defaults to `None`. |

**Returns**
- The value associated with `key`, or `default` if the key does not exist.

**Example**
```python
>>> get_config_value("debug_mode", default=False)
True
>>> get_config_value("nonexistent_key", default="fallback")
'fallback'
```

---

## Configuration File Format

`SHL-config.json` is expected at the project root. The module recognizes at minimum the following structure:

```json
{
  "ttl": {
    "mymemory": 86400,
    "libretranslate": 43200
  },
  "debug_mode": false,
  "max_retries": 3
}
```

- The `ttl` key is optional. If omitted, `get_ttl()` returns `default` for all providers.
- Any additional top-level keys are accessible via `get_config_value()`.

---

## Error Handling & Thread Safety

| Concern | Behavior |
|---------|----------|
| Missing config file | Silently falls back to empty cache. |
| Invalid JSON | Silently falls back to empty cache. |
| Reloading config | Call `load_config()` again to re-read from disk. |
| Thread safety | Not guaranteed. `_config_cache` is a module-level mutable global. Concurrent reads are generally safe in CPython, but concurrent calls to `load_config()` may cause race conditions. |

---

## Usage Example

```python
from shl.config import load_config, get_ttl, get_config_value

# Config is already loaded at import, but can be reloaded explicitly:
load_config()

# Get provider-specific TTL
cache_ttl = get_ttl("mymemory", default=3600)

# Get general config value
debug = get_config_value("debug_mode", default=False)
```
