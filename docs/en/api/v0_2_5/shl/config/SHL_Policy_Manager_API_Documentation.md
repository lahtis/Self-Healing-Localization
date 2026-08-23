# ConfigManager API Documentation

## Overview

`ConfigManager` is the SHL policy configuration manager. It provides zero-dependency, thread-safe configuration loading from a JSON file with automatic file watching, `.env` support, provider availability checks, and reload callbacks.

---

## Module Metadata

| Field | Value |
|-------|-------|
| **File** | `policy_manager.py` |
| **Description** | SHL policy manager |
| **Author** | Tuomas Lähteenmäki |
| **License** | MIT |
| **Version** | `0.2.5` |

---

## Dependencies and Imports

### Standard Library

- `json`
- `os`
- `threading`
- `copy.deepcopy`
- `pathlib.Path`
- `typing` (`Any`, `Callable`, `Dict`, `List`, `Optional`, `Union`)

---

## Module Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `__all__` | `["ConfigManager"]` | Public API export list. |
| `DEFAULT_POLICY_PATH` | `Path.cwd() / "shl-policy-config.json"` | Default path for the policy configuration file. |

---

## Class: `ConfigManager`

### Constructor

```python
ConfigManager(
    path: Optional[Union[str, Path]] = None,
    check_interval: float = 1.0,
    env_path: Optional[Union[str, Path]] = ".env",
)
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | `Optional[Union[str, Path]]` | `None` | Path to the policy configuration JSON file. Defaults to `DEFAULT_POLICY_PATH`. |
| `check_interval` | `float` | `1.0` | Interval in seconds between file change checks in the watcher thread. |
| `env_path` | `Optional[Union[str, Path]]` | `".env"` | Path to the `.env` file to load. If `None`, `.env` loading is skipped. |

#### Instance Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `path` | `Path` | Resolved path to the policy configuration file. |
| `check_interval` | `float` | File watcher check interval in seconds. |
| `env_path` | `Optional[Path]` | Resolved path to the `.env` file, or `None`. |
| `_lock` | `threading.RLock` | Reentrant lock for thread-safe access. |
| `_config` | `Dict[str, Any]` | In-memory configuration dictionary. |
| `_last_mtime` | `float` | Last known modification time of the config file. Initialized to `0.0`. |
| `_last_env_mtime` | `float` | Last known modification time of the `.env` file. Initialized to `0.0`. |
| `_stop_event` | `threading.Event` | Event used to signal the watcher thread to stop. |
| `_watcher` | `Optional[threading.Thread]` | The background watcher thread. |
| `_callbacks` | `List[Callable[[Dict[str, Any]], None]]` | List of callbacks invoked on configuration reload. |

#### Behavior

1. Prints debug information about the config path, current working directory, and whether the file exists.
2. If `env_path` is set, calls `_load_env()`.
3. Calls `reload(force=True)`.
4. Calls `start_watcher()`.

---

### Methods

#### `_load_env() -> bool`

Loads environment variables from the `.env` file.

##### Behavior

- If `self.env_path` is not set or does not exist, returns `False`.
- Opens the file with UTF-8 encoding.
- Iterates line by line:
  - Strips whitespace.
  - Skips empty lines, comments (starting with `#`), and lines without `=`.
  - Splits on the first `=`.
  - Strips key and value.
  - Removes surrounding quotes (`"` or `'`) if the value length is at least 2 and the first and last characters match and are quotes.
  - Sets `os.environ[key] = value`.
- Updates `_last_env_mtime` to the file's `st_mtime`.
- Prints a confirmation message.
- Returns `True` on success, `False` on any exception (with error printed).

---

#### `_check_env_reload() -> bool`

Checks if the `.env` file has been modified and reloads it if necessary.

##### Behavior

- If `env_path` does not exist, returns `False`.
- Compares current `st_mtime` against `_last_env_mtime`.
- If newer, calls `_load_env()`.
- Returns `False` if the file has not changed or on `OSError`.

---

#### `get_env(key: str, default: Optional[str] = None) -> Optional[str]`

Retrieves an environment variable.

##### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `key` | `str` | — | Environment variable name. |
| `default` | `Optional[str]` | `None` | Default value if not set. |

##### Returns

- `Optional[str]` — `os.environ.get(key, default)`.

---

