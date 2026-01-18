# Self‑Healing Localization Layer
### Automatic, self‑maintaining localization for any Python project  
**Author:** Tuomas Lähteenmäki  
**License:** MIT  
**Version:** 0.1.4

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
[![TestPyPI](https://img.shields.io/badge/TestPyPI-self--healing--localization-blue)](https://test.pypi.org/project/self-healing-localization/)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active-success)
![Platform](https://img.shields.io/badge/Platform-Cross--platform-lightgrey)

---

## Overview

Self‑Healing Localization Layer (SHL) is a lightweight, dependency‑free Python library that eliminates missing translations forever.


### What it Provides

SHL (Self-Healing Localization) simplifies your development workflow by automating the tedious parts of internationalization (i18n):

- Zero-Config Setup: Automatically generates missing language directories and JSON files on first run.
- On-the-Fly Healing: Injects missing keys into your translation files dynamically as they are requested in code.
- Smart Fallbacks: Seamlessly reverts to your base language (default: English) to prevent UI breakage.
- Dual-Layer Engine: Unified management for both standard UI strings and complex AI prompt templates.
- AI-Powered Autotranslation: Leverages LLMs to instantly translate missing content into any target language.

### Key Features
#### Self-Healing UI Localization

Never worry about a missing translation again.
- Automatic Infrastructure: Missing locale files are detected and initialized instantly.
- Dynamic Key Injection: New keys added to code are automatically reflected in your JSON storage.
- Safe Defaults: Ensures your UI always stays intact by falling back to the base language.

#### AI-Native Prompt Management

Specifically designed for modern AI applications.
- Template Persistence: Generates and manages prompt templates across multiple languages.
- Cross-Language Consistency: Ensures your AI prompts remain synchronized across all supported locales.
- Smart Fallback: Copies base prompts as templates for new languages to ensure your AI features never fail.

#### Unified Localization Engine
The LocalizationEngine acts as the central brain of your app's languages:

- Total Synchronization: One-click synchronization of all target languages with the base language.
- Clean API: A simple, high-level interface for accessing both UI text and prompt templates.
- Language Enforcement: Validates and ensures the existence of all required language assets at runtime.

---


## Installation

Currently available via TestPyPI (v0.1.4):

```bash
pip install --index-url [https://test.pypi.org/simple/](https://test.pypi.org/simple/) self-healing-localization==0.1.4
```

Self‑Healing Localization Layer (SHL) is a lightweight, dependency‑free Python library that eliminates missing translations forever.

It provides:

- automatic creation of missing language files  
- automatic creation of missing keys  
- fallback to a base language (default: English)  
- unified support for both UI text and AI prompt templates  
- optional AI‑powered translation (planned for v0.2)  

This library is designed to be **dropped into any project** — from small scripts to full applications — and it will maintain localization files automatically as the project grows.

- No more manual JSON editing.  
- No more “missing translation” errors.  
- No more incomplete language packs.

---


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

If `"app_title"` does not exist in `locales/lang_en.json`, it will be added automatically.

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

---

## Project Structure
The library follows a modular design to keep the core logic separate from your application code:

```
self-healing-localization/
│
├─ shl/
│  └─ engine/                  # Core modular engine
│     ├─ core.py               # Main LocalizationEngine
│     ├─ localizer.py          # UI text logic
│     ├─ template_localizer.py # AI template logic
│     ├─ ai_translation.py     # AI translation
│     └─ __init__.py           # Internal package exports
│
├─ pyproject.toml              # Package configuration
└─ README.md                   # Project documentation
```

---

## API Reference (v0.1.x)

### Initialize

```python
engine = LocalizationEngine(lang_code="en")
```

### UI text

```python
engine.ui_text(key, default="")
```

### Template text

```python
engine.template(key, default="")
```

### Ensure language exists

```python
engine.ensure_language("de")
```

### Sync all languages with base language

```python
engine.sync()
```

### Optional language config

If no language is provided programmatically, SHL will automatically read the user language from config.conf

```ini
[SETTINGS]
language = fi
```

---

## Roadmap

### v0.1.x: 
- Core self-healing logic and modular engine.

### v0.1.4 
- Basic automatic translation engine (e.g., English -> Finnish) or any language.

### v0.2
- AI‑powered translation (Gemini / Groq / OpenAI)
- CLI tool (`selfheal sync`, `selfheal translate`)
- Automatic detection of missing keys across all languages

### v0.3
- Web‑based Localization Studio
- Visual diffing of translations
- Export/import language packs

### v1.0
- Full ecosystem integrations (Flask, FastAPI, Django, Flet)
- Community templates
- Official PyPI release


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

With SHLL, any project can become multilingual — automatically, reliably, and without manual maintenance.

**No more missing translations.  
No more incomplete language packs.  
Localization that heals itself.**


#localization • #i18n • #l10n • #self-healing • #translation • #multilingual  #json • #python • #developer-tools • #automation • #templates • #cli #ai-assisted • #language-files • #internationalization • #localization-engine