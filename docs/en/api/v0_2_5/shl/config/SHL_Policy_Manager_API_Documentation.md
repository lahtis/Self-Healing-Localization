# SHL Policy Manager — API Documentation

## Module Overview

**File:** `policy-manager.py`

Future version of the SHL policy manager. A thread-safe, zero-dependency configuration manager for SHL provider policies. Handles JSON-based provider configuration with automatic file watching, `.env` support, allow/deny lists, and fallback provider resolution.

**Note:** This is a future implementation — not yet integrated into the active SHL runtime.

---

## Metadata

| Attribute | Value |
|-----------|-------|
| Author | Tuomas Lähteenmäki |
| Version | 0.2.5 |
| License | MIT |

---

## Dependencies

| Module | Usage |
|--------|-------|
| `__future__.annotations` | Postponed evaluation of type annotations. |
| `json` | JSON configuration file parsing. |
| `os` | Environment variable access and `.env` file loading. |
| `threading` | Thread-safe locks and background file watcher. |
| `time` | Watcher sleep intervals. |
| `copy.deepcopy` | Immutable configuration snapshots. |
| `pathlib.Path` | Cross-platform file path handling. |
| `typing` | Type hints (`Any`, `Callable`, `Dict`, `List`, `Optional`, `Union`). |

---

## Module Exports

```python
__all__ = ["ConfigManager"]
```

---

## Configuration File Format

The policy configuration file (`shl-policy-config.json`) defines provider policies:

```json
{
    "MyMemory": {
        "enabled": true,
        "allow": [],
        "deny": ["html"]
    },
    "DeepL": {
        "enabled": true,
        "allow": [],
        "deny": ["html"]
    },
    "Google": {
        "enabled": true,
        "allow": [],
        "deny": ["html"]
    }
}
```

| Key | Type | Description |
|-----|------|-------------|
| `enabled` | `bool` | Whether the provider is active. |
| `allow` | `list[str]` | Explicitly allowed items (empty = no restrictions). |
| `deny` | `list[str]` | Explicitly denied items (e.g., `"html"`). |

**Fallback Behavior:**
- Fallback providers are automatically derived from other enabled providers.
- A provider can never be its own fallback.
- If no alternative active providers exist, no fallback translation is attempted.
- `base_lang` fallback is handled by router/runtime logic and is not stored in translation files.

---

## Class: `ConfigManager`

```python
class ConfigManager
```

Thread-safe configuration manager for SHL provider policies. Supports hot-reloading via background file watcher, `.env` file integration, and deep-copied immutable configuration access.

### Constructor

```python
def __init__(
    self,
    path: Union[str, Path] = "shl-policy-config.json",
    check_interval: float = 1.0,
    env_path: Optional[Union[str, Path]] = ".env",
) -> None
```

Initializes the configuration manager, loads `.env` (if configured), loads the initial JSON configuration, and starts the background file watcher.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | `Union[str, Path]` | `"shl-policy-config.json"` | Path to the SHL policy configuration JSON file. |
| `check_interval` | `float` | `1.0` | File watcher polling interval in seconds. |
| `env_path` | `Optional[Union[str, Path]]` | `".env"` | Path to the `.env` file. `None` disables `.env` loading. |

**Initialization Sequence**
1. Store paths and create `threading.RLock()`.
2. If `env_path` is set, load `.env` file via `_load_env()`.
3. Force initial configuration load via `reload(force=True)`.
4. Start background file watcher via `start_watcher()`.

**Attributes**

| Attribute | Type | Description |
|-----------|------|-------------|
| `path` | `Path` | Resolved path to the JSON configuration file. |
| `check_interval` | `float` | Watcher polling interval in seconds. |
| `env_path` | `Optional[Path]` | Resolved path to the `.env` file, or `None`. |
| `_lock` | `threading.RLock` | Reentrant lock for thread-safe configuration access. |
| `_config` | `Dict[str, Any]` | In-memory configuration dictionary. |
| `_last_mtime` | `float` | Last known modification time of the JSON config file. |
| `_last_env_mtime` | `float` | Last known modification time of the `.env` file. |
| `_stop_event` | `threading.Event` | Signal to stop the background watcher thread. |
| `_watcher` | `Optional[threading.Thread]` | Background file watcher thread. |
| `_callbacks` | `List[Callable]` | Registered reload callbacks. |

---

### `.env` Management

#### `_load_env()`

```python
def _load_env(self) -> bool
```

Loads environment variables from the configured `.env` file.

