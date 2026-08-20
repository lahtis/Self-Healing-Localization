# SHL Logging Configuration — API Documentation

## Module Overview

**File:** `logging_config.py`

Unified logging configuration for the Self-Healing Localization Layer (SHL). Provides consistent log formatting across all modules, dual-output logging (console for development, rotating file for errors), configurable log levels, and secure API key masking. Designed to be initialized once at application startup and used by all SHL components.

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
| `logging` | Core Python logging framework. |
| `sys` | Console output via `sys.stdout`. |
| `os` | Directory creation and file size checks. |
| `glob` | Backup log file discovery. |
| `logging.handlers.RotatingFileHandler` | Automatic log rotation by file size. |
| `typing.Optional`, `typing.List`, `typing.Dict`, `typing.Any` | Type annotations. |

---

## Module Constants

| Name | Type | Value | Description |
|------|------|-------|-------------|
| `DEFAULT_CONSOLE_LEVEL` | `int` | `logging.INFO` | Default log level for console output. |
| `DEFAULT_FILE_LEVEL` | `int` | `logging.WARNING` | Default log level for file output. |
| `DEFAULT_LOG_FILE` | `str` | `"error.log"` | Default log file path. |
| `DEFAULT_MAX_BYTES` | `int` | `1_048_576` (1 MB) | Maximum log file size before rotation. |
| `DEFAULT_BACKUP_COUNT` | `int` | `3` | Number of rotated backup files to retain. |

---

## Module-Level State

| Name | Type | Description |
|------|------|-------------|
| `_logging_initialized` | `bool` | Whether `setup_logging()` has been called. Prevents duplicate handler registration. |
| `_active_log_files` | `List[str]` | Tracks active log file paths for statistics queries. |

---

## Functions

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

### `setup_logging()`

```python
def setup_logging(
    console_level: int = DEFAULT_CONSOLE_LEVEL,
    file_level: int = DEFAULT_FILE_LEVEL,
    log_file: str = DEFAULT_LOG_FILE,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
    force: bool = False,
) -> logging.Logger
```

Configures unified logging for the entire SHL library. Should be called once at application startup before any other SHL operations.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `console_level` | `int` | `logging.INFO` | Minimum log level for console output. |
| `file_level` | `int` | `logging.WARNING` | Minimum log level for file output. |
| `log_file` | `str` | `"error.log"` | Path to the rotating log file. |
| `max_bytes` | `int` | `1_048_576` | Maximum size in bytes before log rotation. |
| `backup_count` | `int` | `3` | Number of backup files to keep (e.g., `error.log.1`, `error.log.2`). |
| `force` | `bool` | `False` | If `True`, clears existing handlers and re-initializes. |

**Returns**
- `logging.Logger` — The root logger instance.

**Behavior**
1. Checks `_logging_initialized`; skips if already initialized and `force=False`.
2. Sets root logger level to `DEBUG` (handlers perform filtering).
3. Creates a `StreamHandler` → `sys.stdout` for console output.
4. Creates a `RotatingFileHandler` for file output with UTF-8 encoding.
5. Ensures the log directory exists.
6. Configures library-specific levels (`shl` → `DEBUG`, `urllib3`/`requests` → `WARNING`).
7. Logs initialization summary.

**Console Format**
```
INFO     [shl.router] Translation successful
WARNING  [shl.providers.microsoft] Rate limit approaching
```

**File Format**
```
2024-01-15 09:30:45 | INFO     | shl.router | translate_text:142 | Translation successful
2024-01-15 09:31:12 | WARNING  | shl.providers.microsoft | _call_api:89 | Rate limit approaching
```

**Example**
```python
from shl.logging_config import setup_logging
import logging

# Standard setup
setup_logging()

# Debug mode (force re-init)
setup_logging(console_level=logging.DEBUG, force=True)

# Custom file with larger rotation
setup_logging(
    log_file="logs/shl.log",
    max_bytes=5 * 1024 * 1024,  # 5 MB
    backup_count=5,
)
```

---

### `get_logger()`

```python
def get_logger(
    name: str,
    add_shl_prefix: bool = True,
) -> logging.Logger
```

Returns a namespaced logger for an SHL module.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | — | Module name (typically `__name__`). |
| `add_shl_prefix` | `bool` | `True` | If `True`, prefixes the name with `shl.` if not already present. |

**Returns**
- `logging.Logger` — Configured logger instance.

