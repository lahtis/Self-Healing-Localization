# DeepL Translation Adapter — API Documentation

## Module Overview

**File:** `deepl.py`

A robust translation provider adapter for the DeepL API (v2). Implements the `TranslationProvider` interface with support for context matching, formality adjustment, glossary mapping, a runtime language pair registry, and security checks for suspicious output. Automatically detects Free vs Pro API endpoints based on the API key suffix.

---

## Metadata

| Attribute | Value |
|-----------|-------|
| Author | Tuomas Lähteenmäki |
| Version | 0.2.4 |
| License | MIT |
| Provider Name | `deepl` |

---

## Module Constants

| Name | Type | Value | Description |
|------|------|-------|-------------|
| `DEEPL_TIMEOUT` | `int` | `15` | Network timeout in seconds for all API requests. |

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
- `..exceptions.LanguageNotSupportedError`
- `..exceptions.ProviderAccessError`
- `..exceptions.InvalidRequestError`
- `..metadata.TranslationRequest`
- `.base.TranslationProvider`
- `.deepl_registry.DeepLRegistry`

---

## Class: `DeepLAdapter`

```python
class DeepLAdapter(TranslationProvider)
```

DeepL API v2 adapter. Handles text translation with optional context, formality, glossary, and HTML tag handling. Includes built-in security validation and a runtime language pair registry.

### Supported Features

| Feature | Description |
|---------|-------------|
| `formality` | Adjusts translation tone (`formal` → `more`, `informal` → `less`). |
| `context` | Injects SHL metadata (domain, screen, component, type, key) into the translation request. |
| `glossary` | Uses a DeepL glossary ID for terminology consistency. |
| `html_format` | Switches to HTML tag handling mode. |

---

### Constructor

```python
def __init__(self, api_key: Optional[str] = None) -> None
```

Initializes the adapter, loads environment variables, auto-detects the API tier (Free vs Pro), and sets up the language pair registry.

| Parameter | Type | Description |
|-----------|------|-------------|
| `api_key` | `Optional[str]` | Direct API key. If omitted, falls back to the `DEEPL_API_KEY` environment variable. |

**Raises**
- `ValueError` — If no API key is provided either as argument or via environment variable.

**Environment Variables**

| Variable | Description |
|----------|-------------|
| `DEEPL_API_KEY` | DeepL API authentication key. |

**Endpoint Auto-Detection**

| API Key Suffix | Endpoint | Description |
|----------------|----------|-------------|
| Ends with `:fx` | `https://api-free.deepl.com/v2` | DeepL Free API. |
| Any other suffix | `https://api.deepl.com/v2` | DeepL Pro API. |

**Behavior**
1. Loads `.env` from `./env/shl/` via `load_shl_env()`.
2. Resolves the API key (parameter → env var).
3. Strips whitespace from the key.
4. Auto-detects Free vs Pro endpoint based on key suffix.
5. Initializes `DeepLRegistry` for runtime language pair validation.

---

### Properties

#### `name`
```python
@property
def name(self) -> str
```
Returns the provider identifier string.

**Returns:** `"deepl"`

---

#### `supported_features`
```python
@property
def supported_features(self) -> list
```
Returns the list of features supported by this adapter.

**Returns:** `["formality", "context", "glossary", "html_format"]`

---

### Methods

#### `translate()`

```python
def translate(self, request: TranslationRequest) -> str
```

Main entry point for translation. Validates the language pair against the registry, builds the request payload, and calls the DeepL API.

| Parameter | Type | Description |
|-----------|------|-------------|
| `request` | `TranslationRequest` | Translation request object containing text, languages, and metadata. |

**Returns**
- `str` — The translated text.

**Raises**
- `LanguageNotSupportedError` — If the language pair is not in the registry's supported set.
- `TranslationError` — If the API returns an empty, invalid, or suspicious response.
- `ProviderAccessError` — If the API key is invalid or unauthorized (HTTP 401/403/402).
- `RateLimitExceededError` — If rate limit (HTTP 429) or quota (HTTP 456) is exceeded.
- `InvalidRequestError` — If the request payload or configuration is invalid (HTTP 400, 409, 413, 415, 422).
- `ServiceUnavailableError` — On server/gateway errors or network timeouts.

---

#### `build_request()`

```python
def build_request(self, request: TranslationRequest) -> Dict[str, Any]
```

Constructs the DeepL API JSON payload from a `TranslationRequest`.

| Parameter | Type | Description |
|-----------|------|-------------|
| `request` | `TranslationRequest` | Source translation request. |

**Returns**
- `Dict[str, Any]` — JSON-serializable payload dictionary for the DeepL `/translate` endpoint.

**Payload Structure**

| Field | Source | Description |
|-------|--------|-------------|
| `text` | `[request.text]` | Array containing the text to translate (DeepL requires an array). |
| `target_lang` | `request.target_lang.upper()` | Target language code (uppercase). |
| `source_lang` | `request.source_lang.upper()` (optional) | Source language code (uppercase). |
| `context` | Concatenated metadata (optional) | `"Domain: X | Screen: Y | Component: Z | Type: A | Key: B"` |
| `formality` | `request.formality` (optional) | `"less"` if `informal`, `"more"` otherwise. |
| `glossary_id` | `request.glossary["id"]` (optional) | DeepL glossary identifier. |
| `tag_handling` | `"html"` (optional) | Set if `request.html_format=True`. |

