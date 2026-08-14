# SHL — Self-Healing Localization Library
## Complete Technical API Reference

> **Version:** 0.2.2  
> **Author:** Tuomas Lähteenmäki  
> **License:** MIT  
> **Scope:** Core engine, translation subsystem, providers, utilities, and GLFM integration.

---

## Version History

### 0.2.2

- Updated the technical API reference to match the 0.2.2 implementation.
- Removed the deleted `AITranslator` API from the documentation.
- Clarified the GLFM Lite and Full database roles.
- Documented dynamic `lang_code` lookup.
- Documented precomputed GLFM language distances.
- Clarified the provider fallback architecture.
- Documented AI routing and audit as planned extension layers, not completed core functionality.
- Kept the core engine intentionally small and provider-agnostic.
```

---

## Table of Contents

1. [Core Public API (`shl/__init__.py`)](#1-core-public-api-shl__init__py)
2. [Logging Configuration (`logging_config.py`)](#2-logging-configuration-logging_configpy)
3. [Language Utilities (`utils/lang_utils.py`)](#3-language-utilities-utilslang_utilspy)
4. [GLFM Database Loader (`glfm_load_database.py`)](#4-glfm-database-loader-glfm_load_databasepy)
5. [Language Validation and Fallback](#5-language-validation-and-fallback)
6. [Translation Subsystem Overview](#6-translation-subsystem-overview)
7. [Provider Architecture](#7-provider-architecture)
8. [Metadata and Cache](#8-metadata-and-cache)
9. [Provider Capability Matrix](#9-provider-capability-matrix)
10. [Fallback and AI Audit Design](#10-fallback-and-ai-audit-design)
11. [Quick Start Examples](#11-quick-start-examples)

---

# 1. Version (`shl/_version.py`)

| Category | Symbols |
| :-- | :-- |
| **Version** | `__version__`, `__author__`, `__license__` |

# 1. Core Public API (`shl/__init__.py`)

The `shl` package root aggregates the public API into a single importable namespace.

## Exports

| Category | Symbols |
| :-- | :-- |
| **Logging** | `setup_logging`, `get_logger`, `set_level`, `get_log_stats` |
| **Language Validation** | `LanguageValidator` |
| **BCP-47 Utilities** | `parse_bcp47`, `normalize_full_tag`, `base_language`, `has_region`, `get_parent`, `split_tag` |
| **Translation** | `translate_text`, `translate_text_with_metadata`, `get_best_provider` |
| **Provider Discovery** | `get_all_supported_languages`, `get_supported_languages`, `get_provider_priority` |
| **LibreTranslate** | `get_libretranslate_mirror_stats` |
| **Cache** | `TranslationCache` |
| **Metadata** | `TranslationRequest`, `TranslationResult` |
| **Provider Adapters** | `MyMemoryAdapter`, `LibreTranslateAdapter`, `DeepLAdapter`, `GoogleV2Adapter` |
| **Exceptions** | `TranslationError`, `RateLimitExceededError`, `ServiceUnavailableError`, `LanguageNotSupportedError`, `ProviderAccessError`, `InvalidRequestError` |

## Example

```python
import shl

shl.setup_logging("DEBUG")

