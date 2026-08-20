# Translation Cache — API Documentation

## Module Overview

**File:** `cache.py`

Memory-backed translation cache for the SHL client. Prevents duplicate remote API calls by caching evaluated translation results with configurable TTL enforcement and maximum size limits. Uses MD5-based deterministic key generation to uniquely identify translation transactions.

---

## Metadata

| Attribute | Value |
|-----------|-------|
| Author | Tuomas Lähteenmäki |
| Version | 0.2.0 |
| License | MIT |
| Description | Memory-backed in-memory translation cache for SHL client requests. Prevents duplicate remote API calls by caching distinct language-pair hashes with maximum limit evictions and configurable TTL enforcement. |

---

## Dependencies

| Module | Usage |
|--------|-------|
| `hashlib` | MD5 hex digest generation for cache keys. |
| `logging` | Debug and info log output for cache hits, evictions, and clears. |
| `time` | Unix timestamp generation for TTL expiration tracking. |
| `typing.Optional` | Type annotations for optional parameters. |

---

## Module Constants

| Name | Type | Value | Description |
|------|------|-------|-------------|
| `TRANSLATION_CACHE_TTL` | `int` | `3600` | Default time-to-live in seconds (1 hour). |

---

## Class: `TranslationCache`

```python
class TranslationCache
```

Translation cache layer designed to intercept and optimize repeated provider calls. Stores translated strings in memory with automatic expiration and size-based eviction.

---

### Constructor

```python
def __init__(
    self,
    ttl: int = TRANSLATION_CACHE_TTL,
    max_size: int = 10000,
) -> None
```

Initializes the translation cache with configurable TTL and maximum size.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ttl` | `int` | `3600` | Time-to-live in seconds for cached entries. |
| `max_size` | `int` | `10000` | Maximum number of entries before eviction occurs. |

**Attributes**

| Attribute | Type | Description |
|-----------|------|-------------|
| `cache` | `dict[str, tuple]` | Internal dictionary mapping MD5 keys to `(translated_text, timestamp)` tuples. |
| `ttl` | `int` | Configured TTL in seconds. |
| `max_size` | `int` | Maximum cache size before eviction. |

---

### Internal Methods

#### `_generate_key()`

```python
def _generate_key(
    self,
    text: str,
    source_lang: str,
    target_lang: str,
    formality: Optional[str] = None,
    context_type: Optional[str] = None,
) -> str
```

Creates a unique deterministic MD5 hex digest representing the translation transaction footprint.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | `str` | — | Source text to translate. |
| `source_lang` | `str` | — | Source language code. |
| `target_lang` | `str` | — | Target language code. |
| `formality` | `Optional[str]` | `None` | Formality level (included in key if set). |
| `context_type` | `Optional[str]` | `None` | Context type (included in key if set). |

**Returns**
- `str` — 32-character MD5 hex digest.

**Key Format**
```
{text}:{source_lang}:{target_lang}:{formality or ''}:{context_type or ''}
```

**Example**
```python
>>> cache._generate_key("Hello", "en", "fi")
'5d41402abc4b2a76b9719d911017c592'

>>> cache._generate_key("Hello", "en", "fi", formality="formal")
# Different hash due to formality inclusion
```

---

#### `_evict_stale_or_oldest()`

```python
def _evict_stale_or_oldest(self) -> None
```

Internal memory maintenance subroutine to free tracking indices when the cache reaches `max_size`.

**Eviction Priority**
1. **Stale entries first** — Removes all entries whose TTL has expired.
2. **Oldest entry fallback** — If no stale entries exist, removes the single oldest entry by timestamp.

**Logging**
- `DEBUG` — Number of stale entries evicted.

---

### Public Methods

#### `get()`

```python
def get(
    self,
    text: str,
    source_lang: str,
    target_lang: str,
    formality: Optional[str] = None,
    context_type: Optional[str] = None,
) -> Optional[str]
```

Retrieves a cached translation if the signature is fresh (within TTL).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | `str` | — | Source text. |
| `source_lang` | `str` | — | Source language code. |
| `target_lang` | `str` | — | Target language code. |
| `formality` | `Optional[str]` | `None` | Formality level (must match cached entry). |
| `context_type` | `Optional[str]` | `None` | Context type (must match cached entry). |

**Returns**
- `Optional[str]` — Cached translated text if found and not expired, `None` otherwise.

**Behavior**
1. Generates the cache key from all parameters.
2. Checks if the key exists in the cache.
3. If found and `current_time - timestamp < ttl` → returns the cached text.
4. If found but expired → deletes the entry and returns `None`.
5. If not found → returns `None`.

**Logging**
- `DEBUG` — Cache hit with truncated text preview.

**Example**
```python
from shl.cache import TranslationCache

cache = TranslationCache()

# Store a translation
cache.set("Hello", "Hei", "en", "fi")

# Retrieve it
result = cache.get("Hello", "en", "fi")
print(result)  # "Hei"

