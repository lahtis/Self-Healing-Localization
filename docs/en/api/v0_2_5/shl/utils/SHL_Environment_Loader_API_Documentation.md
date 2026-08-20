# SHL Environment Loader — API Documentation

## Module Overview

**File:** `shl/utils/env_loader.py`

Zero-dependency `.env` file loader for the SHL library. Provides manual parsing of environment files without requiring external packages like `python-dotenv`. Includes SHL-specific path resolution, API key masking for secure logging, and lazy environment loading with idempotency control.

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
| `os` | Environment variable access (`os.environ`, `os.getenv`). |
| `logging` | Debug and error log output. |
| `pathlib.Path` | Cross-platform path construction. |
| `typing.Optional`, `typing.Dict` | Type annotations. |

---

## Module-Level State

| Name | Type | Description |
|------|------|-------------|
| `_env_loaded` | `bool` | Tracks whether `load_shl_env()` has been called successfully. Prevents redundant file reads. |

---

## Functions

### `load_dotenv_file()`

```python
def load_dotenv_file(env_file: Path) -> bool
```

Manually parses a `.env` file and loads its key-value pairs into `os.environ`. Requires no external dependencies.

| Parameter | Type | Description |
|-----------|------|-------------|
| `env_file` | `Path` | Path to the `.env` file to parse. |

**Returns**
- `bool` — `True` if the file was found and parsed successfully, `False` otherwise.

**Supported Syntax**

| Format | Example | Result |
|--------|---------|--------|
| `KEY=value` | `API_KEY=abc123` | `os.environ["API_KEY"] = "abc123"` |
| `KEY="value"` | `NAME="My App"` | `os.environ["NAME"] = "My App"` |
| `KEY='value'` | `PATH='/usr/bin'` | `os.environ["PATH"] = "/usr/bin"` |
| `# comment` | `# This is ignored` | Skipped |
| Empty line | | Skipped |

**Parsing Rules**
1. Strips whitespace from each line.
2. Skips empty lines and lines starting with `#`.
3. Splits on the first `=` only (`KEY=a=b` → `key="KEY"`, `value="a=b"`).
4. Strips whitespace from key and value.
5. Removes surrounding single or double quotes from values.
6. Sets the variable via `os.environ[key] = value`.

**Error Handling**
- File not found → returns `False`.
- Any exception during parsing → logs error and returns `False`.

**Example**
```python
from pathlib import Path
from shl.utils.env_loader import load_dotenv_file

loaded = load_dotenv_file(Path("/home/user/project/.env"))
if loaded:
    print("Environment loaded successfully")
```

---

### `load_shl_env()`

```python
def load_shl_env(force: bool = False) -> bool
```

Loads the SHL-specific `.env` file. Searches in a predefined location with automatic fallback to the project root.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `force` | `bool` | `False` | If `True`, reloads the file even if already loaded. |

**Search Order**
1. `./.env/shl/.env` — Primary SHL environment directory (relative to current working directory).
2. `./.env` — Fallback to project root `.env` file.

**Returns**
- `bool` — `True` if an `.env` file was loaded successfully, `False` if no file was found.

**Idempotency**
- If `_env_loaded` is `True` and `force=False`, the function returns immediately without re-reading files.
- After the first successful load, subsequent calls are no-ops unless `force=True`.

**Logging**
- `DEBUG` — Already loaded, loaded from primary path, loaded from fallback path, or not found.

**Example**
```python
from shl.utils.env_loader import load_shl_env

# First call — reads from disk
load_shl_env()  # True (if .env exists)

# Second call — no-op, returns immediately
load_shl_env()  # True

# Force reload
load_shl_env(force=True)  # Re-reads from disk
```

---

### `mask_api_key()`

```python
def mask_api_key(key: Optional[str]) -> str
```

Masks an API key for safe logging, preventing credential leakage in log files or console output.

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | `Optional[str]` | Raw API key string, or `None`. |

**Returns**
- `str` — Masked representation of the key.

**Masking Rules**

| Input Condition | Output |
|-----------------|--------|
| `None` or empty string (`""`) | `"(not set)"` |
| Length ≤ 8 characters | `"*" * len(key)` (fully masked) |
| Length > 8 characters | First 4 chars + `*` padding + last 4 chars |

**Examples**
```python
>>> mask_api_key("my-secret-key-12345")
'my-s*****************12345'
>>> mask_api_key("short")
'*****'
>>> mask_api_key(None)
'(not set)'
>>> mask_api_key("abcd1234xyz")
'abcd***xyz'
```

**Security Note**
This is the canonical way to log API keys across all SHL modules. Always mask credentials before including them in log messages.

---

### `get_env_value()`

```python
def get_env_value(
    key: str,
    default: Optional[str] = None,
) -> Optional[str]
```

