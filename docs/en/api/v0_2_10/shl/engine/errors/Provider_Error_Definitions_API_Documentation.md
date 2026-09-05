# Provider Error Definitions API Documentation

## Overview

`providers.py` defines provider-specific error response definitions for SHL translation services. It provides declarative mappings for translation service error responses, including failure conditions, prioritized error code paths, message paths, and provider-specific error code mappings to SHL error codes.

Provider-specific parsing logic is intentionally excluded from this module. The generic `ErrorParser` uses these definitions to normalize provider errors into SHL error codes.

---

## Module Metadata

| Field | Value |
|-------|-------|
| **File** | `shl/engine/errors/providers.py` |
| **Author** | Tuomas Lähteenmäki |
| **Version** | `0.2.10` |
| **License** | MIT |

---

## Dependencies and Imports

### Internal Modules

The following SHL error code constants are imported from `.codes`:

| Constant | Description |
|----------|-------------|
| `ACCESS_DENIED` | Access denied error. |
| `API_NOT_FOUND` | API endpoint not found error. |
| `AUTH_BLOCKED` | Authentication blocked error. |
| `AUTH_EXPIRED` | Authentication expired error. |
| `AUTH_FAILED` | Authentication failed error. |
| `INVALID_REQUEST` | Invalid request error. |
| `LANG_PAIR_UNSUPPORTED` | Language pair unsupported error. |
| `LANG_UNSUPPORTED` | Language unsupported error. |
| `METHOD_NOT_ALLOWED` | HTTP method not allowed error. |
| `NOT_FOUND` | Resource not found error. |
| `QUOTA_EXCEEDED` | Quota exceeded error. |
| `RATE_LIMIT_EXCEEDED` | Rate limit exceeded error. |
| `REQUEST_TOO_LONG` | Request too long error. |
| `SERVICE_UNAVAILABLE` | Service unavailable error. |
| `TEXT_TOO_LONG` | Text too long error. |

---

## Provider Definitions

Each provider is defined as a dictionary with the following structure:

| Key | Type | Description |
|-----|------|-------------|
| `failure_conditions` | `list[dict]` | Conditions that indicate a failed response. |
| `code_paths` | `tuple[tuple]` | Prioritized nested key paths to extract the error code. |
| `message_paths` | `tuple[tuple]` | Prioritized nested key paths to extract the error message. |
| `error_codes` | `dict` | Mapping from provider-specific error codes to SHL error codes. |

### Failure Condition Structure

Each condition in `failure_conditions` is a dictionary with:

| Key | Type | Description |
|-----|------|-------------|
| `path` | `tuple` | Nested key path in the response data. |
| `operator` | `str` | Comparison operator (`"eq"`, `"ne"`, `"exists"`). |
| `value` | `Any` | Value to compare against (required for `"eq"` and `"ne"`). |
| `code` | `str` | Optional SHL error code to return if this condition matches. |

---

### `PAPAGO`

**Failure Conditions:**

| Path | Operator | Value | Code |
|------|----------|-------|------|
| `("data", "status")` | `eq` | `"FAILED"` | — |

**Code Paths:**

```python
(
    ("data", "errCode"),
)
```

**Message Paths:**

```python
(
    ("data", "errMsg"),
)
```

**Error Code Mapping:**

| Provider Code | SHL Error Code |
|---------------|----------------|
| `N2MT01` | `INVALID_REQUEST` |
| `N2MT02` | `LANG_UNSUPPORTED` |
| `N2MT03` | `INVALID_REQUEST` |
| `N2MT04` | `LANG_UNSUPPORTED` |
| `N2MT05` | `INVALID_REQUEST` |
| `N2MT06` | `LANG_PAIR_UNSUPPORTED` |
| `N2MT07` | `INVALID_REQUEST` |
| `N2MT08` | `TEXT_TOO_LONG` |
| `N2MT99` | `SERVICE_UNAVAILABLE` |
| `LD01` | `INVALID_REQUEST` |
| `LD99` | `SERVICE_UNAVAILABLE` |
| `024` | `AUTH_FAILED` |
| `051` | `API_NOT_FOUND` |
| `200` | `AUTH_FAILED` |

---

### `MYMEMORY`

**Failure Conditions:**

| Path | Operator | Value | Code |
|------|----------|-------|------|
| `("responseStatus",)` | `ne` | `200` | — |
| `("quotaReached",)` | `eq` | `True` | `QUOTA_EXCEEDED` |
| `("responseData", "warning")` | `exists` | — | — |

**Code Paths:**

```python
(
    ("responseStatus",),
)
```

**Message Paths:**

```python
(
    ("responseDetails",),
    ("responseData", "warning"),
)
```

**Error Code Mapping:**

| Provider Code | SHL Error Code |
|---------------|----------------|
| `400` | `INVALID_REQUEST` |
| `403` | `ACCESS_DENIED` |
| `404` | `NOT_FOUND` |
| `413` | `TEXT_TOO_LONG` |
| `414` | `REQUEST_TOO_LONG` |
| `429` | `RATE_LIMIT_EXCEEDED` |
| `500` | `SERVICE_UNAVAILABLE` |
| `502` | `SERVICE_UNAVAILABLE` |
| `503` | `SERVICE_UNAVAILABLE` |
| `504` | `SERVICE_UNAVAILABLE` |

---

### `LIBRETRANSLATE`

**Failure Conditions:**

| Path | Operator | Value | Code |
|------|----------|-------|------|
| `("error",)` | `exists` | — | — |

**Code Paths:**

```python
(
    ("error", "code"),
)
```

**Message Paths:**

