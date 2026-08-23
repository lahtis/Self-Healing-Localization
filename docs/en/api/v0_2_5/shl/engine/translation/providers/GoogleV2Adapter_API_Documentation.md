# GoogleV2Adapter API Documentation

## Overview

`GoogleV2Adapter` is a translation provider adapter for the **Google Cloud Translation Basic (v2) API**. It is dependency-free and uses only Python's standard library (`urllib`). The adapter supports primary and secondary API key failover, plain text and HTML format translation, error mapping to SHL exception types, runtime language pair validation via a registry, and security checks for suspicious output.

---

## Module Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `GOOGLE_TIMEOUT` | `15` | HTTP request timeout in seconds. |
| `GOOGLE_V2_ENDPOINT` | `"https://translation.googleapis.com/language/translate/v2"` | Google Cloud Translation Basic v2 API endpoint. |

---

## Class: `GoogleV2Adapter`

Inherits from `TranslationProvider`.

### Constructor

```python
GoogleV2Adapter(
    api_key: Optional[str] = None,
    backup_api_key: Optional[str] = None,
)
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | `Optional[str]` | `None` | Primary Google Cloud Translation API key. If not provided, falls back to the `GOOGLE_API_KEY` environment variable. |
| `backup_api_key` | `Optional[str]` | `None` | Secondary (backup) API key for failover. If not provided, falls back to the `GOOGLE_BACKUP_API_KEY` environment variable. |

#### Behavior

- Loads environment variables from `./.env/shl/.env` via `load_shl_env()` if not already loaded.
- Strips whitespace from both API keys.
- Sets `has_backup` to `True` only if a backup key is provided and it differs from the primary key.
- Initializes a `GoogleRegistry` instance for runtime language pair validation.
- Raises `ValueError` if no primary API key is available.

---

### Properties

#### `name`

```python
@property
def name(self) -> str
```

Returns the provider identifier string: `"google"`.

#### `supported_features`

```python
@property
def supported_features(self) -> list
```

Returns a list of supported features. Currently returns `["html_format"]`.

---

### Methods

#### `translate(request: TranslationRequest) -> str`

Translates text using the Google Cloud Translation Basic v2 API. Attempts the primary API key first; if that fails with a retryable error, falls back to the backup key.

##### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `request` | `TranslationRequest` | A request object containing the text to translate, source and target languages, and formatting options. |

##### Pre-validation

If `request.source_lang` is set, the adapter validates the language pair against the internal `GoogleRegistry`. If the pair is not supported, a `LanguageNotSupportedError` is raised before any network call.

##### Failover Logic

1. Calls `_call_api()` with the primary key.
2. If the call raises `ProviderAccessError`, `RateLimitExceededError`, or `ServiceUnavailableError`, and a backup key exists, retries with the backup key.
3. If the backup also fails, the original primary error is re-raised.

##### Returns

- `str` — The translated text.

##### Raises

- `LanguageNotSupportedError` — If the language pair is not supported by the registry.
- `ProviderAccessError` — On HTTP 401/403 (primary or backup).
- `RateLimitExceededError` — On HTTP 429 (primary or backup).
- `ServiceUnavailableError` — On server errors (5xx) or network timeouts (primary or backup).
- `InvalidRequestError` — On HTTP 400, 409, 413, 415, 422.
- `TranslationError` — On empty translation payload, empty text, unchanged text, unexpected detected language, unexpected HTML in text mode, suspiciously short output, or unexpected execution failures.

---

#### `build_request(request: TranslationRequest) -> Dict[str, Any]`

Builds the JSON payload for the Google Cloud Translation v2 API.

##### Payload Structure

```json
{
  "q": ["text to translate"],
  "target": "target_language_code",
  "format": "html" | "text",
  "source": "source_language_code"  // omitted if source_lang is None
}
```

- `q` is always a single-element list containing `request.text`.
- `format` is `"html"` if `request.html_format` is `True`, otherwise `"text"`.
- `source` is included only if `request.source_lang` is not `None`.

---

#### `_call_api(api_key: str, payload: Dict[str, Any], is_backup: bool = False) -> str`

Low-level HTTP call executor. This is an internal method.

##### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | `str` | — | The API key to use for this request. |
| `payload` | `Dict[str, Any]` | — | The JSON payload built by `build_request()`. |
| `is_backup` | `bool` | `False` | Whether this call uses the backup API key. |

##### Request Headers

- `Content-Type: application/json`
- `User-Agent: SHL-Client/{SHL_VERSION}`
- `Accept: application/json`

##### Response Processing

1. Parses the JSON response.
2. Checks for an `error` field and delegates to `_handle_api_error()` if present.
3. Extracts the first translation from `data.translations`.
4. Performs the following **security checks** on the translated output:
   - **Empty output**: Raises `TranslationError` if the result is empty or whitespace-only.
   - **Unchanged text**: Raises `TranslationError` if the output equals the input exactly.
   - **Unexpected detected language**: If `source` was declared in the payload and Google returns a `detectedSourceLanguage` that differs from it, raises `TranslationError`.
   - **Unexpected HTML markup**: If `format` is `"text"` and the output contains `<` and `>`, raises `TranslationError`.
   - **Suspiciously short output**: If the output is shorter than 3 characters while the input is longer than 20, raises `TranslationError`.

##### Error Mapping

| HTTP Status | Raised Exception |
|-------------|------------------|
| 401, 403 | `ProviderAccessError` |
| 429 | `RateLimitExceededError` |
| 400 | `InvalidRequestError` (also marks pair unsupported) |
| 409, 413, 415, 422 | `InvalidRequestError` (also marks pair unsupported) |
| 500, 502, 503, 504 | `ServiceUnavailableError` |
| Other HTTP | `TranslationError` |
| `URLError` (timeout) | `ServiceUnavailableError` |
| `socket.timeout` / `TimeoutError` | `ServiceUnavailableError` |
| Other unexpected | `TranslationError` |

---

#### `_handle_api_error(error: Dict[str, Any], payload: Dict[str, Any]) -> str`

Handles Google API error JSON structures. This is an internal method.

Extracts `code` and `message` from the error dict and maps them to the same exception types as `_call_api()`. For status codes 400 and 409–422, it also calls `_mark_unsupported_if_needed()`.

**Note**: The return type annotation is `str`, but the method always raises an exception and never returns a value.

---

#### `_mark_unsupported_if_needed(payload: Dict[str, Any]) -> None`

Marks a language pair as unsupported in the registry. This is an internal method.

If the payload contains an explicit `"source"` key, calls `self.registry.mark_pair_unsupported(source, target)`.

---

## Dependencies and Imports

### Standard Library

- `json`
- `logging`
- `os`
- `socket`
- `typing` (`Dict`, `Any`, `Optional`)
- `urllib.parse` (`urlencode`)
- `urllib.request` (`Request`, `urlopen`)
- `urllib.error` (`URLError`, `HTTPError`)

### SHL Internal Modules

- `shl._version.__version__` (as `SHL_VERSION`)
- `shl.utils.env_loader.load_shl_env`
- `shl.utils.env_loader.mask_api_key`
- `shl.exceptions`:
  - `TranslationError`
  - `ServiceUnavailableError`
  - `RateLimitExceededError`
  - `LanguageNotSupportedError`
  - `ProviderAccessError`
  - `InvalidRequestError`
- `shl.metadata.TranslationRequest`
- `shl.providers.base.TranslationProvider`
- `shl.providers.google_registry.GoogleRegistry`

---

## Usage Example

```python
from shl.providers.googlev2 import GoogleV2Adapter
from shl.metadata import TranslationRequest

