# SHL Package — Public API Reference

## Module Overview

**File:** `__init__.py`

Top-level package initialization for the **Self-Healing Localization Layer (SHL)**. This module defines the public API surface by importing and re-exporting all core components, utilities, providers, and exceptions that end-users and downstream modules are expected to interact with.

---

## Package Metadata

| Attribute | Type | Value | Description |
|-----------|------|-------|-------------|
| `__version__` | `str` | `"0.2.5"` | Current SHL package version. |
| `__author__` | `str` | `"Tuomas Lähteenmäki"` | Package author and maintainer. |
| `__license__` | `str` | `"MIT"` | Software license. |

---

## Public API Categories

### 1. Logging

| Export | Source Module | Description |
|--------|--------------|-------------|
| `setup_logging` | `shl.logging_config` | Initialize unified console + file logging with rotation. |
| `get_logger` | `shl.logging_config` | Get a namespaced logger instance. |
| `set_level` | `shl.logging_config` | Adjust log level at runtime. |
| `get_log_stats` | `shl.logging_config` | Retrieve logging statistics and file info. |

**Example**
```python
from shl import setup_logging, get_logger
import logging

setup_logging(console_level=logging.DEBUG)
logger = get_logger(__name__)
logger.info("SHL initialized")
```

---

### 2. Language Validation

| Export | Source Module | Description |
|--------|--------------|-------------|
| `LanguageValidator` | `shl.language_validator` | Validates language codes against GLFM database and builds fallback chains. |

**Example**
```python
from shl import LanguageValidator

validator = LanguageValidator(use_lite=True)
if validator.is_valid("fi"):
    chain = validator.get_fallback_chain("zh-TW")
```

---

### 3. Language Utilities

| Export | Source Module | Description |
|--------|--------------|-------------|
| `parse_bcp47` | `shl.utils.lang_utils` | Parse a BCP-47 tag into language, script, and region components. |
| `normalize_full_tag` | `shl.utils.lang_utils` | Normalize a language tag to canonical BCP-47 form. |
| `base_language` | `shl.utils.lang_utils` | Extract the base language code from a BCP-47 tag (strip script/region). |
| `has_region` | `shl.utils.lang_utils` | Check whether a language tag contains a region subtag. |
| `get_parent` | `shl.utils.lang_utils` | Get the parent language of a given tag (e.g., `zh-TW` → `zh`). |
| `split_tag` | `shl.utils.lang_utils` | Split a language tag into its structural parts. |

**Example**
```python
from shl import parse_bcp47, normalize_full_tag, base_language

lang, script, region = parse_bcp47("zh-Hant-TW")
# lang="zh", script="Hant", region="TW"

normalized = normalize_full_tag("zh-tw")
# "zh-TW"

base = base_language("zh-Hant-TW")
# "zh"
```

---

### 4. Translation — Core Functions

| Export | Source Module | Description |
|--------|--------------|-------------|
| `translate_text` | `shl.engine.translation` | Main translation entry point with automatic failover and caching. |
| `get_best_provider` | `shl.engine.translation` | Returns the highest-priority provider for a language pair. |
| `get_supported_languages` | `shl.engine.translation` | Returns languages supported by the active providers. |
| `get_libretranslate_mirror_stats` | `shl.engine.translation` | Returns health statistics for LibreTranslate mirrors. |

**Example**
```python
from shl import translate_text, get_best_provider

# Simple translation
result = translate_text("Hello", target_lang="fi", source_lang="en")
print(result)  # "Hei"

# Check best provider
best = get_best_provider("ja", source_lang="en")
print(best)  # "microsoft_translator"
```

---

### 5. Translation — Cache

| Export | Source Module | Description |
|--------|--------------|-------------|
| `TranslationCache` | `shl.engine.translation` | In-memory cache for translation results. |

**Example**
```python
from shl import TranslationCache

cache = TranslationCache()
cache.set("hello", "hei", "en", "fi")
result = cache.get("hello", "en", "fi")
```

---

### 6. Translation — Metadata

