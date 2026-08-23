# LibreTranslateMirrorManager API Documentation

## Overview

`libretranslate_mirrors.py` provides mirror management for LibreTranslate instances within the SHL framework. It includes health checking, weighted routing, language-pair-aware mirror selection, and dynamic mirror loading from environment variables and `.env` files.

---

## Module Constants

### Mirror Status Strings

| Constant | Value | Description |
|----------|-------|-------------|
| `MIRROR_STATUS_UNKNOWN` | `"unknown"` | Initial status before any health check. |
| `MIRROR_STATUS_AVAILABLE` | `"available"` | Mirror passed the health check. |
| `MIRROR_STATUS_UNAVAILABLE` | `"unavailable"` | Mirror failed the health check. |
| `MIRROR_STATUS_DEGRADED` | `"degraded"` | Defined but not actively used in the current implementation. |

### Default Mirror List

```python
DEFAULT_MIRRORS = [
    {"url": "https://libretranslate.com", "weight": 5, "api_key_env": "LIBRETRANSLATE_API_KEY"},
    {"url": "https://libretranslate.de", "weight": 4},
    {"url": "https://translate.mentality.rip", "weight": 3},
    {"url": "https://translate.astian.org", "weight": 2},
]
```

---

## Class: `LibreTranslateMirror`

Represents a single LibreTranslate mirror instance.

### Constructor

```python
LibreTranslateMirror(
    url: str,
    weight: int = 1,
    api_key_env: Optional[str] = None,
    timeout: int = 5,
)
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` | — | The mirror URL. Cannot be empty. Trailing slashes are stripped. |
| `weight` | `int` | `1` | Routing priority weight. Higher values indicate higher priority. |
| `api_key_env` | `Optional[str]` | `None` | Name of the environment variable containing the API key for this mirror. |
| `timeout` | `int` | `5` | HTTP timeout in seconds for health check requests. |

#### Instance Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `url` | `str` | The mirror URL with trailing slashes stripped. |
| `weight` | `int` | The routing weight. |
| `api_key_env` | `Optional[str]` | Environment variable name for the API key. |
| `timeout` | `int` | Health check timeout in seconds. |
| `status` | `str` | Current mirror status (`MIRROR_STATUS_UNKNOWN`, `MIRROR_STATUS_AVAILABLE`, or `MIRROR_STATUS_UNAVAILABLE`). |
| `last_check` | `float` | Unix timestamp of the last health check. Initialized to `0.0`. |
| `last_latency` | `float` | Last measured latency in milliseconds. Initialized to `0.0`. |
| `last_error` | `str` | Last error message string. Initialized to `""`. |
| `supported_languages` | `Dict[str, str]` | Mapping of base language codes to language names. Initialized to `{}`. |

#### Raises

- `ValueError` — If `url` is empty or falsy.

---

### Methods

#### `is_available() -> bool`

Check if the mirror is available based on cached status.

##### Returns

- `bool` — `True` if `status` is `MIRROR_STATUS_AVAILABLE` or `MIRROR_STATUS_UNKNOWN`; `False` otherwise.

---

#### `get_api_key() -> Optional[str]`

Retrieve the API key from environment variables.

##### Returns

- `Optional[str]` — The API key value from the environment variable named by `api_key_env`, or `None` if `api_key_env` is not set or not configured.

---

#### `test() -> bool`

Test the availability and latency of the mirror by querying its `/languages` endpoint.

##### Behavior

1. Records the start time.
2. Sends a `GET` request to `{url}/languages` with:
   - `User-Agent: SHL-Client/{SHL_VERSION}`
   - `Accept: application/json`
3. On success:
   - Parses the JSON response.
   - Populates `supported_languages` with entries where each item is a dict containing `"code"` and `"name"` keys. Language codes are normalized via `base_language()`.
   - Calculates latency in milliseconds (`(end_time - start_time) * 1000`).
   - Sets `status` to `MIRROR_STATUS_AVAILABLE`.
   - Updates `last_check` to current time.
   - Clears `last_error`.
   - Logs a debug message with the URL and language count.
   - Returns `True`.
