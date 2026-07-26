# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)  
and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [0.1.6] - 2026-07-26

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

## [0.1.5] - 2026-01-19

### Fixed
- Fixed incorrect constructor argument usage in core engine. Internal fix, no API change.

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