result = shl.translate_text("Hello", "fi")
print(result)
```

---

# 2. Logging Configuration (`shl/logging_config.py`)

Unified, dependency-free logging layer for SHL.

## Default Settings

| Setting | Default |
| :-- | :-- |
| Console level | `INFO` |
| File level | `WARNING` |
| Log file | `error.log` |
| Maximum file size | 1 MB |
| Backup count | 3 |
| Encoding | UTF-8 |

## API

| Function | Description |
| :-- | :-- |
| `setup_logging(console_level=INFO, file_level=WARNING, log_file="error.log", max_bytes=1_024_000, backup_count=3, force=False)` | Initializes unified logging and returns the root logger. |
| `get_logger(name, add_shl_prefix=True)` | Returns a logger in the `shl.*` namespace. |
| `set_level(level, logger_name=None)` | Changes log level dynamically. |
| `remove_handler(handler_type, logger_name=None)` | Removes handlers by class name and returns the number removed. |
| `get_log_stats()` | Returns logging state and handler statistics. |
| `reset_logging()` | Removes handlers and resets initialization state. |

## Features

- Console output via `StreamHandler`.
- Rotating file output via `RotatingFileHandler`.
- UTF-8 file logging.
- Safe reinitialization with `force=True`.
- Automatic log-directory creation.
- Graceful degradation if file logging cannot be initialized.

---

# 3. Language Utilities (`utils/lang_utils.py`)

`lang_utils.py` is the shared source of truth for BCP-47 parsing and language-code normalization.

## API

| Function | Signature | Returns | Description |
| :-- | :-- | :-- | :-- |
| `parse_bcp47` | `(lang_code: str)` | `(language, script, region)` | Parses a BCP-47-like tag. |
| `normalize_full_tag` | `(lang_code, default="en")` | `str` | Normalizes a complete language tag. |
| `base_language` | `(lang_code, default="en")` | `str` | Returns the base language subtag. |
| `has_region` | `(lang_code)` | `bool` | Checks whether a region is present. |
| `get_parent` | `(lang_code, default="en")` | `str` | Removes the region component. |
| `split_tag` | `(lang_code)` | `dict` | Returns structured tag components. |
| `is_valid` | `(lang_code)` | `bool` | Checks basic language-tag validity. |
| `normalize_language` | `(lang_code, default="en")` | `str` | Alias for `normalize_full_tag()`. |

## BCP-47 Pattern

The utility layer supports language tags with:

```text
language
language-script
language-region
language-script-region
```

Example:

```python
parse_bcp47("zh-Hant-TW")
# ("zh", "hant", "tw")
```

Normalization is performed before language lookup where appropriate. GLFM lookup itself is always driven by the runtime `lang_code`; language codes are not hard-coded to a specific language such as `fin`.

---

# 4. GLFM Database Loader (`utils/glfm_load_database.py`)

GLFM is a separate MIT-licensed project providing language metadata, language relationships, and precomputed fallback information.

SHL uses GLFM as a language and fallback data source. GLFM does not perform the actual translation.

## GLFM Responsibilities

GLFM provides:

- language identifiers;
- ISO 639 mappings;
- BCP-47 information;
- default region and script;
- written-language metadata;
- language-family metadata;
- URIEL/lang2vec-derived features;
- precomputed language distances;
- nearest-language relationships;
- fallback candidates.

The language-distance data is calculated before runtime and stored in the database. SHL does not recalculate URIEL/lang2vec distances during a translation request.

## Database Models

| Mode | File | Description |
| :-- | :-- | :-- |
| **Lite** | `languages_top20.json.gz` | Covers approximately 4,700 languages. Each language contains its 20 nearest related languages. |
| **Full** | `unified_languages.json.gz` | Contains approximately 4,200 languages with broad language-to-language comparison data. |

Lite is not a small language list. It covers the full language set but stores a limited nearest-language neighborhood for each language.

## Typical Lite Record

```json
{
  "id": "fin",
  "iso639_1": "fi",
  "iso639_3": "fin",
  "bcp47": "fi-Latn-FI",
  "default_region": "FI",
  "default_script": "Latn",
  "distance_source": "lang2vec / URIEL",
  "distance_type": "fam",
  "written": true,
  "written_scripts": ["Latn"],
  "nearest_languages": [
    {
      "lang": "est",
      "distance": 0.0003
    },
    {
      "lang": "izh",
      "distance": 0.0003
    }
  ]
}
```


## Meaning of `distance`

The `distance` value is a precomputed GLFM relationship value.

It can be used as:

- a language-similarity metadata value;
- a fallback-priority signal;
- an input to confidence calculation;
- an AI-audit context value;
- a diagnostic value in logs and cache records.

The value does not independently guarantee translation quality. Structural or genealogical language similarity is not the same as translation quality.

The current fallback implementation preserves the order supplied by GLFM. It does not recalculate or resort language distances at runtime.

## API

| Function | Description |
| :-- | :-- |
| `load_language_data(db_path=None)` | Loads and caches compressed GLFM JSON data. |
| `get_glfm_data()` | Returns cached data or `None`. |
| `clear_glfm_cache()` | Clears the in-memory GLFM cache. |
| `get_language_count()` | Returns the count of loaded languages. |
| `find_language(lang_code)` | Finds a language by supported code or tag. |
| `is_lite_available()` | Checks whether Lite data is available. |
| `is_full_available()` | Checks whether Full data is available. |

## Error Handling

| Error | Cause |
| :-- | :-- |
| `FileNotFoundError` | Database file is missing. |
| `gzip.BadGzipFile` | Gzip archive is corrupt. |
| `json.JSONDecodeError` | JSON content is invalid. |
| `ValueError` | JSON root is not a dictionary. |

The compressed data is stored in the library's data directory. SHL should use its loader rather than duplicating gzip and JSON-loading logic elsewhere in the codebase.

---

# 5. Language Validation and Fallback

`LanguageValidator` provides optional GLFM-based language validation, BCP-47 metadata access, and fallback-chain generation.

## Constructor

```python
LanguageValidator(
    glfm_path: Optional[str] = None,
    base_language: str = "en",
    use_lite: bool = True,
)
```


## Parameters

| Parameter | Description |
| :-- | :-- |
| `glfm_path` | Optional custom GLFM database path. |
| `base_language` | Developer-defined final fallback language. |
| `use_lite` | Uses Lite when `True`, Full when `False`. |

Lite is the default because it is always distributed with the package and is substantially smaller. Full is an optional broader dataset when available.

## Runtime Language Lookup

The validator uses the supplied `lang_code` dynamically:

```python
info = validator.get_language_info(lang_code)
```

It does not assume that the requested language is Finnish or use `fin` as a hard-coded key.

Lookup order:

1. ISO 639-1 index;
2. direct language ID;
3. normalized full tag;
4. ISO 639-3 linear fallback lookup.

## Public Properties

| Property | Description |
| :-- | :-- |
| `is_loaded` | Whether GLFM data is loaded and contains records. |
| `is_lite` | Whether Lite mode is active. |
| `max_nearest` | Maximum nearest-language count; 20 for Lite and unlimited for Full. |

## Public Methods

| Method | Description |
| :-- | :-- |
| `is_valid(lang_code, strict=False)` | Validates a language code against GLFM. |
| `get_bcp47(lang_code)` | Returns the GLFM BCP-47 tag. |
| `get_fallback(lang_code)` | Returns the record-level GLFM fallback. |
| `get_language_info(lang_code)` | Returns the complete GLFM record. |
| `get_name(lang_code)` | Returns the language name. |
| `get_region(lang_code)` | Returns the region from the tag. |
| `get_written_scripts(lang_code)` | Returns the language's written scripts. |
| `get_default_script(lang_code)` | Returns the default script. |
| `get_family(lang_code)` | Returns the family value when available. |
| `get_fallback_chain(...)` | Builds a complete fallback chain. |
| `get_best_available_fallback(...)` | Selects the first available language from a chain. |

## Fallback Chain Order

The current order is:

```text
1. Normalized full tag
2. Base language
3. GLFM record-level fallback
4. GLFM nearest languages
5. ISO 639-5 family, if present
6. Developer-defined base language
7. English
```

Example:

```python
chain = validator.get_fallback_chain(
    lang_code="fin",
    base_language="en",
)
```

The nearest-language records are read from:

```python
info["nearest_languages"]
```

Each item contains a language code and a precomputed distance:

```python
{
    "lang": "est",
    "distance": 0.0003,
}
```

The public fallback chain currently returns language codes. Distance values remain available through `get_language_info()` for metadata, routing, diagnostics, and later audit integration.

## `get_best_available_fallback`

```python
candidate = validator.get_best_available_fallback(
    lang_code="fin",
    available_languages=["en", "fi", "et"],
    base_language="en",
)
```

The method walks the fallback chain and returns the first matching provider/application language.

Provider integrations should normalize language identifiers before comparison because a provider may use:

```text
fi
fin
fi-FI
fi-Latn-FI
```

for the same or related language target.

---

# 6. Translation Subsystem Overview

```text
translation/
├── __init__.py
├── router.py
├── metadata.py
├── exceptions.py
├── cache.py
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


