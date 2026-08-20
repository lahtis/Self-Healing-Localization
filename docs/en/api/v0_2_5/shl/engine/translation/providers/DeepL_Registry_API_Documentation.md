# DeepL Language Pair Registry — API Documentation

## Module Overview

**File:** `providers/deepl_registry.py`

Manages localized language validation and runtime learning for unsupported DeepL language pairs. Prevents wasteful network API calls by maintaining a TTL-based blacklist of pairs that have previously failed. Uses ISO 639-1 and BCP-47 standard language code mapping against DeepL's documented supported language set.

---

## Metadata

| Attribute | Value |
|-----------|-------|
| Author | Tuomas Lähteenmäki |
| License | MIT |
| Description | Manages localized language validation and runtime learning for unsupported DeepL language pairs to avoid wasteful network API calls. Uses ISO 639-1 / BCP-47 standard language code mapping. |

---

## Dependencies

| Module | Usage |
|--------|-------|
| `time` | Unix timestamp generation for TTL expiry calculation. |
| `logging` | Debug and warning log output for blacklist events. |
| `typing.Dict`, `typing.Tuple` | Type annotations for the internal cache structure. |

---

## Module Constants

| Name | Type | Value | Description |
|------|------|-------|-------------|
| `DEEPL_SUPPORTED_LANGUAGES_RAW` | `frozenset` | 33 language codes | DeepL-documented supported languages including BCP-47 variants (`en-US`, `en-GB`, `pt-BR`, `pt-PT`, `zh-CN`, `zh-TW`). |
| `DEEPL_SUPPORTED_LANGUAGES` | `frozenset` | Lowercased version of `DEEPL_SUPPORTED_LANGUAGES_RAW` | Case-insensitive lookup set for runtime validation. |

### Supported Language Codes

| Code | Language | Code | Language |
|------|----------|------|----------|
| `bg` | Bulgarian | `lt` | Lithuanian |
| `cs` | Czech | `lv` | Latvian |
| `da` | Danish | `nb` | Norwegian (Bokmål) |
| `de` | German | `nl` | Dutch |
| `el` | Greek | `pl` | Polish |
| `en` | English (unspecified) | `pt` | Portuguese (unspecified) |
| `en-us` | English (American) | `pt-br` | Portuguese (Brazilian) |
| `en-gb` | English (British) | `pt-pt` | Portuguese (European) |
| `es` | Spanish | `ro` | Romanian |
| `et` | Estonian | `ru` | Russian |
| `fi` | Finnish | `sk` | Slovak |
| `fr` | French | `sl` | Slovenian |
| `hu` | Hungarian | `sv` | Swedish |
| `id` | Indonesian | `tr` | Turkish |
| `it` | Italian | `uk` | Ukrainian |
| `ja` | Japanese | `zh` | Chinese (unspecified) |
| `ko` | Korean | `zh-cn` | Chinese (Simplified) |
| | | `zh-tw` | Chinese (Traditional) |

---

## Class: `DeepLRegistry`

```python
class DeepLRegistry
```

Handles runtime language pair support tracking and blacklisting for DeepL. Prevents repeated network calls for unsupported language pairs by combining a static supported-language set with a dynamic runtime blacklist.

### Design Rationale

DeepL supports a fixed set of languages. Rather than querying the API to discover that a pair is unsupported (wasting quota and latency), this registry:
- Validates pairs against a hardcoded list of DeepL-supported languages.
- Maintains a runtime cache of pairs that have been empirically confirmed as unsupported via API errors.
- Automatically expires blacklisted entries after the TTL, allowing retry if DeepL later adds support.

---

### Constructor

```python
def __init__(self, cache_ttl: float = 86400.0) -> None
```

Initializes the registry with a configurable blacklist TTL.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cache_ttl` | `float` | `86400.0` | Time-to-live in seconds for blacklisted pairs. Default is 24 hours. |

**Attributes**

| Attribute | Type | Description |
|-----------|------|-------------|
| `_unsupported_pairs_cache` | `Dict[Tuple[str, str], float]` | Maps `(source, target)` language pair tuples to Unix timestamp expiry values. |
| `cache_ttl` | `float` | The configured TTL in seconds. Immutable after construction. |

---

### Methods

#### `is_pair_supported()`

```python
def is_pair_supported(self, source_lang: str, target_lang: str) -> bool
```

Validates if the language pair is supported using local DeepL language codes and the runtime error blacklist. Zero network overhead.

**Evaluation Order**
1. **Runtime blacklist check** — If the pair exists in `_unsupported_pairs_cache` and the current time is before the expiry timestamp, returns `False`.
2. **TTL expiry cleanup** — If the pair exists but its TTL has expired, it is removed from the cache.
3. **Static support validation** — Returns `True` only if both `source_lang` and `target_lang` are in `DEEPL_SUPPORTED_LANGUAGES`.

| Parameter | Type | Description |
|-----------|------|-------------|
| `source_lang` | `str` | Source language code. Stripped and lowercased internally. |
| `target_lang` | `str` | Target language code. Stripped and lowercased internally. |

**Returns**
- `bool` — `True` if the pair is supported and not blacklisted, `False` otherwise.

**Logging**
- `DEBUG` — When a pair is found in the blacklist and still active.

**Example**
```python
registry = DeepLRegistry(cache_ttl=3600)

