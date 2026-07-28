# Self‑Healing Localization Layer
### Automatic, self‑maintaining localization for any Python project  
**Author:** Tuomas Lähteenmäki  
**License:** MIT  
**Version:** 0.1.7

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Version](https://img.shields.io/badge/Version-0.1.6-brightgreen)
![Status](https://img.shields.io/badge/Status-Active-success)
[![Downloads](https://static.pepy.tech/badge/self-healing-localization)](https://pepy.tech/project/self-healing-localization)

---

## Overview

Self‑Healing Localization Layer (SHL) is a lightweight, dependency‑free Python library that eliminates missing translations forever.

It provides:
- Automatic creation of missing language files . 
- Automatic creation of missing keys. 
- Fallback to a base language (default: English).  
- Unified support for both UI text and optional AI prompt templates.
- GLFM integration for 7,900+ languages with BCP-47 tags and fallback chains.

This library is designed to be **dropped into any project** — from small scripts to full applications — and it will maintain localization files automatically as the project grows.

- No more manual JSON editing.  
- No more "missing translation" errors.  
- No more incomplete language packs.

---

## Key Features

### Self‑Healing UI Localization
- Missing language files are created automatically.  
- Missing keys are added on the fly.  
- Base language is used as fallback.  
- Region subtags preserved: `zh-TW`, `pt-BR` get their own files.

### Self‑Healing AI Prompt Template Localization
Large Language Model (LLM) applications often require localized prompt templates in addition to localized UI text. SHL manages both through the same self-healing localization engine.

- Missing template files are generated automatically.  
- Base templates are copied as fallback.  
- Missing template keys are added automatically.  
- Same region subtag support as UI localization. 

### Unified High‑Level Engine
The `LocalizationEngine` ties everything together:
- Ensures languages exist.  
- Synchronizes all languages with the base language.  
- Provides a single interface for UI text and prompt templates.
- Optional GLFM language validation with BCP-47 tags.

### Zero Dependencies
Pure Python. Works everywhere.

---

### GLFM Language Database (New in v0.1.7)
Optional integration with the Global Language Family Mapper:
- 7,900+ languages with ISO 639-1/2/3/5 codes
- BCP-47 compliant tags (e.g., `fi-Latn-FI`)
- Automatic fallback chain resolution
- Language validation against authoritative data

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
Test version available via TestPyPI preview (v0.1.7):

```bash
pip install -i https://test.pypi.org/simple/ self-healing-localization==0.1.7
```

## Environment Variables (.env)

Create a .env file in your project root (optional):
```ini
MYMEMORY_EMAIL=your@email.com
LIBRETRANSLATE_API_KEY=your-api-key
LIBRETRANSLATE_URL=https://translate.argosopentech.com
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

### 6. Region Subtag Support (New in v0.1.7)

```python
# Brazilian Portuguese and European Portuguese in separate files
engine = LocalizationEngine(lang_code="pt-BR")  # → pt-br.json
engine = LocalizationEngine(lang_code="pt-PT")  # → pt-pt.json

# Traditional and Simplified Chinese in separate files
engine = LocalizationEngine(lang_code="zh-TW")  # → zh-tw.json
engine = LocalizationEngine(lang_code="zh-CN")  # → zh-cn.json
```

### 7. Synchronize All Languages

Sync all keys from the base language to the current language.

```python
engine.sync()
```

### 8. Using GLFM Language Validation
```python
engine = LocalizationEngine(
    lang_code="fi",
    glfm_path="data/unified_languages.json"
)

stats = engine.get_stats()
print(stats["glfm_loaded"])  # True
print(stats["lang_code"])    # fi
```

---

## Project Structure
The library follows a modular design to keep the core logic separate from your application code:

```
self-healing-localization/
│
├── shl/
│   ├── engine/
│   │   ├── core.py
│   │   ├── localizer.py
│   │   ├── template_localizer.py
│   │   ├── ai_translation.py
│   │   └── __init__.py
│   ├── data/
│   │   └── unified_languages.json  # GLFM database
│   ├── language_validator.py
│   ├── logging_config.py
│   └── __init__.py
│
├── tests/
│   ├── test_localizer.py
│   ├── test_template_localizer.py
│   ├── test_core.py
│   ├── test_ai_translation.py
│   ├── test_language_validator.py
│   └── conftest.py
│
├── pyproject.toml
└── README.md
```

---

## API Reference (v0.1.7)

### LocalizationEngine

```python
engine = LocalizationEngine(
    lang_code=None,        # None = auto-detect from config.conf or LANG env
    base_lang="en",
    ui_folder="locales",
    template_folder="prompts",
    config=None,           # Custom configuration dict
    glfm_path=None         # Path to GLFM unified_languages.json
)
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

### AITranslator

```python
from shl.engine.ai_translation import AITranslator

translator = AITranslator(
    provider="auto",                    # "auto", "mymemory", "libretranslate", "none"
    libretranslate_url=None,            # Override LibreTranslate server
    libretranslate_api_key=None,        # Override LibreTranslate API key
    mymemory_email=None                 # Override MyMemory email
)

text = translator.translate("Hello", target_lang="fi")
batch = translator.batch_translate({"a": "Hello", "b": "Goodbye"}, "fi")
```

| Method | Description |
|--------|-------------|
| `translate_text(text, target_lang, source_lang)` | Translate with full fallback chain |
| `get_supported_languages(base_url)` | Fetch languages from LibreTranslate instance |


### Configuration (config.conf)

```ini
[SETTINGS]
language = fi
ai_translation_enabled = true
fallback_to_base = true
```
If no language is provided programmatically, SHL reads the language from '''config.conf'''.

### Translation Services

| Service | Role | Limits |
|--------|-------------|
| MyMemory | Primary | 1,000 chars/day (30,000 with email)|
| LibreTranslate | Fallback | Public instance, rate limited |

Both work without API keys. API key support available via .env file.

## 🛠 Roadmap

### [v0.1.x]
- Core self-healing logic and modular engine.

### [v0.1.4]
- Basic automatic translation engine (e.g., English -> Finnish).

### [v0.1.5] - 2026-01-19 - RELEASED

 - Fixed incorrect constructor argument usage in core engine. Internal fix, no API change.
 - Initial PyPI release.

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

### [v0.1.7] - Current Test PyPI Release

 - GLFM integration (7,900+ languages)
 - Region subtag support (zh-TW, pt-BR)
 - Dynamic language detection with 24h cache
 - Environment variable support (.env)
 - Improved error handling (403, 429)
 - Language code normalization
 - MyMemory email support
 - 106 unit tests

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