## 6.1 Module Index

### Core Routing Functions

- `translate_text(text, target_lang, ...)`
- `translate_text_with_metadata(...)`
- `get_best_provider(pair)`
- `get_provider_priority()`
- `get_all_supported_languages()`
- `get_supported_languages()`
- `get_libretranslate_mirror_stats()`
- `clear_unavailable_cache()`
- `get_unavailable_cache_stats()`

---

# 7. Provider Architecture

## 7.1 Base Interface (`shl/engine/translation/providers/base.py`)

All providers implement the `TranslationProvider` abstraction.


| Member | Description |
| :-- | :-- |
| `translate(request: TranslationRequest) -> str` | Executes the translation. |
| `build_request(request) -> Dict[s

tr, Any]` | Builds provider-specific payload. |
| `name -> str` | Unique provider name. |
| `supported_features -> List[str]` | Provider feature declarations. |
| `supports_feature(feature) -> bool` | Case-insensitive feature check. |

## 7.2 Providers Package

```python
from shl.engine.translation.providers import (
    TranslationProvider,
    MyMemoryAdapter,
    LibreTranslateAdapter,
    DeepLAdapter,
    GoogleV2Adapter,
)
```


## 7.3 DeepL Adapter

```python
DeepLAdapter(
    api_key: str,
    use_free_api: bool = True,
)
```


