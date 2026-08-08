# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)  
and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [0.2.0] - 2026-08-08 - dev log

### Added
- **GLFM (Global Language Family Mapper) integration** via `LanguageValidator` class
  - 7,900+ language database with BCP-47 tags, fallback chains, and validation
  - **GLFM Lite mode** (default): ~428 KB, 20 nearest languages for fallback
  - **Full GLFM mode**: ~925 MB, all 7,900+ languages for research and AI
- **Smart translation routing**: Automatically selects the best translation service (MyMemory or LibreTranslate) based on language pair support
- **Automatic provider fallback**: If primary service fails (rate limit, downtime, etc.), falls back to secondary service
- **LibreTranslate mirror support**: Automatic failover between multiple LibreTranslate instances
- **Comprehensive error classification**:
  - `RateLimitExceededError` - quota or rate limit exceeded
  - `ServiceUnavailableError` - service down or unreachable
  - `LanguageNotSupportedError` - language not supported by service
  - `ProviderAccessError` - access denied (banned, invalid API key)
  - `InvalidRequestError` - bad request parameters
  - `TranslationError` - base exception for all translation errors
- **Translation metadata**: `TranslationRequest` and `TranslationResult` dataclasses for future AI providers (DeepL, Google Cloud)
- **Translation cache**: MD5-based with TTL and size limit
- **Static fallback language lists** from JSON files (`data/languages/mymemory_fallback.json` and `libretranslate_fallback.json`)
- **Atomic file saves** with `.tmp` → `os.replace()` pattern
- **Dirty flag with batch saves** to reduce disk I/O
- **Language file caching** for performance
- **`ai_translation_enabled` config option** (default: `False`) to control AI translation behavior
- **`get_all_supported_languages()`** function for querying supported languages from both services
- **`get_best_provider()`** function for provider selection logic
- **`get_libretranslate_mirror_stats()`** for monitoring mirror health
- **`reload_glfm()`** method for switching between GLFM Lite and Full modes at runtime

### Changed
- **Complete architectural overhaul**: `ai_translation.py` replaced with modular `translation/` package
- **Modular provider architecture**: MyMemory and LibreTranslate as separate adapters
- **LibreTranslate default URL** changed to `https://libretranslate.com` (official instance)
- **MyMemory `/languages` endpoint removed** - replaced with static fallback list + learning from errors
- **Translation error handling** now uses specific exception types instead of generic `Exception`
- **`translate_text()`** now supports `smart_routing` parameter (default: `True`) and `max_retries`/`retry_delay` for resilience
- **`AITranslator`** is now **deprecated** - use `translate_text()` directly
- **`base_lang` parameter** changed to `Optional[str] = None` to distinguish from config.conf
- **`get_stats()`** now returns copies (not references) to prevent mutation
- **`_get_text_with_fallback()`** and **`_get_template_with_fallback()`** merged into generic `_get_with_fallback()`
- **Unified language detection** across all modules (config.conf → SHL_LANGUAGE → LANG)
- **Unified key validation** across all modules
- **Consistent None vs "" handling** across all modules
- **`LanguageValidator._find_language()`** optimized from O(n) to O(1) with ISO 639-1 index
- **Legacy file migration** (`lang_xx.json` → `xx.json`) now preserves legacy files as backups
- **Version** updated to 0.2.0

### Fixed
- GLFM fallback now properly stored as `self.glfm_fallback_chain` and used in full fallback chain
- LibreTranslate HTTP error responses now include detailed error classification
- MyMemory rate limit and quota detection now checks both HTTP status codes and response messages
- Language code normalization now uses centralized `lang_utils.py` across all modules
- Removed duplicate `_validate_key()` and `_detect_language()` implementations (DRY principle)
- Thread-safety documentation added (file locking not supported)
- `__del__` replaced with `atexit` for more reliable cleanup
- `_dirty` flag no longer reset on failed saves
- `set_language()` now saves pending changes before switching
- Translation cache now properly distinguishes between `None` (missing/empty) and `{}` (valid empty file)

### Security
- API keys are now masked in all log messages
- `.env` file loading with secure key handling