| Export | Source Module | Description |
|--------|--------------|-------------|
| `TranslationRequest` | `shl.engine.translation` | Data structure containing translation parameters (text, languages, formality, context, etc.). |
| `TranslationResult` | `shl.engine.translation` | Data structure containing the translated text, source provider, and request metadata. |

**Example**
```python
from shl import TranslationRequest, TranslationResult

request = TranslationRequest(
    text="Welcome",
    source_lang="en",
    target_lang="de",
    formality="formal",
    domain="user_onboarding",
)
```

---

### 7. Translation — Helper Functions

| Export | Source Module | Description |
|--------|--------------|-------------|
| `clear_unavailable_cache` | `shl.engine.translation` | Clears all runtime blacklists and availability registries. |
| `get_unavailable_cache_stats` | `shl.engine.translation` | Returns statistics about blacklisted providers and mirrors. |

**Example**
```python
from shl import clear_unavailable_cache, get_unavailable_cache_stats

# Check blacklist status
stats = get_unavailable_cache_stats()
print(stats)

# Force fresh retry for all providers
clear_unavailable_cache()
```

---

### 8. Translation — Provider Adapters

| Export | Source Module | Description |
|--------|--------------|-------------|
| `MyMemoryAdapter` | `shl.engine.translation` | MyMemory translation provider adapter. |
| `LibreTranslateAdapter` | `shl.engine.translation` | LibreTranslate provider adapter with mirror support. |
| `DeepLAdapter` | *(listed in `__all__`)* | DeepL translation provider adapter. |
| `GoogleV2Adapter` | *(listed in `__all__`)* | Google Translate v2 provider adapter. |
| `PapagoAdapter` | *(listed in `__all__`)* | Naver Papago provider adapter. |
| `MicrosoftTranslatorAdapter` | *(listed in `__all__`)* | Microsoft Translator API v3 adapter. |

**Example**
```python
from shl import MyMemoryAdapter, LibreTranslateAdapter

# Direct provider usage
adapter = MyMemoryAdapter(email="user@example.com")
result = adapter.translate(request)

# LibreTranslate with mirror manager
adapter = LibreTranslateAdapter()
result = adapter.translate(request)
```

---

### 9. Translation — Exceptions

| Export | Source Module | Description |
|--------|--------------|-------------|
| `TranslationError` | `shl.engine.translation` | Base exception for translation failures. |
| `RateLimitExceededError` | `shl.engine.translation` | API rate limit or quota exceeded. |
| `ServiceUnavailableError` | `shl.engine.translation` | Remote service temporarily unavailable or timed out. |
| `LanguageNotSupportedError` | `shl.engine.translation` | Language pair not supported by the provider. |
| `ProviderAccessError` | `shl.engine.translation` | Invalid or unauthorized API credentials. |
| `InvalidRequestError` | `shl.engine.translation` | Malformed request parameters or payload. |

**Example**
```python
from shl import (
    translate_text,
    TranslationError,
    ServiceUnavailableError,
    RateLimitExceededError,
)

try:
    result = translate_text("Hello", target_lang="fi")
except ServiceUnavailableError:
    print("Service temporarily down")
except RateLimitExceededError:
    print("Quota exceeded")
except TranslationError as e:
    print(f"Translation failed: {e}")
```

---

## Complete Usage Example

```python
import logging
from shl import (
    # Metadata
    __version__,
    # Logging
    setup_logging,
    get_logger,
    # Core
    LanguageValidator,
    # Translation
    translate_text,
    get_best_provider,
    TranslationRequest,
    TranslationResult,
    TranslationCache,
    clear_unavailable_cache,
    # Exceptions
    TranslationError,
    ServiceUnavailableError,
)

# 1. Initialize logging
setup_logging(console_level=logging.INFO)
logger = get_logger("my_app")
logger.info(f"Using SHL v{__version__}")

# 2. Validate language
validator = LanguageValidator()
if validator.is_valid("ja"):
    logger.info("Japanese is supported by GLFM")

# 3. Translate with full metadata
request = TranslationRequest(
    text="Welcome to our application!",
    source_lang="en",
    target_lang="de",
    formality="formal",
)

try:
    result = translate_text(
        text=request.text,
        target_lang=request.target_lang,
        source_lang=request.source_lang,
        request=request,
    )
    print(f"Translated: {result}")
    print(f"Best provider: {get_best_provider('de', 'en')}")
except ServiceUnavailableError:
    print("All providers unavailable")
except TranslationError as e:
    print(f"Error: {e}")

# 4. Clear blacklists if needed
clear_unavailable_cache()
```