**Parsing Rules**
- Skips empty lines and lines starting with `#`.
- Splits on the first `=` only.
- Strips whitespace from keys and values.
- Removes surrounding single (`'`) or double (`"`) quotes from values.
- Sets variables via `os.environ[key] = value`.

**Returns**
- `bool` — `True` if the file was loaded successfully, `False` if the file does not exist or loading failed.

**Side Effects**
- Updates `os.environ`.
- Updates `_last_env_mtime`.

**Logging**
- Prints `[Config] Loaded .env from {path}` on success.
- Prints `[Config] Failed to load .env: {exc}` on failure.

---

#### `_check_env_reload()`

```python
def _check_env_reload(self) -> bool
```

Checks whether the `.env` file has been modified since the last load and reloads it if necessary.

**Returns**
- `bool` — `True` if the `.env` file was reloaded, `False` otherwise.

**Behavior**
- Compares current `st_mtime` against `_last_env_mtime`.
- Calls `_load_env()` only if the file is newer.

---

#### `get_env()`

```python
def get_env(
    self,
    key: str,
    default: Optional[str] = None,
) -> Optional[str]
```

Retrieves a value from the environment variables.

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | `str` | Environment variable name. |
| `default` | `Optional[str]` | Default value if the variable is not set. |

**Returns**
- `Optional[str]` — The environment variable value, or `default`.

**Example**
```python
api_key = config.get_env("DEEPL_API_KEY")
ttl = config.get_env("MS_TRANSLATOR_TTL", default="600")
```

---

### JSON Configuration Loading

#### `reload()`

```python
def reload(self, force: bool = False) -> bool
```

Reloads the configuration from the JSON file. If the new file is invalid, the current working configuration is preserved.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `force` | `bool` | `False` | Force reload regardless of file modification time. |

**Returns**
- `bool` — `True` if a new configuration was loaded, `False` if no changes were detected or loading failed.

**Behavior**
1. Checks file existence.
2. Compares `st_mtime` against `_last_mtime` (skipped if `force=True`).
3. Parses JSON and validates that the root is a `dict`.
4. Deep-copies the new configuration to prevent external mutation.
5. Updates `_config` and `_last_mtime` under lock.
6. Invokes all registered reload callbacks with a deep-copied config (outside the lock).

**Error Handling**
- `FileNotFoundError` — Config file not found.
- `ValueError` — Root is not a JSON object.
- `json.JSONDecodeError` — Invalid JSON syntax.
- On any error, the previous configuration is retained.

**Logging**
- Prints `[Config] Reloaded from {path}` on success.
- Prints `[Config] Reload failed → keeping previous config. Error: {exc}` on failure.

---

### General Configuration Access

#### `get()`

```python
def get(self) -> Dict[str, Any]
```

Returns a deep copy of the entire configuration dictionary.

**Returns**
- `Dict[str, Any]` — Immutable snapshot of the current configuration.

**Thread Safety**
- Access is protected by `_lock`.

---

#### `get_value()`

```python
def get_value(
    self,
    key: str,
    default: Any = None,
) -> Any
```

Retrieves a top-level configuration value by key.

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | `str` | Top-level configuration key. |
| `default` | `Any` | Default value if the key is not found. |

**Returns**
- `Any` — The configuration value (deep-copied), or `default`.

**Example**
```python
debug_mode = config.get_value("debug_mode", default=False)
```

---

### Provider Configuration

#### `get_provider()`

```python
def get_provider(
    self,
    name: str,
) -> Dict[str, Any]
```

Retrieves a specific provider's configuration.

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Provider name (e.g., `"DeepL"`, `"MyMemory"`). |

**Returns**
- `Dict[str, Any]` — Deep-copied provider configuration, or `{}` if the provider does not exist or is not a dict.

---

#### `get_provider_setting()`

```python
def get_provider_setting(
    self,
    name: str,
    key: str,
    default: Any = None,
) -> Any
```

Retrieves a specific setting from a provider's configuration.

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Provider name. |
| `key` | `str` | Setting key (e.g., `"enabled"`, `"deny"`). |
| `default` | `Any` | Default value if the provider or key is not found. |

**Returns**
- `Any` — The setting value (deep-copied), or `default`.

**Example**
```python
ttl = config.get_provider_setting("DeepL", "ttl", default=3600)
```

---

#### `is_enabled()`

```python
def is_enabled(
    self,
    provider_name: str,
) -> bool
```

Checks whether a provider is enabled.

| Parameter | Type | Description |
|-----------|------|-------------|
| `provider_name` | `str` | Provider name to check. |

