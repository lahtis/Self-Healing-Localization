# Translation Router — API Documentation

## Module Overview

**File:** `router.py`

The central orchestration layer for the SHL translation ecosystem. Coordinates provider priorities, executes automated failover across multiple translation backends, maintains service availability status via registries and blacklists, and interfaces with the translation cache. Supports DeepL, Google Translate v2, Papago, LibreTranslate, MyMemory, and Microsoft Translator with automatic `.env` credential detection.

---

## Metadata

| Attribute | Value |
|-----------|-------|
| Author | Tuomas Lähteenmäki |
| Version | 0.2.4 |
| License | MIT |

---

## Dependencies

| Module | Usage |
|--------|-------|
| `time` | Timeout tracking and retry backoff delays. |
| `logging` | Router-level log output. |
| `typing.Optional`, `typing.List`, `typing.Dict`, `typing.Any` | Type annotations. |
| `.provider_cache.load_cache` | Loads the provider language support cache. |
| `shl.config.config.get_ttl` | Retrieves TTL configuration values. |
| `.cache.TranslationCache` | In-memory translation result cache. |
| `.metadata.TranslationRequest`, `.metadata.TranslationResult` | Core data structures for translation operations. |
| `.exceptions.TranslationError`, `.exceptions.ServiceUnavailableError`, `.exceptions.LanguageNotSupportedError`, `.exceptions.RateLimitExceededError` | Exception types used for routing decisions. |
| `.providers.*` | All supported provider adapters and their registries. |
| `shl.utils.env_loader.get_env_value` | Reads environment variables with fallback. |
| `shl.config.get_config_value` | Reads configuration values from SHL config. |

---

## Module-Level Globals

| Name | Type | Description |
|------|------|-------------|
| `_translation_cache` | `TranslationCache` | Singleton in-memory cache for translation results. |
| `_mirror_manager` | `LibreTranslateMirrorManager` | Manages LibreTranslate mirror selection and blacklisting. |
| `_libre_registry` | `LibreTranslateRegistry` | Runtime blacklist for unsupported LibreTranslate language pairs. |
| `_google_registry` | `GoogleRegistry` | Runtime blacklist for unsupported Google language pairs. |
| `_papago_registry` | `PapagoRegistry` | Runtime blacklist for unsupported Papago language pairs. |
| `_ms_registry` | `MicrosoftServiceRegistry` | TTL-based availability registry for Microsoft Translator. |

---

## Provider Priority Logic

### Evaluation Order

Providers are evaluated in the following priority order. A provider is included only if all its prerequisites are met:

| Priority | Provider | Prerequisites |
|----------|----------|---------------|
| 1 | **Microsoft Translator** | API key available + registry available + both languages in MS cache. |
| 2 | **DeepL** | API key available (no language cache check). |
| 3 | **Google** | API key available + pair supported by Google registry. |
| 4 | **Papago** | Client ID + Secret available + pair supported by Papago registry and static cache. |
| 5 | **LibreTranslate** | Both languages in LT cache + pair supported by Libre registry. |
| 6 | **MyMemory** | Both languages in MyMemory cache. |

### Credential Resolution

All credentials follow the same resolution order:
1. Explicit parameter passed to the function.
2. Environment variable (via `get_env_value()` and `.env` auto-detection).
3. If neither is available, the provider is skipped.

| Provider | Parameter | Environment Variable |
|----------|-----------|---------------------|
| Microsoft Translator | `microsoft_api_key` | `MICROSOFT_TRANSLATOR_KEY` |
| DeepL | `deepl_key` | `DEEPL_API_KEY` |
| Google | `google_api_key` | `GOOGLE_API_KEY` |
| Papago | `papago_client_id` / `papago_client_secret` | `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` |
| LibreTranslate | — | — (uses mirror manager) |
| MyMemory | `mymemory_email` | — (optional email for higher quota) |

---

## Functions

### `get_provider_priority()`