```python
(
    ("error",),
)
```

**Error Code Mapping:**

| Provider Code | SHL Error Code |
|---------------|----------------|
| `400` | `INVALID_REQUEST` |
| `403` | `ACCESS_DENIED` |
| `404` | `NOT_FOUND` |
| `405` | `METHOD_NOT_ALLOWED` |
| `413` | `TEXT_TOO_LONG` |
| `414` | `REQUEST_TOO_LONG` |
| `429` | `RATE_LIMIT_EXCEEDED` |
| `500` | `SERVICE_UNAVAILABLE` |
| `503` | `SERVICE_UNAVAILABLE` |
| `1010` | `ACCESS_DENIED` |

---

### `DEEPL`

**Failure Conditions:**

| Path | Operator | Value | Code |
|------|----------|-------|------|
| `("message",)` | `exists` | — | — |

**Code Paths:**

```python
(
    ("code",),
    ("status",),
)
```

**Message Paths:**

```python
(
    ("message",),
    ("detail",),
)
```

**Error Code Mapping:**

| Provider Code | SHL Error Code |
|---------------|----------------|
| `400` | `INVALID_REQUEST` |
| `403` | `AUTH_FAILED` |
| `404` | `NOT_FOUND` |
| `413` | `TEXT_TOO_LONG` |
| `414` | `REQUEST_TOO_LONG` |
| `429` | `RATE_LIMIT_EXCEEDED` |
| `456` | `QUOTA_EXCEEDED` |
| `500` | `SERVICE_UNAVAILABLE` |
| `502` | `SERVICE_UNAVAILABLE` |
| `503` | `SERVICE_UNAVAILABLE` |
| `504` | `SERVICE_UNAVAILABLE` |

---

### `GOOGLE`

**Failure Conditions:**

| Path | Operator | Value | Code |
|------|----------|-------|------|
| `("error",)` | `exists` | — | — |

**Code Paths:**

```python
(
    ("error", "status"),
    ("error", "code"),
)
```

**Message Paths:**

```python
(
    ("error", "message"),
    ("error", "details"),
)
```

**Error Code Mapping:**

| Provider Code | SHL Error Code |
|---------------|----------------|
| `400` | `INVALID_REQUEST` |
| `403` | `ACCESS_DENIED` |
| `404` | `NOT_FOUND` |
| `429` | `RATE_LIMIT_EXCEEDED` |
| `500` | `SERVICE_UNAVAILABLE` |
| `503` | `SERVICE_UNAVAILABLE` |
| `"INVALID_ARGUMENT"` | `INVALID_REQUEST` |
| `"PERMISSION_DENIED"` | `ACCESS_DENIED` |
| `"RESOURCE_EXHAUSTED"` | `QUOTA_EXCEEDED` |
| `"INTERNAL"` | `SERVICE_UNAVAILABLE` |
| `"UNAVAILABLE"` | `SERVICE_UNAVAILABLE` |

---

### `MICROSOFT`

**Failure Conditions:**

| Path | Operator | Value | Code |
|------|----------|-------|------|
| `("error",)` | `exists` | — | — |

**Code Paths:**

```python
(
    ("error", "code"),
)
```

**Message Paths:**

```python
(
    ("error", "message"),
)
```

**Error Code Mapping:**

| Provider Code | SHL Error Code |
|---------------|----------------|
| `400036` | `LANG_UNSUPPORTED` |
| `400074` | `INVALID_REQUEST` |
| `401000` | `AUTH_FAILED` |
| `401001` | `AUTH_FAILED` |
| `401002` | `AUTH_EXPIRED` |
| `403000` | `ACCESS_DENIED` |
| `403001` | `QUOTA_EXCEEDED` |
| `413000` | `TEXT_TOO_LONG` |
| `429000` | `RATE_LIMIT_EXCEEDED` |
| `500000` | `SERVICE_UNAVAILABLE` |
| `502000` | `SERVICE_UNAVAILABLE` |
| `503000` | `SERVICE_UNAVAILABLE` |
| `504000` | `SERVICE_UNAVAILABLE` |

---

### `YANDEX`

**Failure Conditions:**

| Path | Operator | Value | Code |
|------|----------|-------|------|
| `("code",)` | `exists` | — | — |

**Code Paths:**

```python
(
    ("code",),
)
```

**Message Paths:**

```python
(
    ("message",),
)
```

**Error Code Mapping:**

| Provider Code | SHL Error Code |
|---------------|----------------|
| `400` | `INVALID_REQUEST` |
| `401` | `AUTH_FAILED` |
| `402` | `AUTH_BLOCKED` |
| `403` | `RATE_LIMIT_EXCEEDED` |
| `404` | `NOT_FOUND` |
| `413` | `TEXT_TOO_LONG` |
| `415` | `INVALID_REQUEST` |
| `422` | `LANG_UNSUPPORTED` |
| `501` | `LANG_PAIR_UNSUPPORTED` |
| `503` | `SERVICE_UNAVAILABLE` |

---

## Usage Example

```python
from shl.engine.errors.providers import PAPAGO, MYMEMORY, GOOGLE
from shl.engine.errors.codes import SERVICE_UNAVAILABLE

# Access a provider definition
papago_codes = PAPAGO["error_codes"]
print(papago_codes["N2MT99"])  # SERVICE_UNAVAILABLE

# Access failure conditions
mymemory_conditions = MYMEMORY["failure_conditions"]

# Access code paths
google_code_paths = GOOGLE["code_paths"]
```

---

## Version

**Module version:** `0.2.10`

**Author:** Tuomas Lähteenmäki

**License:** MIT