### Supported Features

- `formality`;
- `context`;
- `glossary`;
- `html_format`.


### Payload Fields

- `text`;
- `target_lang`;
- `source_lang`;
- `context`;
- `formality`;
- `glossary_id`;
- `tag_handling`.


### Error Mapping

| HTTP / Condition | SHL Exception |
| :-- | :-- |
| 401 / 403 | `ProviderAccessError` |
| 429 / 456 | `RateLimitExceededError` |
| 500+ | `ServiceUnavailableError` |
| 400 | `InvalidRequestError` |
| Timeout | `ServiceUnavailableError` |

## 7.4 Google Cloud v2 Adapter

```python
GoogleV2Adapter(
    api_key: str,
    backup_api_key: Optional[str] = None,
)
```


### Failover

1. Try the primary key.
2. On access, quota, or availability failure, try the backup key.
3. If the backup fails, raise the primary error.

### Payload

- `q`;
- `target`;
- optional `source`;
- `format`.

Google v2 does not expose the glossary and labels functionality of the advanced API.

## 7.5 Google Registry

```python
registry = GoogleRegistry(cache_ttl=86400.0)

registry.is_pair_supported("en", "fi")
registry.mark_pair_unsupported("en", "ga")
registry.clear_blacklist()
```

The registry performs local language-pair checks and caches unsupported pairs.

## 7.6 LibreTranslate Adapter

```python
LibreTranslateAdapter(
    base_url="https://libretranslate.com",
    api_key=None,
    cache_ttl=86400.0,
)
```


### Payload

- `q`;
- `source`;
- `target`;
- `format`;
- optional `api_key`.


### Error Mapping

| HTTP / Condition | SHL Exception |
| :-- | :-- |
| 403 | `ProviderAccessError` |
| 429 | `RateLimitExceededError` |
| 500+ | `ServiceUnavailableError` |
| 404 | `LanguageNotSupportedError` |
| 400 language error | `LanguageNotSupportedError` |
| Other 400 | `InvalidRequestError` |

API keys are masked in logs.

## 7.7 LibreTranslate Registry

The registry validates language pairs against the Argos/OpenNMT support index and maintains a TTL-based unsupported-pair cache.

Special normalized codes include:

```text
pb
zh
zt
```


## 7.8 LibreTranslate Mirrors

`LibreTranslateMirrorManager` supports:

- mirror discovery;
- language-pair selection;
- health checks;
- latency measurement;
- availability states;
- weighted mirror selection;
- diagnostics.


### Mirror Statuses

```text
unknown
available
unavailable
degraded
```


### Main Methods

| Method | Description |
| :-- | :-- |
| `get_best_mirror(force_test=False)` | Selects the preferred mirror. |
| `get_mirror_for_language(target, source="en")` | Finds a mirror supporting the pair. |
| `update_mirror_status(url, available)` | Applies a manual status update. |
| `get_mirror_stats()` | Returns mirror diagnostics. |
| `clear_cache()` | Clears mirror state. |

