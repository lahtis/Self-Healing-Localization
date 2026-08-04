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

Self-Healing Localization Layer (SHL) is a Python localization engine that automatically creates, synchronizes, and maintains language files throughout the lifetime of your application.

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

### Base language
The base language is fully controlled by the developer. 
It is the language in which you primarily write the application’s texts. 
SHL uses it as:
- the fallback when a translation is missing in the target language
- the source when creating or synchronizing other language files

### Self‑Healing UI Localization
- Missing language files are created automatically.  
- Missing keys are added on the fly.  
- Developer-defined base language is used as fallback.  
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

### Smart Translation Routing (v0.2.0)
- Automatically selects the best available service (MyMemory → LibreTranslate).
- Automatic fallback on rate limits or downtime.
- Language support detection with 24-hour cache.
- AI translation is opt-in (`ai_translation_enabled=False` by default).

### Zero Dependencies
Zero runtime dependencies. Pure Python library. Optional online translation services. Works everywhere.

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
Initialize the engine and start retrieving text. Missing keys are added to your JSON files automatically.

```python
from shl.engine import LocalizationEngine

# Initialize the engine (user language = Finnish, base language = English)
engine = LocalizationEngine(lang_code="fi", base_lang="en")

# If 'welcome_msg' is missing, it is created with the given default value
title = engine.ui_text("welcome_msg", "Welcome to the App!")
print(title)
```

### 2. Configuration via config.conf
Create a `config.conf` in your project root:

```ini
[SETTINGS]
language = fi
base_lang = en
ai_translation_enabled = true
```

```python
engine = LocalizationEngine()  # reads language and settings from config.conf
print(engine.ui_text("welcome", "Welcome!"))
```

### 3. Enable AI Translation
AI translation is disabled by default. Enable it when you want missing texts to be translated automatically.

```python
config = {"ai_translation_enabled": True}
engine = LocalizationEngine(lang_code="fi", config=config)

text = engine.ui_text("new_key", "Hello World!")

# → "Hei maailma!" (automatically translated to Finnish)

```

### 4. Prompt Templates
SHL handles localized AI prompt templates the same way as UI text.

```python
prompt = engine.template("summarize_task", "Please summarize the following text:")
```

If the template file for the current language does not exist, it is created automatically using the base language as the source.


### 5. Dynamic Language Switching
Switch languages at runtime without restarting the application.

```python
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

### 8. GLFM Language Validation
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

### 9. Direct Translation (Smart Routing)
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
Note: Language files (`locales/xx.json`), prompt templates (`prompts/xx.json`) are created in your application, not inside the library.

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

### Language detection priority
When `lang_code` is not provided to `LocalizationEngine`, the language is resolved in this order:

1. `config.conf` → `[SETTINGS] language`
2. `SHL_LANGUAGE` environment variable
3. `LANG` environment variable
4. Default: `en`

An explicit `lang_code` argument always takes highest priority and skips auto-detection.

### Configuration Options ('''config.conf''')
```ini
[SETTINGS]
language = fi					# Current UI language
base_lang = en					# Developer-defined base language
ai_translation_enabled = false  # Enable AI translation (default: false)
fallback_to_base = true			# Fall back to base language when key is missing
```
If lang_code is not given when creating the engine, SHL reads the language from config.conf. A value in config.conf overrides environment variables.

```
| Key | Description | Default |
|--------|-------------|-------------|
| language | Active UI language | auto-detect / en|
| base_lang | Developer-defined base language | en | 
| ai_translation_enabled | Enable automatic AI translation | false | 
| fallback_to_base | Fall back to base language when a key is missing | true | 
```

Both work without API keys. API key support available via .env file.


### AI-Translator

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

| Service | Role | Limits | Notes |
|--------|-------------|-------------|-------------|
| MyMemory | Primary | 1,000 chars/day (30,000 with email) | Translation memory + MT fallback |
| LibreTranslate | Fallback | Public instance, rate limited | Open-source MT engine | 

Both work without API keys. API key support available via .env file.

---

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