```python
def get_provider_priority(
    target_lang: str,
    source_lang: str = "en",
    deepl_key: Optional[str] = None,
    google_api_key: Optional[str] = None,
    papago_client_id: Optional[str] = None,
    papago_client_secret: Optional[str] = None,
    microsoft_api_key: Optional[str] = None,
    request: Optional[TranslationRequest] = None,
) -> List[str]
```

Returns an ordered list of provider names that are available and support the given language pair.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `target_lang` | `str` | — | Target language code (e.g., `"fi"`, `"ja"`). |
| `source_lang` | `str` | `"en"` | Source language code (e.g., `"en"`, `"de"`). |
| `deepl_key` | `Optional[str]` | `None` | DeepL API key override. |
| `google_api_key` | `Optional[str]` | `None` | Google API key override. |
| `papago_client_id` | `Optional[str]` | `None` | Papago client ID override. |
| `papago_client_secret` | `Optional[str]` | `None` | Papago client secret override. |
| `microsoft_api_key` | `Optional[str]` | `None` | Microsoft Translator API key override. |
| `request` | `Optional[TranslationRequest]` | `None` | Original request object (reserved for future use). |

**Returns**
- `List[str]` — Ordered list of provider identifier strings. Empty list if no providers are available.

**Logic**
1. Loads the provider language cache via `load_cache()`.
2. For each provider, checks credentials, registry availability, and language support.
3. Returns providers in priority order.

**Example**
```python
providers = get_provider_priority("fi", source_lang="en")
# ["microsoft_translator", "deepl", "google", "libretranslate", "mymemory"]
```

---

### `get_best_provider()`

```python
def get_best_provider(
    target_lang: str,
    source_lang: str = "en",
    deepl_key: Optional[str] = None,
    google_api_key: Optional[str] = None,
    papago_client_id: Optional[str] = None,
    papago_client_secret: Optional[str] = None,
    microsoft_api_key: Optional[str] = None,
    request: Optional[TranslationRequest] = None,
) -> str
```

Returns the highest-priority available provider for the given language pair.

**Parameters**
Same as `get_provider_priority()`.

**Returns**
- `str` — The name of the best available provider, or `"mymemory"` as the ultimate fallback.

**Example**
```python
best = get_best_provider("ko", source_lang="en")
# "papago"  (if credentials and pair are supported)
```

---

### `get_libretranslate_mirror_stats()`

```python
def get_libretranslate_mirror_stats() -> Dict[str, Any]
```

Returns statistics about LibreTranslate mirror health and availability.

**Returns**
- `Dict[str, Any]` — Mirror statistics from the internal `LibreTranslateMirrorManager`.

**Example**
```python
stats = get_libretranslate_mirror_stats()
print(stats)
# {"total_mirrors": 5, "available": 3, "blacklisted": 2, ...}
```

---

### `clear_unavailable_cache()`

```python
def clear_unavailable_cache() -> None
```

Clears all runtime blacklists and availability registries, forcing a fresh start for all providers.

**Side Effects**
- Clears LibreTranslate mirror blacklist.
- Clears Google, LibreTranslate, and Papago pair blacklists.
- Clears Microsoft Translator availability flag.

**Use Cases**
- Manual recovery after operator intervention.
- Testing and debugging.
- Periodic health check resets.

**Example**
```python
clear_unavailable_cache()
# All providers are now eligible for retry
```

---

### `get_unavailable_cache_stats()`

```python
def get_unavailable_cache_stats() -> Dict[str, Any]
```

Returns a snapshot of all runtime blacklist and availability states.

**Returns**
- `Dict[str, Any]` — Dictionary with the following keys:

| Key | Type | Description |
|-----|------|-------------|
| `blacklisted_mirrors` | `int` | Number of blacklisted LibreTranslate mirrors. |
| `blacklisted_google_pairs` | `int` | Number of blacklisted Google language pairs. |
| `blacklisted_libre_pairs` | `int` | Number of blacklisted LibreTranslate language pairs. |
| `blacklisted_papago_pairs` | `int` | Number of blacklisted Papago language pairs. |
| `microsoft_unavailable` | `bool` | `True` if Microsoft Translator is currently marked unavailable. |

