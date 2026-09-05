# SHL Error Codes API Documentation

## Overview

`codes.py` defines common error codes used by the SHL error handling system. These are provider-independent error categories used to normalize translation service errors across different providers.

Provider-specific error codes are mapped to these shared SHL codes by the provider definitions. The codes provide a stable error vocabulary for routing, fallback handling, retry logic, monitoring, and diagnostics.

---

## Module Metadata

| Field | Value |
|-------|-------|
| **File** | `shl/engine/errors/codes.py` |
| **Author** | Tuomas Lähteenmäki |
| **Version** | `0.2.10` |
| **License** | MIT |

---

## Error Code Constants

### Request Errors

| Constant | Value | Description |
|----------|-------|-------------|
| `INVALID_REQUEST` | `"INVALID_REQUEST"` | The request was malformed or contained invalid parameters. |
| `REQUEST_TOO_LONG` | `"REQUEST_TOO_LONG"` | The overall request exceeded the provider's size limit. |
| `TEXT_TOO_LONG` | `"TEXT_TOO_LONG"` | The text payload exceeded the provider's character limit. |
| `METHOD_NOT_ALLOWED` | `"METHOD_NOT_ALLOWED"` | The HTTP method used is not allowed for the requested endpoint. |

### Language Errors

| Constant | Value | Description |
|----------|-------|-------------|
| `LANG_UNSUPPORTED` | `"LANG_UNSUPPORTED"` | The requested language is not supported by the provider. |
| `LANG_PAIR_UNSUPPORTED` | `"LANG_PAIR_UNSUPPORTED"` | The requested source-target language pair is not supported. |

### Authentication and Access Errors

| Constant | Value | Description |
|----------|-------|-------------|
| `AUTH_FAILED` | `"AUTH_FAILED"` | Authentication failed (e.g., invalid credentials). |
| `AUTH_EXPIRED` | `"AUTH_EXPIRED"` | The authentication token or key has expired. |
| `AUTH_BLOCKED` | `"AUTH_BLOCKED"` | The account or API key has been blocked. |
| `ACCESS_DENIED` | `"ACCESS_DENIED"` | Access denied (e.g., insufficient permissions). |
| `API_NOT_FOUND` | `"API_NOT_FOUND"` | The requested API endpoint was not found. |

### Usage and Quota Errors

| Constant | Value | Description |
|----------|-------|-------------|
| `RATE_LIMIT_EXCEEDED` | `"RATE_LIMIT_EXCEEDED"` | The request rate limit has been exceeded. |
| `QUOTA_EXCEEDED` | `"QUOTA_EXCEEDED"` | The usage quota has been exceeded. |

### Resource Errors

| Constant | Value | Description |
|----------|-------|-------------|
| `NOT_FOUND` | `"NOT_FOUND"` | The requested resource was not found. |

### Service Errors

| Constant | Value | Description |
|----------|-------|-------------|
| `TIMEOUT` | `"TIMEOUT"` | The request timed out. |
| `SERVICE_UNAVAILABLE` | `"SERVICE_UNAVAILABLE"` | The translation service is temporarily unavailable. |

### Response Errors

| Constant | Value | Description |
|----------|-------|-------------|
| `INVALID_RESPONSE` | `"INVALID_RESPONSE"` | The response from the provider was invalid or unexpected. |

### Unknown

| Constant | Value | Description |
|----------|-------|-------------|
| `UNKNOWN_ERROR` | `"UNKNOWN_ERROR"` | An unrecognized or unclassified error occurred. |

---

## Complete Error Code List

```python
INVALID_REQUEST = "INVALID_REQUEST"
REQUEST_TOO_LONG = "REQUEST_TOO_LONG"
TEXT_TOO_LONG = "TEXT_TOO_LONG"
METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"

LANG_UNSUPPORTED = "LANG_UNSUPPORTED"
LANG_PAIR_UNSUPPORTED = "LANG_PAIR_UNSUPPORTED"

AUTH_FAILED = "AUTH_FAILED"
AUTH_EXPIRED = "AUTH_EXPIRED"
AUTH_BLOCKED = "AUTH_BLOCKED"
ACCESS_DENIED = "ACCESS_DENIED"
API_NOT_FOUND = "API_NOT_FOUND"

RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
QUOTA_EXCEEDED = "QUOTA_EXCEEDED"

NOT_FOUND = "NOT_FOUND"

TIMEOUT = "TIMEOUT"
SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"

INVALID_RESPONSE = "INVALID_RESPONSE"

UNKNOWN_ERROR = "UNKNOWN_ERROR"
```

---

## Usage Example

```python
from shl.engine.errors.codes import (
    RATE_LIMIT_EXCEEDED,
    SERVICE_UNAVAILABLE,
    LANG_UNSUPPORTED,
)

# Use in error handling
if response_status == 429:
    error_code = RATE_LIMIT_EXCEEDED
elif response_status >= 500:
    error_code = SERVICE_UNAVAILABLE
```

---

## Version

**Module version:** `0.2.10`

**Author:** Tuomas Lähteenmäki

**License:** MIT