### Removed
- `ai_translation.py` (replaced with `translation/` package)
- `_normalize_lang_code()` from `ai_translation.py` (replaced with `base_language()` from `lang_utils.py`)
- `_validate_key()` duplicates from `core.py`, `localizer.py`, and `template_localizer.py`
- `_detect_language()` duplicates from `core.py`, `localizer.py`, and `template_localizer.py`
- `get_mymemory_languages()` function (replaced with static fallback list)
- Automatic legacy file deletion (files are now preserved as backups)


## [0.2.0] - 2026-07-30 - dev log

### Added
- **Smart translation routing**: Automatically selects the best translation service (MyMemory or LibreTranslate) based on language pair support
- **Automatic provider fallback**: If primary service fails (rate limit, downtime, etc.), falls back to secondary service
- **Comprehensive error classification**:
  - `RateLimitExceededError` - quota or rate limit exceeded
  - `ServiceUnavailableError` - service down or unreachable
  - `LanguageNotSupportedError` - language not supported by service
  - `ProviderAccessError` - access denied (banned, invalid API key)
  - `InvalidRequestError` - bad request parameters
  - `TranslationError` - base exception for all translation errors
- **Static fallback language lists** from JSON files (`data/languages/mymemory_fallback.json` and `libretranslate_fallback.json`)
- **MyMemory language support detection** via test translation with 24-hour cache
- **`ai_translation_enabled` config option** (default: `False`) to control AI translation behavior
- **`get_all_supported_languages()`** function for querying supported languages from both services
- **`get_best_provider()`** function for provider selection logic
- **`ProviderAccessError`** and **`InvalidRequestError`** exception classes
- **`get_mymemory_languages()`** function removed (replaced with test-based detection)

### Changed
- **LibreTranslate default URL** changed to `https://libretranslate.com` (official instance)
- **MyMemory `/languages` endpoint removed** - replaced with test-based language support detection
- **Translation error handling** now uses specific exception types instead of generic `Exception`
- **`translate_text()`** now supports `smart_routing` parameter (default: `True`) and `max_retries`/`retry_delay` for resilience
- **`AITranslator`** now uses 24-hour cache for language support detection
- **`get_supported_languages()`** now falls back to static JSON list if LibreTranslate API is unavailable
- **`ai_translation_enabled`** default changed from implicit to explicit `False`
- **`ui_text()`** now only attempts AI translation when `ai_translation_enabled=True`
- **`get_stats()`** now includes `ai_translation_enabled` status
- **Version** updated to 0.2.0

### Fixed
- GLFM fallback now properly stored as `self.glfm_fallback` and used in fallback chain
- LibreTranslate HTTP error responses now include detailed error classification
- MyMemory rate limit and quota detection now checks both HTTP status codes and response messages
- Language code normalization now uses centralized `lang_utils.py` across all modules
- Removed 6 duplicate `_validate_lang_code()` implementations (DRY principle)

### Removed
- `_normalize_lang_code()` from `ai_translation.py` (replaced with `base_language()` from `lang_utils.py`)
- `_validate_lang_code()` from `core.py`, `localizer.py`, and `template_localizer.py`
- `get_mymemory_languages()` function (replaced with test-based detection)
- `mymemory_languages` cache key (replaced with `_mymemory_support_cache`)

### Security
- API keys are now masked in all log messages
- `.env` file loading with secure key handling

---

## [0.1.7] - 2026-07-28 - Test PyPI Preview

### Added
- GLFM (Global Language Family Mapper) integration via `LanguageValidator` class
- 7,900+ language database with BCP-47 tags, fallback chains, and validation
- Region subtag support: `zh-TW`, `pt-BR` get their own files (`zh-tw.json`, `pt-br.json`)
- Dynamic language list fetching from LibreTranslate `/languages` API with 24h cache
- Environment variable support via `.env` file (no external dependencies)
- Optional MyMemory email parameter (`de`) for 30k words/day limit
- LibreTranslate `api_key` and `base_url` as optional parameters
- Detailed error messages for HTTP 403 (Forbidden) and 429 (Rate Limited)
- API key masking in logs for security
- Language code normalization: `en-US` → `en` for LibreTranslate compatibility
- `get_supported_languages()` function for querying available languages
- 11 new unit tests for language validator (106 total)

