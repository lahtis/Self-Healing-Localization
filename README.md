# Self‑Healing Localization
### Automatic, self‑maintaining localization for any Python project  
**Author:** Tuomas Lähteenmäki  
**License:** MIT  
**Version:** 0.2.0

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
[![PyPI](https://img.shields.io/pypi/v/self-healing-localization)](https://pypi.org/project/self-healing-localization/)
[![TestPyPI](https://img.shields.io/badge/TestPyPI-Preview-blueviolet)](https://test.pypi.org/project/self-healing-localization/)
![Status: Beta](https://img.shields.io/badge/Status-Beta-yellow)
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
- - **NEW in v0.2.0:** Smart translation routing between MyMemory and LibreTranslate.

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

### Smart Translation Routing (NEW in v0.2.0)
- Automatically selects the best translation service for each language pair.
- MyMemory as primary service, LibreTranslate as fallback.
- Automatic fallback if primary service fails (rate limit, downtime, etc.).
- Language support detection with 24-hour cache.
- AI translation enabled only when configured (`ai_translation_enabled=False` by default).

### Zero Dependencies
Pure Python. Works everywhere.

---

## What's New in v0.2.0

- **Smart Translation Routing** – Automatically selects MyMemory or LibreTranslate based on language support.
- **Automatic Provider Fallback** – If one service fails, automatically switches to the other.
- **Comprehensive Error Classification** – 6 specific exception types for different error scenarios.
- **Static Fallback Language Lists** – JSON files for easy maintenance when APIs are unavailable.
- **MyMemory Language Support Detection** – Test-based detection with 24-hour cache.
- **`ai_translation_enabled` Config** – AI translations disabled by default for predictable behavior.
- **LibreTranslate Official Instance** – Default URL changed to `https://libretranslate.com`.
- **DRY Architecture** – Centralized language code handling in `lang_utils.py`.
- **106+ Unit Tests** – Full coverage for all components.

v0.1.7 Development Features:
- GLFM Integration – 7,900+ languages with ISO 639, BCP-47, fallback chains.
- Region Subtag Support – `zh-TW`, `pt-BR` get their own files.
- Environment Variable Support – `.env` file for API keys and configuration.
- Translation Cache – Automatically reduces API calls.
- Corrupted File Protection – Automatic `.bak` backup creation.
- Unified Logging – `error.log` with configurable levels.
- Dynamic Language Switching – `set_language()` on the fly.

v0.1.6 Development Features:
- AI Translations – MyMemory + LibreTranslate fallback system
- Translation Cache – Automatically reduces API calls
- Corrupted File Protection – Automatic .bak backup creation
- Unified Logging – `error.log` with configurable levels
- Dynamic Language Switching – `set_language()` on the fly
- Key Validation – Type, emptiness, and whitespace checks
- Legacy File Migration – Automatic `lang_xx.json` → `xx.json` conversion

## Installation

### Stable (PyPI)
```bash
pip install self-healing-localization
```
---

### Latest Development (TestPyPI)
```bash
pip install -i https://test.pypi.org/simple/ self-healing-localization==0.2.0
```

## Environment Variables (.env)

Create a .env file in your project root (optional):

```ini
MYMEMORY_EMAIL=your@email.com
LIBRETRANSLATE_API_KEY=your-api-key
LIBRETRANSLATE_URL=https://libretranslate.com
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

### 2. Enable AI Translation

```python
# Enable AI translations in config
config = {"ai_translation_enabled": True}
engine = LocalizationEngine(lang_code="fi", config=config)

# Now missing texts will be automatically translated
text = engine.ui_text("new_key", "Hello World!")
# → "Hei maailma!" (automatically translated to Finnish)

```

### 3. Retrieve UI text

```python
title = engine.ui_text("app_title", "My Application")
```

If `"app_title"` does not exist in `locales/en.json`, it will be added automatically.

### 4. Retrieve prompt templates

```python
summary_prompt = engine.template("summary_short", "Summarize the text:")
```

If `prompts/fi.json` does not exist, it will be created automatically using `prompts/en.json` as the base.

## 4.1 AI Prompt Templates
Keep your AI prompts localized just like your UI strings.

```python
# Retrieve a localized prompt template
prompt = engine.template("summarize_task", "Please summarize the following text:")
```

### 5. Dynamic Language Switching

Switch languages on the fly without restarting your application.

```python
# Start in English
engine = LocalizationEngine(lang_code="en", config={"ai_translation_enabled": True})

# Switch to Finnish
engine.set_language("fi")
print(engine.ui_text("greeting", "Hello!"))  # "Hei!" (AI-translated)

# Switch to Swedish
engine.set_language("sv")
print(engine.ui_text("greeting", "Hello!"))  # "Hej!" (AI-translated)
```

### 6. Region Subtag Support

```python
# Brazilian Portuguese and European Portuguese in separate files
engine = LocalizationEngine(lang_code="pt-BR")  # → pt-br.json
engine = LocalizationEngine(lang_code="pt-PT")  # → pt-pt.json

# Traditional and Simplified Chinese in separate files
engine = LocalizationEngine(lang_code="zh-TW")  # → zh-tw.json
engine = LocalizationEngine(lang_code="zh-CN")  # → zh-cn.json
```

### 7. Synchronize All Languages

Sync all keys from the fallback chain (GLFM fallback → base language) to the current language.

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
print(stats["glfm_fallback"]) # en (if configured)
```

### 9. Direct Translation with Smart Routing
```python
from shl.engine.ai_translation import translate_text

# Automatically chooses the best provider
result = translate_text("Hello World", target_lang="fi")
print(result)  # "Hei maailma"
```

---

## Project Structure
The library follows a modular design to keep the core logic separate from your application code:

```
self-healing-localization/
│
├── shl/
│   ├── engine/
│   │   ├── core.py                 # Main engine
│   │   ├── localizer.py            # UI localization
│   │   ├── template_localizer.py   # Template localization
│   │   ├── ai_translation.py       # Translation with smart routing
│   │   └── __init__.py
│   ├── utils/
│   │   ├── lang_utils.py           # BCP-47 language code handling
│   │   └── __init__.py
│   ├── data/
│   │   ├── unified_languages.json  # GLFM database
│   │   └── languages/
│   │       ├── mymemory_fallback.json
│   │       └── libretranslate_fallback.json
│   ├── language_validator.py       # GLFM validation
│   ├── logging_config.py           # Unified logging
│   └── __init__.py
│
├── tests/
│   ├── test_localizer.py
│   ├── test_template_localizer.py
│   ├── test_core.py
│   ├── test_ai_translation.py
│   ├── test_language_validator.py
│   ├── test_lang_utils.py
│   └── conftest.py
│
├── pyproject.toml
└── README.md
```

---

## API Reference (v0.2.0)

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


### Configuration Options (config.conf)
```ini
[SETTINGS]
language = fi
ai_translation_enabled = false   # Enable AI translation (default: false)
fallback_to_base = true
```
If no language is provided programmatically, SHL reads the language from '''config.conf'''.

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


### Translation Functions
```python
from shl.engine.ai_translation import (
    translate_text,
    get_all_supported_languages,
    get_best_provider,
    get_supported_languages,
    RateLimitExceededError,
    ServiceUnavailableError,
    LanguageNotSupportedError,
    ProviderAccessError,
    InvalidRequestError,
    TranslationError
)

# Smart translation with automatic provider selection
result = translate_text("Hello", "fi", smart_routing=True)

# Get supported languages from both services
langs = get_all_supported_languages()
print(f"MyMemory: {len(langs['mymemory'])} languages")
print(f"LibreTranslate: {len(langs['libretranslate'])} languages")

# Get best provider for a language pair
provider = get_best_provider("fi", "en")  # "mymemory" or "libretranslate"
```

### Translation Services

| Service | Role | Limits | Notes
|--------|-------------|
| MyMemory | Primary | 1,000 chars/day (30,000 with email) | Translation memory + MT fallback |
| LibreTranslate | Fallback | Public instance, rate limited | Open-source MT engine | 

Both work without API keys. API key support available via .env file.

## Roadmap

### [v0.2.0] - 2026-07-30 - CURRENT RELEASE
 - Smart translation routing (MyMemory + LibreTranslate)
 - Automatic provider fallback
 - Comprehensive error classification
 - Static fallback language lists (JSON)
 - MyMemory language support detection
 - ai_translation_enabled config (default: False)
 - DRY architecture with lang_utils.py
 - 106+ unit tests

### [v0.3.0]
 - AI‑powered translation (Gemini / Groq / OpenAI)
 - CLI tool (`selfheal sync`, `selfheal translate`)
 - Automatic detection of missing keys across all languages
 - Async support

### [v0.4.0]
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

