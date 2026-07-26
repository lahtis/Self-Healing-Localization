# Self‑Healing Localization Layer
### Automatic, self‑maintaining localization for any Python project  
**Author:** Tuomas Lähteenmäki  
**License:** MIT  
**Version:** 0.1.6

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Version](https://img.shields.io/badge/Version-0.1.6-brightgreen)
![Status](https://img.shields.io/badge/Status-Active-success)
[![PyPI Downloads](https://img.shields.io/pypi/dm/self-healing-localization)](https://pypi.org/project/self-healing-localization/)

---

## Overview

Self‑Healing Localization Layer (SHL) is a lightweight, dependency‑free Python library that eliminates missing translations forever.

It provides:
- Automatic creation of missing language files  
- Automatic creation of missing keys  
- Fallback to a base language (default: English)  
- Unified support for both UI text and optional AI prompt templates  

This library is designed to be **dropped into any project** — from small scripts to full applications — and it will maintain localization files automatically as the project grows.

- No more manual JSON editing.  
- No more "missing translation" errors.  
- No more incomplete language packs.

---

## Key Features

### Self‑Healing UI Localization
- Missing language files are created automatically  
- Missing keys are added on the fly  
- Base language is used as fallback  

### Self‑Healing AI Prompt Template Localization
- Missing template files are generated automatically  
- Base templates are copied as fallback  
- Missing template keys are added automatically  

### Unified High‑Level Engine
The `LocalizationEngine` ties everything together:
- Ensures languages exist  
- Synchronizes all languages with the base language  
- Provides clean access to UI text and templates  

### Zero Dependencies
Pure Python. Works everywhere.

---

## What's New in v0.1.6

- AI Translations – MyMemory + LibreTranslate fallback system
- Translation Cache – Automatically reduces API calls
- Corrupted File Protection – Automatic .bak backup creation
- Unified Logging – `error.log` with configurable levels
- Dynamic Language Switching – `set_language()` on the fly
- Comprehensive Tests – pytest unit tests for all components
- Key Validation – Type, emptiness, and whitespace checks
- Legacy File Migration – Automatic `lang_xx.json` → `xx.json` conversion

---

## Installation

### Stable
Stable version available via PyPI (v0.1.5):

```bash
pip install self-healing-localization
```
---

### Test
Test version available via TestPyPI (v0.1.6):

```bash
pip install --index-url [https://test.pypi.org/simple/](https://test.pypi.org/simple/) self-healing-localization==0.1.6
```

## Quick Start

### 1. Basic UI Localization

Initialize the engine and start retrieving text. If the key doesn't exist, it is added to your JSON files automatically.

```python
from shl.engine import LocalizationEngine

# Initialize the engine (e.g., set user language to Finnish)
engine = LocalizationEngine(lang_code="fi", base_lang="en")

# Retrieve UI text. If 'welcome_msg' is missing, it's created with the default value.
title = engine.ui_text("welcome_msg", "Welcome to the App!")
print(title)
```


### 2. Retrieve UI text

```python
title = engine.ui_text("app_title", "My Application")
```

If `"app_title"` does not exist in `locales/en.json`, it will be added automatically.

### 3. Retrieve prompt templates

```python
summary_prompt = engine.template("summary_short", "Summarize the text:")
```

If `prompts/fi.json` does not exist, it will be created automatically using `prompts/en.json` as the base.

### 4. AI Prompt Templates
Keep your AI prompts localized just like your UI strings.

```python
# Retrieve a localized prompt template
prompt = engine.template("summarize_task", "Please summarize the following text:")
```

### 5. Dynamic Language Switching (New in v0.1.6)

Switch languages on the fly without restarting your application.

```python
# Start in English
engine = LocalizationEngine(lang_code="en")

# Switch to Finnish
engine.set_language("fi")
print(engine.ui_text("greeting", "Hello!"))  # "Hei!" (AI-translated)

# Switch to Swedish
engine.set_language("sv")
print(engine.ui_text("greeting", "Hello!"))  # "Hej!" (AI-translated)
```

### 6. Synchronize All Languages

Sync all keys from the base language to the current language.

```python
engine.sync()
```

---

## Project Structure
The library follows a modular design to keep the core logic separate from your application code:

```
self-healing-localization/
│
├── shl/
│ ├── engine/ # Core modular engine
│ │ ├── core.py # Main LocalizationEngine
│ │ ├── localizer.py # UI text logic
│ │ ├── template_localizer.py # AI template logic
│ │ ├── ai_translation.py # AI translation services
│ │ └── init.py # Internal package exports
│ ├── logging_config.py # Unified logging configuration
│ └── init.py
│
├── tests/ # Unit tests
│ ├── test_localizer.py
│ ├── test_template_localizer.py
│ ├── test_core.py
│ ├── test_ai_translation.py
│ └── conftest.py
│
├── pyproject.toml # Package configuration
└── README.md # Project documentation
```

---

## API Reference (v0.1.6)

### LocalizationEngine

```python
engine = LocalizationEngine(
    lang_code=None,        # None = auto-detect from config.conf
    base_lang="en",
    ui_folder="locales",
    template_folder="prompts",
    config=None            # Custom configuration dict
)
```

| Method | Description |
|--------|-------------|
| `engine.ui_text(key, default_value="")` | Retrieve UI text with self-healing |
| `engine.template(key, default="", **kwargs)` | Retrieve prompt template with self-healing |
| `engine.set_language(lang_code)` | Switch language dynamically |
| `engine.ensure_language(lang_code)` | Ensure language files exist |
| `engine.sync()` | Synchronize all keys from base language |
| `engine.get_stats()` | Return engine statistics |
| `engine.ensure_ui_key(key, default="")` | Ensure UI key exists |
| `engine.ensure_template_key(key, default="")` | Ensure template key exists |

### Configuration (config.conf)

```ini
[SETTINGS]
language = fi
ai_translation_enabled = true
fallback_to_base = true
```
If no language is provided programmatically, SHL reads the language from '''config.conf'''.

## 🛠 Roadmap

### [v0.1.x]
- Core self-healing logic and modular engine.

### [v0.1.4]
- Basic automatic translation engine (e.g., English -> Finnish).

### [v0.1.5] - 2026-01-19 - RELEASED

 - Fixed incorrect constructor argument usage in core engine. Internal fix, no API change.
 - Offical PyPI release

### [v0.1.6] - 2026-07-26 - Test PyPI RELEASE
 - Core self-healing logic and modular engine
 - AI translations (MyMemory + LibreTranslate fallback)
 - Translation cache for API call optimization
 - Corrupted JSON file backup (.bak)
 - Unified logging with configurable levels
 - Dynamic language switching (`set_language()`)
 - Key validation and normalization
 - Unit tests (pytest)
 - None vs "" consistency
 - Test PyPI release

### [v0.2.0]
 - AI‑powered translation (Gemini / Groq / OpenAI)
 - CLI tool (`selfheal sync`, `selfheal translate`)
 - Automatic detection of missing keys across all languages
 - Async support

### [v0.3.0]
 - Web‑based Localization Studio
 - Visual diffing of translations
 - Export/import language packs

### [v1.0.0]
 - Full ecosystem integrations (Flask, FastAPI, Django, Flet)
 - Community templates

---

## Contributing

Contributions are welcome.  
This project aims to become a new standard for open‑source localization — simple, automatic, and self‑maintaining.

---

## License

MIT License — free for personal and commercial use.

---

## Vision

Localization should never be a burden.

With SHL, any project can become multilingual — automatically, reliably, and without manual maintenance.

**No more missing translations.  
No more incomplete language packs.  
Localization that heals itself.**


#localization • #i18n • #l10n • #self-healing • #translation • #multilingual #json • #python • #developer-tools • #automation • #templates • #cli #ai-assisted • #language-files • #internationalization • #localization-engine