# Supported pair
registry.is_pair_supported("en", "de")   # True
registry.is_pair_supported("EN", "DE")   # True (case-insensitive)

# Unsupported pair (not in DeepL's list)
registry.is_pair_supported("en", "th")   # False

# Blacklisted pair
registry.mark_pair_unsupported("en", "ja")
registry.is_pair_supported("en", "ja")   # False

# After TTL expires
# registry.is_pair_supported("en", "ja")  # True (if both languages are in supported set)
```

---

#### `mark_pair_unsupported()`

```python
def mark_pair_unsupported(self, source_lang: str, target_lang: str) -> None
```

Blacklists a language pair for the configured TTL duration. Typically called after the DeepL API returns an error indicating the pair is unsupported.

| Parameter | Type | Description |
|-----------|------|-------------|
| `source_lang` | `str` | Source language code. Stripped and lowercased internally. |
| `target_lang` | `str` | Target language code. Stripped and lowercased internally. |

**Behavior**
- Computes expiry as `time.time() + self.cache_ttl`.
- Stores the pair in `_unsupported_pairs_cache`.

**Side Effects**
- Mutates `_unsupported_pairs_cache`.

**Logging**
- `WARNING` — Logs the blacklisted pair and TTL duration.

**Example**
```python
registry = DeepLRegistry(cache_ttl=600)
registry.mark_pair_unsupported("en", "th")
# Logs: "Blacklisted DeepL language pair ('en', 'th') for 600.0 seconds due to API error."
```

---

#### `clear_blacklist()`

```python
def clear_blacklist(self) -> None
```

Resets the runtime tracking cache, immediately making all previously blacklisted pairs eligible for retry.

**Behavior**
- Clears `_unsupported_pairs_cache` entirely.

**Use Cases**
- Manual recovery after an operator resolves an upstream issue.
- Testing and debugging.
- Forcing retry of all pairs before natural TTL expiration.

**Example**
```python
registry = DeepLRegistry()
registry.mark_pair_unsupported("en", "ja")
registry.is_pair_supported("en", "ja")  # False

registry.clear_blacklist()
registry.is_pair_supported("en", "ja")  # True (if supported by DeepL)
```

---

## State Diagram

```
┌─────────────────┐
│   Not in Cache  │
│  (default state)│
└────────┬────────┘
         │
         │ mark_pair_unsupported()
         ▼
┌─────────────────┐     TTL expired
│   Blacklisted   │◄──────────────────┐
│  (unsupported)  │                   │
└────────┬────────┘                   │
         │                            │
         │ is_pair_supported()        │
         │ (returns False)            │
         ▼                            │
┌─────────────────┐                   │
│   Auto-cleanup  │───────────────────┘
│ (remove on read)│
└─────────────────┘
         │
         │ clear_blacklist()
         ▼
┌─────────────────┐
│   Not in Cache  │
│  (manual reset) │
└─────────────────┘
```

---

## Thread Safety

| Concern | Status | Notes |
|---------|--------|-------|
| Concurrent reads | Generally safe | `is_pair_supported()` reads and may delete from the dict. In CPython, single-key dict operations are atomic, but concurrent read + write may raise `RuntimeError` in rare edge cases. |
| Concurrent writes | Not guaranteed | `mark_pair_unsupported()` and `clear_blacklist()` mutate the cache. Race conditions possible under high concurrency. |

**Recommendation:** If the registry is shared across multiple threads, wrap calls with a `threading.Lock` or `threading.RLock`.

---

## Integration with DeepLAdapter

The `DeepLAdapter` instantiates one `DeepLRegistry` per adapter instance:

```python
self.registry = DeepLRegistry()
```

**Trigger point for `mark_pair_unsupported()`:**
- HTTP 400 (Invalid Request) or HTTP 422 in `DeepLAdapter._call_api()` — the adapter calls `self.registry.mark_pair_unsupported(source_lang, target_lang)` before raising `InvalidRequestError` or `LanguageNotSupportedError`.

**Check point:**
- In `DeepLAdapter.translate()`, the adapter calls `self.registry.is_pair_supported(request.source_lang, request.target_lang)` before building the request.

---

## Usage Example

```python
from deepl_registry import DeepLRegistry

# Initialize with a 1-hour blacklist TTL
registry = DeepLRegistry(cache_ttl=3600)

# Check support (statically supported, not yet blacklisted)
is_ok = registry.is_pair_supported("en", "de")
print(is_ok)  # True

# Check unsupported language
is_ok = registry.is_pair_supported("en", "th")
print(is_ok)  # False (Thai not in DeepL's supported list)

# Simulate an API failure on a supported pair → blacklist
registry.mark_pair_unsupported("en", "fi")

# Now blocked
is_ok = registry.is_pair_supported("en", "fi")
print(is_ok)  # False

# After operator fixes the issue, force retry
registry.clear_blacklist()
is_ok = registry.is_pair_supported("en", "fi")
print(is_ok)  # True
```

---

## Logging

The module uses Python's standard `logging` module under the logger name `__name__`.

**Log Levels Used**

| Level | Event |
|-------|-------|
| `DEBUG` | Pair is found in the blacklist and is still active (blocked). |
| `WARNING` | Pair is added to the blacklist via `mark_pair_unsupported()`. |

---

## Changelog

| Version | Notes |
|---------|-------|
| Current — TTL-based runtime blacklist with auto-expiry on read, manual clear, and static DeepL language validation against 33 supported codes. |