**Example**
```python
stats = get_unavailable_cache_stats()
print(f"Blacklisted mirrors: {stats['blacklisted_mirrors']}")
print(f"Microsoft available: {not stats['microsoft_unavailable']}")
```

---

### `translate_text_with_metadata()`

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

The core translation execution function. Routes the request through available providers with automatic failover, caching, retries, and timeout enforcement.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | `str` | — | Text to translate. |
| `target_lang` | `str` | — | Target language code. |
| `source_lang` | `str` | `"en"` | Source language code. |
| `use_cache` | `bool` | `True` | Whether to check and store results in the translation cache. |
| `mymemory_email` | `Optional[str]` | `None` | Email for MyMemory API (higher quota). |
| `deepl_key` | `Optional[str]` | `None` | DeepL API key override. |
| `google_api_key` | `Optional[str]` | `None` | Google API key override. |
| `google_backup_api_key` | `Optional[str]` | `None` | Backup Google API key for failover. |
| `papago_client_id` | `Optional[str]` | `None` | Papago client ID override. |
| `papago_client_secret` | `Optional[str]` | `None` | Papago client secret override. |
| `microsoft_api_key` | `Optional[str]` | `None` | Microsoft Translator API key override. |
| `max_retries` | `int` | `2` | Maximum retry attempts per provider. |
| `retry_delay` | `float` | `1.0` | Base delay in seconds between retries (multiplied by attempt number). |
| `total_timeout` | `float` | `30.0` | Maximum total time in seconds for the entire translation attempt. |
| `request` | `Optional[TranslationRequest]` | `None` | Pre-built request object. If omitted, one is created from the other parameters. |

**Returns**
- `TranslationResult` — Object containing the translated text, source provider name, and request metadata.

**Raises**
- `ServiceUnavailableError` — If all providers fail or the total timeout is exceeded.

**Execution Flow**

```
1. Input validation
   ├── Empty text → return TranslationResult with empty text
   └── Non-string → coerce to string

2. Cache check (if use_cache=True)
   └── Hit → return cached TranslationResult

3. Provider priority resolution
   └── Get ordered list of available providers

4. Provider iteration with failover
   ├── For each provider:
   │   ├── Check total_timeout
   │   └── For each retry attempt (max_retries):
   │       ├── Check total_timeout
   │       ├── Instantiate adapter
   │       ├── Call adapter.translate(request)
   │       ├── On success → cache result → return TranslationResult
   │       ├── LanguageNotSupportedError → blacklist pair → break to next provider
   │       ├── RateLimitExceededError → break to next provider
   │       ├── TranslationError → backoff retry → continue
   │       └── Other Exception → mark Microsoft unavailable (if applicable) → break
   └── All failed → raise ServiceUnavailableError
```

**Exception Handling per Provider**

| Exception Type | Action | Registry Effect |
|----------------|--------|-----------------|
| `LanguageNotSupportedError` | Skip to next provider. | Blacklist pair for Google, LibreTranslate, or Papago. |
| `RateLimitExceededError` | Skip to next provider. | None. |
| `TranslationError` | Retry with exponential backoff. | None. |
| Other exception | Skip to next provider. | Mark Microsoft Translator unavailable (if MS service). |

**Retry Backoff**
```python
backoff = retry_delay * (attempt + 1)
# Attempt 0: 1.0s, Attempt 1: 2.0s
```

**Example**
```python
from router import translate_text_with_metadata
from shl.metadata import TranslationRequest

request = TranslationRequest(
    text="Hello, world!",
    source_lang="en",
    target_lang="fi",
    formality="formal",
)

result = translate_text_with_metadata(
    text="Hello, world!",
    target_lang="fi",
    source_lang="en",
    use_cache=True,
    max_retries=2,
    total_timeout=30.0,
    request=request,
)

print(result.translated_text)  # "Hei, maailma!"
print(result.source)           # "microsoft_translator" (or best available)
```

