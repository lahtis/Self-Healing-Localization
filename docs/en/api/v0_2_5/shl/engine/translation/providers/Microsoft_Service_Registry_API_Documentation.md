# Microsoft Service Registry — API Documentation

## Module Overview

**File:** `microsoft_registry.py`

A lightweight, time-based service availability registry for the Microsoft Translator adapter. Uses a simple TTL (time-to-live) mechanism to temporarily mark the Microsoft Translator service as unavailable after failures, preventing repeated requests to a known-broken endpoint.

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
| `time` | Unix timestamp comparison for TTL expiration. |
| `typing.Optional` | Type hints (imported, not directly used in current implementation). |

---

## Class: `MicrosoftServiceRegistry`

```python
class MicrosoftServiceRegistry
```

A TTL-based circuit-breaker-style registry that tracks whether the Microsoft Translator service should be considered temporarily unavailable.

### Design Rationale

Instead of querying a potentially failing remote endpoint on every translation request, the registry records a "cooldown" period. Once the service is marked unavailable, all subsequent `is_available()` checks return `False` until the TTL expires. This reduces unnecessary network traffic and API quota consumption during outages.

---

### Constructor

```python
def __init__(self, ttl_seconds: int = 600) -> None
```

Initializes the registry with a configurable TTL.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ttl_seconds` | `int` | `600` | Duration in seconds for which the service remains marked unavailable after a failure. |

**Behavior**
- Sets `self.ttl` to the provided TTL value.
- Initializes `self.unavailable_until` to `0.0`, meaning the service is considered available by default.

---

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `ttl` | `int` | The configured TTL in seconds. Immutable after construction. |
| `unavailable_until` | `float` | Unix timestamp until which the service is considered unavailable. `0.0` means available. |

---

### Methods

#### `mark_unavailable()`

```python
def mark_unavailable(self) -> None
```

Marks the Microsoft Translator service as temporarily unavailable.

**Behavior**
- Sets `unavailable_until` to `time.time() + self.ttl`.
- From this point until the calculated timestamp, `is_available()` will return `False`.

**Side Effects**
- Mutates `self.unavailable_until`.

**Example**
```python
registry = MicrosoftServiceRegistry(ttl_seconds=300)
registry.mark_unavailable()
# Service is now unavailable for the next 5 minutes
```

---

#### `is_available()`

```python
def is_available(self) -> bool
```

Checks whether the Microsoft Translator service is currently considered available.

**Returns**
- `bool` — `True` if the current time is past `unavailable_until` (or if `unavailable_until` is `0.0`), meaning the service is available. `False` if the cooldown period is still active.

**Logic**
```python
return time.time() >= self.unavailable_until
```

**Example**
```python
registry = MicrosoftServiceRegistry(ttl_seconds=600)

# Initially available
print(registry.is_available())  # True

# Mark as unavailable
registry.mark_unavailable()
print(registry.is_available())  # False

# After 10 minutes
print(registry.is_available())  # True (TTL expired)
```

---

#### `clear()`

```python
def clear(self) -> None
```

Manually resets the availability state, immediately marking the service as available regardless of any active TTL.

**Behavior**
- Sets `unavailable_until` back to `0.0`.

**Use Cases**
- Manual recovery after an operator fixes an upstream issue.
- Testing and debugging.
- Forcing a retry before the natural TTL expiration.

**Example**
```python
registry = MicrosoftServiceRegistry(ttl_seconds=3600)
registry.mark_unavailable()

# Operator resolves the issue — force immediate retry
registry.clear()
print(registry.is_available())  # True
```

---

## State Diagram

```
┌─────────────┐
│   Initial   │  unavailable_until = 0.0
│  (available)│
└──────┬──────┘
       │
       │ mark_unavailable()
       ▼
┌─────────────┐
│ Unavailable │  unavailable_until = now + ttl
│  (cooldown) │
└──────┬──────┘
       │
       │ time passes ≥ ttl
       ▼
┌─────────────┐
│   Available │  is_available() → True
│   (expired) │
└──────┬──────┘
       │
       │ clear()
       ▼
┌─────────────┐
│   Available │  (same as initial)
│   (manual)  │
└─────────────┘
```

---

## Thread Safety

| Concern | Status | Notes |
|---------|--------|-------|
| Concurrent reads | Generally safe | `is_available()` only reads `unavailable_until`. In CPython, single attribute reads are atomic. |
| Concurrent writes | Not guaranteed | `mark_unavailable()` and `clear()` mutate `unavailable_until`. Race conditions possible under high concurrency without external locking. |

**Recommendation:** If the registry is shared across multiple threads, wrap calls with a `threading.Lock` or use a `threading.RLock`.

---

## Usage Example

```python
from microsoft_registry import MicrosoftServiceRegistry

# Initialize with a 10-minute cooldown
registry = MicrosoftServiceRegistry(ttl_seconds=600)

# Before every translation request, check availability
if not registry.is_available():
    print("Microsoft Translator is temporarily unavailable. Skipping request.")
    return

try:
    response = call_microsoft_api(text, target_lang)
except (HTTPError, TimeoutError, URLError):
    # Mark service unavailable to prevent hammering the failing endpoint
    registry.mark_unavailable()
    raise

# If an operator manually resolves the issue:
# registry.clear()
```

---

## Integration with MicrosoftTranslatorAdapter

The `MicrosoftTranslatorAdapter` instantiates one `MicrosoftServiceRegistry` per adapter instance:

```python
self.registry = MicrosoftServiceRegistry(ttl_seconds=ttl_seconds)
```

**Trigger points for `mark_unavailable()`:**
- HTTP 500, 502, 503, 504 (server/gateway errors)
- Network timeouts (`socket.timeout`, `TimeoutError`)
- Socket/URL errors (`URLError`)
- Unexpected execution failures in `_call_api()`

**Check point:**
- At the start of every `translate()` call via `self.registry.is_available()`.

---

## Changelog

| Version | Notes |
|---------|-------|
| 0.2.5 | Current — simple TTL-based registry with `mark_unavailable`, `is_available`, and `clear`. |