4. On failure (catches `URLError` and generic `Exception`):
   - Sets `status` to `MIRROR_STATUS_UNAVAILABLE`.
   - Updates `last_check` to current time.
   - Stores the error string in `last_error`.
   - Logs a debug message with the URL and error.
   - Returns `False`.

##### Returns

- `bool` — `True` if the mirror is operational; `False` otherwise.

---

#### `to_dict() -> Dict[str, Any]`

Convert mirror metadata to a dictionary for persistence or stats.

##### Returns

- `Dict[str, Any]` — A dictionary containing:
  - `"url"`
  - `"weight"`
  - `"status"`
  - `"last_check"`
  - `"last_latency"`
  - `"last_error"`
  - `"supported_languages_count"` (integer count of supported languages)

---

## Class: `LibreTranslateMirrorManager`

Manages pool distribution, routing, and health checks for LibreTranslate mirrors.

### Constructor

```python
LibreTranslateMirrorManager(
    mirrors: Optional[List[Dict[str, Any]]] = None,
    test_interval: int = 300,
    max_failures: int = 3,
)
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `mirrors` | `Optional[List[Dict[str, Any]]]` | `None` | List of mirror configuration dictionaries. If `None`, mirrors are loaded from environment sources. |
| `test_interval` | `int` | `300` | Time in seconds between automatic health check re-tests. |
| `max_failures` | `int` | `3` | Defined but not actively used in the current implementation. |

#### Instance Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `mirrors` | `List[LibreTranslateMirror]` | List of instantiated mirror objects. |
| `test_interval` | `int` | Health check re-test interval in seconds. |
| `max_failures` | `int` | Maximum failure threshold (reserved for future use). |

#### Behavior

- If `mirrors` is `None`, calls `_load_mirrors_from_env()` to discover mirrors.
- Passes the resolved mirror list to `_load_mirrors()` to instantiate `LibreTranslateMirror` objects.

---

### Methods

#### `_load_mirrors_from_env() -> List[Dict[str, Any]]`

Load unique mirror configurations from `.env` file and environment variables. This is an internal method.

##### Behavior

1. **Parse local `.env` file** — Reads `{cwd}/.env` line by line. For lines starting with `LIBRETRANSLATE_MIRROR_`, extracts the value after `=`, strips quotes and whitespace, and adds unique URLs to the result list.
2. **Check active process environment variables** — Iterates `os.environ` for keys starting with `LIBRETRANSLATE_MIRROR_`, applies the same cleaning, and adds unique URLs.
3. **Fallback** — If no custom mirrors are discovered, returns `DEFAULT_MIRRORS`.

##### Returns

- `List[Dict[str, Any]]` — A list of mirror configuration dictionaries, each containing at minimum `"url"`.

---

#### `_load_mirrors(mirrors: List[Dict[str, Any]]) -> None`

Safely instantiate `LibreTranslateMirror` instances from a raw list. This is an internal method.

##### Behavior

- Clears the existing `self.mirrors` list.
- Iterates over `mirrors`:
  - If an item is a `str`, converts it to `{"url": item}`.
  - Extracts `"url"`. If empty or missing, skips the entry.
  - Creates a `LibreTranslateMirror` with:
    - `url` from the dict
    - `weight` from dict (default `1`)
    - `api_key_env` from dict (default `None`)
    - `timeout` from dict (default `5`)

---

#### `get_best_mirror(force_test: bool = False) -> Optional[LibreTranslateMirror]`

Select the optimal mirror based on status, weight, and latency.

##### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `force_test` | `bool` | `False` | If `True`, forces a health check on all mirrors regardless of `test_interval`. |

##### Behavior

1. Iterates all mirrors and calls `test()` if `force_test` is `True` or if the time since `last_check` exceeds `test_interval`.
2. Filters mirrors where `is_available()` returns `True`.
3. If no mirrors are available, re-tests all mirrors and filters again.
4. If still no mirrors available, logs a warning and returns `None`.
5. Sorts available mirrors by:
   - Primary: `weight` (descending)
   - Secondary: negative latency (faster responses first; mirrors with `last_latency <= 0` use `0`)
6. Returns the first (best) mirror.

##### Returns

- `Optional[LibreTranslateMirror]` — The best available mirror, or `None` if none are available.

---

#### `get_mirror_for_language(target_lang: str, source_lang: str = "en") -> Optional[LibreTranslateMirror]`

Find the highest priority mirror supporting the requested language pair.

##### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `target_lang` | `str` | — | Target language code. Normalized via `base_language()`. |
| `source_lang` | `str` | `"en"` | Source language code. Normalized via `base_language()`. |

##### Behavior

1. Normalizes both language codes using `base_language()`.
2. Re-tests stale mirrors (where `time.time() - last_check > test_interval`).
3. Sorts all mirrors by weight (descending) and negative latency.
4. Iterates sorted mirrors and returns the first available mirror where both `target` and `source` exist in `supported_languages`.
5. If no available mirror supports the pair, force-re-tests all mirrors and repeats the check.
6. Returns `None` if no mirror supports the language pair.

##### Returns

- `Optional[LibreTranslateMirror]` — A mirror supporting the language pair, or `None`.

---

#### `update_mirror_status(url: str, available: bool) -> None`

Explicitly overwrite a specific mirror's runtime status.

##### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `url` | `str` | The mirror URL to update. Trailing slashes are stripped for matching. |
| `available` | `bool` | If `True`, sets status to `MIRROR_STATUS_AVAILABLE`; otherwise `MIRROR_STATUS_UNAVAILABLE`. |

##### Behavior

- Strips trailing slashes from the provided URL.
- Finds the first mirror with a matching `url`.
- Updates its `status` and `last_check` to current time.

---

#### `get_mirror_stats() -> List[Dict[str, Any]]`

Collect current structural performance metrics across the cluster.

##### Returns

- `List[Dict[str, Any]]` — A list of dictionaries, one per mirror, as returned by `LibreTranslateMirror.to_dict()`.

---

#### `clear_cache() -> None`

Reset internal availability cache and forced status tracking flags.

##### Behavior

- For each mirror:
  - Sets `status` to `MIRROR_STATUS_UNKNOWN`
  - Sets `last_check` to `0.0`
  - Clears `supported_languages` to `{}`

---

## Dependencies and Imports

### Standard Library

- `json`
- `logging`
- `os`
- `time`
- `typing` (`List`, `Dict`, `Optional`, `Any`)
- `urllib.request` (`Request`, `urlopen`)
- `urllib.error` (`URLError`)

### SHL Internal Modules

- `shl._version.__version__` (as `SHL_VERSION`)
- `shl.utils.lang_utils.base_language`

---

## Usage Example

```python
from shl.providers.libretranslate_mirrors import (
    LibreTranslateMirrorManager,
    LibreTranslateMirror,
)