#### `reload(force: bool = False) -> bool`

Reloads the configuration from disk.

##### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `force` | `bool` | `False` | If `True`, reloads regardless of modification time. |

##### Behavior

1. If `self.path` does not exist, calls `_create_default_config()`.
2. Gets the file's `st_mtime`.
3. If not `force` and `mtime <= _last_mtime`, returns `False`.
4. Opens and parses the JSON file.
5. Validates that the root is a `dict`.
6. Deep-copies the new configuration.
7. Acquires the lock, updates `_config` and `_last_mtime`.
8. Deep-copies the config for callbacks.
9. Invokes all registered callbacks with the new config.
10. Prints a confirmation message.
11. Returns `True` on success.
12. On any exception, prints an error and returns `False`.

##### Returns

- `bool` — `True` if the configuration was reloaded; `False` otherwise.

---

#### `_create_default_config() -> None`

Creates the default policy configuration file. This is an internal method.

##### Default Configuration

```json
{
  "MyMemory": {
    "enabled": true,
    "allow": [],
    "deny": ["html"],
    "timeout": 10,
    "requires_env": ["MYMEMORY_EMAIL"],
    "priority": 1
  },
  "LibreTranslate": {
    "enabled": true,
    "allow": [],
    "deny": ["html"],
    "timeout": 8,
    "requires_env": [],
    "priority": 2
  },
  "DeepL": {
    "enabled": false,
    "allow": [],
    "deny": [],
    "timeout": 5,
    "requires_env": ["DEEPL_API_KEY"],
    "priority": 3
  },
  "Google": {
    "enabled": false,
    "allow": [],
    "deny": [],
    "timeout": 5,
    "requires_env": ["GOOGLE_API_KEY"],
    "priority": 4
  },
  "MicrosoftTranslator": {
    "enabled": false,
    "allow": [],
    "deny": [],
    "timeout": 5,
    "requires_env": ["MICROSOFT_TRANSLATOR_KEY"],
    "priority": 5
  },
  "Papago": {
    "enabled": false,
    "allow": [],
    "deny": ["html"],
    "timeout": 5,
    "requires_env": ["NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET"],
    "priority": 6
  }
}
```

##### Behavior

- Creates parent directories if needed (`mkdir(parents=True, exist_ok=True)`).
- Writes the default config to `self.path` as JSON with `indent=4` and `ensure_ascii=False`.
- Prints a confirmation message.

---

#### `get() -> Dict[str, Any]`

Returns a deep copy of the entire configuration.

##### Returns

- `Dict[str, Any]` — A copy of the current configuration dictionary.

---

#### `get_value(key: str, default: Any = None) -> Any`

Retrieves a top-level value from the configuration.

##### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `key` | `str` | — | Top-level configuration key. |
| `default` | `Any` | `None` | Default value if key is missing. |

##### Returns

- `Any` — The value associated with `key`, or `default`. Returned as a deep copy.

---

#### `get_provider(name: str) -> Dict[str, Any]`

Retrieves a provider's configuration dictionary.

##### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Provider name (top-level key). |

##### Returns

- `Dict[str, Any]` — The provider's configuration as a deep copy. Returns `{}` if the provider is not found or is not a dictionary.

---

#### `get_provider_setting(name: str, key: str, default: Any = None) -> Any`

Retrieves a specific setting from a provider's configuration.

##### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | Provider name. |
| `key` | `str` | Setting key within the provider dict. |
| `default` | `Any` | `None` | Default value if provider or key is missing. |

##### Returns

- `Any` — The setting value as a deep copy, or `default`.

---

#### `is_enabled(provider_name: str) -> bool`

Checks if a provider is enabled.

##### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `provider_name` | `str` | Provider name. |

##### Returns

- `bool` — `True` if the provider's `"enabled"` setting is truthy; `False` otherwise.

---

#### `is_available(provider_name: str) -> bool`

Checks if a provider is available (enabled and has all required environment variables).

##### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `provider_name` | `str` | Provider name. |

##### Behavior

1. Returns `False` if the provider is not enabled.
2. Gets the `"requires_env"` list.
3. If `requires_env` is not a list, returns `True`.
4. Returns `True` only if all required environment variables are set (truthy).

##### Returns

- `bool` — `True` if the provider is enabled and all required environment variables are present.

---

