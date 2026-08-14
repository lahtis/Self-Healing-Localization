# SHL — Self-Healing Localization Library
## Complete Technical API Reference

> **Version:** 0.2.0  
> **Author:** Tuomas Lähteenmäki  
> **License:** MIT  
> **Scope:** Core engine, translation subsystem, providers, utilities, and GLFM integration.

---

## Table of Contents

1. [Core Public API (`shl/__init__.py`)](#1-core-public-api-shl__init__py)
2. [Logging Configuration (`logging_config.py`)](#2-logging-configuration-logging_configpy)
3. [Language Utilities (`utils/lang_utils.py`)](#3-language-utilities-utilslang_utilspy)
4. [GLFM Database Loader (`glfm_load_database.py`)](#4-glfm-database-loader-glfm_load_databasepy)
5. [Translation Subsystem Overview](#5-translation-subsystem-overview)
   - 5.1 [Module Index (`translation/__init__.py`)](#51-module-index-translation__init__py)
   - 5.2 [Metadata DTOs (`metadata.py`)](#52-metadata-dtos-metadatapy)
   - 5.3 [Exception Taxonomy (`exceptions.py`)](#53-exception-taxonomy-exceptionspy)
   - 5.4 [Translation Cache (`cache.py`)](#54-translation-cache-cachepy)
   - 5.5 [Deprecated AI Translator (`ai_translation_deprecated.py`)](#55-deprecated-ai-translator-ai_translation_deprecatedpy)
6. [Provider Architecture](#6-provider-architecture)
   - 6.1 [Base Interface (`providers/base.py`)](#61-base-interface-providersbasepy)
   - 6.2 [Providers Package (`providers/__init__.py`)](#62-providers-package-providers__init__py)
   - 6.3 [DeepL Adapter (`providers/deepl.py`)](#63-deepl-adapter-providersdeeplpy)
   - 6.4 [Google Cloud v2 Adapter (`providers/googleV2.py`)](#64-google-cloud-v2-adapter-providersgooglev2py)
   - 6.5 [Google Registry (`providers/google_registry.py`)](#65-google-registry-providersgoogle_registrypy)
   - 6.6 [LibreTranslate Adapter (`providers/libretranslate.py`)](#66-libretranslate-adapter-providerslibretranslatepy)
   - 6.7 [LibreTranslate Registry (`providers/libretranslate_registry.py`)](#67-libretranslate-registry-providerslibretranslate_registrypy)
   - 6.8 [LibreTranslate Mirrors (`providers/libretranslate_mirrors.py`)](#68-libretranslate-mirrors-providerslibretranslate_mirrorspy)
   - 6.9 [MyMemory Adapter (`providers/mymemory.py`)](#69-mymemory-adapter-providersmymemorypy)
   - 6.10 [MyMemory Registry (`providers/mymemory_registry.py`)](#610-mymemory-registry-providersmymemory_registrypy)
7. [Provider Capability Matrix](#7-provider-capability-matrix)
8. [Quick Start Examples](#8-quick-start-examples)

---

## 1. Core Public API (`shl/__init__.py`)

The `shl` package root aggregates the entire public API surface into a single importable namespace.

### Exports

| Category | Symbols |
|----------|---------|
| **Version** | `__version__`, `__author__`, `__license__` |
| **Logging** | `setup_logging`, `get_logger`, `set_level`, `get_log_stats` |
| **Language Validation** | `LanguageValidator` |
| **BCP-47 Utilities** | `parse_bcp47`, `normalize_full_tag`, `base_language`, `has_region`, `get_parent`, `split_tag` |
| **Translation (High-Level)** | `translate_text`, `get_best_provider`, `get_all_supported_languages`, `get_supported_languages`, `get_libretranslate_mirror_stats` |
| **Translation Cache** | `TranslationCache` |
| **Translation Metadata** | `TranslationRequest`, `TranslationResult` |
| **Provider Adapters** | `MyMemoryAdapter`, `LibreTranslateAdapter` |
| **Deprecated** | `AITranslator` |
| **Exceptions** | `TranslationError`, `RateLimitExceededError`, `ServiceUnavailableError`, `LanguageNotSupportedError`, `ProviderAccessError`, `InvalidRequestError` |

### Example

```python
import shl

shl.setup_logging("DEBUG")
result = shl.translate_text("Hello", "fi")
print(result)
```

---

## 2. Logging Configuration (`logging_config.py`)

Unified, dependency-free logging layer for SHL.

### Default Settings

| Setting | Value |
|---------|-------|
| Console level | `INFO` |
| File level | `WARNING` |
| Log file | `error.log` |
| Max file size | 1 MB |
| Backup count | 3 |

### API

| Function | Description |
|----------|-------------|
| `setup_logging(console_level=INFO, file_level=WARNING, log_file="error.log", max_bytes=1_024_000, backup_count=3, force=False)` | Initialize unified logging. Returns root logger. |
| `get_logger(name, add_shl_prefix=True)` | Get a logger in the `shl.*` namespace. |
| `set_level(level, logger_name=None)` | Change log level dynamically. |
| `remove_handler(handler_type, logger_name=None)` | Remove handlers by class name. Returns count removed. |
| `get_log_stats()` | Return dict with `initialized`, `handlers`, `log_files`, `log_file_size`, `backup_files`, `handler_types`. |
| `reset_logging()` | Clear all handlers and reset initialization state. |

### Features

- Console output via `StreamHandler` (stdout)
- Rotating file output via `RotatingFileHandler` (UTF-8)
- Safe re-initialization with `force=True`
- Automatic directory creation for log files
- Graceful degradation if file handler creation fails

---

## 3. Language Utilities (`utils/lang_utils.py`)

Single source of truth for BCP-47 language tag parsing and normalization.

### API

| Function | Signature | Returns | Description |
|----------|-----------|---------|-------------|
| `parse_bcp47` | `(lang_code: str)` | `(lang, script, region)` | Parse tag into components. Accepts hyphens/underscores, strips encoding suffixes. |
| `normalize_full_tag` | `(lang_code, default="en")` | `str` | Canonical lowercase tag for file naming / GLFM lookup. |
| `base_language` | `(lang_code, default="en")` | `str` | Extract bare language subtag (e.g. `"zh"` from `"zh-Hant-TW"`). |
| `has_region` | `(lang_code)` | `bool` | Check if tag contains a region subtag. |
| `get_parent` | `(lang_code, default="en")` | `str` | Parent tag without region (e.g. `"zh-hant"` from `"zh-Hant-TW"`). |
| `split_tag` | `(lang_code)` | `dict` | Structured dict with `language`, `script`, `region`, `tag`, `valid`. |
| `is_valid` | `(lang_code)` | `bool` | Check if tag is a valid BCP-47 code. |
| `normalize_language` | `(lang_code, default="en")` | `str` | Alias for `normalize_full_tag()`. |

### BCP-47 Regex

```
^([a-z]{2,3})                 # language
(?:-([a-z]{4}))?              # optional script
(?:-([a-z]{2}|\d{3}))?       # optional region
$
```

---

## 4. GLFM Database Loader (`glfm_load_database.py`)

Loads the Global Language Family Mapper (GLFM) database from gzipped JSON using only the standard library.

### Database Files

| Mode | File | Size |
|------|------|------|
| Lite | `languages_top20.json.gz` | ~428 KB |
| Full | `unified_languages.json.gz` | ~800 MB |

### API

| Function | Description |
|----------|-------------|
| `load_language_data(db_path=None)` | Load and cache GLFM data. Auto-falls back Lite → Full. |
| `get_glfm_data()` | Return cached data or `None`. |
| `clear_glfm_cache()` | Clear the in-memory cache. |
| `get_language_count()` | Return number of loaded languages (0 if not loaded). |
| `find_language(lang_code)` | Find language by ISO 639-1, ISO 639-3, or BCP-47 tag. |
| `is_lite_available()` | Check if Lite DB exists on disk. |
| `is_full_available()` | Check if Full DB exists on disk. |

### Error Handling

| Error | Cause |
|-------|-------|
| `FileNotFoundError` | Database file missing |
| `gzip.BadGzipFile` | Corrupted gzip archive |
| `json.JSONDecodeError` | Invalid JSON |
| `ValueError` | JSON root is not a dictionary |

---

## 5. Translation Subsystem Overview

```
translation/
├── __init__.py          # Public API manifest
├── router.py            # Routing & provider selection
├── metadata.py          # DTOs (TranslationRequest, TranslationResult)
├── exceptions.py        # Unified error taxonomy
├── cache.py             # In-memory translation cache
├── ai_translation_deprecated.py  # Legacy AITranslator
└── providers/
    ├── __init__.py
    ├── base.py
    ├── deepl.py
    ├── googleV2.py
    ├── google_registry.py
    ├── libretranslate.py
    ├── libretranslate_registry.py
    ├── libretranslate_mirrors.py
    ├── mymemory.py
    └── mymemory_registry.py
```

### 5.1 Module Index (`translation/__init__.py`)

Central export manifest for the translation subsystem.

#### Core Routing Functions

- `translate_text(text, target_lang, ...)` — Main translation with smart routing.
- `translate_text_with_metadata(...)` — Returns full `TranslationResult`.
- `get_best_provider(pair)` — Select optimal provider for a language pair.
- `get_provider_priority()` — Return provider priority ordering.
- `get_all_supported_languages()` — Combined language list from all providers.
- `get_supported_languages()` — LibreTranslate languages (legacy compat).
- `get_libretranslate_mirror_stats()` — Mirror latency & availability.
- `clear_unavailable_cache()` — Reset provider-unavailable cache.
- `get_unavailable_cache_stats()` — Provider failure statistics.

#### Cache, Metadata, Providers, Exceptions

See dedicated sections below.

#### Deprecated

- `AITranslator` — Legacy class preserved for backwards compatibility.

### 5.2 Metadata DTOs (`metadata.py`)

#### TranslationRequest

Three-tier metadata schema implemented as a `@dataclass`.

**Tier 1 — Core Pipeline** (all providers)

| Field | Type | Description |
|-------|------|-------------|
| `text` | `str` | Text to translate |
| `source_lang` | `str` | Source language code |
| `target_lang` | `str` | Target language code |

**Tier 2 — Context Controls** (DeepL, Google Cloud, LLM routers)

| Field | Type | Description |
|-------|------|-------------|
| `context_type` | `Optional[str]` | UI element type: `button`, `label`, `tooltip` |
| `domain` | `Optional[str]` | Application domain: `desktop_ui`, `web`, `mobile` |
| `formality` | `Optional[str]` | `formal` or `informal` |
| `glossary` | `Optional[Dict[str,str]]` | Term overrides |
| `html_format` | `bool` | Preserve HTML markup |

**Tier 3 — Internal Tracking** (SHL engine)

| Field | Type | Description |
|-------|------|-------------|
| `key` | `Optional[str]` | Logical identifier, e.g. `settings.save` |
| `screen` | `Optional[str]` | UI screen name |
| `component` | `Optional[str]` | UI component name |
| `source_id` | `Optional[str]` | Unique SHL identifier |
| `metadata` | `Dict[str, Any]` | Flexible extension dict |

#### TranslationResult

| Field | Type | Description |
|-------|------|-------------|
| `translated_text` | `str` | Final translated string |
| `source` | `str` | Provider name: `mymemory`, `libretranslate`, `deepl`, `google` |
| `confidence` | `Optional[float]` | Provider-dependent confidence score |
| `raw_response` | `Optional[Dict]` | Full provider response for debugging |
| `request_metadata` | `Optional[TranslationRequest]` | Original request object |

### 5.3 Exception Taxonomy (`exceptions.py`)

```
TranslationError (base)
├── ServiceUnavailableError   # Provider down / timeout / unreachable
├── RateLimitExceededError    # Quota or throttling
├── LanguageNotSupportedError # Unsupported language pair
├── ProviderAccessError       # Auth / API key failure
└── InvalidRequestError       # Malformed payload / bad parameters
```

All provider adapters map their native HTTP/network errors into this hierarchy.

### 5.4 Translation Cache (`cache.py`)

In-memory cache preventing redundant remote API calls.

```python
from shl.engine.translation.cache import TranslationCache

cache = TranslationCache(ttl=3600, max_size=10000)
cache.set("Hello", "Hei", "en", "fi")
result = cache.get("Hello", "en", "fi")  # "Hei"
```

| Method | Description |
|--------|-------------|
| `get(text, source_lang, target_lang, formality, context_type)` | Retrieve cached translation if fresh. |
| `set(text, translated, source_lang, target_lang, ...)` | Store translation with TTL timestamp. |
| `clear()` | Flush all entries. |
| `size()` | Return current entry count. |

**Eviction Strategy:**
1. Remove all expired entries (stale).
2. If still at capacity, remove the oldest entry.

**Key Generation:** Deterministic MD5 hash of `text:source:target:formality:context`.

### 5.5 Deprecated AI Translator (`ai_translation_deprecated.py`)

`AITranslator` is deprecated and emits a `DeprecationWarning` on import.

All methods are thin wrappers around the new `translate_text()` router function.

| Method | Modern Equivalent |
|--------|-------------------|
| `translate(text, target_lang, source_lang)` | `translate_text(...)` |
| `batch_translate(texts, target_lang, source_lang)` | Loop + `translate_text(...)` |
| `get_cache_stats()` | `get_unavailable_cache_stats()` |
| `clear_cache()` | `clear_unavailable_cache()` |

---

## 6. Provider Architecture

### 6.1 Base Interface (`providers/base.py`)

All providers inherit from `TranslationProvider` (ABC).

| Abstract Member | Description |
|-----------------|-------------|
| `translate(request: TranslationRequest) -> str` | Execute translation. |
| `build_request(request) -> Dict[str, Any]` | Construct provider-specific payload. |
| `name -> str` | Unique provider identifier. |
| `supported_features -> List[str]` | Optional: declare advanced metadata support. |
| `supports_feature(feature) -> bool` | Capability check (case-insensitive). |

### 6.2 Providers Package (`providers/__init__.py`)

```python
from shl.engine.translation.providers import (
    TranslationProvider,
    MyMemoryAdapter,
    LibreTranslateAdapter,
    DeepLAdapter,
    GoogleV2Adapter,
)
```

### 6.3 DeepL Adapter (`providers/deepl.py`)

High-quality translation with advanced metadata support.

**Constructor:**
```python
DeepLAdapter(api_key: str, use_free_api: bool = True)
```

**Supported Features:** `formality`, `context`, `glossary`, `html_format`

**Payload Fields:**
- `text` — list of strings
- `target_lang` — uppercase ISO code
- `source_lang` — optional (auto-detect if omitted)
- `context` — built from `domain`, `screen`, `component`, `context_type`, `key`
- `formality` — `"more"` (formal) or `"less"` (informal)
- `glossary_id` — from `request.glossary["id"]`
- `tag_handling` — `"html"` if `html_format=True`

**Error Mapping:**

| HTTP | SHL Exception |
|------|---------------|
| 401 / 403 | `ProviderAccessError` |
| 429 / 456 | `RateLimitExceededError` |
| 500+ | `ServiceUnavailableError` |
| 400 | `InvalidRequestError` |
| Timeout | `ServiceUnavailableError` |

### 6.4 Google Cloud v2 Adapter (`providers/googleV2.py`)

Dependency-free Basic API adapter with failover.

**Constructor:**
```python
GoogleV2Adapter(api_key: str, backup_api_key: Optional[str] = None)
```

**Failover Logic:**
1. Attempt with primary key.
2. On `ProviderAccessError`, `RateLimitExceededError`, or `ServiceUnavailableError` → retry with backup key.
3. If backup fails → re-raise primary error.

**Payload Fields:**
- `q` — list of strings
- `target` — target language
- `source` — optional source language
- `format` — `"html"` or `"text"`

**Note:** Google v2 does **not** support `glossary` or `labels` (Advanced/v3 features).

**Error Mapping:**

| HTTP | SHL Exception |
|------|---------------|
| 403 | `ProviderAccessError` |
| 429 | `RateLimitExceededError` |
| 500+ | `ServiceUnavailableError` |
| 400 | `InvalidRequestError` |

### 6.5 Google Registry (`providers/google_registry.py`)

Zero-network language pair validator for Google Cloud Translation.

```python
registry = GoogleRegistry(cache_ttl=86400.0)
registry.is_pair_supported("en", "fi")  # True
registry.mark_pair_unsupported("en", "ga")
registry.clear_blacklist()
```

- Uses `STANDARD_ISO_CODES` frozenset (ISO 639-1 + BCP-47 regional codes).
- TTL-based blacklisting of unsupported pairs.
- Prevents wasteful API calls.

### 6.6 LibreTranslate Adapter (`providers/libretranslate.py`)

Lightweight open-source translation adapter.

**Constructor:**
```python
LibreTranslateAdapter(
    base_url: Optional[str] = "https://libretranslate.com",
    api_key: Optional[str] = None,
    cache_ttl: float = 86400.0,
)
```

**Fast-Fail:** Checks `LibreTranslateRegistry` before every network call.

**Payload Fields:**
- `q` — text
- `source` / `target` — language codes
- `format` — always `"text"`
- `api_key` — optional

**Error Mapping:**

| HTTP | SHL Exception |
|------|---------------|
| 403 | `ProviderAccessError` |
| 429 | `RateLimitExceededError` |
| 500+ | `ServiceUnavailableError` |
| 404 | `LanguageNotSupportedError` |
| 400 (language) | `LanguageNotSupportedError` |
| 400 (other) | `InvalidRequestError` |

**API Key Masking:**
Logs mask long keys as `abcd********wxyz`.

### 6.7 LibreTranslate Registry (`providers/libretranslate_registry.py`)

Validates language pairs against the Argos OpenNMT index.

- `STANDARD_ISO_CODES` includes special codes: `pb`, `zh`, `zt`.
- Same TTL-blacklist pattern as other registries.

### 6.8 LibreTranslate Mirrors (`providers/libretranslate_mirrors.py`)

Production-grade mirror management for high availability.

#### Classes

**LibreTranslateMirror**

| Attribute | Description |
|-----------|-------------|
| `url` | Mirror base URL |
| `weight` | Priority weight (higher = preferred) |
| `api_key_env` | Environment variable for API key |
| `timeout` | Health-check timeout |
| `status` | `unknown`, `available`, `unavailable`, `degraded` |
| `last_latency` | Measured latency in ms |
| `supported_languages` | Normalized language map |

**LibreTranslateMirrorManager**

| Method | Description |
|--------|-------------|
| `get_best_mirror(force_test=False)` | Select optimal mirror by weight + latency. |
| `get_mirror_for_language(target, source="en")` | Find mirror supporting the language pair. |
| `update_mirror_status(url, available)` | Manual status override. |
| `get_mirror_stats()` | List of dicts with mirror diagnostics. |
| `clear_cache()` | Reset all mirror states. |

**Mirror Discovery:**
1. `.env` variables matching `LIBRETRANSLATE_MIRROR_*`
2. Process environment variables
3. Hardcoded `DEFAULT_MIRRORS`

### 6.9 MyMemory Adapter (`providers/mymemory.py`)

Free public translation API adapter.

**Constructor:**
```python
MyMemoryAdapter(email: Optional[str] = None, cache_ttl: Optional[float] = None)
```

- Uses a **module-level shared** `MyMemoryRegistry` instance.
- Email unlocks higher daily quota (10k words vs 1k anonymous).

**Payload Fields:**
- `q` — text
- `langpair` — `"source|target"`
- `de` — optional email

**Error Mapping:**

| Condition | SHL Exception |
|-----------|---------------|
| `quotaReached` or quota warning | `RateLimitExceededError` |
| 403 | `ProviderAccessError` |
| 429 | `RateLimitExceededError` |
| 500+ | `ServiceUnavailableError` |
| 404 | `LanguageNotSupportedError` |
| 400 (language) | `LanguageNotSupportedError` |
| 400 (other) | `InvalidRequestError` |

### 6.10 MyMemory Registry (`providers/mymemory_registry.py`)

Validates against MyMemory's supported ISO + regional codes.

- Includes regional variants: `zh-cn`, `zh-tw`, `pt-br`.
- Shared module-level registry persists across adapter instances.

---

## 7. Provider Capability Matrix

| Provider | Formality | Glossary | HTML | Context | Failover | Registry | Mirrors |
|----------|:---------:|:--------:|:----:|:-------:|:--------:|:--------:|:-------:|
| **DeepL** | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Google v2** | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ |
| **LibreTranslate** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| **MyMemory** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |

---

## 8. Quick Start Examples

### Basic Translation

```python
from shl import translate_text

print(translate_text("Hello world", "fi"))
```

### With Metadata (DeepL)

```python
from shl.engine.translation import translate_text_with_metadata
from shl.engine.translation.metadata import TranslationRequest

req = TranslationRequest(
    text="Save",
    source_lang="en",
    target_lang="fi",
    context_type="button",
    formality="formal",
    screen="settings",
)

result = translate_text_with_metadata(req)
print(result.translated_text)
```

### Direct Provider Usage

```python
from shl.engine.translation.providers import DeepLAdapter
from shl.engine.translation.metadata import TranslationRequest

deepl = DeepLAdapter(api_key="YOUR_KEY")
req = TranslationRequest(text="Hello", source_lang="en", target_lang="de")
print(deepl.translate(req))
```

### Logging Setup

```python
from shl import setup_logging, get_logger
import logging

setup_logging(console_level=logging.DEBUG, file_level=logging.ERROR)
log = get_logger(__name__)
log.info("SHL ready")
```

### Language Utilities

```python
from shl import parse_bcp47, base_language, normalize_full_tag

print(parse_bcp47("zh-Hant-TW"))        # ('zh', 'hant', 'tw')
print(base_language("zh-Hant-TW"))      # 'zh'
print(normalize_full_tag("EN-us"))      # 'en-us'
```

### GLFM Database

```python
from shl.glfm_load_database import load_language_data, find_language

db = load_language_data()
print(find_language("fi"))
```

### Exception Handling

```python
from shl import translate_text
from shl.engine.translation.exceptions import (
    TranslationError,
    RateLimitExceededError,
    LanguageNotSupportedError,
)

try:
    result = translate_text("Hello", "xx")
except LanguageNotSupportedError:
    print("Language not supported")
except RateLimitExceededError:
    print("Quota exceeded — retry later")
except TranslationError as e:
    print(f"Translation failed: {e}")
```

---

*End of API Reference — Self-Healing Localization Layer v0.2.0*
