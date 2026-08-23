# Router API Documentation

## Overview

`router.py` provides policy-aware routing for the SHL translation ecosystem. It manages provider priority selection, translation execution with retry logic, caching, timeout handling, and runtime blacklist management across multiple translation providers.

---

## Module Metadata

| Field | Value |
|-------|-------|
| **File** | `router.py` |
| **Author** | Tuomas Lähteenmäki |
| **Version** | `0.2.5-casefix` |
| **License** | MIT |

---

## Dependencies and Imports

### Standard Library

- `time`
- `logging`
- `typing` (`Optional`, `List`, `Dict`, `Any`)

### SHL Internal Modules

- `.provider_cache.load_cache`
- `.cache.TranslationCache`
- `.metadata.TranslationRequest`, `.metadata.TranslationResult`
- `.exceptions.TranslationError`, `.exceptions.ServiceUnavailableError`, `.exceptions.LanguageNotSupportedError`, `.exceptions.RateLimitExceededError`
- `.providers.microsoft.MicrosoftTranslatorAdapter`
- `.providers.mymemory.MyMemoryAdapter`
- `.providers.libretranslate.LibreTranslateAdapter`
- `.providers.libretranslate_mirrors.LibreTranslateMirrorManager`
- `.providers.libretranslate_registry.LibreTranslateRegistry`
- `.providers.deepl.DeepLAdapter`
- `.providers.googlev2.GoogleV2Adapter`
- `.providers.google_registry.GoogleRegistry`
- `.providers.papago.PapagoAdapter`
- `.providers.papago_registry.PapagoRegistry`
- `.providers.microsoft_registry.MicrosoftServiceRegistry`
- `shl.config.policy_manager.ConfigManager`
- `shl.utils.env_loader.get_env_value`
- `shl.config.get_config_value`

---

## Module-Level Initialization

### Policy Manager

```python
try:
    _policy = ConfigManager()
    _USE_POLICY = True
    print(f"[Router] PolicyManager loaded from {_policy.path}")
except Exception as e:
    _USE_POLICY = False
    _policy = None
    print(f"[Router] PolicyManager failed to load: {e}")
```

Attempts to initialize `ConfigManager` at module load time. If it fails, policy-based routing is disabled.

### Provider Cache

```python
_PROVIDER_CACHE = load_cache()
```

Loads the provider language cache once at module initialization.

### Shared Instances

| Variable | Type | Description |
|----------|------|-------------|
| `_translation_cache` | `TranslationCache` | Shared translation cache instance. |
| `_mirror_manager` | `LibreTranslateMirrorManager` | Shared LibreTranslate mirror manager. |
| `_libre_registry` | `LibreTranslateRegistry` | Shared LibreTranslate language pair registry. |
| `_google_registry` | `GoogleRegistry` | Shared Google language pair registry. |
| `_papago_registry` | `PapagoRegistry` | Shared Papago language pair registry. |
| `_ms_registry` | `MicrosoftServiceRegistry` | Shared Microsoft service registry, initialized with `ttl_seconds` from `get_config_value("microsoft_translator.ttl")`. |

---

## Functions

### `_has_any_paid_key() -> bool`

Checks whether any paid API key is configured.

#### Behavior

Returns `True` if any of the following environment variables is set (via `get_env_value`):

- `MICROSOFT_TRANSLATOR_KEY`
- `DEEPL_API_KEY`
- `GOOGLE_API_KEY`
- `NAVER_CLIENT_ID`

---

### `get_provider_priority(...)`

```python
def get_provider_priority(
    target_lang: str,
    source_lang: str = "en",
    deepl_key: Optional[str] = None,
    google_api_key: Optional[str] = None,
    papago_client_id: Optional[str] = None,
    papago_client_secret: Optional[str] = None,
    microsoft_api_key: Optional[str] = None,
    mymemory_email: Optional[str] = None,
    request: Optional[TranslationRequest] = None,
) -> List[str]
```

Returns providers in usage order.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `target_lang` | `str` | — | Target language code. |
| `source_lang` | `str` | `"en"` | Source language code. |
| `deepl_key` | `Optional[str]` | `None` | DeepL API key. |
| `google_api_key` | `Optional[str]` | `None` | Google API key. |
| `papago_client_id` | `Optional[str]` | `None` | Papago client ID. |
| `papago_client_secret` | `Optional[str]` | `None` | Papago client secret. |
| `microsoft_api_key` | `Optional[str]` | `None` | Microsoft Translator API key. |
| `mymemory_email` | `Optional[str]` | `None` | MyMemory email address. |
| `request` | `Optional[TranslationRequest]` | `None` | Optional translation request object (not used in the function body). |

