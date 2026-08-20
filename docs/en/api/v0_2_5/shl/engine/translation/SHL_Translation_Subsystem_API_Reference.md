# SHL Translation Subsystem — Public API Reference

## Module Overview

**File:** `shl/engine/translation/__init__.py`

Central export manifest for the SHL translation subsystem. Re-exports all public interfaces of the translation engine under a unified namespace, including routing functions, provider adapters, caching, metadata structures, and exception types.

---

## Metadata

| Attribute | Value |
|-----------|-------|
| Author | Tuomas Lähteenmäki |
| Version | 0.2.0 |
| License | MIT |
| Description | Central export manifest for the SHL translation subsystem. Exposes routing interfaces, provider adapters, caching mechanics, and exception taxonomy under a unified public API namespace. |

---

## Public API Categories

### 1. Core Routing Functions

Imported from `shl.engine.translation.router`:

| Export | Description |
|--------|-------------|
| `translate_text` | Simplified translation entry point. Returns only the translated string (fail-safe). |
| `translate_text_with_metadata` | Full translation with `TranslationResult` output, caching, retries, and failover. |
| `get_best_provider` | Returns the highest-priority available provider for a language pair. |
| `get_provider_priority` | Returns an ordered list of all available providers for a language pair. |
| `get_libretranslate_mirror_stats` | Returns health statistics for LibreTranslate mirror endpoints. |
| `clear_unavailable_cache` | Clears all runtime blacklists and availability registries. |
| `get_unavailable_cache_stats` | Returns statistics about blacklisted providers and mirrors. |

**Example**
```python
from shl.engine.translation import translate_text, get_best_provider

# Simple translation
text = translate_text("Hello", target_lang="fi", source_lang="en")

# Check best provider
best = get_best_provider("ja", source_lang="en")
print(best)  # "microsoft_translator"
```

---

### 2. Cache Management

Imported from `shl.engine.translation.cache`:

| Export | Description |
|--------|-------------|
| `TranslationCache` | In-memory cache for translation results with TTL support. |

**Example**
```python
from shl.engine.translation import TranslationCache

cache = TranslationCache()
cache.set("hello", "hei", "en", "fi", ttl=3600)
result = cache.get("hello", "en", "fi")
```

---

### 3. Metadata and Data Structures

Imported from `shl.engine.translation.metadata`:

| Export | Description |
|--------|-------------|
| `TranslationRequest` | Dataclass containing all translation parameters (text, languages, formality, context, etc.). |
| `TranslationResult` | Dataclass containing the translated text, source provider, confidence, and audit metadata. |

**Example**
```python
from shl.engine.translation import TranslationRequest, TranslationResult

request = TranslationRequest(
    text="Welcome",
    source_lang="en",
    target_lang="de",
    formality="formal",
    domain="desktop_ui",
)
```

---

### 4. Provider Adapters

Imported from individual provider modules under `shl.engine.translation.providers`:

| Export | Source Module | Description |
|--------|--------------|-------------|
| `MyMemoryAdapter` | `.providers.mymemory` | MyMemory translation provider with email quota support. |
| `LibreTranslateAdapter` | `.providers.libretranslate` | LibreTranslate provider with mirror failover and language discovery. |
| `DeepLAdapter` | `.providers.deepl` | DeepL translation provider with formality and glossary support. |
| `GoogleV2Adapter` | `.providers.googlev2` | Google Translate v2 provider. |
| `PapagoAdapter` | `.providers.papago` | Naver Papago provider with honorific and glossary support. |
| `MicrosoftTranslatorAdapter` | `.providers.microsoft` | Microsoft Translator API v3 with context metadata and TTL registry. |

**Example**
```python
from shl.engine.translation import (
    MyMemoryAdapter,
    DeepLAdapter,
    MicrosoftTranslatorAdapter,
)

# Direct provider usage
adapter = DeepLAdapter(api_key="your-key")
result = adapter.translate(request)

# Microsoft Translator with context
ms = MicrosoftTranslatorAdapter(api_key="your-key")
result = ms.translate(request)
```

---

### 5. Exception Taxonomy

Imported from `shl.engine.translation.exceptions`:

| Export | Description |
|--------|-------------|
| `TranslationError` | Base exception for all translation failures. |
| `ServiceUnavailableError` | Remote service temporarily unavailable or timed out. |
| `RateLimitExceededError` | API rate limit or quota exceeded. |
| `LanguageNotSupportedError` | Language pair not supported by the provider. |
| `ProviderAccessError` | Invalid or unauthorized API credentials. |
| `InvalidRequestError` | Malformed request parameters or payload. |

**Example**
```python
from shl.engine.translation import (
    translate_text,
    TranslationError,
    ServiceUnavailableError,
    RateLimitExceededError,
)

try:
    result = translate_text("Hello", target_lang="fi")
except ServiceUnavailableError:
    print("All providers unavailable")
except RateLimitExceededError:
    print("Quota exceeded")
except TranslationError as e:
    print(f"Translation failed: {e}")
```

