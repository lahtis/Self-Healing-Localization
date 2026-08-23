# MyMemoryAdapter API Documentation

## Overview

`MyMemoryAdapter` is a translation provider adapter for the **MyMemory translation API**. It is dependency-free and uses only Python's standard library (`urllib`). The adapter supports email-based authentication, runtime language pair validation via a shared registry, quota and rate limit detection, match quality validation, and security checks for suspicious output.

---

## Module Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `MYMEMORY_TIMEOUT` | `10` | HTTP request timeout in seconds. |
| `MYMEMORY_DEFAULT_EMAIL` | `os.getenv("MYMEMORY_EMAIL", "")` | Default email address read from the `MYMEMORY_EMAIL` environment variable. Falls back to an empty string if not set. |

---

## Shared Registry Instance

```python
_registry = MyMemoryRegistry()
```

A module-level shared instance of `MyMemoryRegistry` used for runtime language pair validation and blacklisting across all `MyMemoryAdapter` instances.

---

## Class: `MyMemoryAdapter`

Inherits from `TranslationProvider`.

### Constructor

```python
MyMemoryAdapter(
    email: str | None = None,
    cache_ttl: float | None = None,
)
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `email` | `str \| None` | `None` | Email address for the MyMemory API. If not provided, falls back to `MYMEMORY_DEFAULT_EMAIL`. |
| `cache_ttl` | `float \| None` | `None` | If provided, updates the shared registry's `cache_ttl` attribute. |

#### Instance Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `email` | `str` | The resolved email address used for API requests. |

---

### Properties

#### `name`

```python
@property
def name(self) -> str
```

Returns the provider identifier string: `"mymemory"`.

---

### Methods

#### `translate(request: TranslationRequest) -> str`

Translates text using the MyMemory API.

##### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `request` | `TranslationRequest` | A request object containing the text to translate, source and target languages, and formatting options. |

##### Behavior

1. Normalizes `source_lang` and `target_lang` by lowercasing and stripping whitespace. `source_lang` defaults to an empty string if `None`.
2. Checks if the language pair is supported via the shared `_registry.is_pair_supported(src, tgt)`.
   - If not supported, raises `LanguageNotSupportedError` immediately.
3. Builds the request payload via `build_request()`.
4. Calls `_call_api()` with the payload.
5. If `_call_api()` raises `LanguageNotSupportedError`, marks the pair as unsupported in the registry via `_registry.mark_pair_unsupported(src, tgt)` and re-raises the exception.

##### Returns

- `str` — The translated text.

##### Raises

- `LanguageNotSupportedError` — If the pair is not supported by the registry or returned by the API.
- `ProviderAccessError` — On API response status 403 or HTTP 403.
- `RateLimitExceededError` — On quota reached, API response status 429, or HTTP 429.
- `ServiceUnavailableError` — On API response status >= 500, HTTP >= 500, or network/timeout errors.
- `InvalidRequestError` — On API response status 400 (when the error body does not contain "language" or "invalid").
- `TranslationError` — On empty text, unchanged text, weak match quality, suspiciously short output, unexpected status codes, invalid JSON, or unexpected execution failures.

---

#### `build_request(request: TranslationRequest) -> Dict[str, Any]`

Builds the request payload for the MyMemory API.

##### Payload Structure

```json
{
  "q": "text to translate",
  "langpair": "source|target",
  "de": "optional_email_address"
}
```

- `q` is the text from `request.text`.
- `langpair` is formatted as `{source_lang}|{target_lang}` where both are lowercased and stripped. `source_lang` defaults to an empty string if `None`.
- `de` is included only if `self.email` is truthy.

##### Returns

- `Dict[str, Any]` — The request payload dictionary.

---

#### `_call_api(payload: Dict[str, Any]) -> str`

Calls the MyMemory API and processes the response. This is an internal method.

##### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `payload` | `Dict[str, Any]` | The payload built by `build_request()`. |

##### Request Construction

- Base URL: `https://api.mymemory.translated.net/get`
- Query parameters:
  - `q` — URL-encoded via `urllib.parse.quote`
  - `langpair` — The language pair string
  - `de` — URL-encoded email (included only if present in payload)
- Headers:
  - `User-Agent: SHL-Client/{SHL_VERSION}`
  - `Accept: application/json`
- Timeout: `MYMEMORY_TIMEOUT` seconds

##### Response Processing

1. Parses the JSON response.
2. Extracts:
   - `responseStatus` — API status code
   - `responseData` — Dictionary containing translation details (defaults to `{}`)
   - `quotaReached` — Boolean flag
   - `warning` — Warning string from `responseData`
3. **Quota / Rate Limit Check**:
   - If `quotaReached` is `True` or `"quota"` is found in `warning` (case-insensitive), raises `RateLimitExceededError`.
