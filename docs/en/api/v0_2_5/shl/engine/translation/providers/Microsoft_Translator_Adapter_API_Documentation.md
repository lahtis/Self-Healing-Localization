# Microsoft Translator Adapter — API Documentation

## Module Overview

**File:** `microsoft_translator.py`

A robust translation provider adapter for the Microsoft Translator API (v3). Implements the `TranslationProvider` interface with support for context matching, formality adjustment, HTML handling, a service-level availability registry (TTL-based), and security checks for suspicious output.

---

## Metadata

| Attribute | Value |
|-----------|-------|
| Author | Tuomas Lähteenmäki |
| Version | 0.2.5 |
| License | MIT |
| Provider Name | `microsoft_translator` |

---

## Module Constants

| Name | Type | Value | Description |
|------|------|-------|-------------|
| `MS_TIMEOUT` | `int` | `15` | Network timeout in seconds for all API requests. |

---

## Dependencies

### Standard Library
- `json`
- `logging`
- `os`
- `socket`
- `urllib.request` (`Request`, `urlopen`)
- `urllib.error` (`URLError`, `HTTPError`)

### SHL Internal
- `shl._version.__version__`
- `shl.utils.env_loader.load_shl_env`
- `shl.utils.env_loader.mask_api_key`
- `..exceptions.TranslationError`
- `..exceptions.ServiceUnavailableError`
- `..exceptions.RateLimitExceededError`
- `..exceptions.ProviderAccessError`
- `..exceptions.InvalidRequestError`
- `..metadata.TranslationRequest`
- `.base.TranslationProvider`
- `.microsoft_registry.MicrosoftServiceRegistry`

---

## Class: `MicrosoftTranslatorAdapter`

```python
class MicrosoftTranslatorAdapter(TranslationProvider)
```

Microsoft Translator API v3 adapter. Handles text translation with optional context, formality, and HTML formatting. Includes built-in security validation and a TTL-based service availability registry.

### Supported Features

| Feature | Description |
|---------|-------------|
| `formality` | Adjusts translation tone (`formal` / `informal`) where supported by the target language. |
| `context` | Injects SHL metadata (domain, screen, component, type, key) into the translation request. |
| `html_format` | Switches between `textType=html` and `textType=plain`. |

---

### Constructor

```python
def __init__(self, api_key: Optional[str] = None) -> None
```

Initializes the adapter, loads environment variables, and sets up the service registry.

| Parameter | Type | Description |
|-----------|------|-------------|
| `api_key` | `Optional[str]` | Direct API key. If omitted, falls back to the `MICROSOFT_TRANSLATOR_KEY` environment variable. |

**Raises**
- `ValueError` — If no API key is provided either as argument or via environment variable.

**Environment Variables**

| Variable | Default | Description |
|----------|---------|-------------|
| `MICROSOFT_TRANSLATOR_KEY` | — | API subscription key for Microsoft Translator. |
| `MS_TRANSLATOR_TTL` | `600` | TTL in seconds for the service availability registry. |

**Behavior**
1. Loads `.env` from `./env/shl/` via `load_shl_env()`.
2. Resolves the API key (parameter → env var).
3. Strips whitespace from the key.
4. Sets the base URL to `https://api.cognitive.microsofttranslator.com/translate?api-version=3.0`.
5. Initializes `MicrosoftServiceRegistry` with the configured TTL.

---

### Properties

#### `name`
```python
@property
def name(self) -> str
```
Returns the provider identifier string.

**Returns:** `"microsoft_translator"`

---

#### `supported_features`
```python
@property
def supported_features(self) -> list
```
Returns the list of features supported by this adapter.

**Returns:** `["formality", "context", "html_format"]`

---

### Methods

#### `translate()`

```python
def translate(self, request: TranslationRequest) -> str
```

Main entry point for translation. Checks service availability, builds the request payload, and calls the Microsoft Translator API.

| Parameter | Type | Description |
|-----------|------|-------------|
| `request` | `TranslationRequest` | Translation request object containing text, languages, and metadata. |

**Returns**
- `str` — The translated text.

**Raises**
- `ServiceUnavailableError` — If the TTL registry marks the service as unavailable.
- `TranslationError` — If the API returns an empty, invalid, or suspicious response.
- `ProviderAccessError` — If the API key is invalid or unauthorized (HTTP 401/403).
- `RateLimitExceededError` — If rate limit is exceeded (HTTP 429).
- `InvalidRequestError` — If the request payload or configuration is invalid (HTTP 400, 409, 413, 415, 422).

---

#### `build_request()`

```python
def build_request(self, request: TranslationRequest) -> Dict[str, Any]
```

Constructs the Microsoft Translator API payload and query parameters from a `TranslationRequest`.

| Parameter | Type | Description |
|-----------|------|-------------|
| `request` | `TranslationRequest` | Source translation request. |

**Returns**
- `Dict[str, Any]` — A dictionary with two keys:
  - `"params"` — Query parameters for the API URL.
  - `"body"` — JSON body array containing the text and optional context.

**Request Mapping**