**Example**
```python
from shl.logging_config import get_logger

# Standard usage
logger = get_logger(__name__)
# Name: "shl.my_module" (if __name__ == "my_module")

# External module
logger = get_logger("my_app", add_shl_prefix=False)
# Name: "my_app"
```

---

### `set_level()`

```python
def set_level(
    level: int,
    logger_name: Optional[str] = None,
) -> None
```

Changes the log level of a logger at runtime.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `level` | `int` | — | New log level (e.g., `logging.DEBUG`). |
| `logger_name` | `Optional[str]` | `None` | Logger to modify. `None` = root logger. |

**Example**
```python
from shl.logging_config import set_level
import logging

# Enable debug for entire application
set_level(logging.DEBUG)

# Quiet down a specific module
set_level(logging.ERROR, 'shl.providers.mymemory')
```

---

### `remove_handler()`

```python
def remove_handler(
    handler_type: str,
    logger_name: Optional[str] = None,
) -> int
```

Removes all handlers of a specific type from a logger.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `handler_type` | `str` | — | Handler class name (e.g., `"StreamHandler"`, `"RotatingFileHandler"`). |
| `logger_name` | `Optional[str]` | `None` | Target logger. `None` = root logger. |

**Returns**
- `int` — Number of handlers removed.

**Example**
```python
from shl.logging_config import remove_handler

# Disable console output
remove_handler('StreamHandler')

# Disable file output
remove_handler('RotatingFileHandler')
```

---

### `get_log_stats()`

```python
def get_log_stats() -> Dict[str, Any]
```

Returns statistics about the current logging configuration and active log files.

**Returns**
- `Dict[str, Any]` — Dictionary with the following keys:

| Key | Type | Description |
|-----|------|-------------|
| `initialized` | `bool` | Whether `setup_logging()` has been called. |
| `handlers` | `int` | Total number of handlers on the root logger. |
| `log_files` | `List[str]` | List of active log file paths. |
| `handler_types` | `List[str]` | Class names of all registered handlers. |
| `log_file_size` | `int` | Size in bytes of the primary log file (0 if not found). |
| `backup_files` | `int` | Number of rotated backup files found. |

**Example**
```python
from shl.logging_config import get_log_stats

stats = get_log_stats()
print(f"Handlers: {stats['handlers']}")
print(f"Log files: {stats['log_files']}")
print(f"Primary log size: {stats['log_file_size']} bytes")
print(f"Backups: {stats['backup_files']}")
```

---

### `reset_logging()`

```python
def reset_logging() -> None
```

Completely resets the logging configuration. Removes all handlers, clears active log file tracking, and resets the initialization flag.

**Use Cases**
- Unit testing (clean state between tests).
- Complete reconfiguration with different parameters.
- Application shutdown and cleanup.

**Example**
```python
from shl.logging_config import reset_logging, setup_logging

# Clean slate
reset_logging()

# Re-initialize with new settings
setup_logging(console_level=logging.DEBUG)
```

---

## Recommended Usage Pattern

```python
# === app.py or main entry point ===
from shl.logging_config import setup_logging
import logging

# Initialize once at startup
setup_logging(
    console_level=logging.INFO,
    file_level=logging.WARNING,
    log_file="logs/shl-error.log",
)

# === any_shl_module.py ===
import logging
from shl.logging_config import mask_api_key

logger = logging.getLogger(__name__)

def some_function(api_key: str):
    logger.debug(f"Initializing with key: {mask_api_key(api_key)}")
    logger.info("Processing translation request")
    logger.warning("Rate limit approaching")
    logger.error("Translation failed")
```

---

## Log Level Guidelines

| Level | When to Use | Example |
|-------|-------------|---------|
| `DEBUG` | Detailed diagnostic information. | Request payloads, response data, cache hits/misses. |
| `INFO` | General operational events. | Translation successful, provider selected, cache updated. |
| `WARNING` | Unexpected but non-fatal events. | Rate limit approaching, fallback provider used, retry attempt. |
| `ERROR` | Failed operations that affect functionality. | Translation failed, API unreachable, invalid response. |
| `CRITICAL` | System-level failures. | (Reserved for future use — configuration corruption, etc.) |

---

## Thread Safety

Python's `logging` module is thread-safe by design. The `setup_logging()` function and all utility functions in this module are safe to call from multiple threads once initialization is complete. However, `setup_logging()` itself should be called from a single thread during application startup to avoid race conditions in handler registration.

---

## Changelog

| Version | Notes |
|---------|-------|
| 0.2.4 | Current — unified logging with console/file output, rotating file handler, API key masking, runtime level adjustment, and log statistics. |
