# ErrorParser API Documentation

## Overview

`ErrorParser` is a provider-independent parser for SHL translation service errors. It parses HTTP responses, provider-specific JSON payloads, and exceptions using declarative provider definitions. Different provider error formats are normalized into the common `NormalizedError` model.

Provider-specific parsing logic is intentionally excluded from this module. Provider differences are defined externally through provider configuration mappings.

A successful provider response returns `None`. Error responses are normalized into `NormalizedError` instances.

---

## Module Metadata

| Field | Value |
| --- | --- |
| **File** | `shl/engine/errors/parser.py` |
| **Author** | Tuomas Lähteenmäki |
| **Version** | `0.2.10` |
| **License** | MIT |

---

## Dependencies and Imports

### Standard Library

- `json`
- `typing` (`Any`, `Mapping`, `Optional`, `Sequence`, `Union`)

### Internal Modules

- `.codes` — SHL error code constants.
- `.models.NormalizedError` — Immutable normalized error data class.

---

## Module Constant: `DEFAULT_HTTP_CODES`

Default mapping from HTTP status codes to SHL error codes:

| HTTP Status | SHL Error Code |
| --- | --- |
| `400` | `INVALID_REQUEST` |
| `401` | `AUTH_FAILED` |
| `403` | `ACCESS_DENIED` |
| `404` | `NOT_FOUND` |
| `405` | `METHOD_NOT_ALLOWED` |
| `408` | `TIMEOUT` |
| `413` | `TEXT_TOO_LONG` |
| `414` | `REQUEST_TOO_LONG` |
| `429` | `RATE_LIMIT_EXCEEDED` |
| `500` | `SERVICE_UNAVAILABLE` |
| `502` | `SERVICE_UNAVAILABLE` |
| `503` | `SERVICE_UNAVAILABLE` |
| `504` | `SERVICE_UNAVAILABLE` |

---

## Class: `ErrorParser`

### Constructor

```python
ErrorParser(
    provider: str,
    config: Optional[Mapping[str, Any]] = None,
) -> None
```

#### Parameters

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `provider` | `str` | — | The name of the translation provider. |
| `config` | `Optional[Mapping[str, Any]]` | `None` | Provider-specific error configuration dictionary. |

#### Instance Attributes

| Attribute | Type | Description |
| --- | --- | --- |
| `provider` | `str` | Provider name. |
| `config` | `dict` | The provider configuration as a plain dict (empty if `config` is `None`). |
| `failure_conditions` | `tuple` | Configured failure conditions from `config["failure_conditions"]` (default empty tuple). |
| `code_paths` | `tuple` | Configured code lookup paths from `config["code_paths"]` (default empty tuple). |
| `message_paths` | `tuple` | Configured message lookup paths from `config["message_paths"]` (default empty tuple). |
| `error_code_map` | `dict` | Configured error code mapping from `config["error_codes"]` (default empty dict). |

---

### Methods

#### `parse(response: Any = None, *, http_status: Optional[int] = None, exception: Optional[Exception] = None) -> Optional[NormalizedError]`

Parses a provider response into a normalized SHL error.

##### Parameters

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `response` | `Any` | `None` | The provider response (dict, bytes, str, or None). |
| `http_status` | `Optional[int]` | `None` | HTTP status code, if available. |
| `exception` | `Optional[Exception]` | `None` | Exception instance, if an exception was raised. |

##### Returns

- `Optional[NormalizedError]` — `None` if the response is considered successful; otherwise a `NormalizedError` instance.

##### Behavior

1. **Exception path**: If `exception` is not `None`, delegates to `_parse_exception()` and returns immediately.
2. **Payload decoding**: Calls `_decode_payload(response)` to convert the response into a dictionary.
3. **Invalid payload**: If payload is `None`, returns `_parse_invalid_response(http_status)`.
4. **Failure condition check**: Calls `_find_failure_condition(payload)`.
5. **Code and message extraction**:

- `_find_mapped_error_code(payload)` — finds a provider code that exists in `error_code_map`.
- `_find_error_code(payload)` — finds the raw provider error code.
- `_find_message(payload)` — finds the error message.

6. **Failure condition matched**: If a failure condition is found:

- Calls `_normalize_failure(failure_condition, provider_code, http_status)`.
- Returns `_build_error(normalized_code, ...)`.

7. **HTTP error (>= 400)**: If `http_status >= 400`:

- Calls `_normalize_http_error(provider_code, http_status)`.
- Returns `_build_error(normalized_code, ...)`.

8. **Mapped provider code**: If `provider_code` is not `None`:

- Calls `_normalize_provider_code(provider_code)`.
- If the result is not `UNKNOWN_ERROR`, returns `_build_error(...)`.

9. **Success (2xx-3xx)**: If `http_status` is in range `200 <= http_status < 400`, returns `None`.
10. **Fallback**: Returns `_parse_invalid_response(http_status, payload=payload)`.

