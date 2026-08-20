# Papago Translation Adapter — API Documentation

## Module Overview

**File:** `papago.py`

A robust translation provider adapter for the Naver Papago API. Handles language pair validation, honorific support, glossary mapping, a runtime registry for unsupported pairs, and security checks for suspicious output.

---

## Metadata

| Attribute | Value |
|-----------|-------|
| Author | Tuomas Lähteenmäki |
| Version | 0.2.4 |
| License | MIT |
| Provider Name | `papago` |

---

## Module Constants

| Name | Type | Value | Description |
|------|------|-------|-------------|
| `PAPAGO_TIMEOUT` | `int` | `15` | Network timeout in seconds for all API requests. |
| `PAPAGO_ENDPOINT` | `str` | `"https://papago.apigw.ntruss.com/nmt/v1/translation"` | Base URL for the Papago NMT v1 translation endpoint. |

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

---

## Class: `PapagoRegistry`

```python
class PapagoRegistry
```

Lightweight runtime registry for supported Papago language pairs. Maintains a static set of officially supported bidirectional pairs and a dynamic set of pairs that have been empirically confirmed as unsupported (e.g., via HTTP 400 responses).

### Supported Language Pairs

The registry defines the following officially supported pairs. All listed pairs are bidirectional.

| Source | Targets |
|--------|---------|
| `ko` (Korean) | `en`, `ja`, `zh-cn`, `zh-tw`, `vi`, `th`, `id`, `fr`, `es`, `ru`, `de`, `it` |
| `en` (English) | `ja`, `zh-cn`, `zh-tw`, `vi`, `th`, `id`, `fr`, `es`, `ru`, `de` |
| `ja` (Japanese) | `zh-cn`, `zh-tw`, `vi`, `th`, `id`, `fr` |
| `zh-cn` (Simplified Chinese) | `zh-tw` |

**Language Code Aliases**

| Alias | Normalized To |
|-------|---------------|
| `zh` | `zh-cn` |
| `zh-hans` | `zh-cn` |
| `zh-hant` | `zh-tw` |
| `jp` | `ja` |
| `kr` | `ko` |

---

### Constructor

```python
def __init__(self) -> None
```

Initializes the registry with an empty dynamic unsupported-pair cache.

**Attributes**

| Attribute | Type | Description |
|-----------|------|-------------|
| `_unsupported` | `set` | Runtime cache of language pairs confirmed unsupported by the API. |

---

### Methods

#### `_normalize()`

```python
def _normalize(self, lang: str) -> str
```

Normalizes a language code to Papago's canonical form.

| Parameter | Type | Description |
|-----------|------|-------------|
| `lang` | `str` | Raw language code string. |

**Returns**
- `str` — Normalized language code, or empty string if input is falsy.

**Normalization Steps**
1. Lowercase.
2. Replace underscores with hyphens.
3. Map known aliases to canonical codes.

---

#### `is_pair_supported()`

```python
def is_pair_supported(self, source: str, target: str) -> bool
```

Checks whether a language pair is supported by Papago.

| Parameter | Type | Description |
|-----------|------|-------------|
| `source` | `str` | Source language code. |
| `target` | `str` | Target language code. |

**Returns**
- `bool` — `True` if the pair is supported or if source is `"auto"` / empty. `False` if the pair is in the unsupported cache or not in the official supported set.

**Logic**
- If `source` is empty or `"auto"`, returns `True` (auto-detect allowed).
- If the normalized pair exists in `_unsupported`, returns `False`.
- If the normalized pair exists in `SUPPORTED_PAIRS`, returns `True`.
- Otherwise, returns `False`.

---

#### `mark_pair_unsupported()`

```python
def mark_pair_unsupported(self, source: str, target: str) -> None
```

Adds a language pair to the runtime unsupported cache. Typically called after receiving an HTTP 400 from the Papago API.

| Parameter | Type | Description |
|-----------|------|-------------|
| `source` | `str` | Source language code. |
| `target` | `str` | Target language code. |

**Side Effects**
- Adds the normalized pair to `_unsupported`.

---

## Class: `PapagoAdapter`