---

## `__all__` Export List

The following names are explicitly exported when using `from shl import *`:

```python
__all__ = [
    # Version
    "__version__",
    "__author__",
    "__license__",
    # Logging
    "setup_logging",
    "get_logger",
    "set_level",
    "get_log_stats",
    # Core
    "LanguageValidator",
    # Lang utils
    "parse_bcp47",
    "normalize_full_tag",
    "base_language",
    "has_region",
    "get_parent",
    "split_tag",
    # Translation — main functions
    "translate_text",
    "get_best_provider",
    "get_libretranslate_mirror_stats",
    # Translation — cache
    "TranslationCache",
    # Translation — metadata
    "TranslationRequest",
    "TranslationResult",
    # Translation — helpers
    "clear_unavailable_cache",
    "get_unavailable_cache_stats",
    # Translation — providers
    "MyMemoryAdapter",
    "LibreTranslateAdapter",
    "DeepLAdapter",
    "GoogleV2Adapter",
    "PapagoAdapter",
    "MicrosoftTranslatorAdapter",
    # Translation — exceptions
    "TranslationError",
    "RateLimitExceededError",
    "ServiceUnavailableError",
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
| `__author__` | `shl._version.__author__` |
| `__license__` | `shl._version.__license__` |
| `setup_logging` | `shl.logging_config.setup_logging` |
| `get_logger` | `shl.logging_config.get_logger` |
| `set_level` | `shl.logging_config.set_level` |
| `get_log_stats` | `shl.logging_config.get_log_stats` |
| `LanguageValidator` | `shl.language_validator.LanguageValidator` |
| `parse_bcp47` | `shl.utils.lang_utils.parse_bcp47` |
| `normalize_full_tag` | `shl.utils.lang_utils.normalize_full_tag` |
| `base_language` | `shl.utils.lang_utils.base_language` |
| `has_region` | `shl.utils.lang_utils.has_region` |
| `get_parent` | `shl.utils.lang_utils.get_parent` |
| `split_tag` | `shl.utils.lang_utils.split_tag` |
| `translate_text` | `shl.engine.translation.translate_text` |
| `get_best_provider` | `shl.engine.translation.get_best_provider` |
| `get_supported_languages` | `shl.engine.translation.get_supported_languages` |
| `get_libretranslate_mirror_stats` | `shl.engine.translation.get_libretranslate_mirror_stats` |
| `TranslationCache` | `shl.engine.translation.TranslationCache` |
| `TranslationRequest` | `shl.engine.translation.TranslationRequest` |
| `TranslationResult` | `shl.engine.translation.TranslationResult` |
| `clear_unavailable_cache` | `shl.engine.translation.clear_unavailable_cache` |
| `get_unavailable_cache_stats` | `shl.engine.translation.get_unavailable_cache_stats` |
| `MyMemoryAdapter` | `shl.engine.translation.MyMemoryAdapter` |
| `LibreTranslateAdapter` | `shl.engine.translation.LibreTranslateAdapter` |
| `TranslationError` | `shl.engine.translation.TranslationError` |
| `RateLimitExceededError` | `shl.engine.translation.RateLimitExceededError` |
| `ServiceUnavailableError` | `shl.engine.translation.ServiceUnavailableError` |
| `LanguageNotSupportedError` | `shl.engine.translation.LanguageNotSupportedError` |
| `ProviderAccessError` | `shl.engine.translation.ProviderAccessError` |
| `InvalidRequestError` | `shl.engine.translation.InvalidRequestError` |

---

## Changelog

| Version | Notes |
|---------|-------|
| 0.2.5 | Current — consolidated public API exposing logging, language validation, translation engine, provider adapters, and exceptions at the package level. |
