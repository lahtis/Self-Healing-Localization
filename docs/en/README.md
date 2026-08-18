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
| **LibreTranslate | Privacy, self-hosting, and offline use | Open-source, self-hosted API, offline support, Argos Translate engine |
| **MyMemory** | Free, always available | Community translations |

## Translation API Comparison

### Feature Comparison

| SHL | Provider | HTML format | Glossaries | Formal/informal tone | Contextual suggestions | Honorifics | Language detection | Document translation | Website translation | Batch translation | Notes |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| + | **DeepL** | + | + | + | – | – | – | + (limited) | – | + | Highest quality especially for European languages. Free quota 500k characters/month (one-time). |
| + | **Papago** | – | + | + (only certain languages) | – | + | + | + | + | – | Strong in Asian languages, especially Korean. |
| + | **Google Translate v2** | + | – (v2) / + (v3) | + | + | – | + | + | – | + | Widest language support (100+ languages). Free 500k characters/month. |
| + | **LibreTranslate** | + (*) | – | – (***) | – | – | + | + | – | + | Only free and self-hostable option. Quality lower than commercial options. |
| + | **myMemory** | – | – | – | – | – | + (limited) | + | – | + | Free but limited to 5000 characters/day. Leverages huge translation memory. |
| - | **Microsoft Azure Translator** | + | + | + | – | – | + | + | – | + | Most affordable of the major cloud providers (~$10 / million chars). |
| - | **Amazon Translate** | ? | + | – | – | – | + | + | – | + | S3 batch translations and deep AWS integration. |
| - | **ModernMT** | ? | + (Adaptive) | ? | + | ? | ? | + (DOCX) | ? | + | Learns in real-time from translation memory, 200+ languages. |
| - | **SYSTRAN** | ? | + | ? | ? | ? | ? | ? | ? | ? | Strong in specialized domains (e.g., legal, technical). |
| - | **IBM Watson** | ? | + | ? | ? | ? | ? | ? | ? | ? | Customizable for your own data and industry. |
| - | **Yandex Translate** | ? | + | ? | ? | ? | ? | ? | ? | ? | Wide language support and enterprise-grade support. |
| - | **OpenAI (GPT-4o etc.)** | + (via prompt) | + (via prompt) | + (via prompt) | + | + (via prompt) | + | – | – | + | Excellent for tone, style and context management, but expensive and slower compared to NMT APIs. |

#### Legend

| Symbol | Description |
| :---: | :--- |
| **+** | Full or strong support |
| **–** | No support or not a significant feature |
| **?** | Information not available |
| **(*)** | Experimental |
| **(***)** | Under development |
| **SHL +** | Service is on your original list |
| **SHL –** | Service was added later to the comparison |

### Feature Descriptions

| Feature | Description |
| :--- | :--- |
| **HTML format** | Preserves HTML tags and structure in translation |
| **Glossaries** | Custom dictionaries to ensure consistent translation of specific terms (e.g., product names) |
| **Formal/informal tone** | Adjust the formality level of the translation (e.g., "you" vs. "You" formal) |
| **Contextual suggestions** | Alternative translation suggestions that consider context |
| **Honorifics** | Support for honorific forms (especially in Asian languages) |
| **Language detection** | Automatic detection of the source language |
| **Document translation** | Translation of entire files (PDF, Word, Excel) |
| **Website translation** | Translation that preserves website structure |
| **Batch translation** | Translate multiple texts in a single request |

## POST Method Support

| SHL | Provider | POST support | Notes |
| :---: | :--- | :---: | :--- |
| + | **DeepL** | **Mandatory** | DeepL has announced that starting March 2025, the `/translate` endpoint will only accept POST requests. GET requests and query parameters will be rejected. This is done for security and industry best practices. |
| + | **Papago** | Yes | Papago's text translation API (`/nmt/v1/translation`) uses POST requests. API calls require Client ID and Client Secret in HTTP headers. |
| + | **Google Translate v2** | Yes | Google Translation API v2 uses POST requests. Text is sent as JSON in the request body (`q` parameter) and the API key is provided either as a URL query parameter or in the header. |
| + | **LibreTranslate** | Yes | LibreTranslate's REST API uses POST requests to the `/translate` endpoint. The request body contains the text (`q`), source and target language codes in JSON format. An API key can be included if required. |
| + | **myMemory** | Yes | myMemory's translation API (`/api/v1/translate`) accepts POST requests. Parameters (`q` and `langpair`) are sent URL-encoded in the request body. |
| - | **Microsoft Azure Translator** | Yes | Azure Translator Text API uses POST requests. Text is sent as JSON in the request body. |
| - | **Amazon Translate** | Yes | Amazon Translate API uses POST requests. Text is sent as JSON in the request body. |
| - | **ModernMT** | Yes | ModernMT's API uses POST requests. |
| - | **SYSTRAN** | Yes | SYSTRAN's API uses POST requests. |
| - | **IBM Watson** | Yes | IBM Watson Language Translator uses POST requests. |
| - | **Yandex Translate** | Yes | Yandex Translate API uses POST requests. |
| - | **OpenAI (GPT-4o etc.)** | Yes | OpenAI's API uses POST requests for chat completions. |

## How to Choose the Right API?

| SHL | Use Case | Recommended Service |
| :---: | :--- | :--- |
| + | **Highest quality (European languages)** | **DeepL** is the clear choice when translation fluency and naturalness are important. |
| + | **Broadest language support and scalability** | **Google Translate** is unmatched in the number of languages, and **Microsoft Azure** offers a very comprehensive selection at an affordable price. |
| - | **Best price and AWS ecosystem** | **Amazon Translate** is the logical choice in the AWS environment. **Microsoft Azure** is often the cheapest in terms of pricing. |
| + | **Asian markets (especially Korea)** | **Papago** is a strong, specialized option. |
| + | **Full control, privacy and cost** | **LibreTranslate** is the only option you can self-host for free. |
| + | **Quick prototyping without registration** | **myMemory** is an easy and quick way to test translations without an API key. |
| - | **Tone, style and complex content** | **LLM-based APIs** (OpenAI, Claude, Gemini) excel in marketing and brand content, but are more expensive. |
| - | **Specialized or regulated industries** | **SYSTRAN** and **IBM Watson** offer customization and security suitable for e.g., legal and healthcare sectors. |

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
- **GLFM Lite** (default): ~428 KB, 7,900+ languages and 20 nearest languages for fallback.
- **Full GLFM** (optional): ~925 MB – includes over 7,900 languages and their nearest languages (lang2vec / URIEL) for research and AI.
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
