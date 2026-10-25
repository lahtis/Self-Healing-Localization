# SHL Guide

This is the full guide for Self-Healing Localization (SHL).
For a quick overview, see the [README](../README.md).

---

## Table of contents

1. [Installation](#installation)
2. [Configuration](#configuration)
3. [Basic usage](#basic-usage)
4. [Adding a new string](#adding-a-new-string)
5. [You stay in control](#you-stay-in-control)
6. [Language codes](#language-codes)
7. [Which provider should I use?](#which-provider-should-i-use)
8. [How it works](#how-it-works)
9. [Supported providers](#supported-providers)
10. [Coming from gettext?](#coming-from-gettext)
11. [Limitations](#limitations)
12. [Troubleshooting](#troubleshooting)

---

## Installation

### Stable (PyPI)

```bash
pip install self-healing-localization
```
Latest development (TestPyPI)

Latest development (TestPyPI)
bash

pip install -i https://test.pypi.org/simple/ self-healing-localization==0.3.0

Virtual environment (recommended)
bash

python3 -m venv venv
source venv/bin/activate
pip install self-healing-localization

Configuration
Environment variables (.env)

SHL works without API keys — it falls back to a local provider if
available. For the best results, create a .env file in your project
root with at least one provider:
ini

# Free tier — good for small projects
MYMEMORY_EMAIL=your@email.com

# Or: best quality (paid)
# DEEPL_API_KEY=your-api-key

# Or: self-hosted
# LIBRETRANSLATE_API_KEY=your-api-key
# LIBRETRANSLATE_URL=http://localhost:5000

# Or: local provider (if installed)
# LOCAL_TRANSLATOR_API_KEY=your-api-key

# Language detection (optional)
# DETECTLANGUAGE_API_KEY=your-api-key

If you don't have any API keys, SHL will still work — but translations
may be limited to the local provider.
<!-- TARKISTA: Onko Local-provider oletuksena käytössä ilman .env:iä? Jos ei, kerro se tässä. -->
config.conf

Create a config.conf in your project root:
ini

[SETTINGS]
language = fin
base_lang = eng
m_translation_enabled = true

    The library generates shl-config.json and shl-policy-config.json
    automatically in the project root.

config.json (provider policy)

For fine-grained control over providers, use shl-config.json:
json

{
  "providers": {
    "MyMemory": {
      "enabled": true,
      "priority": 8,
      "requires_env": ["MYMEMORY_EMAIL"]
    },
    "Local": {
      "enabled": true,
      "priority": 1,
      "requires_env": ["LOCAL_TRANSLATOR_API_KEY"]
    }
  }
}

    Tip: Use the SHL Policy Editor
    to edit this file visually.

Basic usage
UI localization
python

from shl.engine import LocalizationEngine

engine = LocalizationEngine(base_lang="eng", lang_code="fin")
title = engine.ui_text("welcome_msg", "Welcome to the App!")
print(title)  # "Tervetuloa sovellukseen!" (if translation exists)

How SHL interprets base_lang and lang_code

    base_lang — the language your source code is written in.
    SHL uses it to know which JSON file is the authoritative source,
    and which language to translate from.

    lang_code — the language the user wants to see.
    SHL uses it to decide which JSON file to read and write.

Example:

    base_lang="eng" → source strings are English.

    lang_code="fin" → user wants Finnish UI.

Enable machine translation

Machine translation is disabled by default. Enable it when you want
missing texts to be translated automatically:
python

config = {"m_translation_enabled": True}
engine = LocalizationEngine(lang_code="fin", config=config)

text = engine.ui_text("new_key", "Hello World!")
# → "Hei maailma!" (automatically translated to Finnish)

Prompt templates

SHL handles localized AI prompt templates the same way as UI text:
python

prompt = engine.template("summarize_task", "Please summarize the following text:")

If the template file for the current language does not exist, it is
created automatically using the base language as the source.
Dynamic language switching

Switch languages at runtime without restarting the application:
python

engine = LocalizationEngine(lang_code="eng", config={"m_translation_enabled": True})

# Switch to Finnish
engine.set_language("fin")
print(engine.ui_text("greeting", "Hello!"))  # "Hei!" (machine-translated)

# Switch to Swedish
engine.set_language("swe")
print(engine.ui_text("greeting", "Hello!"))  # "Hej!" (machine-translated)

Region subtag support
python

# Brazilian Portuguese and European Portuguese in separate files
engine = LocalizationEngine(lang_code="pt-BR")  # → pt-br.json
engine = LocalizationEngine(lang_code="pt-PT")  # → pt-pt.json

# Traditional and Simplified Chinese in separate files
engine = LocalizationEngine(lang_code="zh-TW")  # → zh-tw.json
engine = LocalizationEngine(lang_code="zh-CN")  # → zh-cn.json

Direct translation (smart routing)
python

from shl.engine.translation import translate_text

# Automatically chooses the best provider
result = translate_text("Hello World", target_lang="fin")
print(result)  # "Hei maailma"

Adding a new string

Before:
python

menu = Gtk.Menu()
menu.append(ui_text("File", "File"))
menu.append(ui_text("Edit", "Edit"))

You add a new item:
python

menu.append(ui_text("Settings", "Settings"))   # ← new key

Next time the app starts:
json

{
  "File": "Tiedosto",
  "Edit": "Muokkaa",
  "Settings": "Asetukset"   // ← translated automatically
}

No xgettext. No .po file. No msgfmt. No manual translation.
You stay in control

Machine translation is a starting point, not the final word.
Once a translation is saved to locales/<lang>.json, you can edit it
by hand. SHL will not overwrite your edits — it only fills in what's
missing.

If you want to translate everything manually, just disable
m_translation_enabled in your config:
python

config = {"m_translation_enabled": False}
engine = LocalizationEngine(lang_code="fin", config=config)
# Missing keys are created with the default value, but not translated.

Language codes

SHL accepts ISO 639-1, ISO 639-3, and BCP-47 language codes.
Internally, files use the canonical ISO 639-3 form:
Input	File
fin, fi, fi-FI	fin.json
fra, fr, fr-FR	fra.json
pt-BR	pt-br.json
zh-TW	zh-tw.json
<!-- TARKISTA: Onko tämä oikein? README:ssä aiemmin luki sekä ISO 639-3 että pt-BR → pt-br.json. Varmista, että tiedostonimet ovat todella näin (ISO 639-3 vs. BCP-47). -->
Which provider should I use?
Situation	Recommended
Offline / no API key	Local
Free tier, quick start	MyMemory
Best quality	DeepL
Self-hosted	LibreTranslate
Enterprise	Microsoft Translator / Google
<!-- TARKISTA: Onko Local oikeasti ilmainen ja offline? Configissa Local vaatii LOCAL_TRANSLATOR_API_KEY:n. Jos se on paikallinen palvelin, kerro se tässä. -->
How it works
text

┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Your app       │────▶│  LocalizationEngine │───▶│  Provider router │
│  ui_text(...)   │     │  (fallback chain)  │     │  (10 providers)  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
                                                 ┌─────────────────┐
                                                 │ locales/fra.json │
                                                 └─────────────────┘

    Your app calls ui_text("key", "Default text").

    If the key exists in locales/<lang>.json, it is returned immediately.

    If not, SHL asks the provider router for a translation.

    The router tries providers in priority order (configurable).

    The result is saved to locales/<lang>.json and returned.

Eager translation, not lazy

Most localization libraries translate lazily: when the user opens a
menu, the string is translated on demand — and the UI lags.

SHL translates eagerly: preload() scans your source code,
translates all missing keys at startup, and saves them to JSON.
When the user opens a menu, the translation is already on disk.

No lazy loading. No UI lag. Translations are ready before the user
needs them.
Supported providers
Tested and operational
Provider	Free tier	API key	Notes
MyMemory	✅	email	Rate-limited, good for small projects
DeepL	❌	✅	Best quality, paid
LibreTranslate	✅	optional	Self-hosted or community
LibreTranslate Community	✅	optional	Public instance
<!-- TARKISTA: Onko Local testattu? Configissa se on enabled. Lisää se taulukkoon, jos se on tuotantokäytössä. -->
Implemented, not yet fully tested
Provider	Notes
Google Translate	Requires API key
Microsoft Translator	Requires API key
Papago	Korean-focused, requires Naver keys
Yandex	Russian-focused, requires API key
DetectLanguage	Language detection only

    Developer note: SHL is a zero-budget project. Providers are
    implemented first, tested as resources allow. If you can test a
    provider, please open an issue with your results.

Memory providers

The following memory providers have been tested and are currently
operational (as of v0.2.17):

    MyMemory.dev

    Note that MYMEMORY_API_KEY (translated.com) and
    MYMEMORY_DEV_API_KEY (mymemory.dev) are separate variables for
    separate services.

Coming from gettext?

If your code already uses gettext-style calls:
python

from gettext import gettext as _

label = _("Welcome")
count = ngettext("%d message", "%d messages", n)

SHL's scanner will pick up "Welcome" and the plural forms. You can:

    Keep using gettext for runtime translation, and use SHL only to
    generate JSON files from your existing code.

    Migrate gradually: replace _() with L() one file at a time.

    Run both side by side — gettext for legacy code, SHL for new code.

SHL does not read or write .po / .mo files. If you need full
gettext interoperability (round-trip between JSON and .po), that is
not built in — but the scanner can read gettext-style calls, so SHL
can coexist with an existing gettext setup.
Limitations

    SHL does not translate user-generated content. If your users
    write messages, comments, or reviews, those stay in the language
    they were written in. SHL is a localization library, not a content
    translation service.

    SHL does not modify user data or configuration files. It only
    operates on the application's own localization layer.

    Machine translation quality depends on the provider. Review
    translations before shipping.

    Some providers require paid subscriptions or API keys.

    SHL is in beta. APIs may change before 1.0.

Troubleshooting
"My translations don't appear"

    Check that m_translation_enabled is True.

    Check that a provider is enabled in shl-config.json.

    Check error.log for provider errors.

    Verify the JSON file exists: locales/<lang>.json.

"The JSON file is empty"

The file may be created empty on first run and filled on the next
startup. If it stays empty:

    Check that preload() ran to completion.

    Check that the scanner found keys: grep -rn "ui_text" .

    Check that the provider returned a translation.

"Wrong language in the UI"

    Check lang_code in your config.

    Check that locales/<lang>.json exists and contains the right keys.

    If the language is not supported, SHL falls back to base_lang.

"Translation failed for key X"

This is logged when a provider returns an error. The key is saved with
its default value, and the next run will try again.
See also

    README — quick overview

    Policy Editor — visual config editor

    Digital Guestbook — demo application

    Codeberg repository















## Overview
Self‑Healing Localization Library (SHL) is a dependency‑free Python library that automates application localization and independently repairs missing translations. The library creates, updates, and synchronizes translation files throughout the application’s lifecycle without manual maintenance.

SHL follows a self‑healing principle: when the application requests a missing translation key, the library automatically generates it, fetches a machine translation if needed, and stores the result in the correct language file. This makes localization deterministic and reduces developer workload.

### Features
* Automatic creation of missing translations
* Automatic generation of new language files
* BCP‑47 language code support (e.g., fi‑FI, pt‑BR, zh‑TW)
* GLFM‑based language validation
* Machine translation support: Microsoft Translator, DeepL, Google Translate, MyMemory, LibreTranslate, LibreTranslate Community, Papago Translate, Yandex Translate and Localhost.
* Self‑healing localization pipeline
* Unified high‑level localization engine
* Offline and online support
* Zero‑dependency core
* Free and open‑source - SHL is fully free; paid providers may require separate subscriptions.

### Translation Providers Status
The following translation providers have been tested and are currently operational:

* MyMemory (translated.net)
* DeepL
* LibreTranslate
* LibreTranslate Community

The other supported providers are implemented but have not yet been fully tested.

> **Developer note:** SHL is a zero-budget project. Provider support is implemented first, while full provider testing is performed as resources allow. MyMemory, DeepL, LibreTranslate, and LibreTranslate Community have currently been tested successfully. Some providers may require a temporary paid subscription or other access in order to complete testing.

### Memory Providers Status
The following memory providers have been tested and are currently operational (as of v0.2.17):

* MyMemory.dev

> Note that `MYMEMORY_API_KEY` (translated.com) and `MYMEMORY_DEV_API_KEY` (mymemory.dev) are separate variables for separate services.

### Limitations
SHL does not process user‑audited or user‑modified files. The library does not perform self‑healing corrections on user data files or configuration files; it operates strictly within the application’s own localization layer.

### Architecture
SHL’s architecture is based on a layered model where the localization engine routes translation requests through a router to different providers. The provider layer uses configuration that defines provider priorities, timeouts, environment variables, and content filtering.


---

## Quick Start

### Installation

## Creating a virtual environment
```bash
python3 -m venv venv

source venv/bin/activate
```

### Stable (PyPI)
```bash
pip install self-healing-localization
```
---

### Latest Development (TestPyPI)
```bash
pip install -i https://test.pypi.org/simple/ self-healing-localization==0.3.0
```

## Environment Variables (.env)
Create a `.env` file in your project root (optional):
```ini
MYMEMORY_EMAIL=your@email.com
LIBRETRANSLATE_API_KEY=your-api-key
LIBRETRANSLATE_COMMUNITY_API_KEY=your-api-key
MYMEMORY_DEV_API_KEY=your-api-key
DEEPL_API_KEY=your-api-key
GOOGLE_API_KEY=your-api-key
MICROSOFT_TRANSLATOR_KEY=your-api-key
NAVER_CLIENT_ID=your-api-key
NAVER_CLIENT_SECRET=your-api-key
YANDEX_API_KEY=your-api-key
LOCAL_TRANSLATOR_API_KEY=your-api-key
DETECTLANGUAGE_API_KEY=your-api-key
```

> Environment variables are optional, but required for providers that use API keys. If a provider has no API key, SHL will still work offline and fall back to local translation or self‑healing behavior.

## Configuration via config.conf
Create a `config.conf` in your project root:

```ini
[SETTINGS]
language = fin
base_lang = eng
m_translation_enabled = true
```

> The library generates `shl-config.json` and `shl-policy-config.json` automatically in the project root.

## Quick Start

### 1. Basic UI Localization
Initialize the engine and start retrieving text. Missing keys are added to your JSON files automatically.

```python
from shl.engine import LocalizationEngine

shl.setup_logging("DEBUG")

# Initialize the engine ISO 639-3 (user language = Finnish, base = English)
engine = LocalizationEngine(base_lang="eng")

# If 'welcome_msg' is missing, it is created with the given default value
title = engine.ui_text("welcome_msg", "Welcome to the App!")

print(title)  # "Tervetuloa sovellukseen!" (if translation exists)
```

#### SHL interprets this as:

* base_lang="eng" → source code strings are English
* lang_code="fin" → user wants Finnish UI

So SHL does:
* 1. Look for welcome_msg in fin.json
* 2. If missing:
- Create the key in fin.json
- Use the default value "Welcome to the App!" as the English source
- Translate English → Finnish

* 3. Return the Finnish result

> Note: SHL uses ISO 639-3 (ISO 3-letter) language codes, such as eng for English, fin for Finnish, ita for Italian, and fra for French.

#### Core takeaway

- base_lang = the language your source JSON files are written in  
- lang_code = the language the user wants to see in the UI right now
Everything else in SHL’s behavior flows from that.

#### How SHL interprets these two parameters

##### 1) base_lang

This is the language of your canonical UI strings — the language your codebase “speaks”.


SHL uses base_lang to:
* know which JSON file is the authoritative source
* know what language missing keys should be stored in
* know what language to translate from when generating other languages


##### 2) lang_code

This is the language the user wants to see.

Examples:
* Finnish user → lang_code="fin"
* English user → lang_code="eng"
* Italian user → lang_code="ita"

SHL uses lang_code to:

* decide which JSON file to read from
* decide which JSON file to write new keys into
* decide which language to translate to

--- 
 
### 3. Enable Machine Translation
Machine translation is disabled by default. Enable it when you want missing texts to be translated automatically.

```python
config = {"m_translation_enabled": True} 					# you can overwrite config in code
engine = LocalizationEngine(lang_code="fin", config=config)

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
engine = LocalizationEngine(lang_code="eng", config={"m_translation_enabled": True})

# Switch to Finnish
engine.set_language("fin")
print(engine.ui_text("greeting", "Hello!"))  # "Hei!" (Machine-translated)

# Switch to Swedish
engine.set_language("swe")
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
result = translate_text("Hello World", target_lang="fin")
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

