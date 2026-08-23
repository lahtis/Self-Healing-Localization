# LibreTranslateAdapter API Documentation

## Overview

`LibreTranslateAdapter` is a translation provider adapter for the **LibreTranslate API**. It is dependency-free and uses only Python's standard library (`urllib`). The adapter supports configurable base URLs, API key authentication, runtime language pair validation via a registry, mirror management for failover, and comprehensive error mapping to SHL exception types.

---

## Module Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `LIBRETRANSLATE_TIMEOUT` | `15` | HTTP request timeout in seconds for translation calls. |
| `LIBRETRANSLATE_LANGUAGES_TIMEOUT` | `10` | HTTP request timeout in seconds for the `/languages` endpoint. |
| `LIBRETRANSLATE_DEFAULT_URL` | `"https://libretranslate.com"` | Default base URL for the LibreTranslate API. |
| `LIBRETRANSLATE_DEFAULT_API_KEY` | `""` | Default API key (empty string). |

---

## Function: `get_supported_languages`

```python
def get_supported_languages(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: float = LIBRETRANSLATE_LANGUAGES_TIMEOUT,
) -> List[Dict[str, Any]]
```

Fetch supported languages from the LibreTranslate `/languages` endpoint.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_url` | `Optional[str]` | `None` | Base URL of the LibreTranslate instance. Falls back to `LIBRETRANSLATE_URL` environment variable, then `LIBRETRANSLATE_DEFAULT_URL`. |
| `api_key` | `Optional[str]` | `None` | API key for authentication. Falls back to `LIBRETRANSLATE_API_KEY` environment variable, then `LIBRETRANSLATE_DEFAULT_API_KEY`. |
| `timeout` | `float` | `LIBRETRANSLATE_LANGUAGES_TIMEOUT` | Request timeout in seconds. |

### Behavior

- Loads environment variables via `load_shl_env()` if not already loaded.
- Resolves `base_url` and `api_key` using the parameter → environment variable → default fallback chain.
- Strips trailing slashes from `base_url`.
- Constructs the URL as `{resolved_base_url}/languages`.
- Appends `api_key` as a query parameter if `resolved_api_key` is truthy.
- Sends a `GET` request with headers `Accept: application/json` and `User-Agent: SHL/{SHL_VERSION}`.

### Returns

- `List[Dict[str, Any]]` — The JSON list returned by the `/languages` endpoint.

### Raises

- `ProviderAccessError` — On HTTP 401 or 403.
- `RateLimitExceededError` — On HTTP 429.
- `ServiceUnavailableError` — On HTTP 5xx, `URLError` with timeout, or `socket.timeout` / `TimeoutError`.
- `TranslationError` — On other HTTP errors, invalid JSON response, or unexpected response format (non-list).

---

## Class: `LibreTranslateAdapter`

Inherits from `TranslationProvider`.

### Constructor

```python
LibreTranslateAdapter(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    cache_ttl: float = 86400.0,
    mirror_manager: Optional[Any] = None,
    mirrors: Optional[List[Dict[str, Any]]] = None,
)
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_url` | `Optional[str]` | `None` | Base URL of the LibreTranslate instance. Falls back to `LIBRETRANSLATE_URL` env, then `LIBRETRANSLATE_DEFAULT_URL`. |
| `api_key` | `Optional[str]` | `None` | API key for authentication. Falls back to `LIBRETRANSLATE_API_KEY` env, then `LIBRETRANSLATE_DEFAULT_API_KEY`. |
| `cache_ttl` | `float` | `86400.0` | Time-to-live in seconds for the language pair registry cache. |
| `mirror_manager` | `Optional[Any]` | `None` | An optional mirror manager instance. If provided, it is used directly. |
| `mirrors` | `Optional[List[Dict[str, Any]]]` | `None` | A list of mirror configurations. Used only if `mirror_manager` is `None`; triggers lazy import and construction of `LibreTranslateMirrorManager`. |

#### Behavior

- Loads environment variables via `load_shl_env()` if not already loaded.
- Resolves `base_url` and `api_key` using the parameter → environment variable → default fallback chain.
- Strips trailing slashes from `base_url`.
- Initializes a `LibreTranslateRegistry` with the given `cache_ttl`.
- If `mirror_manager` is `None` and `mirrors` is not `None`, lazily imports `LibreTranslateMirrorManager` from `.libretranslate_mirrors` and constructs it with the provided `mirrors`.
- Logs a debug message with the resolved `base_url` and masked `api_key`.

---

### Properties

#### `name`

```python
@property
def name(self) -> str
```

Returns the provider identifier string: `"libretranslate"`.

#### `supported_features`

```python
@property
def supported_features(self) -> List[str]
```

Returns a list of supported features. Currently returns an empty list `[]`.

---

### Methods

#### `supports_feature(feature: str) -> bool`

Checks whether a given feature is supported.

##### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `feature` | `str` | The feature name to check. |

##### Returns

- `bool` — `True` if the lowercased feature name is in `supported_features`; `False` otherwise.

---

#### `translate(request: TranslationRequest) -> str`

Translates text using the LibreTranslate API.

##### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `request` | `TranslationRequest` | A request object containing the text to translate, source and target languages, and formatting options. |

##### Behavior

1. Checks if the language pair `(source_lang, target_lang)` is supported via `self.registry.is_pair_supported()`.
   - If not supported, raises `LanguageNotSupportedError` immediately.
2. Builds the request payload via `build_request()`.
3. Calls `_call_api()` with the payload.
4. If `_call_api()` raises `LanguageNotSupportedError`, marks the pair as unsupported in the registry via `mark_pair_unsupported()` and re-raises the exception.

##### Returns

- `str` — The translated text.

##### Raises

- `LanguageNotSupportedError` — If the pair is not supported by the registry or returned by the API.
- `ProviderAccessError` — On HTTP 403.
- `RateLimitExceededError` — On HTTP 429.
- `ServiceUnavailableError` — On HTTP 5xx, empty/unmodified response, or network/timeout errors.
- `InvalidRequestError` — On HTTP 400 (when the error body does not contain "language").
- `TranslationError` — On HTTP errors not otherwise mapped, invalid JSON, or unexpected execution failures.

---

#### `build_request(request: TranslationRequest) -> Dict[str, Any]`

Builds the JSON payload for the LibreTranslate `/translate` endpoint.

##### Payload Structure

```json
{
  "q": "text to translate",
  "source": "source_language_code",
  "target": "target_language_code",
  "format": "text",
  "api_key": "optional_api_key"
}
```

- `q`, `source`, and `target` are taken directly from `request`.
- `format` is always `"text"`.
- `api_key` is included only if `self.api_key` is truthy.

---

#### `_get_translation_base_url() -> str`

Resolves the URL used for translation. This is an internal method.

##### Behavior

- If `self.mirror_manager` is not `None`, calls `get_best_mirror()` on it.
  - If the returned mirror is not `None` and has a truthy `url` attribute, returns `mirror.url` with trailing slashes stripped.
- Falls back to `self.base_url`.

##### Returns

- `str` — The resolved base URL for the translation request.

---

#### `_call_api(payload: Dict[str, Any]) -> str`

Calls the LibreTranslate `/translate` endpoint. This is an internal method.

##### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `payload` | `Dict[str, Any]` | The JSON payload built by `build_request()`. |

##### Behavior

1. Extracts `source` and `target` from the payload.
2. Resolves the base URL via `_get_translation_base_url()`.
3. Sends a `POST` request to `{base_url}/translate` with:
   - `Content-Type: application/json`
   - `User-Agent: SHL/{SHL_VERSION}`
   - `Accept: application/json`
4. Parses the JSON response and extracts `translatedText`.
5. Validates the translation:
   - Must be a `str`.
   - Must be truthy (non-empty).
   - Must not equal the original `q` value.
   - If valid, logs a debug message with the first 100 characters and returns the text.
   - If invalid, raises `ServiceUnavailableError` with message "LibreTranslate returned empty or unmodified text".

##### Error Mapping

| Condition | Raised Exception |
|-----------|------------------|
| HTTP 403 | `ProviderAccessError` — "invalid or banned API key" |
| HTTP 429 | `RateLimitExceededError` |
| HTTP >= 500 | `ServiceUnavailableError` |
| HTTP 404 | `LanguageNotSupportedError` |
| HTTP 400 + "language" in error body (case-insensitive) | `LanguageNotSupportedError` |
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

- `json`
- `logging`
- `os`
- `socket`
- `typing` (`Any`, `Dict`, `List`, `Optional`)
- `urllib.error` (`HTTPError`, `URLError`)
- `urllib.parse` (`urlencode`)
- `urllib.request` (`Request`, `urlopen`)

### SHL Internal Modules

- `shl._version.__version__` (as `SHL_VERSION`)
- `shl.utils.env_loader.load_shl_env`
- `shl.utils.env_loader.mask_api_key`
- `shl.exceptions`:
  - `InvalidRequestError`
  - `LanguageNotSupportedError`
  - `ProviderAccessError`
  - `RateLimitExceededError`
  - `ServiceUnavailableError`
  - `TranslationError`
- `shl.metadata.TranslationRequest`
- `shl.providers.base.TranslationProvider`
- `.libretranslate_registry.LibreTranslateRegistry`
- `.libretranslate_mirrors.LibreTranslateMirrorManager` (lazy import)

---

## Usage Example

```python
from shl.providers.libretranslate import LibreTranslateAdapter, get_supported_languages
from shl.metadata import TranslationRequest