**Context Format**
```
"Domain: X | Screen: Y | Component: Z | Type: A | Key: B"
```
Only non-empty metadata fields are included.

**Formality Mapping**

| `request.formality` | DeepL Value |
|---------------------|-------------|
| `"informal"` | `"less"` |
| Any other value (e.g., `"formal"`) | `"more"` |

---

#### `_call_api()`

```python
def _call_api(
    self,
    payload: Dict[str, Any],
    request: TranslationRequest
) -> str
```

Internal method that executes the HTTP POST request to the DeepL API, validates the response, and applies security checks.

| Parameter | Type | Description |
|-----------|------|-------------|
| `payload` | `Dict[str, Any]` | Output from `build_request()`. |
| `request` | `TranslationRequest` | Original request (used for security comparisons). |

**Returns**
- `str` — The validated translated text.

**HTTP Headers Sent**

| Header | Value |
|--------|-------|
| `Authorization` | `DeepL-Auth-Key {api_key}` |
| `Content-Type` | `application/json` |
| `User-Agent` | `SHL-Client/{SHL_VERSION}` |
| `Accept` | `application/json` |

**Expected Response Structure**
```json
{
  "translations": [
    {
      "text": "...",
      "detected_source_language": "EN"
    }
  ]
}
```

---

## Security Checks

After receiving a successful API response, the adapter performs the following validations. If any check fails, a `TranslationError` is raised.

| # | Check | Condition | Error Message |
|---|-------|-----------|---------------|
| 1 | Empty output | `not translated` or `translated.strip() == ""` | `"DeepL returned empty text."` |
| 2 | Unchanged text | `translated.strip() == payload["text"][0].strip()` | `"DeepL returned unchanged text."` |
| 3 | Unexpected source language | `detected != request.source_lang.lower()` | `"DeepL detected unexpected source language '{detected}'..."` |
| 4 | Unexpected HTML | `html_format=False` and `<` and `>` present in output | `"DeepL returned unexpected HTML markup."` |
| 5 | Suspiciously short | `len(translated) < 3` and `len(source_text) > 20` | `"DeepL returned suspiciously short output."` |

---

## Error Handling

### HTTP Status Code Mapping

| Status Code | Exception Raised | Description |
|-------------|------------------|-------------|
| `401`, `403` | `ProviderAccessError` | Invalid or unauthorized API token. |
| `402` | `ProviderAccessError` | Billing issue or payment required. |
| `408` | `ServiceUnavailableError` | Request timeout. |
| `429` | `RateLimitExceededError` | Maximum burst request cadence exceeded. |
| `456` | `RateLimitExceededError` | Periodic character quota limit reached. |
| `500`, `502`, `503`, `504` | `ServiceUnavailableError` | Remote endpoint or gateway issue. |
| `400` | `InvalidRequestError` | Invalid request configuration. Pair may be marked unsupported in registry. |
| `409`, `413`, `415`, `422` | `InvalidRequestError` | Request payload or configuration not acceptable. Pair may be marked unsupported. |
| Other | `TranslationError` | Unrecognized HTTP error. |

### Network & Timeout Errors

| Error Type | Exception Raised | Description |
|------------|------------------|-------------|
| `socket.timeout`, `TimeoutError` | `ServiceUnavailableError` | Connection or network timeout. |
| `URLError` (other) | `ServiceUnavailableError` | Socket pipeline failure. |

### Fallback Behavior

Any unexpected non-HTTP exception is caught. Already-typed SHL exceptions are re-raised as-is. All other exceptions are wrapped in a `TranslationError` with the original exception type and message.

---

## Usage Example

```python
from shl.providers.deepl import DeepLAdapter
from shl.metadata import TranslationRequest

# Initialize with API key from environment
adapter = DeepLAdapter()

# Or with explicit key
adapter = DeepLAdapter(api_key="your-deepl-key")

# Build a translation request
request = TranslationRequest(
    text="Welcome to our application!",
    source_lang="en",
    target_lang="de",
    formality="formal",
    domain="user_dashboard",
    screen="settings",
    component="greeting_label",
    key="welcome_msg",
    glossary={"id": "your-glossary-id"},
)

# Translate
try:
    result = adapter.translate(request)
    print(result)  # "Willkommen in unserer Anwendung!"
except LanguageNotSupportedError:
    print("Language pair not supported by DeepL")
except ProviderAccessError:
    print("Invalid API key or billing issue")
except RateLimitExceededError:
    print("Quota or rate limit exceeded")
except TranslationError as e:
    print(f"Translation failed: {e}")
```

---

## Logging

The module uses Python's standard `logging` module under the logger name `__name__`.

**Log Levels Used**

| Level | Event |
|-------|-------|
| `DEBUG` | Adapter initialization (masked API key, endpoint), outgoing request URL and text length, successful translation. |

---

## Thread Safety

The adapter itself does not maintain mutable per-request state beyond the `DeepLRegistry`. Thread safety depends on the registry implementation. The `urllib` request path is stateless per call.

---

## Changelog

| Version | Notes |
|---------|-------|
| 0.2.4 | Current — DeepL Free/Pro auto-detection, context metadata, formality mapping, glossary support, registry validation, and security checks. |