## 7.9 MyMemory Adapter

```python
MyMemoryAdapter(
    email: Optional[str] = None,
    cache_ttl: Optional[float] = None,
)
```

The adapter uses a shared registry instance.

Email configuration can provide a higher public quota than anonymous use.

## 7.10 MyMemory Registry

The registry validates ISO and regional language codes, including variants such as:

```text
zh-cn
zh-tw
pt-br
```


---

# 8. Metadata and Cache

## 8.1 `TranslationRequest`

`TranslationRequest` is a dataclass containing three metadata levels.

### Tier 1 — Core Pipeline

| Field | Type | Description |
| :-- | :-- | :-- |
| `text` | `str` | Text to translate. |
| `source_lang` | `str` | Source language. |
| `target_lang` | `str` | Requested target language. |

### Tier 2 — Context

| Field | Type | Description |
| :-- | :-- | :-- |
| `context_type` | `Optional[str]` | UI type such as `button`, `label`, or `tooltip`. |
| `domain` | `Optional[str]` | Application domain. |
| `formality` | `Optional[str]` | Formality preference. |
| `glossary` | `Optional[Dict[str, str]]` | Term overrides or provider glossary information. |
| `html_format` | `bool` | Whether markup must be preserved. |

### Tier 3 — Internal Tracking

| Field | Type | Description |
| :-- | :-- | :-- |
| `key` | `Optional[str]` | Logical translation key. |
| `screen` | `Optional[str]` | UI screen. |
| `component` | `Optional[str]` | UI component. |
| `source_id` | `Optional[str]` | Unique SHL identifier. |
| `metadata` | `Dict[str, Any]` | Extension metadata. |

GLFM information can be stored in metadata without coupling core DTO fields directly to the GLFM schema:

```python
request.metadata["glfm"] = {
    "requested_language": "fin",
    "fallback_language": "est",
    "distance": 0.0003,
}
```


## 8.2 `TranslationResult`

| Field | Type | Description |
| :-- | :-- | :-- |
| `translated_text` | `str` | Translation result. |
| `source` | `str` | Provider or generation source. |
| `confidence` | `Optional[float]` | Provider or router confidence. |
| `raw_response` | `Optional[Dict]` | Raw provider response. |
| `request_metadata` | `Optional[TranslationRequest]` | Original request. |

Possible future source labels include:

```text
google
deepl
libretranslate
mymemory
ai_generated
ai_corrected
fallback_translation
human_verified
```

These labels should be introduced consistently if AI routing is implemented.

## 8.3 Exception Taxonomy

```text
TranslationError
├── ServiceUnavailableError
├── RateLimitExceededError
├── LanguageNotSupportedError
├── ProviderAccessError
└── InvalidRequestError
```

Provider-native errors are mapped into this hierarchy.

## 8.4 Translation Cache

The cache prevents redundant provider calls.

```python
from shl.engine.translation.cache import TranslationCache

cache = TranslationCache(
    ttl=3600,
    max_size=10000,
)

cache.set("Hello", "Hei", "en", "fi")
result = cache.get("Hello", "en", "fi")
```


### Methods

| Method | Description |
| :-- | :-- |
| `get(text, source_lang, target_lang, formality, context_type)` | Returns a fresh cached result. |
| `set(text, translated, source_lang, target_lang, ...)` | Stores a result. |
| `clear()` | Flushes the cache. |
| `size()` | Returns current entry count. |

### Eviction

1. Remove expired entries.
2. If capacity is still exceeded, remove the oldest entry.

### Cache Identity

The cache key is deterministic and includes the text, language pair, and relevant context fields.

If fallback and AI routing are added, the cache identity should also preserve at least:

- requested language;
- actually used language;
- provider;
- fallback chain or fallback language;
- audit status;
- prompt/model version where relevant.

---

# 9. Provider Capability Matrix

| Provider | Formality | Glossary | HTML | Context | Failover | Registry | Mirrors |
| :-- | :--: | :--: | :--: | :--: | :--: | :--: | :--: |
| **DeepL** | + | + | + | + | - | - | - |
| **Google v2** | - | - | + | - | + | + | - |
| **LibreTranslate** | - | - | - | - | - | + | + |
| **MyMemory** | - | - | - | - | - | + | - |


