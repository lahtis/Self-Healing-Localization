# Changelog
All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)  
and this project adheres to [Semantic Versioning](https://semver.org/).

---



---

## [0.1.1] - 2026-01-10
### Notes
This version focuses on stabilizing the original implementation before the architectural overhaul in 0.2.0.

- Initial release of the **Self‑Healing Localization Layer (SHLL)**.
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
- AI‑powered translation is planned for **v0.3**.  
- CLI tooling and Localization Studio are planned for future releases.

### [Unreleased]
#### Planned
- AI‑powered translation module (Gemini / Groq / OpenAI).  
- CLI tool (`selfheal sync`, `selfheal translate`).  
- Automatic detection of missing keys across all languages.  
- Web‑based Localization Studio.  
- Visual diffing of translations.  
- Export/import of language packs.  
- Framework integrations (Flask, FastAPI, Django, Flet).  

---

## [0.1.0] — Initial Release
- The initial release version. The structure existed, but the system was still clearly incomplete and partially broken.
  
---