# Different parameters = different cache key
result = cache.get("Hello", "en", "fi", formality="formal")
print(result)  # None (different key)
```

---

#### `set()`

```python
def set(
    self,
    text: str,
    translated: str,
    source_lang: str,
    target_lang: str,
    formality: Optional[str] = None,
    context_type: Optional[str] = None,
) -> None
```

Commits an evaluated translation string into the tracking dictionary.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | `str` | — | Source text. |
| `translated` | `str` | — | Translated text to cache. |
| `source_lang` | `str` | — | Source language code. |
| `target_lang` | `str` | — | Target language code. |
| `formality` | `Optional[str]` | `None` | Formality level. |
| `context_type` | `Optional[str]` | `None` | Context type. |

**Behavior**
1. If cache size is at or above `max_size` → calls `_evict_stale_or_oldest()`.
2. Generates the cache key.
3. Stores `(translated, time.time())` in the cache.

**Example**
```python
cache = TranslationCache(ttl=3600, max_size=5000)

# Cache a translation
cache.set(
    text="Welcome to our application!",
    translated="Tervetuloa sovellukseemme!",
    source_lang="en",
    target_lang="fi",
)

# Cache with context
cache.set(
    text="Save",
    translated="Tallenna",
    source_lang="en",
    target_lang="fi",
    context_type="button",
)
```

---

#### `clear()`

```python
def clear(self) -> None
```

Flushes all entries from the cache.

**Side Effects**
- Empties the internal `cache` dictionary.

**Logging**
- `INFO` — Cache fully cleared.

**Example**
```python
cache.clear()
print(cache.size())  # 0
```

---

#### `size()`

```python
def size(self) -> int
```

Returns the current number of cached entries.

**Returns**
- `int` — Number of entries in the cache.

**Example**
```python
print(f"Cache size: {cache.size()}")
# Cache size: 42
```

---

## Complete Usage Example

```python
from shl.cache import TranslationCache

# Initialize cache with custom settings
cache = TranslationCache(ttl=7200, max_size=5000)

# Store translations
cache.set("Hello", "Hei", "en", "fi")
cache.set("Goodbye", "Näkemiin", "en", "fi")
cache.set("Hello", "Hola", "en", "es")

# Retrieve from cache
result = cache.get("Hello", "en", "fi")
print(result)  # "Hei"

# Check cache size
print(f"Cached entries: {cache.size()}")
# Cached entries: 3

# Miss (different language pair)
result = cache.get("Hello", "en", "de")
print(result)  # None

# Miss (expired entry — after TTL)
import time
time.sleep(7201)
result = cache.get("Hello", "en", "fi")
print(result)  # None (expired)

# Clear all
cache.clear()
print(f"After clear: {cache.size()}")  # 0
```

---

## Cache Key Determinism

The cache key is deterministic based on all input parameters. This means:

| Scenario | Cache Key | Result |
|----------|-----------|--------|
| Same text, same languages | Identical | Cache hit |
| Same text, different target | Different | Cache miss |
| Same text, different formality | Different | Cache miss |
| Same text, different context_type | Different | Cache miss |
| Whitespace differences in text | Different | Cache miss |

**Recommendation:** Normalize text (strip whitespace) before caching if whitespace variance is not semantically significant.

---

## Eviction Strategy

```
Cache reaches max_size (e.g., 10000)
    │
    ├── Check for stale entries (expired TTL)
    │   ├── Found → Remove all stale entries
    │   │   └── Cache size reduced
    │   └── Not found → Remove oldest single entry
    │       └── Cache size = max_size - 1
    │
    └── New entry can now be inserted
```

---

## Thread Safety

| Component | Status | Notes |
|-----------|--------|-------|
| `get()` | Caution | Read operation, but may delete expired entries. Not atomic in multi-threaded use. |
| `set()` | Not safe | May trigger eviction and dictionary mutation. Race conditions possible. |
| `clear()` | Not safe | Clears the entire dictionary. |
| `size()` | Generally safe | Simple length read. |

**Recommendation:** In multi-threaded environments, wrap cache operations with a `threading.Lock` or use one `TranslationCache` instance per thread.

---

## Performance Characteristics

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| `get()` | O(1) | Dictionary lookup by MD5 key. |
| `set()` | O(1) | Dictionary insertion. Eviction is O(n) in worst case (scanning all entries for stale keys). |
| `_generate_key()` | O(1) | MD5 hash of bounded-size string. |
| `clear()` | O(1) | Dictionary clear. |
| `size()` | O(1) | Dictionary length. |

---

## Logging

The module uses Python's standard `logging` module under the logger name `__name__`.

**Log Levels Used**

| Level | Event |
|-------|-------|
| `DEBUG` | Cache hit (with truncated text preview), stale entry eviction count. |
| `INFO` | Cache fully cleared. |

---

## Changelog

| Version | Notes |
|---------|-------|
| 0.2.0 | Current — MD5-based deterministic cache keys, TTL expiration, size-based eviction with stale-first strategy, and context-aware caching (formality, context_type). |
