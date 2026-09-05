# NormalizedError Model API Documentation

## Overview

`models.py` defines data models for normalized SHL translation service errors. These are immutable data structures used to represent normalized provider errors after they have been processed by the generic error parser.

The models are provider-independent and contain both the SHL normalized error information and relevant provider-specific diagnostic details.

---

## Module Metadata

| Field | Value |
|-------|-------|
| **File** | `shl/engine/errors/models.py` |
| **Author** | Tuomas Lähteenmäki |
| **Version** | `0.2.10` |
| **License** | MIT |

---

## Dependencies and Imports

### Standard Library

- `dataclasses.dataclass`
- `typing.Any`
- `typing.Optional`

---

## Class: `NormalizedError`

```python
@dataclass(frozen=True)
class NormalizedError:
```

An immutable data class representing a normalized translation service error.

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `code` | `str` | — | The SHL normalized error code (e.g., `"RATE_LIMIT_EXCEEDED"`, `"SERVICE_UNAVAILABLE"`). |
| `provider` | `str` | — | The name of the translation provider that returned the error. |
| `message` | `Optional[str]` | `None` | Human-readable error message from the provider, if available. |
| `temporary` | `bool` | `False` | Indicates whether the error is temporary (e.g., a transient service outage). |
| `retryable` | `bool` | `False` | Indicates whether the request can be retried. |
| `http_status` | `Optional[int]` | `None` | The HTTP status code returned by the provider, if applicable. |
| `provider_code` | `Optional[str]` | `None` | The original provider-specific error code before normalization. |
| `details` | `Optional[Any]` | `None` | Additional provider-specific diagnostic details (type depends on provider). |

### Immutability

The class is decorated with `@dataclass(frozen=True)`, meaning all instances are immutable after creation. Any attempt to modify a field after instantiation will raise a `FrozenInstanceError`.

---

## Usage Example

```python
from shl.engine.errors.models import NormalizedError

# Create a normalized error instance
error = NormalizedError(
    code="RATE_LIMIT_EXCEEDED",
    provider="google",
    message="Quota exceeded for quota metric 'translate.googleapis.com/read_requests'",
    temporary=True,
    retryable=True,
    http_status=429,
    provider_code="429",
    details={"retry_after": 60},
)

# Access fields
print(error.code)         # RATE_LIMIT_EXCEEDED
print(error.provider)     # google
print(error.retryable)    # True

# Immutability: this will raise FrozenInstanceError
# error.code = "INVALID_REQUEST"
```

---

## Version

**Module version:** `0.2.10`

**Author:** Tuomas Lähteenmäki

**License:** MIT