4. **Status Code Handling**:
   - `403` → `ProviderAccessError`
   - `429` → `RateLimitExceededError`
   - `>= 500` → `ServiceUnavailableError`
   - `404` → `LanguageNotSupportedError`
   - `400` → Checks if the JSON-dumped response contains `"language"` or `"invalid"` (case-insensitive). If so, raises `LanguageNotSupportedError`; otherwise raises `InvalidRequestError`.
   - Other non-200 → `TranslationError`
5. **Translation Extraction**:
   - `translatedText` from `responseData`
   - `match` from `responseData`, converted to `float` (defaults to `0`)
6. **Security Checks**:
   - **Empty text**: Raises `TranslationError` if the result is empty or whitespace-only.
   - **Unchanged text**: Raises `TranslationError` if the output equals the input exactly.
   - **Weak match quality**: Raises `TranslationError` if `match_quality < 0.1`.
   - **Suspiciously short output**: Raises `TranslationError` if the output is shorter than 3 characters while the input exceeds 20 characters.
7. Logs a debug message with the first 100 characters of the translation and returns the text.

##### Error Mapping

| Condition | Raised Exception |
|-----------|------------------|
| Quota reached or "quota" in warning | `RateLimitExceededError` |
| API status 403 | `ProviderAccessError` |
| API status 429 | `RateLimitExceededError` |
| API status >= 500 | `ServiceUnavailableError` |
| API status 404 | `LanguageNotSupportedError` |
| API status 400 + "language"/"invalid" in body | `LanguageNotSupportedError` |
| API status 400 (other) | `InvalidRequestError` |
| API status != 200 | `TranslationError` |
| HTTP 403 | `ProviderAccessError` |
| HTTP 429 | `RateLimitExceededError` |
| HTTP >= 500 | `ServiceUnavailableError` |
| HTTP 404 | `LanguageNotSupportedError` |
| HTTP 400 + "language"/"invalid" in body | `LanguageNotSupportedError` |
| HTTP 400 (other) | `InvalidRequestError` |
| Other HTTP | `TranslationError` |
| `URLError` (timeout) | `ServiceUnavailableError` |
| `socket.timeout` / `TimeoutError` | `ServiceUnavailableError` |
| `json.JSONDecodeError` | `TranslationError` |
| Other unexpected | `TranslationError` |

##### Returns

- `str` — The translated text.

---

## Dependencies and Imports

### Standard Library

- `os`
- `json`
- `logging`
- `socket`
- `typing` (`Dict`, `Any`)
- `urllib.request` (`Request`, `urlopen`)
- `urllib.parse` (`quote`)
- `urllib.error` (`URLError`, `HTTPError`)

### SHL Internal Modules

- `shl._version.__version__` (as `SHL_VERSION`)
- `shl.exceptions`:
  - `TranslationError`
  - `ServiceUnavailableError`
  - `RateLimitExceededError`
  - `LanguageNotSupportedError`
  - `ProviderAccessError`
  - `InvalidRequestError`
- `shl.metadata.TranslationRequest`
- `shl.providers.base.TranslationProvider`
- `.mymemory_registry.MyMemoryRegistry`

---

## Usage Example

```python
from shl.providers.mymemory import MyMemoryAdapter
from shl.metadata import TranslationRequest

# Initialize adapter
adapter = MyMemoryAdapter(
    email="your-email@example.com",
    cache_ttl=86400.0,
)

# Build and execute a translation request
request = TranslationRequest(
    text="Hello, world!",
    source_lang="en",
    target_lang="fi",
)

try:
    result = adapter.translate(request)
    print(result)
except LanguageNotSupportedError:
    print("Language pair not supported.")
except RateLimitExceededError:
    print("Quota or rate limit exceeded.")
except ProviderAccessError:
    print("Access denied.")
except ServiceUnavailableError:
    print("Service temporarily unavailable.")
except TranslationError as e:
    print(f"Translation failed: {e}")
```

---

## Shared Registry Behavior

The adapter uses a **module-level shared instance** of `MyMemoryRegistry` (`_registry`). This means:

- All `MyMemoryAdapter` instances share the same language pair blacklist.
- Setting `cache_ttl` via any adapter instance affects the shared registry globally.
- Blacklisted pairs persist across adapter instances within the same process.

---

## Security Checks Summary

The adapter performs the following runtime validations on the API response:

1. **Empty text** — Rejects empty or whitespace-only translations.
2. **Unchanged text** — Rejects translations identical to the input.
3. **Weak match quality** — Rejects translations with a match score below `0.1`.
4. **Suspiciously short output** — Rejects outputs shorter than 3 characters when the input exceeds 20 characters.

---

## Quota Detection

The adapter detects quota exhaustion through two mechanisms:

1. **`quotaReached` field** — If `response_data.get("quotaReached")` returns `True`.
2. **Warning text** — If the `warning` field in `responseData` contains the word "quota" (case-insensitive).

Both conditions raise `RateLimitExceededError`.