| `TranslationRequest` Field | API Mapping |
|----------------------------|-------------|
| `text` | `body[0]["text"]` |
| `target_lang` | `params["to"]` |
| `source_lang` | `params["from"]` (optional) |
| `formality` | `params["formality"]` → `"informal"` or `"formal"` |
| `html_format` | `params["textType"]` → `"html"` or `"plain"` |
| `domain` | Appended to `"context"` string |
| `screen` | Appended to `"context"` string |
| `component` | Appended to `"context"` string |
| `context_type` | Appended to `"context"` string |
| `key` | Appended to `"context"` string |

**Context Format**
```
"Domain: X | Screen: Y | Component: Z | Type: A | Key: B"
```
Only non-empty metadata fields are included.

---

#### `_call_api()`

```python
def _call_api(
    self,
    payload: Dict[str, Any],
    request: TranslationRequest
) -> str
```

Internal method that executes the HTTP request against the Microsoft Translator API, validates the response, and applies security checks.

| Parameter | Type | Description |
|-----------|------|-------------|
| `payload` | `Dict[str, Any]` | Output from `build_request()`. |
| `request` | `TranslationRequest` | Original request (used for security comparisons). |

**Returns**
- `str` — The validated translated text.

**HTTP Headers Sent**

| Header | Value |
|--------|-------|
| `Ocp-Apim-Subscription-Key` | `{api_key}` |
| `Content-Type` | `application/json` |
| `User-Agent` | `SHL-Client/{SHL_VERSION}` |
| `Accept` | `application/json` |

---

## Security Checks

After receiving a successful API response, the adapter performs the following validations. If any check fails, a `TranslationError` is raised.

| # | Check | Condition | Error Message |
|---|-------|-----------|---------------|
| 1 | Empty output | `translated.strip() == ""` | `"Microsoft Translator returned empty text."` |
| 2 | Unchanged text | `translated.strip() == request.text.strip()` | `"Microsoft Translator returned unchanged text."` |
| 3 | Unexpected HTML | `html_format=False` and `<` and `>` present in output | `"Microsoft Translator returned unexpected HTML markup."` |
| 4 | Suspiciously short | `len(translated) < 3` and `len(request.text) > 20` | `"Microsoft Translator returned suspiciously short output."` |

---

## Error Handling

### HTTP Status Code Mapping

| Status Code | Exception Raised | Description |
|-------------|------------------|-------------|
| `401`, `403` | `ProviderAccessError` | Invalid or unauthorized API key. |
| `429` | `RateLimitExceededError` | Rate limit exceeded. |
| `500`, `502`, `503`, `504` | `ServiceUnavailableError` | Remote endpoint or gateway issue. Service is marked unavailable in the registry. |
| `400` | `InvalidRequestError` | Invalid request configuration. |
| `409`, `413`, `415`, `422` | `InvalidRequestError` | Request payload or configuration not acceptable. |
| Other | `TranslationError` | Unrecognized HTTP error. |

### Network & Timeout Errors

| Error Type | Exception Raised | Side Effect |
|------------|------------------|-------------|
| `socket.timeout`, `TimeoutError` | `ServiceUnavailableError` | Service marked unavailable via registry. |
| `URLError` (other) | `ServiceUnavailableError` | Service marked unavailable via registry. |

### Fallback Behavior

Any unexpected non-HTTP exception is caught, the service is marked unavailable, and a `TranslationError` is raised with the original exception type and message. Already-typed SHL exceptions are re-raised as-is.

---

## Service Availability Registry

The adapter uses `MicrosoftServiceRegistry` to track whether the Microsoft Translator service is currently reachable.

- **Check:** `registry.is_available()` is called at the start of every `translate()` call.
- **Mark Unavailable:** `registry.mark_unavailable()` is called on:
  - HTTP 500/502/503/504
  - Network timeouts
  - Socket/URL errors
  - Unexpected execution failures
- **TTL:** Configurable via `MS_TRANSLATOR_TTL` environment variable (default: 600 seconds).

---

## Usage Example

```python
from shl.providers.microsoft_translator import MicrosoftTranslatorAdapter
from shl.metadata import TranslationRequest

# Initialize with API key from environment
adapter = MicrosoftTranslatorAdapter()

# Build a translation request
request = TranslationRequest(
    text="Hello, world!",
    source_lang="en",
    target_lang="fi",
    formality="formal",
    html_format=False,
    domain="user_dashboard",
    screen="settings",
    component="greeting_label",
    key="welcome_msg"
)

# Translate
try:
    result = adapter.translate(request)
    print(result)  # "Hei, maailma!"
except ServiceUnavailableError:
    print("Service temporarily unavailable")
except ProviderAccessError:
    print("Invalid API key")
except RateLimitExceededError:
    print("Rate limit exceeded")
except TranslationError as e:
    print(f"Translation failed: {e}")
```

---

## Logging

The module uses Python's standard `logging` module under the logger name `__name__`.

**Log Levels Used**

| Level | Event |
|-------|-------|
| `DEBUG` | Adapter initialization (masked API key, TTL) |
| `DEBUG` | Outgoing request URL, text length |
| `DEBUG` | Successful translation completion |

---

## Thread Safety

The adapter itself does not maintain mutable per-request state beyond the `MicrosoftServiceRegistry`. Thread safety depends on the registry implementation. The `urllib` request path is stateless per call.

---

## Changelog

| Version | Notes |
|---------|-------|
| 0.2.5 | Current — includes context metadata, formality, HTML handling, TTL registry, and security checks. |
