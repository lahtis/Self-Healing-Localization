# Self‑Healing Localization (SHL)
### Automatic, self‑maintaining localization for any Python project  
**Author:** Tuomas Lähteenmäki  
**License:** MIT  
**Version:** 0.1.1

**DEV:** 0.2.0


![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
[![TestPyPI](https://img.shields.io/badge/TestPyPI-self--healing--localization-blue)](https://test.pypi.org/project/self-healing-localization/)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active-success)
![Platform](https://img.shields.io/badge/Platform-Cross--platform-lightgrey)
![Localization](https://img.shields.io/badge/Localization-Self--Healing-orange)


---

## 🌍 Overview

Self‑Healing Localization (SHL) is a lightweight, dependency‑free Python library that eliminates missing translations forever.

It provides:

- automatic creation of missing language files  
- automatic creation of missing keys  
- fallback to a base language (default: English)  
- unified support for both UI text and AI prompt templates  
- optional AI‑powered translation (planned for v0.2)  

This library is designed to be **dropped into any project** — from small scripts to full applications — and it will maintain localization files automatically as the project grows.

No more manual JSON editing.  
No more “missing translation” errors.  
No more incomplete language packs.

---

## ✨ Key Features

### ✔ Self‑healing UI localization  
- Missing language files are created automatically  
- Missing keys are added on the fly  
- Base language is used as fallback  

### ✔ Self‑healing AI prompt template localization  
- Missing template files are generated automatically  
- Base templates are copied as fallback  
- Missing template keys are added automatically  

### ✔ Unified high‑level engine  
The `LocalizationEngine` ties everything together:

- ensures languages exist  
- synchronizes all languages with the base language  
- provides clean access to UI text and templates  

### ✔ Zero dependencies  
Pure Python. Works everywhere.

---

## 📦 Installation

(PyPI release planned for v0.2)

Clone the repository:

```bash
git clone https://codeberg.org/lahtis/Self_Healing_Localization
```

Import the engine:

```python
from shl.engine import LocalizationEngine
```

---

## 🚀 Quick Start

### 1. Initialize the engine

```python
from shl.engine import LocalizationEngine

engine = LocalizationEngine(lang_code="fi")  # Finnish
```

### 2. Retrieve UI text

```python
title = engine.ui_text("app_title", "My Application")
```

If `"app_title"` does not exist in `locales/lang_fi.json`, it will be added automatically.

### 3. Retrieve prompt templates

```python
summary_prompt = engine.template("summary_short", "Summarize the text:")
```

If `prompts/fi.json` does not exist, it will be created automatically using `prompts/en.json` as the base.

---

## 🧩 Project Structure

```
SHL/
│
├─ api/
│   ├─ localizer.py            # UI text localization
│   ├─ template_localizer.py   # Prompt template localization
│   ├─ engine.py               # Unified high-level manager
│   └─ ai_translation.py       # (planned) AI-powered translation
│
├─ locales/
│   └─ lang_en.json            # Base UI language
│
├─ prompts/
│   └─ en.json                 # Base template language
│
└─ README.md
```

---

## 🔧 API Reference (v0.1)

### Initialize

```python
engine = LocalizationEngine(lang_code="fi")
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

---

## 🛠 Roadmap

### v0.2


---

## 🤝 Contributing

Contributions are welcome.  
This project aims to become a new standard for open‑source localization — simple, automatic, and self‑maintaining.

---

## 📄 License

MIT License — free for personal and commercial use.

---

## ⭐ Vision

Localization should never be a burden.

With SHLL, any project can become multilingual — automatically, reliably, and without manual maintenance.

**No more missing translations.  
No more incomplete language packs.  
Localization that heals itself.**


#localization • #i18n • #l10n • #self-healing • #translation • #multilingual  
#json • #python • #developer-tools • #automation • #templates • #cli  
#ai-assisted • #language-files • #internationalization • #localization-engine

