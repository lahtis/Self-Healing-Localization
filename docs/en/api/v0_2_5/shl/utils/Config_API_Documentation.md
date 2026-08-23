# Config API Documentation

## Overview

`config.py` provides a simple configuration loader that reads values from a `config.json` file located in the same directory as the module.

---

## Module Metadata

| Field | Value |
|-------|-------|
| **File** | `config.py` |
| **Author** | Tuomas Lähteenmäki |
| **Version** | `0.2.4` |
| **License** | MIT |
| **Description** | Load `config.json` |

---

## Dependencies and Imports

### Standard Library

- `json`
- `os`

---

## Module Constants

### `CONFIG_PATH`

```python
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
```

The absolute path to the `config.json` file, resolved relative to the directory containing this module (`config.py`).

---

## Functions

### `get_config_value(key: str, default=None)`

Reads a single value from the `config.json` file by key.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `key` | `str` | — | The key to look up in the JSON object. |
| `default` | `Any` | `None` | The value to return if the file does not exist, is unreadable, or the key is missing. |

#### Behavior

1. Checks if `CONFIG_PATH` exists on disk.
   - If the file does not exist, returns `default` immediately.
2. Opens `CONFIG_PATH` in read mode with UTF-8 encoding.
3. Parses the file contents as JSON.
4. Returns `data.get(key, default)`.
5. If any exception occurs during file I/O or JSON parsing, catches it silently and returns `default`.

#### Returns

- `Any` — The value associated with `key` in `config.json`, or `default` if the key is missing or an error occurs.

---

## Usage Example

```python
from shl.config.config import get_config_value

# Read a configuration value
ttl = get_config_value("cache_ttl", default=3600)
enabled = get_config_value("feature_enabled", default=False)

# Returns default if config.json is missing or key does not exist
missing = get_config_value("nonexistent_key", default="fallback")
```

---

## Config File Format

The module expects `config.json` to be a valid JSON object (dictionary). Example:

```json
{
  "cache_ttl": 3600,
  "feature_enabled": true,
  "max_retries": 3
}
```

---

## Error Handling

All errors are handled silently:

- Missing `config.json` file → returns `default`.
- Invalid JSON syntax → returns `default`.
- File permission errors → returns `default`.
- Missing key in JSON → returns `default`.

---

## Version

**Module version:** `0.2.4`

**Author:** Tuomas Lähteenmäki

**License:** MIT