```python
class PapagoAdapter(TranslationProvider)
```

Papago (Naver Cloud) translation provider adapter. Implements the `TranslationProvider` interface with support for honorifics, glossary keys, and language pair validation.

### Supported Features

| Feature | Description |
|---------|-------------|
| `honorific` | Controls honorific level in Korean and other supported languages. |
| `glossary` | Uses a `glossaryKey` for terminology consistency. |
| `formality` | DeepL-style formality mapped to honorific behavior for compatibility. |

---

### Constructor

```python
def __init__(
    self,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
) -> None
```

Initializes the adapter with Papago API credentials.

| Parameter | Type | Description |
|-----------|------|-------------|
| `client_id` | `Optional[str]` | Naver Cloud Platform client ID. Falls back to `NAVER_CLIENT_ID` env var. |
| `client_secret` | `Optional[str]` | Naver Cloud Platform client secret. Falls back to `NAVER_CLIENT_SECRET` env var. |

**Raises**
- `ValueError` — If neither parameter nor environment variable provides both `client_id` and `client_secret`.

**Environment Variables**

| Variable | Description |
|----------|-------------|
| `NAVER_CLIENT_ID` | Naver Cloud Platform API client ID. |
| `NAVER_CLIENT_SECRET` | Naver Cloud Platform API client secret. |

**Behavior**
1. Loads `.env` from `./env/shl/` via `load_shl_env()`.
2. Resolves credentials (parameter → env var).
3. Strips whitespace from both credentials.
4. Sets `base_url` to `PAPAGO_ENDPOINT`.
5. Initializes `PapagoRegistry`.

---

### Properties

#### `name`
```python
@property
def name(self) -> str
```
Returns the provider identifier.

**Returns:** `"papago"`

---

#### `supported_features`
```python
@property
def supported_features(self) -> list
```
Returns the list of supported non-standard features.

**Returns:** `["honorific", "glossary", "formality"]`

---

### Methods

#### `translate()`

```python
def translate(self, request: TranslationRequest) -> str
```

Main entry point for translation. Validates the language pair, builds the request, and calls the Papago API.

| Parameter | Type | Description |
|-----------|------|-------------|
| `request` | `TranslationRequest` | Translation request with text, languages, and metadata. |

**Returns**
- `str` — The translated text.

**Raises**
- `LanguageNotSupportedError` — If the language pair is not in the registry's supported set.
- `TranslationError` — If the response is empty, unchanged, or fails security checks.
- `ProviderAccessError` — If credentials are invalid (HTTP 401/403).
- `RateLimitExceededError` — If rate limit is exceeded (HTTP 429).
- `InvalidRequestError` — If request parameters are invalid (HTTP 400).
- `ServiceUnavailableError` — On server/gateway errors or network timeouts.

---

#### `build_request()`

```python
def build_request(self, request: TranslationRequest) -> Dict[str, Any]
```

Constructs the Papago API JSON payload from a `TranslationRequest`.

| Parameter | Type | Description |
|-----------|------|-------------|
| `request` | `TranslationRequest` | Source translation request. |

**Returns**
- `Dict[str, Any]` — JSON-serializable payload dictionary.

**Payload Structure**

| Field | Source | Description |
|-------|--------|-------------|
| `source` | `request.source_lang` (normalized, defaults to `"auto"`) | Source language code. |
| `target` | `request.target_lang` (normalized) | Target language code. |
| `text` | `request.text` | Text to translate. |
| `honorific` | `request.honorific` or `request.formality` | `"true"` or `"false"` (optional). |
| `glossaryKey` | `request.glossary["id"]` | Glossary identifier (optional). |

**Honorific Resolution Priority**

1. **`request.honorific`** (direct field, recommended)
   - `bool` → `"true"` / `"false"`
   - `str` → mapped: `("true", "1", "yes", "formal", "more", "polite", "honorific")` → `"true"`, anything else → `"false"`

2. **Fallback to `request.formality`** (DeepL compatibility)
   - `("formal", "more", "honorific", "polite")` → `"true"`
   - `("informal", "less", "casual")` → `"false"`

---

#### `_call_api()`