### Changed
- `_validate_lang_code()` preserves region subtags for file naming in both Localizer and TemplateLocalizer
- `_detect_language()` converts `LANG` env var to proper format (`zh_TW` → `zh-TW`)
- `translate_text()` accepts optional `libretranslate_url`, `libretranslate_api_key`, `mymemory_email`
- `AITranslator` class accepts optional configuration parameters
- Translation cache enforces max size (10,000 entries) to prevent memory issues
- All hardcoded language mappings replaced with dynamic LibreTranslate API queries
- `_normalize_lang_code()` handles Chinese subtags and region stripping
- `get_stats()` now includes `glfm_loaded` key

### Fixed
- LibreTranslate HTTP error responses now include detailed debug logging
- Language code compatibility between MyMemory (5-char) and LibreTranslate (2-char)
- `LANG` environment variable parsing for region-specific locales

---

## [0.1.6] - 2026-07-26 - Test PyPI Preview

### Added
- AI translations via MyMemory API with LibreTranslate fallback system
- Translation cache (MD5-based, configurable TTL) to reduce API calls
- Corrupted JSON file protection with automatic .bak backup creation
- Unified logging configuration (`logging_config.py`) with console and rotating file handlers
- Dynamic language switching via `set_language()` method
- Key validation: type checking, emptiness detection, whitespace normalization
- Comprehensive pytest unit tests for all core components
- `get_stats()` method for engine diagnostics and monitoring
- Automatic migration from legacy file format (`lang_xx.json` → `xx.json`)

### Changed
- File naming format changed from `lang_xx.json` to `xx.json`
- `sync()` now calls `ui_text()` for self-healing during synchronization
- `template()` now supports self-healing with default parameter and `**kwargs` variable substitution
- Base language fallback made persistent across all lookup paths
- Consistent None vs "" handling across all four core files
- `LocalizationEngine.__init__`: `lang_code` now defaults to `None` with automatic detection
- Config file support at engine level via `config` parameter
- All log messages and comments changed to English

### Fixed
- MyMemory `responseStatus` validation to detect failed translations
- Corrupted JSON handling: exceptions now logged instead of crashing

---

## [0.1.5] - 2026-01-19

### Fixed
- Fixed incorrect constructor argument usage in core engine. Internal fix, no API change.

---

## [0.1.5] - 2026-01-10

### Notes
This version focuses on stabilizing the original implementation before the architectural overhaul in 0.2.0.

- Initial release of the **Self‑Healing Localization Layer (SHL)**.
- `localizer.py`:  
  - Automatic creation of missing UI language files.  
  - Automatic creation of missing UI keys.  
  - Fallback to base language (`en`).  
  - Self‑healing behavior for all UI text lookups.

- `template_localizer.py`:  
  - Automatic creation of missing prompt template language files.  
  - Automatic copying of base template (`en.json`) when a language is missing.  
  - Automatic creation of missing template keys.  
  - Self‑healing behavior for all template lookups.

- `engine.py`:  
  - Unified high‑level interface for UI and template localization.  
  - `ensure_language()` for creating all required files for a new language.  
  - `sync()` for synchronizing all languages with the base language.  
  - Clean API for retrieving UI text and templates.

### Notes
- This version focuses on core functionality and stability.  

---

## [0.1.4] - 2026-01-18

- Project focus returned to concrete solutions to localization problems.
- The library translates the provided texts, for example from English to another language.
- Basic automatic translation engine (e.g., English -> Finnish, or any supported language)

---

## [0.1.1] - 2026-01-10

### Added
- Initial release of the Self‑Healing Localization Layer (SHL)
- `localizer.py`: Automatic creation of missing UI language files, missing UI keys, fallback to base language, self‑healing behavior
- `template_localizer.py`: Automatic creation of missing prompt template files, base template copying, missing template key creation, self‑healing behavior
- `engine.py`: Unified high‑level interface, `ensure_language()`, `sync()`, clean API for UI text and templates

### Notes
This version focuses on stabilizing the original implementation before the architectural overhaul in 0.2.0.

---

## [0.1.0] - Initial Release

### Added
- Initial release version. Basic structure existed but system was incomplete and partially broken.