---

### 6. Version

| Export | Description |
|--------|-------------|
| `__version__` | Current SHL package version string. |

---

## `__all__` Export List

```python
__all__ = [
    "__version__",

    # Core Routing Functions
    "translate_text",
    "translate_text_with_metadata",
    "get_best_provider",
    "get_provider_priority",
    "get_supported_languages",
    "get_libretranslate_mirror_stats",
    "clear_unavailable_cache",
    "get_unavailable_cache_stats",

    # Cache Management
    "TranslationCache",

    # Metadata and Data Structures
    "TranslationRequest",
    "TranslationResult",

    # Provider Adapters
    "MyMemoryAdapter",
    "LibreTranslateAdapter",
    "DeepLAdapter",
    "GoogleV2Adapter",
    "PapagoAdapter",
    "MicrosoftTranslatorAdapter",

    # Exception Taxonomy
    "TranslationError",
    "ServiceUnavailableError",
    "RateLimitExceededError",
    "LanguageNotSupportedError",
    "ProviderAccessError",
    "InvalidRequestError",
]
```

---

## Import Map

| Public Name | Internal Source |
|-------------|-----------------|
| `__version__` | `shl._version.__version__` |
| `translate_text` | `.router.translate_text` |
| `translate_text_with_metadata` | `.router.translate_text_with_metadata` |
| `get_best_provider` | `.router.get_best_provider` |
| `get_provider_priority` | `.router.get_provider_priority` |
| `get_libretranslate_mirror_stats` | `.router.get_libretranslate_mirror_stats` |
| `clear_unavailable_cache` | `.router.clear_unavailable_cache` |
| `get_unavailable_cache_stats` | `.router.get_unavailable_cache_stats` |
| `TranslationCache` | `.cache.TranslationCache` |
| `TranslationRequest` | `.metadata.TranslationRequest` |
| `TranslationResult` | `.metadata.TranslationResult` |
| `MyMemoryAdapter` | `.providers.mymemory.MyMemoryAdapter` |
| `LibreTranslateAdapter` | `.providers.libretranslate.LibreTranslateAdapter` |
| `get_supported_languages` | `.providers.libretranslate.get_supported_languages` |
| `DeepLAdapter` | `.providers.deepl.DeepLAdapter` |
| `GoogleV2Adapter` | `.providers.googlev2.GoogleV2Adapter` |
| `PapagoAdapter` | `.providers.papago.PapagoAdapter` |
| `MicrosoftTranslatorAdapter` | `.providers.microsoft.MicrosoftTranslatorAdapter` |
| `TranslationError` | `.exceptions.TranslationError` |
| `ServiceUnavailableError` | `.exceptions.ServiceUnavailableError` |
| `RateLimitExceededError` | `.exceptions.RateLimitExceededError` |
| `LanguageNotSupportedError` | `.exceptions.LanguageNotSupportedError` |
| `ProviderAccessError` | `.exceptions.ProviderAccessError` |
| `InvalidRequestError` | `.exceptions.InvalidRequestError` |

---

## Complete Usage Example

```python
from shl.engine.translation import (
    # Routing
    translate_text,
    translate_text_with_metadata,
    get_best_provider,
    get_provider_priority,
    # Metadata
    TranslationRequest,
    TranslationResult,
    # Cache
    TranslationCache,
    # Providers
    DeepLAdapter,
    MicrosoftTranslatorAdapter,
    # Exceptions
    TranslationError,
    ServiceUnavailableError,
)

# 1. Simple translation
text = translate_text("Hello, world!", target_lang="fi")
print(text)

# 2. Full translation with metadata
request = TranslationRequest(
    text="Welcome to our application!",
    source_lang="en",
    target_lang="de",
    formality="formal",
    domain="desktop_ui",
)

result = translate_text_with_metadata(
    text=request.text,
    target_lang=request.target_lang,
    source_lang=request.source_lang,
    request=request,
)
print(f"Translated: {result.translated_text}")
print(f"Provider: {result.source}")

# 3. Check available providers
providers = get_provider_priority("ja", source_lang="en")
print(f"Available: {providers}")

# 4. Direct provider usage
adapter = DeepLAdapter(api_key="your-key")
result = adapter.translate(request)

# 5. Cache management
cache = TranslationCache()
cache.set("test", "result", "en", "fi")
print(f"Cache hit: {cache.get('test', 'en', 'fi')}")

# 6. Error handling
try:
    text = translate_text("Hello", target_lang="xx")
except LanguageNotSupportedError:
    print("Language not supported")
except TranslationError as e:
    print(f"Error: {e}")
```

---

## Changelog

| Version | Notes |
|---------|-------|
| 0.2.0 | Current — unified public API for the SHL translation subsystem exposing routing, providers, cache, metadata, and exceptions. |