#### Behavior

1. **Policy-manager mode**: If `_USE_POLICY` is `True` and `_policy` is not `None`, calls `_policy.get_available_providers()`. If the result is truthy, returns the list with all names lowercased.

2. **Zero-budget fast path**: If `_has_any_paid_key()` returns `False`:
   - Resolves `mymemory_email` from parameter or `MYMEMORY_EMAIL` env.
   - If `mymemory_email` is truthy, returns `["mymemory"]`.
   - Otherwise returns `["libretranslate"]`.

3. **Legacy cache-based mode**:
   - Extracts language sets from `_PROVIDER_CACHE["providers"]`:
     - `pg_langs`: set of lowercase codes from `"papago"`
     - `mm_langs`: set of lowercase codes from `"mymemory_iso_639_1"`
     - `ms_langs`: set of lowercase codes from `"microsoft_translator"` keys
     - `lt_langs`: set of lowercase codes from `"libretranslate"` keys
   - Builds provider list in the following order:
     - **microsoft_translator**: If `ms_key` is available (parameter or env) AND `_ms_registry.is_available()` AND both languages are in `ms_langs`.
     - **deepl**: If `deepl_key` is available (parameter or env).
     - **google**: If `google_api_key` is available (parameter or env) AND `_google_registry.is_pair_supported(source_lang, target_lang)`.
     - **papago**: If `papago_client_id` and `papago_client_secret` are available (parameter or env) AND `_papago_registry.is_pair_supported(source_lang, target_lang, static_pg)` where `static_pg` is `True` if both languages are in `pg_langs`.
     - **libretranslate**: If both languages are in `lt_langs` AND `_libre_registry.is_pair_supported(source_lang, target_lang)`.
     - **mymemory**: If `mymemory_email` is available (parameter or env), OR if both languages are in `mm_langs`.
   - If the list is empty, appends `"mymemory"` as a fallback.

#### Returns

- `List[str]` — Provider names in priority order.

---

### `get_provider_timeout(provider_name: str) -> float`

Retrieves a provider's timeout from the policy manager or returns a default.

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `provider_name` | `str` | Name of the provider. |

#### Behavior

- If `_USE_POLICY` is `True` and `_policy` is not `None`, returns `_policy.get_timeout(provider_name, default=10.0)`.
- Otherwise returns `10.0`.

#### Returns

- `float` — Timeout in seconds.

---

### `get_best_provider(...)`

```python
def get_best_provider(
    target_lang: str,
    source_lang: str = "en",
    deepl_key: Optional[str] = None,
    google_api_key: Optional[str] = None,
    papago_client_id: Optional[str] = None,
    papago_client_secret: Optional[str] = None,
    microsoft_api_key: Optional[str] = None,
    mymemory_email: Optional[str] = None,
    request: Optional[TranslationRequest] = None,
) -> str
```

Returns the highest-priority provider name.

#### Behavior

Calls `get_provider_priority()` with the same arguments and returns the first element. If the list is empty, returns `"mymemory"`.

#### Returns

- `str` — The best provider name.

---

### `get_libretranslate_mirror_stats() -> Dict[str, Any]`

Gets statistics about LibreTranslate mirrors.

#### Returns

- `Dict[str, Any]` — The result of `_mirror_manager.get_stats()`.

---

### `clear_unavailable_cache() -> None`

Clears all runtime blacklist caches.

#### Behavior

Calls the following clear methods in order:

1. `_mirror_manager.clear_blacklist()`
2. `_libre_registry.clear_blacklist()`
3. `_google_registry.clear_blacklist()`
4. `_papago_registry.clear_blacklist()`
5. `_ms_registry.clear()`

---

### `get_unavailable_cache_stats() -> Dict[str, Any]`

Returns statistics about unavailable/blacklisted entries.

#### Returns

- `Dict[str, Any]` — A dictionary with the following keys:
  - `"blacklisted_mirrors"`: `len(_mirror_manager.blacklist)`
  - `"blacklisted_google_pairs"`: `len(_google_registry._unsupported_pairs_cache)`
  - `"blacklisted_libre_pairs"`: `len(_libre_registry._unsupported_pairs_cache)`
  - `"blacklisted_papago_pairs"`: `len(_papago_registry._unsupported_pairs_cache)`
  - `"microsoft_unavailable"`: `not _ms_registry.is_available()`

---

### `translate_text_with_metadata(...)`