#### `get_timeout(provider_name: str, default: float = 10.0) -> float`

Retrieves the timeout for a provider.

##### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `provider_name` | `str` | Provider name. |
| `default` | `float` | `10.0` | Default timeout if not configured. |

##### Returns

- `float` — The provider's timeout, cast to `float`.

---

#### `get_enabled_providers() -> List[str]`

Returns a list of all enabled provider names.

##### Returns

- `List[str]` — Names of providers where `config.get("enabled", False) is True`.

---

#### `get_available_providers() -> List[str]`

Returns a list of available provider names, sorted by priority.

##### Behavior

1. Iterates over all top-level configuration entries.
2. Skips entries that are not dictionaries or are not enabled.
3. Checks `requires_env`: if it's a non-empty list, verifies all environment variables are set.
4. Collects `(priority, name)` tuples.
5. Sorts by priority (ascending).
6. Returns only the names.

##### Returns

- `List[str]` — Available provider names sorted by priority.

---

#### `get_fallback_providers(current_provider: Optional[str] = None) -> List[str]`

Returns a list of enabled providers excluding the current one.

##### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `current_provider` | `Optional[str]` | `None` | Provider name to exclude. |

##### Returns

- `List[str]` — Enabled provider names except `current_provider`.

---

#### `on_reload(callback: Callable[[Dict[str, Any]], None]) -> None`

Registers a callback to be invoked when the configuration is reloaded.

##### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `callback` | `Callable[[Dict[str, Any]], None]` | Function to call on reload. Receives a deep copy of the config. |

##### Raises

- `TypeError` — If `callback` is not callable.

##### Behavior

- Acquires the lock.
- Adds the callback to `_callbacks` if not already present.

---

#### `remove_reload_callback(callback: Callable[[Dict[str, Any]], None]) -> None`

Removes a previously registered reload callback.

##### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `callback` | `Callable[[Dict[str, Any]], None]` | The callback to remove. |

##### Behavior

- Acquires the lock.
- Removes the callback from `_callbacks` if present.

---

#### `start_watcher() -> None`

Starts the background file watcher thread.

##### Behavior

- Acquires the lock.
- If a watcher thread already exists and is alive, returns immediately.
- Clears the stop event.
- Creates and starts a daemon thread named `"SHLConfigWatcher"` that runs `_watch()`.
- Prints a confirmation message with the check interval.

---

#### `_watch() -> None`

The watcher thread's main loop. This is an internal method.

##### Behavior

- Runs while `_stop_event` is not set.
- Each iteration:
  - Calls `_check_env_reload()`.
  - Calls `reload()`.
  - Catches and prints any exceptions.
  - Waits for `_stop_event` with `timeout=self.check_interval`.

---

#### `stop_watcher() -> None`

Stops the background file watcher thread.

##### Behavior

- Sets `_stop_event`.
- If the watcher thread exists and is alive, joins it with a 2.0-second timeout.
- Prints a message indicating whether the thread stopped in time.
- Sets `_watcher` to `None`.

---

#### `close() -> None`

Closes the manager by stopping the watcher.

##### Behavior

- Calls `stop_watcher()`.

---

#### `__enter__() -> "ConfigManager"`

Context manager entry. Returns `self`.

#### `__exit__(exc_type: Any, exc_value: Any, traceback: Any) -> None`

Context manager exit. Calls `close()`.

---

## Thread Safety

All public methods that access or mutate `_config` or `_callbacks` acquire `self._lock` (a `threading.RLock`). The watcher thread runs in the background as a daemon and is started automatically during construction.

---

## Usage Example

```python
from shl.config.policy_manager import ConfigManager

# Initialize with default path
manager = ConfigManager()

# Check provider availability
if manager.is_available("DeepL"):
    print("DeepL is ready")

# Get timeout
timeout = manager.get_timeout("LibreTranslate", default=10.0)

# Get available providers (sorted by priority)
providers = manager.get_available_providers()

# Register a reload callback
def on_config_change(config):
    print("Config reloaded!")

manager.on_reload(on_config_change)

# Use as context manager
with ConfigManager(path="custom-policy.json") as mgr:
    config = mgr.get()
    print(config)
```

---

## Version

**Module version:** `0.2.5`

**Author:** Tuomas Lähteenmäki

**License:** MIT
