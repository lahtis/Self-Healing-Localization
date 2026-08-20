# Papago Language Pair Registry — API Documentation

## Module Overview

**File:** `papago_registry.py`

A TTL-based runtime blacklist registry for Papago language pairs. Complements static provider cache data by dynamically learning and temporarily blocking language pairs that have previously failed at the Papago API. Prevents repeated requests to known-unsupported pairs, reducing unnecessary API quota consumption and latency.

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
| `time` | Unix timestamp generation for TTL expiry calculation. |
| `logging` | Debug and warning log output for blacklist events. |
| `typing.Dict`, `typing.Tuple` | Type annotations for the internal cache structure. |

---

## Class: `PapagoRegistry`

```python
class PapagoRegistry
```

Tracks runtime Papago language pair support using a TTL-based blacklist. When the Papago API rejects a language pair (e.g., HTTP 400), the pair is added to an in-memory blacklist with a configurable time-to-live. Subsequent `is_pair_supported()` calls return `False` for blacklisted pairs until the TTL expires.

### Design Rationale

Static support lists may not cover all edge cases or API-side changes. This registry provides a lightweight, self-learning layer that:
- Avoids hammering the API with pairs that have already failed.
- Automatically recovers after the TTL expires (allowing retry if the API later supports the pair).
- Can be manually cleared by an operator.

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
def is_pair_supported(
    self,
    source_lang: str,
    target_lang: str,
    static_supported: bool
) -> bool
```

Checks whether a Papago language pair is currently considered supported.

**Evaluation Order**
1. **Runtime blacklist check** — If the pair exists in `_unsupported_pairs_cache` and the current time is before the expiry timestamp, returns `False`.
2. **TTL expiry cleanup** — If the pair exists but its TTL has expired, it is removed from the cache.
3. **Static support fallback** — Returns the value of `static_supported` (provided by the caller, typically from `provider_cache`).

| Parameter | Type | Description |
|-----------|------|-------------|
| `source_lang` | `str` | Source language code. Stripped and lowercased internally. |
| `target_lang` | `str` | Target language code. Stripped and lowercased internally. |
| `static_supported` | `bool` | Static support flag from the provider cache or configuration. |

**Returns**
- `bool` — `True` if the pair is not blacklisted and `static_supported` is `True`. `False` if blacklisted or `static_supported` is `False`.

**Logging**
- `DEBUG` — When a pair is found in the blacklist and still active.

**Example**
```python
registry = PapagoRegistry(cache_ttl=3600)

# Statically supported, not blacklisted
registry.is_pair_supported("en", "ko", static_supported=True)   # True

# Blacklist the pair
registry.mark_pair_unsupported("en", "ko")
registry.is_pair_supported("en", "ko", static_supported=True)   # False

# After TTL expires
# registry.is_pair_supported("en", "ko", static_supported=True)  # True
```

---

#### `mark_pair_unsupported()`

```python
def mark_pair_unsupported(
    self,
    source_lang: str,
    target_lang: str
) -> None
```

Adds a language pair to the runtime blacklist for the configured TTL duration.

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
registry = PapagoRegistry(cache_ttl=600)
registry.mark_pair_unsupported("ja", "de")
# Logs: "Papago: Blacklisted language pair ('ja', 'de') for 600.0 seconds due to API error."
```

---

#### `clear_blacklist()`

```python
def clear_blacklist(self) -> None
```

Removes all entries from the runtime blacklist, immediately making all previously blacklisted pairs eligible for retry.

**Behavior**
- Clears `_unsupported_pairs_cache` entirely.

**Use Cases**
- Manual recovery after an operator resolves an upstream issue.
- Testing and debugging.
- Forcing retry of all pairs before natural TTL expiration.

**Example**
```python
registry = PapagoRegistry()
registry.mark_pair_unsupported("en", "th")
registry.is_pair_supported("en", "th", static_supported=True)  # False

registry.clear_blacklist()
registry.is_pair_supported("en", "th", static_supported=True)  # True
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
| Concurrent reads | Generally safe | `is_pair_supported()` reads and may delete from the dict. In CPython, single-key dict operations are atomic, but concurrent read + write may raise `RuntimeError` (dictionary changed size during iteration) in rare edge cases. |
| Concurrent writes | Not guaranteed | `mark_pair_unsupported()` and `clear_blacklist()` mutate the cache. Race conditions possible under high concurrency. |

**Recommendation:** If the registry is shared across multiple threads, wrap calls with a `threading.Lock` or `threading.RLock`.

---

## Integration with PapagoAdapter

The `PapagoAdapter` instantiates one `PapagoRegistry` per adapter instance:

```python
self.registry = PapagoRegistry()
```

**Trigger point for `mark_pair_unsupported()`:**
- HTTP 400 (Invalid Request) in `PapagoAdapter._call_api()` — the adapter calls `self.registry.mark_pair_unsupported(source_lang, target_lang)` before raising `InvalidRequestError`.

**Check point:**
- In `PapagoAdapter.translate()`, the adapter calls `self.registry.is_pair_supported(request.source_lang, request.target_lang, static_supported=...)` before building the request. The `static_supported` value typically comes from a static provider cache or configuration layer.

---

## Usage Example

```python
from papago_registry import PapagoRegistry

# Initialize with a 1-hour blacklist TTL
registry = PapagoRegistry(cache_ttl=3600)

# Check support (statically supported, not yet blacklisted)
is_ok = registry.is_pair_supported("en", "ko", static_supported=True)
print(is_ok)  # True

# Simulate an API failure → blacklist the pair
registry.mark_pair_unsupported("en", "ko")

# Now blocked
is_ok = registry.is_pair_supported("en", "ko", static_supported=True)
print(is_ok)  # False

# After operator fixes the issue, force retry
registry.clear_blacklist()
is_ok = registry.is_pair_supported("en", "ko", static_supported=True)
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
| 0.2.4 | Current — TTL-based runtime blacklist with auto-expiry on read, manual clear, and logging. |