```python
def translate_text_with_metadata(
    text: str,
    target_lang: str,
    source_lang: str = "en",
    use_cache: bool = True,
    mymemory_email: Optional[str] = None,
    deepl_key: Optional[str] = None,
    google_api_key: Optional[str] = None,
    google_backup_api_key: Optional[str] = None,
    papago_client_id: Optional[str] = None,
    papago_client_secret: Optional[str] = None,
    microsoft_api_key: Optional[str] = None,
    max_retries: int = 2,
    retry_delay: float = 1.0,
    total_timeout: float = 30.0,
    request: Optional[TranslationRequest] = None,
) -> TranslationResult
```

Translates text with full metadata, retry logic, caching, and provider failover.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | `str` | — | Text to translate. |
| `target_lang` | `str` | — | Target language code. |
| `source_lang` | `str` | `"en"` | Source language code. |
| `use_cache` | `bool` | `True` | Whether to read from and write to the translation cache. |
| `mymemory_email` | `Optional[str]` | `None` | MyMemory email. |
| `deepl_key` | `Optional[str]` | `None` | DeepL API key. |
| `google_api_key` | `Optional[str]` | `None` | Google API key. |
| `google_backup_api_key` | `Optional[str]` | `None` | Google backup API key. |
| `papago_client_id` | `Optional[str]` | `None` | Papago client ID. |
| `papago_client_secret` | `Optional[str]` | `None` | Papago client secret. |
| `microsoft_api_key` | `Optional[str]` | `None` | Microsoft Translator API key. |
| `max_retries` | `int` | `2` | Maximum retry attempts per provider. |
| `retry_delay` | `float` | `1.0` | Base delay in seconds between retries (multiplied by attempt index). |
| `total_timeout` | `float` | `30.0` | Maximum total time in seconds for the entire translation operation. |
| `request` | `Optional[TranslationRequest]` | `None` | Optional pre-built request object. |

#### Behavior

1. **Input validation**:
   - If `text` is empty or falsy, returns a `TranslationResult` with `translated_text=text`, `source="input_validation"`, and a default `TranslationRequest`.
   - If `text` is not a `str`, converts it with `str(text)`.
   - If `request` is `None`, creates a `TranslationRequest(text=text, source_lang=source_lang, target_lang=target_lang)`.

2. **Cache lookup**:
   - If `use_cache` is `True`, calls `_translation_cache.get(text, source_lang, target_lang, formality, context_type)`.
   - If a cached result is found, returns a `TranslationResult` with `source="cache"`.

3. **Provider selection**:
   - Calls `get_provider_priority()` to determine the provider order.
   - Prints the provider order to stdout for debugging.

4. **Provider resolution**:
   - `ms_key` is resolved from `microsoft_api_key` or `MICROSOFT_TRANSLATOR_KEY` env.

5. **Provider iteration**:
   - Iterates over each provider in `order`.
   - Breaks the loop if `time.time() - start_time > total_timeout`.
   - For each provider:
     - Computes `provider_timeout` via `get_provider_timeout(service)`.
     - Computes `service_deadline = min(start_time + total_timeout, time.time() + provider_timeout)`.
     - Iterates `for attempt in range(max_retries)`:
       - Breaks if `time.time() > service_deadline`.
       - Instantiates the appropriate adapter and calls `translate(request)`:
         - `"microsoft_translator"`: `MicrosoftTranslatorAdapter(api_key=ms_key)`
         - `"deepl"`: `DeepLAdapter(api_key=deepl_key)` if `deepl_key` else `DeepLAdapter()`
         - `"google"`: `GoogleV2Adapter(api_key=google_api_key, backup_api_key=google_backup_api_key)` if `google_api_key` else `GoogleV2Adapter()`
         - `"papago"`: `PapagoAdapter(client_id=papago_client_id, client_secret=papago_client_secret)` if both are provided else `PapagoAdapter()`
         - `"libretranslate"`: `LibreTranslateAdapter(mirror_manager=_mirror_manager)`
         - `"mymemory"`: `MyMemoryAdapter(email=mymemory_email)`
       - If `translated` is not `None`:
         - If `use_cache` is `True`, stores the result in `_translation_cache.set(...)`.
         - Returns a `TranslationResult` with `source=service`.

6. **Exception handling per attempt**:
   - `LanguageNotSupportedError`:
     - Marks the pair unsupported in the corresponding registry (`_google_registry`, `_libre_registry`, or `_papago_registry`).
     - Breaks to the next provider.
   - `RateLimitExceededError`: Breaks to the next provider.
   - `TranslationError`:
     - Computes `backoff = retry_delay * (attempt + 1)`.
     - If `time.time() + backoff > service_deadline`, breaks.
     - If `attempt < max_retries - 1`, sleeps for `backoff` seconds and continues.
   - Generic `Exception`:
     - If the service is `"microsoft_translator"`, calls `_ms_registry.mark_unavailable()`.
     - Breaks to the next provider.

