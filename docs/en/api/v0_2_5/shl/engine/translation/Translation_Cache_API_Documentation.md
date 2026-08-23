# TranslationCache API Documentation

## Overview

`TranslationCache` is a memory-backed translation cache with optional disk persistence. It prevents duplicate remote API calls by storing translated strings with TTL-based expiration, max-size eviction, and optional JSON persistence for warm starts and debugging.

---

## Module Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `TRANSLATION_CACHE_TTL` | `3600` | Default time-to-live in seconds (1 hour). |

---

## Class: `TranslationCache`

### Constructor

```python
TranslationCache(
    ttl: int = TRANSLATION_CACHE_TTL,
    max_size: int = 10000,
    persist: bool = True,
    persist_path: Optional[str] = None,
)
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ttl` | `int` | `TRANSLATION_CACHE_TTL` (3600) | Time-to-live in seconds for cache entries. |
| `max_size` | `int` | `10000` | Maximum number of entries before eviction is triggered. |
| `persist` | `bool` | `True` | Whether to save the cache to disk for warm starts. |
| `persist_path` | `Optional[str]` | `None` | Path for the persistence file. Defaults to `<CWD>/.shl_cache.json` if not provided. |

#### Instance Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `cache` | `dict[str, tuple]` | In-memory cache mapping MD5 hex keys to `(cached_text, timestamp)` tuples. |
| `ttl` | `int` | The TTL value in seconds. |
| `max_size` | `int` | The maximum cache size. |
| `persist` | `bool` | Whether disk persistence is enabled. |
| `persist_path` | `Path` | Resolved `Path` object for the persistence file. |
| `_lock` | `threading.RLock` | Reentrant lock for thread-safe access. |
| `_dirty` | `bool` | Flag indicating whether the cache has unsaved changes. |
| `_last_save` | `float` | Unix timestamp of the last successful disk save. Initialized to `0.0`. |

#### Behavior

- If `persist` is `True`, the constructor immediately calls `_load_from_disk()` to restore previously saved entries.
- The `persist_path` is resolved as a `pathlib.Path` object.

---

### Key Generation

#### `_generate_key(text: str, source_lang: str, target_lang: str, formality: Optional[str] = None, context_type: Optional[str] = None) -> str`

Creates a unique deterministic MD5 hex digest for a translation request.

##### Key Format

The raw key is constructed as:

```
"{text}:{source_lang}:{target_lang}:{formality or ''}:{context_type or ''}"
```

This string is UTF-8 encoded and hashed using `hashlib.md5`. The resulting 32-character hex digest is used as the cache key.

---

### Disk Persistence

#### `_load_from_disk() -> None`

Loads cache entries from disk on startup. This is an internal method.

##### Behavior

- If `persist_path` does not exist, returns immediately.
- Opens the file and parses JSON.
- Validates that the root is a `dict`.
- Iterates entries, skipping items that are not a 2-element list.
- Skips expired entries (`now - timestamp > self.ttl`).
- Loads valid entries into `self.cache` under the reentrant lock.
- Logs the number of loaded entries.
- Catches `json.JSONDecodeError` and `OSError`, logging a warning on failure.

---

#### `save_to_disk() -> bool`

Saves the current cache to disk.

##### Returns

- `bool` — `True` if the save was successful; `False` if persistence is disabled or an error occurred.

##### Behavior

- Returns `False` immediately if `persist` is `False`.
- Acquires the lock and serializes all cache entries into a dictionary where each value is a `[text, timestamp]` list.
- Creates parent directories if needed (`mkdir(parents=True, exist_ok=True)`).
- Writes JSON with `indent=2` and `ensure_ascii=False`.
- Sets `_dirty` to `False` and `_last_save` to current time.
- Logs the number of saved entries.
- Catches `OSError`, logs an error, and returns `False`.

---

#### `_maybe_save(min_interval: float = 2.0) -> None`

Saves to disk if enough time has passed since the last save. This is an internal method.

##### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_interval` | `float` | `2.0` | Minimum seconds between disk saves. |

##### Behavior

- Compares `time.time() - self._last_save` against `min_interval`.
- Calls `save_to_disk()` only if the interval has elapsed.

---

### Public API

#### `get(text: str, source_lang: str, target_lang: str, formality: Optional[str] = None, context_type: Optional[str] = None) -> Optional[str]`

Retrieves a localized string from memory if the signature is fresh.

##### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `text` | `str` | Original text to translate. |
| `source_lang` | `str` | Source language code. |
| `target_lang` | `str` | Target language code. |
| `formality` | `Optional[str]` | Optional formality hint. |
| `context_type` | `Optional[str]` | Optional context type hint. |

