# EnvLoader API Documentation

## Overview

`env_loader.py` provides dependency-free `.env` file loading for the SHL framework. It parses `KEY=value` lines manually without external packages, supports quoted values and comments, and offers utility functions for safe API key masking and environment variable access.

---

## Module Metadata

| Field | Value |
|-------|-------|
| **File** | `shl/utils/env_loader.py` |
| **Author** | Tuomas Lähteenmäki |
| **Version** | `0.2.4` |
| **License** | MIT |

---

## Dependencies and Imports

### Standard Library

- `os`
- `logging`
- `pathlib.Path`
- `typing` (`Optional`, `Dict`)

---

## Module-Level State

### `_env_loaded`

```python
_env_loaded = False
```

A module-level boolean flag tracking whether the SHL environment has been loaded. Used by `load_shl_env()` to prevent duplicate loading.

---

## Functions

### `load_dotenv_file(env_file: Path) -> bool`

Loads a `.env` file manually without external dependencies.

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `env_file` | `Path` | Path to the `.env` file to load. |

#### Supported Formats

- `KEY=value`
- `KEY="value"`
- `KEY='value'`
- `# comments` (lines starting with `#`)
- Empty lines

#### Behavior

1. If `env_file` does not exist, returns `False`.
2. Opens the file with UTF-8 encoding.
3. Iterates line by line:
   - Strips whitespace.
   - Skips empty lines and comment lines (starting with `#`).
   - Splits on the first `=` character.
   - Strips whitespace from key and value.
   - Removes surrounding double quotes (`"`) or single quotes (`'`) if present.
   - Sets the environment variable via `os.environ[key] = value`.
4. Returns `True` on success.
5. On any exception, logs an error and returns `False`.

#### Returns

- `bool` — `True` if the file was loaded successfully; `False` otherwise.

---

### `load_shl_env(force: bool = False) -> bool`

Loads the `.env` file from the `./.env/shl/` directory.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `force` | `bool` | `False` | If `True`, reloads even if already loaded. |

#### Behavior

1. Checks the global `_env_loaded` flag. If `True` and `force` is `False`, logs a debug message and returns `True`.
2. Resolves the primary path: `Path.cwd() / ".env" / "shl" / ".env"`.
3. If the primary file exists, attempts to load it via `load_dotenv_file()`.
   - On success, sets `_env_loaded = True`, logs a debug message, and returns `True`.
4. Falls back to the project root: `Path.cwd() / ".env"`.
   - If the fallback file exists, attempts to load it.
   - On success, sets `_env_loaded = True`, logs a debug message, and returns `True`.
5. If no file is found, logs a debug message, sets `_env_loaded = True`, and returns `False`.

#### Returns

- `bool` — `True` if an environment file was loaded; `False` if no file was found.

---

### `mask_api_key(key: Optional[str]) -> str`

Masks an API key for safe logging.

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | `Optional[str]` | The API key to mask. |

#### Masking Rules

| Condition | Result |
|-----------|--------|
| `key` is falsy (`None`, empty) | `"(not set)"` |
| Stripped string is empty | `"(not set)"` |
| Length <= 8 | `"*" * len(key)` (fully masked) |
| Length > 8 | First 4 chars + `"*" * (len - 8)` + last 4 chars |

#### Examples

| Input | Output |
|-------|--------|
| `None` | `(not set)` |
| `""` | `(not set)` |
| `"abc123"` | `******` |
| `"my-secret-api-key-12345"` | `my-s****************2345` |

#### Returns

- `str` — The masked API key string.

---

### `get_env_value(key: str, default: Optional[str] = None) -> Optional[str]`

Gets an environment variable value, ensuring the SHL environment is loaded first.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `key` | `str` | — | The environment variable name. |
| `default` | `Optional[str]` | `None` | Default value if the variable is not set. |

#### Behavior

1. Calls `load_shl_env()` to ensure the environment is loaded.
2. Returns `os.getenv(key, default)`.

#### Returns

- `Optional[str]` — The environment variable value, or `default`.

---

### `get_env_value_masked(key: str, default: Optional[str] = None) -> str`

Gets a masked environment variable value.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `key` | `str` | — | The environment variable name. |
| `default` | `Optional[str]` | `None` | Default value if the variable is not set. |

#### Behavior

1. Calls `get_env_value(key, default)`.
2. Passes the result through `mask_api_key()`.

#### Returns

- `str` — The masked value (never `None`; `(not set)` is returned for missing values).

---

### `get_env_file_path() -> Path`

Returns the path to the SHL `.env` file.

#### Returns

- `Path` — `Path.cwd() / ".env" / "shl" / ".env"`.

---

### `is_env_loaded() -> bool`

Checks if the SHL environment has been loaded.

#### Returns

- `bool` — The current value of the global `_env_loaded` flag.

---

### `reset_env_loader() -> None`

Resets the environment loader state.

#### Behavior

- Sets the global `_env_loaded` flag to `False`.
- Logs a debug message.

---

## Usage Example

```python
from shl.utils.env_loader import (
    load_shl_env,
    get_env_value,
    get_env_value_masked,
    mask_api_key,
    get_env_file_path,
    is_env_loaded,
    reset_env_loader,
)

# Load environment (idempotent)
load_shl_env()

# Get a value
api_key = get_env_value("DEEPL_API_KEY")

# Get a masked value for logging
masked = get_env_value_masked("DEEPL_API_KEY")
print(f"API key: {masked}")  # API key: abcd****************wxyz

# Mask any key directly
masked = mask_api_key("my-secret-key")

# Check if loaded
if is_env_loaded():
    print("Environment loaded")

# Get the expected .env path
path = get_env_file_path()

# Force reload
load_shl_env(force=True)

# Reset state
reset_env_loader()
```

---

## Version

**Module version:** `0.2.4`

**Author:** Tuomas Lähteenmäki

**License:** MIT