**Returns**
- `bool` — `True` if the provider exists and its `enabled` field is truthy, `False` otherwise.

**Example**
```python
if config.is_enabled("DeepL"):
    print("DeepL is active")
```

---

### Allow / Deny Lists

#### `is_allowed()`

```python
def is_allowed(
    self,
    provider_name: str,
    item: str,
    default: bool = True,
) -> bool
```

Checks whether a specific item is allowed for a provider based on its `allow` and `deny` lists.

**Evaluation Order:**
1. If `item` is in `deny` → `False`
2. If `allow` is empty → `default`
3. If `item` is in `allow` → `True`
4. Otherwise → `False`

| Parameter | Type | Description |
|-----------|------|-------------|
| `provider_name` | `str` | Provider name. |
| `item` | `str` | Item to check (e.g., `"html"`). |
| `default` | `bool` | Default value when `allow` list is empty. |

**Returns**
- `bool` — Whether the item is allowed for the provider.

**Example**
```python
# Config: {"MyMemory": {"enabled": true, "deny": ["html"]}}
config.is_allowed("MyMemory", "html")       # False
config.is_allowed("MyMemory", "plain_text") # True (default, allow is empty)
```

---

#### `get_allowed_items()`

```python
def get_allowed_items(
    self,
    provider_name: str,
) -> Dict[str, List[str]]
```

Returns a provider's `allow` and `deny` lists.

| Parameter | Type | Description |
|-----------|------|-------------|
| `provider_name` | `str` | Provider name. |

**Returns**
- `Dict[str, List[str]]` — Dictionary with keys `"allow"` and `"deny"`, each containing a list of strings (deep-copied).

**Example**
```python
items = config.get_allowed_items("DeepL")
print(items)
# {"allow": [], "deny": ["html"]}
```

---

### Provider Lists

#### `get_provider_list()`

```python
def get_provider_list(self) -> List[str]
```

Returns all provider names defined in the configuration.

**Returns**
- `List[str]` — List of top-level keys whose values are dictionaries.

**Example**
```python
providers = config.get_provider_list()
# ["MyMemory", "DeepL", "Google"]
```

---

#### `get_enabled_providers()`

```python
def get_enabled_providers(self) -> List[str]
```

Returns all enabled providers, preserving the order from the configuration file.

**Returns**
- `List[str]` — List of provider names where `enabled` is `True`.

**Example**
```python
enabled = config.get_enabled_providers()
# ["DeepL", "Google"]
```

---

#### `get_fallback_providers()`

```python
def get_fallback_providers(
    self,
    current_provider: Optional[str] = None,
) -> List[str]
```

Returns all enabled providers except the current one, suitable for failover routing.

| Parameter | Type | Description |
|-----------|------|-------------|
| `current_provider` | `Optional[str]` | The provider currently in use. Never returned as a fallback. |

**Returns**
- `List[str]` — List of enabled providers excluding `current_provider`.

**Example**
```python
# Current provider is "DeepL"
fallbacks = config.get_fallback_providers("DeepL")
# ["Google", "MyMemory"]
```

---

### Reload Callbacks

#### `on_reload()`

```python
def on_reload(
    self,
    callback: Callable[[Dict[str, Any]], None],
) -> None
```

Registers a callback to be invoked after a successful configuration reload.

| Parameter | Type | Description |
|-----------|------|-------------|
| `callback` | `Callable[[Dict[str, Any]], None]` | Function receiving a deep-copied configuration dict. |

**Raises**
- `TypeError` — If `callback` is not callable.

**Behavior**
- Callbacks are deduplicated (same callback registered twice = once).
- Callbacks execute outside the configuration lock to prevent deadlocks.
- Exceptions in callbacks are caught and logged, not propagated.

**Example**
```python
def on_config_change(new_config):
    print("Config reloaded!")
    print(new_config.keys())

config.on_reload(on_config_change)
```

---

#### `remove_reload_callback()`

```python
def remove_reload_callback(
    self,
    callback: Callable[[Dict[str, Any]], None],
) -> None
```

Removes a previously registered reload callback.

| Parameter | Type | Description |
|-----------|------|-------------|
| `callback` | `Callable[[Dict[str, Any]], None]` | The callback to remove. |

---

### File Watcher

#### `start_watcher()`

```python
def start_watcher(self) -> None
```

Starts a background daemon thread that polls the configuration and `.env` files for changes.

**Behavior**
- Creates a `threading.Thread` named `"SHLConfigWatcher"` running `_watch()`.
- Thread is a daemon — does not block program exit.
- If a watcher is already running, this call is a no-op.

