# Getting Started

## Installation

```bash
pip install self-healing-localization
```
--- 

## Basic Usage
```python
from shl.engine import LocalizationEngine

# Initialize engine (Finnish as active language, English as base)
engine = LocalizationEngine(lang_code="fi", base_lang="en")

# Retrieve UI text — missing keys are created automatically
title = engine.ui_text("welcome_msg", "Welcome to the App!")

print(title)  # "Tervetuloa sovellukseen!"
```
--- 

## Configuration via File

Create config.conf in your project root:
```ini
[SETTINGS]
language = fi
base_lang = en
m_translation_enabled = true
```

```python
from shl.engine.core import LocalizationEngine

# Automatically reads configurations from config.conf
engine = LocalizationEngine()
```
--- 

## Enable Machine Translation
Machine translation can be toggled on during initialization to allow automatic real-time fallbacks using configured providers.
```python
from shl.engine.core import LocalizationEngine

engine = LocalizationEngine(
    lang_code="fi", 
    m_translation_enabled=True
)

text = engine.ui_text("new_key", "Hello World!")

print(text)  # "Hei maailma!"
```

--- 

## Dynamic Language Switching
Your application's source code and default strings can be written in any language. However, using a major language (like English) as your base is highly recommended to ensure the highest possible machine translation quality.
```python
# Start with the language used in your source code (e.g., "en")
engine = LocalizationEngine(lang_code="en")

# Switch the active UI language dynamically
engine.set_language("fi")

print(engine.ui_text("greeting", "Hello!"))  # "Hei!"
```

--- 

## Prompt Templates
Just like with UI text, your default prompt templates in the source code can be written in any language. However, using a major base language (like English) is recommended for the best translation accuracy.
```python
from shl.engine.core import LocalizationEngine

engine = LocalizationEngine(lang_code="fi")

# Retrieves or creates the prompt template translated into Finnish
prompt = engine.template("summarize_task", "Please summarize the following text:")

print(prompt)  # "Tiivistä seuraava teksti:"
```

---