---

#### `_build_error(code: str, *, message: Optional[str], http_status: Optional[int], provider_code: Optional[str], details: Optional[Mapping[str, Any]]) -> NormalizedError`

Builds a normalized SHL error.

##### Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| `code` | `str` | SHL error code. |
| `message` | `Optional[str]` | Error message. |
| `http_status` | `Optional[int]` | HTTP status code. |
| `provider_code` | `Optional[str]` | Original provider error code. |
| `details` | `Optional[Mapping[str, Any]]` | Diagnostic details. |

##### Returns

- `NormalizedError` — A frozen dataclass instance with `temporary` and `retryable` flags set via `_is_temporary()` and `_is_retryable()`.

---

#### `_normalize_failure(failure_condition: Mapping[str, Any], provider_code: Optional[str], http_status: Optional[int]) -> str`

Normalizes a configured failure condition.

##### Priority Order

1. Explicit `"code"` from the failure condition (highest priority).
2. Mapped `provider_code` via `_normalize_provider_code()`.
3. HTTP status via `_from_http_status_code()`.
4. Falls back to `UNKNOWN_ERROR`.

---

#### `_normalize_http_error(provider_code: Optional[str], http_status: int) -> str`

Normalizes an HTTP error.

##### Priority Order

1. Known `provider_code` via `_normalize_provider_code()` (if result is not `UNKNOWN_ERROR`).
2. Generic HTTP status mapping via `_from_http_status_code()`.

---

#### `_decode_payload(response: Any) -> Optional[dict[str, Any]]`

Decodes a response into a dictionary mapping.

##### Behavior

- If `response` is `None`, returns `None`.
- If `response` is a `Mapping`, returns `dict(response)`.
- If `response` is `bytes`, decodes as UTF-8 with `errors="replace"`.
- If `response` is a `str`, attempts `json.loads()`.
- If the parsed result is a `Mapping`, returns `dict(payload)`.
- Returns `None` for all other cases or on `JSONDecodeError`.

---

#### `_find_failure_condition(payload: Mapping[str, Any]) -> Optional[Mapping[str, Any]]`

Returns the first configured condition that indicates failure.

##### Behavior

- Iterates over `self.failure_conditions`.
- Skips conditions that are not `Mapping` instances.
- Extracts `"path"` (must be a `Sequence` but not `str` or `bytes`) and `"operator"` (defaults to `"eq"`).
- Reads the value from the payload at the given path via `_get_path()`.
- Checks if the condition matches via `_condition_matches()`.
- Returns the first matching condition, or `None` if none match.

---

#### `_condition_matches(value: Any, operator: str, expected: Any) -> bool`

Evaluates a declarative failure condition.

##### Supported Operators

| Operator | Behavior |
| --- | --- |
| `"exists"` | Returns `True` if `value is not None`. |
| `"not_exists"` | Returns `True` if `value is None`. |
| `"eq"` | Returns `True` if `value == expected`. |
| `"ne"` | Returns `True` if `value != expected`. |
| `"in"` | Returns `True` if `expected` is a collection and `value in expected`. |
| `"not_in"` | Returns `True` if `expected` is a collection and `value not in expected`. |
| (other) | Returns `False`. |

---

#### `_find_error_code(payload: Mapping[str, Any]) -> Optional[str]`

Finds the first provider error code from configured paths.

##### Behavior

- Calls `_find_value(payload, self.code_paths)`.
- If the value is `str`, `int`, or `float`, returns `str(value)`.
- Otherwise returns `None`.

---

#### `_find_mapped_error_code(payload: Mapping[str, Any]) -> Optional[str]`

Finds the first provider code that has a configured SHL mapping.

##### Behavior

- Iterates over `self.code_paths`.
- For each path, reads the value via `_get_path()`.
- Builds a list of candidate values:
- The raw value.
- If the value is a `str`, also tries `_coerce_code(value)` (integer conversion).
- Returns `str(candidate)` for the first candidate found in `self.error_code_map`.
- Returns `None` if no mapped code is found.

---

#### `_find_message(payload: Mapping[str, Any]) -> Optional[str]`

Finds an error message using configured paths.

##### Behavior

- Calls `_find_value(payload, self.message_paths)`.
- Type conversion:
- `str` → returned as-is.
- `int` / `float` → converted to `str`.
- `list` / `tuple` → joined with `"; "`.
- `Mapping` → serialized to JSON with `ensure_ascii=False`.
- Other → converted to `str`.

---

#### `_find_value(payload: Mapping[str, Any], paths: Sequence[Sequence[str]]) -> Any`

Returns the first value found from configured paths.

##### Behavior

- Iterates over `paths`.
- For each path, calls `_get_path(payload, path)`.
- Returns the first non-`None` value.
- Returns `None` if no value is found.