**Logging**
- Prints `[Config] Watcher started (interval: {check_interval}s)`.

---

#### `_watch()`

```python
def _watch(self) -> None
```

Internal watcher loop. Runs until `_stop_event` is set.

**Polling Cycle**
1. Check `.env` for changes via `_check_env_reload()`.
2. Check JSON config for changes via `reload()`.
3. Sleep for `check_interval` seconds (or until `_stop_event` is set).

**Error Handling**
- Exceptions during the cycle are caught and logged, not propagated.

---

#### `stop_watcher()`

```python
def stop_watcher(self) -> None
```

Signals the watcher thread to stop and waits for it to terminate.

**Behavior**
- Sets `_stop_event`.
- Joins the watcher thread with a 2-second timeout.
- Logs whether the thread stopped cleanly or timed out.

---

#### `close()`

```python
def close(self) -> None
```

Shuts down the `ConfigManager` by stopping the watcher thread.

**Alias:** `stop_watcher()`

---

### Context Manager Support

```python
def __enter__(self) -> "ConfigManager"
def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None
```

Supports `with` statement for automatic cleanup:

```python
with ConfigManager() as config:
    providers = config.get_enabled_providers()
# Watcher is automatically stopped on exit
```

---

### Debug

#### `print_config()`

```python
def print_config(self) -> None
```

Pretty-prints the current configuration to stdout.

**Warning:** Do not use if the configuration contains secret values.

**Output Format**
```
==================================================
SHL POLICY CONFIGURATION
==================================================

DeepL:
  enabled: True
  allow: []
  deny: ['html']

Google:
  enabled: True
  allow: []
  deny: ['html']

==================================================
```

---

## Thread Safety

| Component | Mechanism | Notes |
|-----------|-----------|-------|
| Configuration reads | `threading.RLock` | All `get_*` methods acquire the lock. |
| Configuration writes | `threading.RLock` | `reload()` and internal updates acquire the lock. |
| Callbacks | Lock-free | Executed outside the lock to prevent deadlocks. |
| Watcher thread | Daemon thread | Independent polling loop, exception-safe. |

**Recommendation:** The `ConfigManager` is designed for concurrent read-heavy access. Write operations (`reload`) are infrequent and brief.

---

## Usage Example

```python
from policy_manager import ConfigManager

# Initialize with default paths
with ConfigManager(
    path="shl-policy-config.json",
    check_interval=2.0,
    env_path=".env",
) as config:

    # Check which providers are enabled
    enabled = config.get_enabled_providers()
    print(f"Enabled: {enabled}")

    # Check if a provider supports HTML
    for provider in enabled:
        if config.is_allowed(provider, "html"):
            print(f"{provider} supports HTML")
        else:
            print(f"{provider} does NOT support HTML")

    # Get fallback providers for DeepL
    fallbacks = config.get_fallback_providers("DeepL")
    print(f"DeepL fallbacks: {fallbacks}")

    # Register a reload callback
    def on_change(new_cfg):
        print("Configuration was hot-reloaded!")

    config.on_reload(on_change)

    # Manual reload (e.g., after external edit)
    config.reload(force=True)

    # Read environment variable
    api_key = config.get_env("DEEPL_API_KEY")
```

---

## State Diagram

```
┌─────────────────┐
│   __init__()    │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌──────────┐
│_load_  │ │ reload() │
│  env() │ │ (force)  │
└────────┘ └────┬─────┘
                │
                ▼
        ┌───────────────┐
        │ start_watcher │
        │   (daemon)    │
        └───────┬───────┘
                │
        ┌───────┴───────┐
        ▼               ▼
   ┌─────────┐    ┌──────────┐
   │ _watch()│    │ get_*()  │
   │ (poll)  │    │ (read)   │
   └────┬────┘    └────┬─────┘
        │              │
        ▼              ▼
   ┌─────────┐    ┌──────────┐
   │ reload()│    │ __exit__ │
   │(if mtime│    │ close()  │
   │ changed)│    │ stop_    │
   └────┬────┘    │ watcher()│
        │         └──────────┘
        ▼
   ┌─────────┐
   │callbacks│
   │ (lock-  │
   │  free)  │
   └─────────┘
```

---

## Changelog

| Version | Notes |
|---------|-------|
| 0.2.5 | Current — future policy manager with thread-safe config loading, `.env` support, file watcher, allow/deny lists, and fallback provider resolution. Not yet integrated into active SHL runtime. |