# Initialize with explicit keys (or rely on environment variables)
adapter = GoogleV2Adapter(
    api_key="your-primary-key",
    backup_api_key="your-backup-key",
)

# Build a translation request
request = TranslationRequest(
    text="Hello, world!",
    source_lang="en",
    target_lang="fi",
    html_format=False,
)

# Execute translation
try:
    result = adapter.translate(request)
    print(result)  # "Hei, maailma!"
except LanguageNotSupportedError:
    print("Language pair not supported.")
except RateLimitExceededError:
    print("Rate limit exceeded.")
except ProviderAccessError:
    print("API key invalid or expired.")
except ServiceUnavailableError:
    print("Google service temporarily unavailable.")
except TranslationError as e:
    print(f"Translation failed: {e}")
```

---

## Security Checks Summary

The adapter performs the following runtime validations on Google API responses:

1. **Empty output** — Rejects empty or whitespace-only translations.
2. **Unchanged text** — Rejects translations identical to the input.
3. **Unexpected detected source language** — If a source language was explicitly declared, rejects responses where Google's detected source differs.
4. **Unexpected HTML markup** — In plain-text mode (`format="text"`), rejects outputs containing `<` and `>`.
5. **Suspiciously short output** — Rejects outputs shorter than 3 characters when the input exceeds 20 characters.

---

## Failover Behavior

Failover to the backup API key occurs **only** for the following primary-key failures:

- `ProviderAccessError` (HTTP 401/403)
- `RateLimitExceededError` (HTTP 429)
- `ServiceUnavailableError` (HTTP 5xx or network timeout)

If the backup key also fails, the **original primary error** is raised (chained via `from backup_err`).

---

## Version

**Module version:** `0.2.4`

**Author:** Tuomas Lähteenmäki

**License:** MIT