```python
def _call_api(
    self,
    payload: Dict[str, Any],
    request: TranslationRequest
) -> str
```

Executes the HTTP POST request to the Papago API and validates the response.

| Parameter | Type | Description |
|-----------|------|-------------|
| `payload` | `Dict[str, Any]` | Output from `build_request()`. |
| `request` | `TranslationRequest` | Original request for security comparisons. |

**HTTP Headers Sent**

| Header | Value |
|--------|-------|
| `X-NCP-APIGW-API-KEY-ID` | `{client_id}` |
| `X-NCP-APIGW-API-KEY` | `{client_secret}` |
| `Content-Type` | `application/json` |
| `User-Agent` | `SHL-Client/{SHL_VERSION}` |
| `Accept` | `application/json` |

**Expected Response Structure**
```json
{
  "message": {
    "result": {
      "translatedText": "...",
      "srcLangType": "en"
    }
  }
}
```

---

## Security Checks

After a successful API response, the adapter applies the following validations:

| # | Check | Condition | Error Message |
|---|-------|-----------|---------------|
| 1 | Empty output | `translated.strip() == ""` | `"Papago returned empty text."` |
| 2 | Unchanged text | `translated.strip() == payload["text"].strip()` | `"Papago returned unchanged text."` |
| 3 | Detected language mismatch | `source_lang != "auto"` and `detected != expected` | Warning logged (non-fatal). |
| 4 | Unexpected HTML | `html_format=False` and `<` and `>` present | `"Papago returned unexpected HTML markup."` |
| 5 | Suspiciously short | `len(translated) < 3` and `len(payload["text"]) > 20` | `"Papago returned suspiciously short output."` |

---

## Error Handling

### HTTP Status Code Mapping

| Status Code | Exception Raised | Side Effect | Description |
|-------------|------------------|-------------|-------------|
| `401`, `403` | `ProviderAccessError` | — | Invalid or unauthorized API credentials. |
| `429` | `RateLimitExceededError` | — | Rate limit or quota exceeded. |
| `400` | `InvalidRequestError` | Pair marked unsupported in registry | Invalid request parameters. |
| `500`, `502`, `503`, `504` | `ServiceUnavailableError` | — | Remote endpoint or gateway issue. |
| Other | `TranslationError` | — | Unrecognized HTTP error. |

### Network & Timeout Errors

| Error Type | Exception Raised | Description |
|------------|------------------|-------------|
| `socket.timeout`, `TimeoutError` | `ServiceUnavailableError` | Connection or network timeout. |
| `URLError` (other) | `ServiceUnavailableError` | Socket pipeline failure. |

### Fallback Behavior

Any unexpected non-HTTP exception is caught and wrapped in a `TranslationError` with the original exception type and message. Already-typed SHL exceptions are re-raised as-is.

---

## Usage Example

```python
from shl.providers.papago import PapagoAdapter
from shl.metadata import TranslationRequest

# Initialize with credentials from environment
adapter = PapagoAdapter()

# Build a translation request
request = TranslationRequest(
    text="Hello, how are you?",
    source_lang="en",
    target_lang="ko",
    honorific=True,
    glossary={"id": "my-glossary-key"},
)

# Translate
try:
    result = adapter.translate(request)
    print(result)  # "안녕하세요, 어떻게 지내세요?"
except LanguageNotSupportedError:
    print("Language pair not supported by Papago")
except ProviderAccessError:
    print("Invalid API credentials")
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
| `DEBUG` | Adapter initialization (masked client_id) |
| `DEBUG` | Outgoing request URL and text length |
| `DEBUG` | Successful translation completion |
| `WARNING` | Detected source language differs from declared source language |

---

## Thread Safety

`PapagoAdapter` maintains instance state (`client_id`, `client_secret`, `registry`). The `PapagoRegistry._unsupported` set is mutated at runtime when HTTP 400 errors occur. Concurrent access to the same adapter instance across threads may cause race conditions on the registry. Consider using one adapter instance per thread or adding external locking for shared instances.

---

## Changelog

| Version | Notes |
|---------|-------|
| 0.2.4 | Current — honorific/formality mapping, glossary support, language pair registry, security checks. |