##### Returns

- `Optional[str]` — The cached translated text if found and not expired; `None` if missing or expired.

##### Behavior

1. Generates the cache key via `_generate_key()`.
2. Acquires the lock and checks if the key exists.
3. If found, verifies that `time.time() - timestamp < self.ttl`.
   - If fresh, logs a debug message and returns the cached text.
   - If expired, deletes the entry, sets `_dirty = True`, and returns `None`.
4. If not found, returns `None`.

---

#### `set(text: str, translated: str, source_lang: str, target_lang: str, formality: Optional[str] = None, context_type: Optional[str] = None) -> None`

Commits an evaluated translation string into the tracking dictionary.

##### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `text` | `str` | Original text. |
| `translated` | `str` | The translated result. |
| `source_lang` | `str` | Source language code. |
| `target_lang` | `str` | Target language code. |
| `formality` | `Optional[str]` | Optional formality hint. |
| `context_type` | `Optional[str]` | Optional context type hint. |

##### Behavior

1. Acquires the lock.
2. If `len(self.cache) >= self.max_size`, calls `_evict_stale_or_oldest()`.
3. Generates the cache key via `_generate_key()`.
4. Stores `(translated, time.time())` in `self.cache`.
5. Sets `_dirty = True`.
6. If `self.persist` is `True`, calls `_maybe_save()`.

---

#### `_evict_stale_or_oldest() -> None`

Internal memory maintenance subroutine to free tracking indices.

##### Behavior

1. Identifies all keys where `now - timestamp >= self.ttl`.
2. If stale entries exist, deletes them and logs a debug message with the count.
3. If no stale entries exist, finds the oldest entry by minimum timestamp and deletes it.

---

#### `clear() -> None`

Flushes all structural references inside the local context map.

##### Behavior

1. Acquires the lock and clears `self.cache`.
2. Sets `_dirty = True`.
3. If persistence is enabled and the file exists, attempts to delete `persist_path`.
4. Logs an info message.

---

#### `size() -> int`

Returns the current cumulative index assignment count.

##### Returns

- `int` — The number of entries currently in the cache.

---

#### `is_dirty() -> bool`

Returns `True` if the cache has changes not yet saved to disk.

##### Returns

- `bool` — The current value of `_dirty`.

---

### Context Manager Support

#### `__enter__() -> "TranslationCache"`

Returns `self` for use in a `with` statement.

#### `__exit__(exc_type, exc_val, exc_tb) -> None`

Auto-saves to disk on exit if `persist` is enabled and `_dirty` is `True`.

##### Behavior

- Calls `save_to_disk()` if both `self.persist` and `self._dirty` are truthy.
- Does not suppress exceptions.

---

## Thread Safety

All cache operations are protected by a `threading.RLock` (`self._lock`):

- `get()` acquires the lock for reading and potential eviction.
- `set()` acquires the lock for writing and potential eviction.
- `save_to_disk()` acquires the lock during serialization.
- `clear()` acquires the lock during clearing.
- `size()` acquires the lock during counting.

The reentrant lock allows nested acquisitions by the same thread.

---

## Persistence File Format

The persistence file is a JSON object where each key is an MD5 hex digest and each value is a 2-element list:

```json
{
  "a1b2c3d4...": ["translated text", 1699999999.123],
  "e5f6g7h8...": ["another translation", 1699999999.456]
}
```

- Index 0: The cached translated string.
- Index 1: The Unix timestamp when the entry was cached.

Expired entries are skipped during load but remain in the file until the next save.

---

## Dependencies and Imports

### Standard Library

- `hashlib`
- `json`
- `logging`
- `time`
- `threading`
- `pathlib.Path`
- `typing.Optional`

---

## Usage Example

```python
from shl.cache import TranslationCache

# Initialize with default settings (TTL 1h, max 10k entries, disk persistence)
cache = TranslationCache()

# Store a translation
cache.set(
    text="Hello",
    translated="Hei",
    source_lang="en",
    target_lang="fi",
)

# Retrieve a translation
result = cache.get("Hello", "en", "fi")
if result:
    print(f"Cached: {result}")

# Check cache size
print(f"Entries: {cache.size()}")

# Clear cache
cache.clear()

# Use as context manager for auto-save on exit
with TranslationCache(persist=True, persist_path="/tmp/my_cache.json") as c:
    c.set("World", "Maailma", "en", "fi")
```

---

## Version

**Module version:** `0.2.5-persist`

**Author:** Tuomas Lähteenmäki

**License:** MIT