---

# 10. Fallback and AI Audit Design

## 10.1 Translation Flow

The intended translation pipeline is:

```text
Router
    ↓
Google / DeepL / LibreTranslate / MyMemory
    ↓
GLFM fallback chain when required
    ↓
Metadata and cache
    ↓
Confidence evaluation
    ├── sufficient → final result
    └── insufficient → AI Router
```

GLFM supplies language and fallback information. It does not translate text.

## 10.2 GLFM Fallback Role

For an unsupported or unavailable requested language:

```text
requested language
    ↓
GLFM language record
    ↓
20 nearest Lite languages
    ↓
provider-supported candidate
```

The GLFM `distance` value describes the precomputed language relationship and can be carried through the pipeline:

```json
{
  "requested_language": "fin",
  "fallback_language": "est",
  "glfm_distance": 0.0003,
  "provider": "deepl"
}
```

The distance is a routing and audit signal, not a direct translation-quality guarantee.

## 10.3 AI Router

The AI Router is planned for difficult or unavailable translations.

It may be invoked when:

- no provider supports the requested language;
- no fallback provider produces a usable result;
- provider results disagree;
- confidence is too low;
- the text is context-sensitive;
- terminology or placeholders appear corrupted;
- the source text is ambiguous.

The AI may:

- accept a provider result;
- correct a provider result;
- produce a new translation;
- compare multiple candidate translations;
- mark the result for human review;
- report that no reliable translation can be produced.


## 10.4 AI Input Context

An AI audit request may contain:

```json
{
  "source_text": "Save",
  "source_language": "en",
  "requested_language": "vot",
  "fallback_chain": ["vot", "izh", "liv", "est", "en"],
  "fallback_language": "est",
  "glfm_distance": 0.0003,
  "provider_translation": "...",
  "provider": "deepl",
  "confidence": 0.61,
  "context": {
    "context_type": "button",
    "screen": "settings",
    "component": "save_button"
  }
}
```


## 10.5 AI Output Requirements

AI output must preserve:

- the intended meaning;
- requested or explicitly selected target language;
- placeholders;
- variables;
- HTML and Markdown structure;
- numbers and units;
- technical terms;
- required tone and context.

The AI must be allowed to return an uncertain result rather than inventing a confident-looking translation.

Possible result states:

```text
accepted
corrected
ai_generated
review_required
unavailable
```

Example:

```json
{
  "translated_text": "...",
  "source": "ai_generated",
  "confidence": 0.68,
  "status": "review_required",
  "requested_language": "vot",
  "fallback_language": "fin"
}
```


## 10.6 Core Boundary

The core engine should not contain:

- provider-specific HTTP logic;
- GLFM file-format logic;
- URIEL/lang2vec calculations;
- AI model integrations;
- prompt construction;
- audit policy implementation.

These belong in separate adapters, providers, or integration modules.

---

# 11. Quick Start Examples

## 11.1 Basic Translation

```python
from shl import translate_text

result = translate_text("Hello world", "fi")
print(result)
```


## 11.2 Translation with Metadata

```python
from shl.engine.translation import translate_text_with_metadata
from shl.engine.translation.metadata import TranslationRequest

request = TranslationRequest(
    text="Save",
    source_lang="en",
    target_lang="fi",
    context_type="button",
    formality="formal",
    screen="settings",
)

result = translate_text_with_metadata(request)

print(result.translated_text)
print(result.source)
print(result.confidence)
```


## 11.3 Direct Provider Usage

```python
from shl.engine.translation.providers import DeepLAdapter
from shl.engine.translation.metadata import TranslationRequest

deepl = DeepLAdapter(api_key="YOUR_KEY")

request = TranslationRequest(
    text="Hello",
    source_lang="en",
    target_lang="de",
)

result = deepl.translate(request)
print(result)
```


## 11.4 Logging

```python
from shl import setup_logging, get_logger
import logging

setup_logging(
    console_level=logging.DEBUG,
    file_level=logging.ERROR,
)

logger = get_logger(__name__)
logger.info("SHL ready")
```


## 11.5 Language Utilities