7. **Final fallback**:
   - If all providers fail or time out, raises `ServiceUnavailableError` with message `"All translation services failed or timed out within {total_timeout}s."`.

#### Returns

- `TranslationResult` — The translation result with metadata.

#### Raises

- `ServiceUnavailableError` — If all providers fail or the total timeout is exceeded.

---

### `translate_text(...)`

```python
def translate_text(
    text: str,
    target_lang: str,
    source_lang: str = "en",
    use_cache: bool = True,
    mymemory_email: Optional[str] = None,
    deepl_key: Optional[str] = None,
    google_api_key: Optional[str] = None,
    google_backup_api_key: Optional[str] = None,
    papago_client_id: Optional[str] = None,
    papago_client_secret: Optional[str] = None,
    microsoft_api_key: Optional[str] = None,
    max_retries: int = 2,
    retry_delay: float = 1.0,
    total_timeout: float = 30.0,
    request: Optional[TranslationRequest] = None,
) -> str
```

Raw translation wrapper that returns only the translated string.

#### Parameters

Same as `translate_text_with_metadata()`.

#### Behavior

Calls `translate_text_with_metadata()` with the same arguments.

- On success, returns `result.translated_text`.
- On `ServiceUnavailableError`, logs a warning and returns the original `text`.
- On any other `Exception`, logs an error with `exc_info=True` and returns the original `text`.

#### Returns

- `str` — The translated text, or the original text if translation fails.

---

## Provider Instantiation Logic

The router instantiates adapters differently depending on whether credentials are provided:

| Provider | Credential Check | Adapter Instantiation |
|----------|-----------------|----------------------|
| `microsoft_translator` | `ms_key` resolved | `MicrosoftTranslatorAdapter(api_key=ms_key)` |
| `deepl` | `deepl_key` | `DeepLAdapter(api_key=deepl_key)` if key else `DeepLAdapter()` |
| `google` | `google_api_key` | `GoogleV2Adapter(api_key=..., backup_api_key=...)` if key else `GoogleV2Adapter()` |
| `papago` | `client_id` and `client_secret` | `PapagoAdapter(client_id=..., client_secret=...)` if both else `PapagoAdapter()` |
| `libretranslate` | Always | `LibreTranslateAdapter(mirror_manager=_mirror_manager)` |
| `mymemory` | Always | `MyMemoryAdapter(email=mymemory_email)` |

---

## Retry and Backoff Logic

- `max_retries` attempts are made per provider.
- `retry_delay` is multiplied by `(attempt + 1)` to produce the backoff duration.
- The service deadline (`min(total_timeout_remaining, provider_timeout)`) is checked before each attempt.
- `TranslationError` triggers a retry with backoff; `LanguageNotSupportedError` and `RateLimitExceededError` skip to the next provider immediately.

---

## Cache Behavior

- If `use_cache` is `True`, the router checks `_translation_cache` before making any API calls.
- On success, the result is stored in `_translation_cache` with `formality` and `context_type` as part of the cache key.
- Cache hits return `source="cache"` in the `TranslationResult`.

---

## Timeout Logic

- `total_timeout` governs the entire translation operation.
- `provider_timeout` is fetched per provider (default `10.0`, overridable via policy manager).
- `service_deadline = min(start_time + total_timeout, time.time() + provider_timeout)`.
- The provider loop breaks if the total timeout is exceeded before trying the next provider.
- Each attempt breaks if `time.time() > service_deadline`.

---

## Usage Example

```python
from shl.engine.translation.router import (
    translate_text,
    translate_text_with_metadata,
    get_best_provider,
    clear_unavailable_cache,
    get_unavailable_cache_stats,
)

# Simple translation
result = translate_text(
    text="Hello, world!",
    target_lang="fi",
    source_lang="en",
    use_cache=True,
)

# Translation with metadata
translation_result = translate_text_with_metadata(
    text="Hello, world!",
    target_lang="fi",
    source_lang="en",
    deepl_key="your-deepl-key",
    max_retries=3,
    total_timeout=60.0,
)
print(f"Translated by: {translation_result.source}")

# Get best provider
best = get_best_provider("fi", "en")
print(f"Best provider: {best}")

# Clear blacklists
clear_unavailable_cache()

# Get blacklist stats
stats = get_unavailable_cache_stats()
print(stats)
```

---

## Version

**Module version:** `0.2.5-casefix`

**Author:** Tuomas Lähteenmäki

**License:** MIT
