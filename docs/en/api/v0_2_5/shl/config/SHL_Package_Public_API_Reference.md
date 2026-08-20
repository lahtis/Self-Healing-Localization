# SHL Package — API Documentation

## Module Overview

**File:** `__init__.py`

Package-level initialization for the **Self-Healing Localization Layer (SHL)** — a lightweight, dependency-free Python library designed to eliminate missing translations by providing intelligent fallback mechanisms, multi-provider translation routing, and runtime language support management.

---

## Package Metadata

| Attribute | Value |
|-----------|-------|
| Name | `shl` |
| Full Name | Self-Healing Localization Layer (SHL) |
| Description | A lightweight, dependency-free Python library that eliminates missing translations forever. |

---

## Public API

The `shl` package exposes the following functions at the top level for convenient access:

### `get_ttl()`

```python
from shl import get_ttl
```

Retrieves the TTL (time-to-live) value for a specific translation provider from the SHL configuration.

**Imported from:** `shl.config`

**Signature**
```python
def get_ttl(provider: str, default=None) -> Any
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `provider` | `str` | Provider identifier (e.g., `"mymemory"`, `"libretranslate"`, `"microsoft_translator"`). |
| `default` | `Any` | Fallback value returned if the provider is not found in the TTL configuration section. Defaults to `None`. |

**Returns**
- `Any` — The configured TTL value for the provider, or `default` if not found.

**Example**
```python
from shl import get_ttl

ttl = get_ttl("mymemory", default=3600)
print(ttl)  # 86400 (or the configured value)
```

---

### `get_config_value()`

```python
from shl import get_config_value
```

Retrieves an arbitrary top-level configuration value from the SHL configuration file.

**Imported from:** `shl.config`

**Signature**
```python
def get_config_value(key: str, default=None) -> Any
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | `str` | Top-level configuration key. |
| `default` | `Any` | Fallback value returned if the key is not present. Defaults to `None`. |

**Returns**
- `Any` — The value associated with `key`, or `default` if the key does not exist.

**Example**
```python
from shl import get_config_value

debug = get_config_value("debug_mode", default=False)
max_retries = get_config_value("max_retries", default=3)
```

---

## Configuration File

SHL reads its configuration from `SHL-config.json` located at the project root. The file is loaded once at module import time and cached in memory.

**Expected structure:**
```json
{
    "ttl": {
        "mymemory": 86400,
        "libretranslate": 43200,
        "microsoft_translator": 600
    },
    "debug_mode": false,
    "max_retries": 3
}
```

| Section | Description |
|---------|-------------|
| `ttl` | Provider-specific cache TTL values in seconds. |
| *(top-level)* | Arbitrary configuration keys accessible via `get_config_value()`. |

---

## Usage Example

```python
import shl

# Read provider TTL
cache_ttl = shl.get_ttl("libretranslate", default=3600)
print(f"LibreTranslate cache TTL: {cache_ttl}s")

# Read general configuration
debug_mode = shl.get_config_value("debug_mode", default=False)
print(f"Debug mode: {debug_mode}")
```

---

## Related Modules

| Module | Purpose |
|--------|---------|
| `shl.config` | Configuration loading and accessor functions (`get_ttl`, `get_config_value`). |
| `shl.router` | Intelligent translation routing with failover across multiple providers. |
| `shl.cache` | In-memory translation result caching. |
| `shl.metadata` | Core data structures (`TranslationRequest`, `TranslationResult`). |
| `shl.providers` | Provider adapter implementations (DeepL, Google, Papago, LibreTranslate, MyMemory, Microsoft). |

---

## Changelog

| Version | Notes |
|---------|-------|
| Current | Exposes `get_ttl` and `get_config_value` at the package level for convenient configuration access. |