```python
from shl import (
    parse_bcp47,
    base_language,
    normalize_full_tag,
)

print(parse_bcp47("zh-Hant-TW"))
# ("zh", "hant", "tw")

print(base_language("zh-Hant-TW"))
# "zh"

print(normalize_full_tag("EN-us"))
# "en-us"
```


## 11.6 GLFM Loader

```python
from shl.glfm_load_database import (
    load_language_data,
    find_language,
)

database = load_language_data()

language = find_language("fi")

if language:
    print(language.get("bcp47"))
    print(language.get("nearest_languages", [])[:10])
```


## 11.7 `LanguageValidator` with Dynamic `lang_code`

```python
from shl.language_validator import LanguageValidator

validator = LanguageValidator(
    base_language="en",
    use_lite=True,
)

lang_code = "fin"

if validator.is_valid(lang_code):
    info = validator.get_language_info(lang_code)

    print(info.get("bcp47"))
    print(validator.get_fallback_chain(
        lang_code,
        base_language="en",
    ))
```

The implementation uses the supplied `lang_code`. The example uses `fin` only as a sample value; the library does not hard-code Finnish.

## 11.8 Best Available Fallback

```python
from shl.language_validator import LanguageValidator

validator = LanguageValidator()

available = ["en", "fi", "et"]

candidate = validator.get_best_available_fallback(
    lang_code="fin",
    available_languages=available,
    base_language="en",
)

print(candidate)
```

Provider integrations should normalize identifiers before matching `fin`, `fi`, and BCP-47 variants.

## 11.9 Exception Handling

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
    print("Language is not supported")
except RateLimitExceededError:
    print("Provider quota exceeded")
except TranslationError as error:
    print(f"Translation failed: {error}")
```


---

## Version Notes

Version 0.2.2 provides the working foundation for provider-based localization and GLFM-assisted fallback.

The current architecture intentionally separates:

```text
Core engine
    ↓
Translation providers
    ↓
GLFM language/fallback data
    ↓
Metadata and cache
    ↓
Future confidence and AI audit layers
```

GLFM is an independent project and data source. SHL consumes its loader and language records; it does not reproduce GLFM's precomputation or language-distance algorithms inside the core.

---

*End of API Reference — Self-Healing Localization Layer v0.2.2*

---







## Version History

### 0.2.2

- Updated the technical API reference to match the 0.2.2 implementation.
- Removed the deleted `AITranslator` API from the documentation.
- Clarified the GLFM Lite and Full database roles.
- Documented dynamic `lang_code` lookup.
- Documented precomputed GLFM language distances.
- Clarified the provider fallback architecture.
- Documented AI routing and audit as planned extension layers, not completed core functionality.
- Kept the core engine intentionally small and provider-agnostic.
```


## Testauksen tavoite

Lopuksi pitää olla sama versio kaikissa näissä:

```text
pyproject.toml / setup configuration
shl.__version__
dokumentaatio
test metadata
testiraportit
release notes
```

Tavoitetila:

```text
Kirjasto:      0.2.2
Dokumentaatio: 0.2.2
Testit:        0.2.2
```

Tärkeää on myös erottaa versionumeron päivitys toiminnallisista muutoksista: jos 0.2.2 sisältää dokumentaation, testien rajapinnan mukautuksia, ne kirjataan muutoksiksi, mutta uusia keskeneräisiä AI- tai Full GLFM -ominaisuuksia ei pidä kuvata valmiina.

---

# Luultavasti lisän dokumentit myös git version  alkaen doc/v022/en/  josta v022 on versio numero. Jolloin saan pysymään dokumentit ajantasalla.

Se on hyvä ja selkeä ratkaisu. Dokumentaatio kannattaa versionoida Gitissä omiin hakemistoihinsa, esimerkiksi:

```text
docs/
└── v022/
    └── en/
        └── technical_api_reference.md
```


## Suositeltu rakenne

Jos mukaan tulee myöhemmin suomenkielinen dokumentaatio:

```text
docs/
└── v022/
    ├── en/
    │   ├── technical_api_reference.md
    │   ├── quickstart.md
    │   └── changelog.md
    └── fi/
        ├── technical_api_reference.md
        ├── quickstart.md
        └── changelog.md