# Initialize with default mirrors
manager = LibreTranslateMirrorManager()

# Get the best available mirror
best = manager.get_best_mirror()
if best:
    print(f"Best mirror: {best.url} (latency: {best.last_latency}ms)")

# Find a mirror supporting a specific language pair
mirror = manager.get_mirror_for_language("fi", "en")
if mirror:
    print(f"Found mirror for en->fi: {mirror.url}")

# Get stats for all mirrors
stats = manager.get_mirror_stats()
for s in stats:
    print(f"{s['url']}: {s['status']} ({s['supported_languages_count']} languages)")

# Manually update a mirror's status
manager.update_mirror_status("https://libretranslate.com", available=False)

# Reset all cached statuses
manager.clear_cache()
```

---

## Environment Variable Loading

The manager discovers mirrors from two sources:

1. **`.env` file** — Reads `{current_working_directory}/.env` for lines starting with `LIBRETRANSLATE_MIRROR_`.
2. **Process environment** — Checks `os.environ` for keys starting with `LIBRETRANSLATE_MIRROR_`.

Values are cleaned by stripping whitespace and surrounding quotes (`"` or `'`). Duplicate URLs are deduplicated. If no custom mirrors are found, `DEFAULT_MIRRORS` is used.

---

## Health Check Details

The `test()` method queries `{mirror_url}/languages`:

- **Success**: Parses the JSON array of language objects, normalizes codes via `base_language()`, stores them in `supported_languages`, and records latency.
- **Failure**: Catches `URLError` and generic `Exception`, marks the mirror as unavailable, and stores the error message.

Only dictionary items containing both `"code"` and `"name"` keys are included in `supported_languages`.
