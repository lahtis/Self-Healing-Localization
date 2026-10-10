# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)  
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.3.0] - 2026-10-10

### Added
- **`shl/utils/safe_http_common.py`** — shared constants,
  `SafeHTTPError`, and DNS/response helpers used by both HTTP paths.
- **`shl/utils/safe_http.py`** — safe outbound HTTP for public
  internet endpoints. Enforces HTTPS, validates every resolved IP
  against `is_global`, follows validated redirects only, and caps
  response size.
- **`shl/utils/safe_local_http.py`** — safe HTTP for localhost and
  internal network endpoints. Uses an explicit hostname and port
  allowlist, rejects any hostname that resolves to a public IP, and
  refuses to follow redirects.
- **`shl/_version.py`** — single source of truth for the package
  version.
- **`ConfigManager.validate_config()`** — returns warnings about
  missing provider configuration. Intended to be logged at startup so
  the user sees what to enable before the first call fails.
- **`libretranslate_endpoints.json`** — user-editable endpoint list
  for LibreTranslate Community, auto-created from library defaults on
  first run.
- **Tests** — 67 unit tests for the safe HTTP layer, plus a
  `SafeHTTPError.kind` protocol guard in
  `tests/engine/errors/test_kind_protocol.py`.

### Changed
- **All translation and language detection providers now route
  outbound HTTP through `safe_urlopen`** or `safe_local_urlopen`:
  `deepl`, `googlev2`, `googlev3` (parked), `libretranslate`,
  `libretranslate_mirrors`, `libretranslate_community`, `microsoft`,
  `mymemory`, `papago`, `yandex`, `local_translator`,
  `provider_cache`, `private_mymemory`.
- **`Detection router`** now:
  - reads `status_code` from `SafeHTTPError` (falls back to `code`);
  - honors policy `retry_delay` before retrying;
  - treats an empty result as definitive, not retryable;
  - raises a clear error when no detection providers are enabled.
- **`LocalTranslatorAdapter`** uses `safe_local_urlopen` instead of
  the outbound path, so the local endpoint passes the allowlist
  rather than being rejected by `is_global`.
- **`pyproject.toml`** reads the version dynamically from
  `shl/_version.py` and requires Python 3.10+.
- **Provider base classes** (translation and detection) use Python
  3.10+ type syntax and `@staticmethod _mask_credential`.
- **Provider defaults** — all translation and detection providers
  default to `enabled: false`. First run creates a config with
  everything off; the user opts in explicitly.

### Security
- Two distinct HTTP paths with distinct security models:
  - **Outbound**: HTTPS only, public-IP-only resolution, redirect
    validation, response size limits.
  - **Local**: explicit hostname and port allowlist, no public IPs,
    no redirects.
- `SafeHTTPError.kind` values are documented and guarded by a test
  against drift with `HTTP_EXCEPTION_CODES` in the error parser.

### Fixed
- `tests/test_parser.py` — two outdated tests corrected:
  - an empty body with a 2xx status is now accepted as valid;
  - `ConnectionError` maps to `NETWORK_ERROR`, not
    `SERVICE_UNAVAILABLE`.
- `provider_cache.py` — a single unreachable or misbehaving provider
  no longer breaks the whole cache generation. Each provider fetch is
  isolated and returns a safe empty result on failure.
- Removed dead public endpoints (`translate.mentality.rip`,
  `translate.astian.org`) from LibreTranslate Community defaults.
- `libretranslate_community.py` — endpoint list is loaded at
  construction time via `load_endpoints()`, honouring the user
  override file.

### Known limitations
- Translation providers still call `urllib.request.Request` directly
  to construct requests; only the transport (opening the connection)
  is routed through `safe_urlopen`. This is intentional: `Request`
  construction is not a security boundary.
- DNS rebinding is accepted as a non-issue for hard-coded endpoints.
  See `docs/reference/pinned_https.py` for a reference implementation
  if endpoints ever become configurable.

---

## [0.2.11] - 2026-09-16 Language Detect
- Added Language detect profider to prevented failed translations. (en -> message -> fr message = Null)
- Added Language detect language cache
- Added Language detect router

## [0.2.10] - 2026-09-06 HTML Handling & Placeholder Protection

### HTML Handling
- Added HTML-aware translation handling.
- HTML content is now processed separately from plain text.
- HTML tags are protected during translation to prevent translation providers from modifying or translating the markup.
- Text nodes inside HTML are translated while preserving the original HTML structure.
- HTML handling is integrated with provider policy routing, allowing providers without native HTML support to use the protected translation path.

### Placeholder Protection
- Reworked placeholder protection to use provider-safe tokens.
- Replaced the previous private-use Unicode token format with a `{session_id_index_random}` format.
- Added reliable preservation of both named placeholders such as `{name}` and empty placeholders such as `{}`.
- Protected placeholders are restored to their exact original form after translation.
- Prevented provider-side changes such as inserted spaces or modified placeholder contents from causing validation failures.

### Cache
- Prevented failed translations (`None`) from being stored in the translation cache.
- Cache loading now ignores invalid `null` translation entries.
- Normal cache write logging was changed from warning level to informational level.

### Documentation
- Added placeholder handling guidance to the API description.
- Documented that named placeholders are recommended when possible, while empty `{}` placeholders are also supported.
- Documented that placeholders must remain unchanged during translation.

### Verification
- Verified placeholder preservation with MyMemory.
- Verified:
  - `Saved: {}` → `Gespeichert: {}`
  - `Clear the {} database` → `Löschen der {} Datenbank`
- Confirmed that the restored translation, rather than the internal protection token, is stored in the cache.



## [0.2.10] - 2026-09-05 Router Error Handling
- Updated the translation router to work with the new provider error-code handling.
- Provider adapters now normalize service-specific error responses, while the router is responsible for interpreting those errors and deciding the next action.

The router will use the error type to determine whether to:

- retry the provider,
- fall back to another translation provider,
- temporarily mark a language pair as unavailable,
- or stop immediately for permanent errors.

This keeps provider-specific error handling inside the adapters and routing decisions centralized in the router.
No changes were made to the existing provider error-code implementations.

## [v0.2.5]- no date

- Repair router provider cache, add a new policy manager and config.

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