---

#### `_get_path(payload: Mapping[str, Any], path: Sequence[str]) -> Any`

Reads a nested value from a mapping.

##### Behavior

- Traverses the mapping following the sequence of keys in `path`.
- If any intermediate value is not a `Mapping` or a key is missing, returns `None`.
- Returns the final value if all keys exist.

---

#### `_normalize_provider_code(provider_code: Union[str, int]) -> str`

Maps a provider-specific code to an SHL error code.

##### Behavior

1. Looks up `str(provider_code)` in `self.error_code_map`.
2. If not found, tries `_coerce_code(provider_code_str)` (converts numeric strings to integers).
3. Looks up the coerced value in `self.error_code_map`.
4. Returns `UNKNOWN_ERROR` if no mapping is found.

---

#### `_coerce_code(value: Any) -> Any`

Converts numeric string codes to integers when possible.

##### Behavior

- Attempts `int(value)`.
- Returns the integer on success.
- Returns the original value on `TypeError` or `ValueError`.

---

#### `_parse_invalid_response(http_status: Optional[int], payload: Optional[Mapping[str, Any]] = None) -> NormalizedError`

Creates an error for an invalid or undecodable response.

##### Behavior

- If `http_status` is not `None`, maps it via `_from_http_status_code()`.
- If the result is `UNKNOWN_ERROR`, uses `INVALID_RESPONSE`.
- If `http_status` is `None`, uses `INVALID_RESPONSE`.
- Returns a `NormalizedError` with message `"Invalid or empty provider response."`.

---

#### `_from_http_status_code(http_status: Optional[int]) -> str`

Maps an HTTP status code to an SHL error code.

##### Behavior

- If `http_status` is `None`, returns `UNKNOWN_ERROR`.
- Returns `DEFAULT_HTTP_CODES.get(http_status, UNKNOWN_ERROR)`.

---

#### `_parse_exception(exception: Exception, http_status: Optional[int]) -> NormalizedError`

Normalizes an exception into an SHL error.

##### Behavior

- Calls `_exception_to_code(exception)` to determine the SHL error code.
- Returns a `NormalizedError` with:
- `message = str(exception)`
- `details = {"exception_type": type(exception).__name__}`

---

#### `_exception_to_code(exception: Exception) -> str`

Maps common exception types to SHL error codes based on the exception class name (lowercased).

##### Mapping Rules

| Condition in Class Name | SHL Error Code |
| --- | --- |
| Contains `"timeout"` | `TIMEOUT` |
| Contains `"connection"` or `"connect"` | `SERVICE_UNAVAILABLE` |
| Contains `"auth"` and `"expired"` | `AUTH_FAILED` |
| Contains `"auth"` | `AUTH_FAILED` |
| Contains `"access"` or `"permission"` | `ACCESS_DENIED` |
| Contains `"rate"` and `"limit"` | `RATE_LIMIT_EXCEEDED` |
| Contains `"quota"` | `QUOTA_EXCEEDED` |
| Contains `"text"` and `"long"` | `TEXT_TOO_LONG` |
| Contains `"request"` and `"long"` | `REQUEST_TOO_LONG` |
| Contains `"method"` and `"allowed"` | `METHOD_NOT_ALLOWED` |
| Contains `"not"` and `"found"` | `NOT_FOUND` |
| Contains `"language"` and `"support"` | `LANG_UNSUPPORTED` |
| (no match) | `UNKNOWN_ERROR` |

---

#### `_is_temporary(code: str) -> bool`

Returns whether an error is considered temporary.

##### Temporary Errors

- `RATE_LIMIT_EXCEEDED`
- `QUOTA_EXCEEDED`
- `SERVICE_UNAVAILABLE`
- `TIMEOUT`

---

#### `_is_retryable(code: str) -> bool`

Returns whether an error can normally be retried.

##### Retryable Errors

- `RATE_LIMIT_EXCEEDED`
- `SERVICE_UNAVAILABLE`
- `TIMEOUT`

---

## Usage Example

```python
from shl.engine.errors.parser import ErrorParser
from shl.engine.errors.providers import GOOGLE

# Initialize parser with provider configuration
parser = ErrorParser(provider="google", config=GOOGLE)

# Parse an HTTP response
error = parser.parse(
    response={"error": {"code": 429, "message": "Rate limit exceeded"}},
    http_status=429,
)

if error:
    print(error.code)        # RATE_LIMIT_EXCEEDED
    print(error.retryable)   # True
    print(error.temporary)   # True

# Parse an exception
error = parser.parse(
    exception=ConnectionError("Failed to connect"),
    http_status=None,
)

if error:
    print(error.code)        # SERVICE_UNAVAILABLE
```

---

## Version

**Module version:** `0.2.10`

**Author:** Tuomas Lähteenmäki

**License:** MIT