# Initialize adapter
adapter = LibreTranslateAdapter(
    base_url="https://libretranslate.com",
    api_key="your-api-key",
)

# Fetch supported languages
langs = get_supported_languages()
print(langs)

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
except ProviderAccessError:
    print("API key invalid or banned.")
except RateLimitExceededError:
    print("Rate limit exceeded.")
except ServiceUnavailableError:
    print("Service temporarily unavailable.")
except TranslationError as e:
    print(f"Translation failed: {e}")
```

---

## Mirror Management

The adapter supports optional mirror management for failover:

- If `mirror_manager` is provided during initialization, it is used directly.
- If `mirror_manager` is `None` and `mirrors` is provided, the adapter lazily imports `LibreTranslateMirrorManager` and constructs it with the given mirror list.
- During translation, `_get_translation_base_url()` queries the mirror manager for the best available mirror before falling back to the configured `base_url`.

---

## Response Validation

The adapter performs the following validations on the `translatedText` field returned by the API:

1. **Type check** — Must be a `str`.
2. **Non-empty** — Must be truthy (not empty or `None`).
3. **Modified** — Must not equal the original input text (`payload["q"]`).

If any check fails, a `ServiceUnavailableError` is raised.

---

## License

MIT

## Author

Tuomas Lähteenmäki
