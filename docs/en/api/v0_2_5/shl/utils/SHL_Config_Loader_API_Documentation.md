# SHL Config Loader — API Documentation

## Module Overview

**File:** `config.py`

Minimal configuration loader for the SHL library. Reads key-value pairs from a JSON file (`config.json`) located alongside this module. Provides a single accessor function with safe fallback behavior.

---

## Metadata

| Attribute | Value |
|-----------|-------|
| Author | Tuomas Lähteenmäki |
| Version | 0.2.4 |
| License | MIT |

---

## Dependencies

| Module | Usage |
|--------|-------|
| `json` | Parsing the configuration file. |
| `os` | File existence checks and path construction. |

---

## Module Constants

| Name | Type | Value | Description |
|------|------|-------|-------------|
| `CONFIG_PATH` | `str` | `os.path.join(os.path.dirname(__file__), "config.json")` | Absolute path to the JSON configuration file, resolved relative to this module's directory. |

---

## Functions

### `get_config_value()`

```python
def get_config_value(key: str, default=None) -> Any
```

Retrieves a top-level value from the JSON configuration file.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `key` | `str` | — | Top-level key to look up in the configuration JSON. |
| `default` | `Any` | `None` | Value returned if the file is missing, unreadable, invalid, or the key is not found. |

**Returns**
- `Any` — The value associated with `key`, or `default` on any failure.

**Behavior**
1. Checks if `CONFIG_PATH` exists. If not, returns `default`.
2. Opens the file as UTF-8 and parses it as JSON.
3. Returns `data.get(key, default)`.
4. On any exception (invalid JSON, permission error, etc.), silently returns `default`.

**Fail-Silent Design**
The function never raises. All error conditions (missing file, malformed JSON, I/O errors) are handled gracefully by returning the default value.

**Example**
```python
from shl.config import get_config_value

# Read a configuration value
debug_mode = get_config_value("debug_mode", default=False)
max_retries = get_config_value("max_retries", default=3)
timeout = get_config_value("request_timeout", default=30.0)

# Missing key returns default
unknown = get_config_value("nonexistent_key", default="fallback")
# "fallback"
```

---

## Configuration File Format

`config.json` is expected in the same directory as `config.py`:

```json
{
    "debug_mode": false,
    "max_retries": 3,
    "request_timeout": 30.0,
    "cache_enabled": true
}
```

- Only top-level keys are accessible via `get_config_value()`.
- Nested objects can be stored but must be accessed as a whole (e.g., `get_config_value("providers")`).

---

## Usage Example

```python
from shl.config import get_config_value

# Check if debug logging is enabled
if get_config_value("debug_mode", default=False):
    print("Debug mode is ON")

# Get provider-specific settings
provider_ttl = get_config_value("mymemory_ttl", default=86400)
```

---

## Thread Safety

`get_config_value()` performs read-only file access and is safe for concurrent use. However, it reads the file from disk on **every call** — there is no in-memory caching. For high-frequency access, consider caching the result in the calling code.

---

## Performance Notes

| Concern | Behavior |
|---------|----------|
| Disk I/O | File is read and parsed on every call. |
| Caching | None. Repeated calls with the same key re-read the file. |
| JSON parsing | Full file is parsed even if only one key is needed. |

For applications that read configuration frequently, wrapping `get_config_value()` with a simple cache or loading the file once at startup is recommended.

---

## Changelog

| Version | Notes |
|---------|-------|
| 0.2.4 | Current — minimal JSON config loader with fail-silent `get_config_value()`. |
