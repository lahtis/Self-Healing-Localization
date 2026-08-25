# Self‑Healing Localization (SHL) Library
### Automatic, self‑maintaining localization for any Python project  

* **Author:**  Tuomas Lähteenmäki  
* **License:** MIT  
* **Version:** 0.2.9
* **Type:**    Library
* **Status:**  Dev


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
- Demonstration: https://youtu.be/t5veRZtt3dU?si=ADD4yS5C2VwNKx9f
---

## Overview
Self‑Healing Localization Library (SHL) is a dependency‑free Python library that automates application localization and independently repairs missing translations. The library creates, updates, and synchronizes translation files throughout the application’s lifecycle without manual maintenance.

SHL follows a self‑healing principle: when the application requests a missing translation key, the library automatically generates it, fetches a machine translation if needed, and stores the result in the correct language file. This makes localization deterministic and reduces developer workload.

### Features
* Automatic creation of missing translations
* Automatic generation of new language files
* BCP‑47 language code support (e.g., fi‑FI, pt‑BR, zh‑TW)
* GLFM‑based language validation
* Machine translation support: Microsoft Translator, DeepL, Google Translate, MyMemory, LibreTranslate, Papago Translate, Yandex Translate and Localhost.
* Self‑healing localization pipeline
* Unified high‑level localization engine
* Offline and online support
* Zero‑dependency core
* Free and open‑source - SHL is fully free; paid providers may require separate subscriptions.

### Limitations
SHL does not process user‑audited or user‑modified files. The library does not perform self‑healing corrections on user data files or configuration files; it operates strictly within the application’s own localization layer.

### Architecture
SHL’s architecture is based on a layered model where the localization engine routes translation requests through a router to different providers. The provider layer uses configuration that defines provider priorities, timeouts, environment variables, and content filtering.

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
pip install -i https://test.pypi.org/simple/ self-healing-localization==0.2.9
```

## Environment Variables (.env)
Create a `.env` file in your project root (optional):
```ini
MYMEMORY_EMAIL=your@email.com
MYMEMORY_API_KEY=your-api-key
LIBRETRANSLATE_API_KEY=your-api-key
DEEPL_API_KEY=your-api-key
GOOGLE_API_KEY=your-api-key
MICROSOFT_TRANSLATOR_KEY=your-api-key
NAVER_CLIENT_ID=your-api-key
NAVER_CLIENT_SECRET=your-api-key
YANDEX_API_KEY=your-api-key
LOCAL_TRANSLATOR_API_KEY=your-api-key
```

> Environment variables are optional, but required for providers that use API keys.
If a provider has no API key, SHL will still work offline and fall back to local translation or self‑healing behavior

## Configuration via config.conf
Create a `config.conf` in your project root:

```ini
[SETTINGS]
language = fi
base_lang = en
m_translation_enabled = true
```

> The library generates `shl-config.json` and `shl-policy-config.json` automatically in the project root.

## Quick Start

### 1. Basic UI Localization
Initialize the engine and start retrieving text. Missing keys are added to your JSON files automatically.

```python
from shl.engine import LocalizationEngine

shl.setup_logging("DEBUG")

# Initialize the engine (user language = Finnish, base = English)
engine = LocalizationEngine(base_lang="en")

# If 'welcome_msg' is missing, it is created with the given default value
title = engine.ui_text("welcome_msg", "Welcome to the App!")

print(title)  # "Tervetuloa sovellukseen!" (if translation exists)
```

#### SHL interprets this as:

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
 
### 3. Enable Machine Translation
Machine translation is disabled by default. Enable it when you want missing texts to be translated automatically.

```python
config = {"m_translation_enabled": True} 					# you can overwrite config in code
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

### 8. UI translations
Check the latest documentation files.

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

> **No more missing translations. No more incomplete language packs. Localization that heals itself.**


#localization • #i18n • #l10n • #self-healing • #translation • #multilingual #json • #python • #developer-tools • #automation • #templates • #cli #ai-assisted • #language-files • #internationalization • #localization-engine