Retrieves an environment variable, automatically loading the SHL `.env` file first if not already loaded.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `key` | `str` | — | Environment variable name. |
| `default` | `Optional[str]` | `None` | Default value if the variable is not set. |

**Returns**
- `Optional[str]` — The environment variable value, or `default`.

**Behavior**
1. Calls `load_shl_env()` to ensure `.env` is loaded (idempotent).
2. Returns `os.getenv(key, default)`.

**Example**
```python
from shl.utils.env_loader import get_env_value

# Automatically loads .env if needed
api_key = get_env_value("DEEPL_API_KEY")
ttl = get_env_value("MS_TRANSLATOR_TTL", default="600")
```

---

### `get_env_value_masked()`

```python
def get_env_value_masked(
    key: str,
    default: Optional[str] = None,
) -> str
```

Retrieves an environment variable and returns it in masked form suitable for logging.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `key` | `str` | — | Environment variable name. |
| `default` | `Optional[str]` | `None` | Default value if the variable is not set. |

**Returns**
- `str` — Masked value (via `mask_api_key()`), never `None`.

**Example**
```python
from shl.utils.env_loader import get_env_value_masked

# Safe for logging
masked = get_env_value_masked("MICROSOFT_TRANSLATOR_KEY")
logger.debug(f"Using API key: {masked}")
# Using API key: abcd****************wxyz
```

---

### `get_env_file_path()`

```python
def get_env_file_path() -> Path
```

Returns the primary SHL `.env` file path without loading it.

**Returns**
- `Path` — Resolved path to `./.env/shl/.env` (relative to current working directory).

**Example**
```python
from shl.utils.env_loader import get_env_file_path

path = get_env_file_path()
print(path)
# /home/user/project/.env/shl/.env
```

---

### `is_env_loaded()`

```python
def is_env_loaded() -> bool
```

Checks whether the SHL environment has been loaded.

**Returns**
- `bool` — `True` if `load_shl_env()` has completed successfully at least once.

**Example**
```python
from shl.utils.env_loader import is_env_loaded

if not is_env_loaded():
    print("Environment not yet loaded")
```

---

### `reset_env_loader()`

```python
def reset_env_loader() -> None
```

Resets the environment loader state, allowing `load_shl_env()` to re-read the file on the next call.

**Side Effects**
- Sets `_env_loaded` to `False`.

**Use Cases**
- Unit testing (clean state between tests).
- Application reconfiguration.
- Directory changes during runtime.

**Example**
```python
from shl.utils.env_loader import reset_env_loader, load_shl_env

# Reset and reload after changing working directory
reset_env_loader()
load_shl_env()
```

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
)
import logging

logger = logging.getLogger(__name__)

# 1. Ensure environment is loaded (idempotent)
load_shl_env()

# 2. Read credentials
api_key = get_env_value("MICROSOFT_TRANSLATOR_KEY")
if not api_key:
    raise ValueError("API key not configured")

# 3. Log safely with masking
logger.info(f"Initialized with key: {get_env_value_masked('MICROSOFT_TRANSLATOR_KEY')}")
# Initialized with key: abcd****************wxyz

# 4. Direct masking for non-env values
logger.debug(f"Client ID: {mask_api_key('my-client-id-12345')}")
# Client ID: my-c*****************2345

# 5. Check loader state
print(f"Env loaded: {is_env_loaded()}")

# 6. Get expected file path
print(f"Env file: {get_env_file_path()}")
```

---

## File Search Paths

```
Current Working Directory
├── .env/
│   └── shl/
│       └── .env      ← Primary (checked first)
└── .env              ← Fallback (checked second)
```

Both paths are resolved relative to `Path.cwd()` at call time.

---

## Thread Safety

| Function | Status | Notes |
|----------|--------|-------|
| `load_dotenv_file()` | Safe | Read-only file access, no shared state. |
| `load_shl_env()` | Generally safe | `_env_loaded` flag is set atomically in CPython, but concurrent calls may race on file reads. |
| `get_env_value()` | Safe | Calls `load_shl_env()` then `os.getenv()`. |
| `mask_api_key()` | Safe | Pure function, no shared state. |
| `reset_env_loader()` | Caution | Resets `_env_loaded`. Should not be called concurrently with `load_shl_env()`. |

**Recommendation:** Call `load_shl_env()` once during application startup from a single thread. After initialization, all read operations are safe for concurrent use.

---

## Logging

The module uses Python's standard `logging` module under the logger name `__name__`.

**Log Levels Used**

| Level | Event |
|-------|-------|
| `DEBUG` | Environment already loaded, loaded from primary/fallback path, loader reset. |
| `ERROR` | Failed to parse `.env` file. |

---

## Changelog

| Version | Notes |
|---------|-------|
| 0.2.4 | Current — zero-dependency `.env` loader with SHL path resolution, API key masking, and lazy loading. |