---

### `translate_text()`

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

Simplified wrapper around `translate_text_with_metadata()` that returns only the translated string.

**Parameters**
Same as `translate_text_with_metadata()`.

**Returns**
- `str` — The translated text, or the original `text` if all providers fail (fail-safe).

**Behavior**
- Calls `translate_text_with_metadata()` internally.
- On any exception, returns the original `text` instead of raising.

**Example**
```python
from router import translate_text

translated = translate_text(
    text="Hello, world!",
    target_lang="fi",
    source_lang="en",
)
print(translated)  # "Hei, maailma!" (or "Hello, world!" on total failure)
```

---

## Failover Behavior Summary

| Scenario | Behavior |
|----------|----------|
| Empty input text | Returns immediately with empty text, source `"input_validation"`. |
| Cache hit | Returns cached result immediately, source `"cache"`. |
| Provider succeeds | Returns translated text with provider name as source. |
| Provider rate-limited | Skips to next provider in priority list. |
| Provider doesn't support language pair | Blacklists pair and skips to next provider. |
| Provider transient error | Retries with backoff up to `max_retries`. |
| Total timeout exceeded | Breaks out and raises `ServiceUnavailableError`. |
| All providers fail | Raises `ServiceUnavailableError` (or returns original text via `translate_text()`). |

---

## Usage Example: Full Workflow

```python
from shl.router import (
    get_provider_priority,
    get_best_provider,
    translate_text,
    translate_text_with_metadata,
    get_unavailable_cache_stats,
    clear_unavailable_cache,
)
from shl.metadata import TranslationRequest

# 1. Check which providers are available for a language pair
providers = get_provider_priority("ja", source_lang="en")
print(providers)  # ["microsoft_translator", "deepl", "google", "libretranslate", "mymemory"]

# 2. Get the best provider
best = get_best_provider("ja", source_lang="en")
print(best)  # "microsoft_translator"

# 3. Translate with full metadata
request = TranslationRequest(
    text="Welcome to our application!",
    source_lang="en",
    target_lang="ja",
    formality="formal",
    domain="user_onboarding",
)

result = translate_text_with_metadata(
    text="Welcome to our application!",
    target_lang="ja",
    source_lang="en",
    request=request,
    total_timeout=45.0,
)

print(f"Translated: {result.translated_text}")
print(f"Provider: {result.source}")

# 4. Simple translation (fail-safe)
text = translate_text("Hello", target_lang="fi")
print(text)  # "Hei"

# 5. Check blacklist status
stats = get_unavailable_cache_stats()
print(stats)

# 6. Clear all blacklists for fresh retry
clear_unavailable_cache()
```

---

## Thread Safety

| Component | Status | Notes |
|-----------|--------|-------|
| `_translation_cache` | Generally safe | `TranslationCache` implementation determines thread safety. |
| Registries (`_libre_registry`, `_google_registry`, `_papago_registry`) | Not safe | Mutable caches. Concurrent modifications may cause race conditions. |
| `_ms_registry` | Generally safe | TTL-based flag. Reads are safe; writes (mark_unavailable) may race. |
| `_mirror_manager` | Not safe | Mutable blacklist. Concurrent access may race. |

**Recommendation:** In multi-threaded environments, use one router instance per thread or wrap registry-modifying calls with locks.

---

## Logging

The module uses Python's standard `logging` module under the logger name `__name__`.

**Log Levels Used**

| Level | Event |
|-------|-------|
| `DEBUG` | Provider initialization, request details, successful translations. |
| `WARNING` | Blacklist events, detected language mismatches, provider unavailability. |
| `ERROR` | Unhandled exceptions during translation execution. |

---

## Changelog

| Version | Notes |
|---------|-------|
| 0.2.4 | Current — intelligent routing with 6 providers, automated failover, caching, retries, timeout enforcement, and comprehensive registry/blacklist management. |
