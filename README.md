# Self‑Healing Localization (SHL) Library
### Automatic, self‑maintaining localization for any Python project  

* **Author:**  Tuomas Lähteenmäki  
* **License:** MIT  
* **Version:** 0.2.4
* **Type:**    Library
* **Status:** in development


![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
[![PyPI](https://img.shields.io/pypi/v/self-healing-localization)](https://pypi.org/project/self-healing-localization/)
[![TestPyPI](https://img.shields.io/badge/TestPyPI-Preview-blueviolet)](https://test.pypi.org/project/self-healing-localization/)
![Status: Beta](https://img.shields.io/badge/Status-Beta-yellow)
[![Downloads](https://static.pepy.tech/badge/self-healing-localization)](https://pepy.tech/project/self-healing-localization)

---

## Primary Links
- Canonical Repository (Codeberg): https://codeberg.org/lahtis/Self_Healing_Localization
- GitHub Mirror: https://github.com/lahtis/Self-Healing-Localization
- Documentation: https://codeberg.org/lahtis/Self_Healing_Localization/src/branch/main/docs
---

## Overview

Self-Healing Localization Layer (SHL) is a Python localization engine that automatically creates, synchronizes, and maintains language files throughout the lifetime of your application.


### What makes SHL different?

| Feature | SHL | Traditional i18n | other |
|---------|-----|------------------|-----|
| Missing keys created automatically | + | - |
| Missing language files created automatically | + | - |
| Zero runtime dependencies | + | - | (often require gettext, Babel, etc.) |
| BCP-47 region subtag support | + | ~ | (limited) |
| GLFM language validation (7,900+ languages) | + | - |
| Self-healing fallback chains | + | - |
| Smart translation routing | + | - |

### Key Benefits

- **No more manual JSON editing.**  
- **No more "missing translation" errors.**  
- **No more incomplete language packs.**  
- **Write code in your native language.** SHL handles the rest.

---

## Features

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

### GLFM Integration (7,900+ languages)
- **GLFM Lite** (default): ~428 KB, 20 nearest languages for fallback.
- **Full GLFM** (optional): ~925 MB, all 7,900+ languages for research and AI.
- Language validation with BCP-47 tags.
- Language family fallback chains.

### Smart Translation Routing (v0.2.0)
- Automatically selects the best available service (MyMemory → LibreTranslate).
- Automatic fallback on rate limits or downtime.
- Language support detection with 24-hour cache.
- Machine translation is opt-in (`m_translation_enabled=False` by default).

### Zero Dependencies
Zero runtime dependencies. Pure Python library. Optional online translation services. Works everywhere.

---

## Quick Start

### Installation

### Stable (PyPI)
```bash
pip install self-healing-localization
```
---

### Latest Development (TestPyPI)
```bash
pip install -i https://test.pypi.org/simple/ self-healing-localization==0.2.3
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

# Initialize the engine (user language = Finnish, base = English)
engine = LocalizationEngine(lang_code="fi", base_lang="en")

# If 'welcome_msg' is missing, it is created with the given default value
title = engine.ui_text("welcome_msg", "Welcome to the App!")

print(title)  # "Tervetuloa sovellukseen!" (if translation exists)
```
SHL interprets this as:

* base_lang="en" → source code strings are English
* lang_code="fi" → user wants Finnish UI

So SHL does:
* 1. Look for welcome_msg in fi.json
* 2. If missing:
- Create the key in fi.json
- Use the default value "Welcome to the App!" as the English source
- Translate English → Finnish

* 3. Return the Finnish result

#### Core takeaway

- base_lang = the language your source JSON files are written in  
- lang_code = the language the user wants to see in the UI right now
Everything else in SHL’s behavior flows from that.

#### How SHL interprets these two parameters

##### 1) base_lang

This is the language of your canonical UI strings — the language your codebase “speaks”.

Examples:
* If your app is written in English → base_lang="en"
* If your app is written in Finnish → base_lang="fi"
* If your app is written in Italian → base_lang="it"

SHL uses base_lang to:
* now which JSON file is the authoritative source
* know what language missing keys should be stored in
* know what language to translate from when generating other languages

##### 2) lang_code

This is the language the user wants to see.

Examples:
* Finnish user → lang_code="fi"
* English user → lang_code="en"
* Italian user → lang_code="it"

SHL uses lang_code to:

* decide which JSON file to read from
* decide which JSON file to write new keys into
* decide which language to translate to

--- 
 
### 2. Configuration via config.conf
Create a `config.conf` in your project root:

```ini
[SETTINGS]
language = fi
base_lang = en
m_translation_enabled = true
```

```python
engine = LocalizationEngine()  # reads language and settings from config.conf
print(engine.ui_text("welcome", "Welcome!"))
```

### 3. Enable Machine Translation
Machine translation is disabled by default. Enable it when you want missing texts to be translated automatically.

```python
config = {"m_translation_enabled": True}
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
engine = LocalizationEngine(lang_code="en", config={"m_translation_enabled": True})

# Switch to Finnish
engine.set_language("fi")
print(engine.ui_text("greeting", "Hello!"))  # "Hei!" (Machine-translated)

# Switch to Swedish
engine.set_language("sv")
print(engine.ui_text("greeting", "Hello!"))  # "Hej!" (Machine-translated)
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

### 7. Direct Translation (Smart Routing)
```python
from shl.engine.translation import translate_text

# Automatically chooses the best provider
result = translate_text("Hello World", target_lang="fi")
print(result)  # "Hei maailma"
```
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

