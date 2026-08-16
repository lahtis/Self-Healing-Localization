# SHL — Self-Healing Localization Library Documentation
## Complete Technical API Reference

> **Version:** 0.2.3  
> **Author:** Tuomas Lähteenmäki  
> **License:** MIT  
> **Scope:** Core engine, translation subsystem, providers, utilities, and GLFM integration.

---

Welcome to the Self-Healing Localization Library documentation. SHL is a smart, zero-overhead localization library featuring automated missing-key translation and robust language fallback chains.

## Quick Links

- [Getting Started](guides/v0_2_0/getting_started.md)
- [Configuration Guide](guides/v0_2_0/configuration.md)
- [Usage Guide](guides/v0_2_0/usage.md)
- [API Reference](api/v0_2_0/engine.md)
- [Full Guide](api/v0_2_3/SHL_Complete_API_Reference_v023.md)
- [Development](development/readme.md)
---

# What Makes SHL Different?

## Feature Comparison

| Feature | SHL | Traditional i18n | Other (gettext, Babel) |
|---------|-----|------------------|------------------------|
| Missing keys created automatically | ✅ Yes | ❌ No | ❌ No |
| Missing language files created automatically | ✅ Yes | ❌ No | ❌ No |
| Zero runtime dependencies | ✅ Yes | ❌ No | ❌ No (often require gettext, Babel, etc.) |
| BCP-47 region subtag support | ✅ Yes | ⚠️ Limited | ⚠️ Limited |
| GLFM language validation (7,900+ languages) | ✅ Yes | ❌ No | ❌ No |
| Self-healing fallback chains | ✅ Yes | ❌ No | ❌ No |
| Smart translation routing | ✅ Yes | ❌ No | ❌ No |
| Provider-agnostic architecture | ✅ Yes | ❌ No | ❌ No |
| DeepL, Google, Papago, MyMemory support | ✅ Yes | ❌ No | ❌ No |
| AI-powered quality validation (future) | ✅ Planned | ❌ No | ❌ No |
| Human-editable translation files | ✅ Yes | ✅ Yes | ✅ Yes |
| No translation memory (TM) required | ✅ Yes | ⚠️ Optional | ⚠️ Optional |

---

## Translation Capabilities

| Feature | SHL | Traditional i18n | Other |
|---------|-----|------------------|-------|
| Single words | ✅ Yes | ✅ Yes | ✅ Yes |
| Complete sentences | ✅ Yes | ❌ No | ❌ No |
| Dynamic text | ✅ Yes | ❌ No | ❌ No |
| Questions | ✅ Yes | ❌ No | ❌ No |
| Error messages | ✅ Yes | ❌ No | ❌ No |
| Placeholders and variables | ✅ Yes | ⚠️ Manual only | ⚠️ Manual only |
| Context-aware translations | ✅ Planned | ❌ No | ❌ No |
| Formality levels | ✅ DeepL only | ❌ No | ❌ No |
| HTML/Markdown preservation | ✅ DeepL/Google | ❌ No | ❌ No |
| Glossary support | ✅ DeepL | ❌ No | ❌ No |

---

## AI-Powered Translation Quality

### Current State (v0.2.2)

SHL uses multiple translation providers to ensure the best quality:

| Provider | Best For | Features |
|----------|----------|----------|
| **DeepL** | European languages | Formality, glossary, context, HTML preservation |
| **Papago** | Asian languages (Korean, Japanese, Chinese) | Cultural accuracy |
| **Google Translate v2** | Wide language coverage | HTML format, failover |
| **MyMemory** | Free, always available | Community translations |

### AI-Powered Quality Pipeline (Planned)

---

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

## Contents

### Guides
- [Getting Started](guides/v0_2_0/getting_started.md) - Installation and basic code integration.
- [Configuration](guides/v0_2_0/configuration.md) - Setting up `config.conf`, environment variables, and translation providers.
- [Usage Guide](guides/v0_2_0/usage.md) - Deep dive into dynamic switching, prompt templates, and GLFM data modes.

### API Reference
- [LocalizationEngine API](api/v0_2_0/engine.md) - Main interface for UI text, templates, and runtime state.
- [Translation API](api/v0_2_0/translation.md) - Standalone translation utilities, smart routing, and error boundaries.

### Examples
- [Basic Usage](examples/basic_usage.py) - Quick-start setup example.
- [Dynamic Configuration](examples/configuration_setup.py) - Working with local config files and environment variables.
- [Direct Translation](examples/translation_services.py) - Utilizing the smart provider routing standalone.

---

## Building Documentation Locally

The documentation is built using MkDocs and the Material theme.

```bash
# Install required dependencies
pip install mkdocs mkdocs-material

# Preview and serve the documentation locally (updates in real-time)
mkdocs serve

# Build static HTML site for deployment
mkdocs build
