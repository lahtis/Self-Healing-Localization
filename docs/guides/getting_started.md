# Getting Started

## Installation

```bash
pip install self-healing-localization
```
--- 

# Basic Usage
```python
from shl.engine import LocalizationEngine

# Initialize engine (Finnish as active language, English as base)
engine = LocalizationEngine(lang_code="fi", base_lang="en")

# Retrieve UI text — missing keys are created automatically
title = engine.ui_text("welcome_msg", "Welcome to the App!")
print(title)  # "Tervetuloa sovellukseen!"
```
--- 

# Configuration

Create config.conf in your project root:
```ini
[SETTINGS]
language = fi
base_lang = en
m_translation_enabled = true
```
```python
engine = LocalizationEngine()  # Reads from config.conf
```
--- 

# Enable Machine Translation
```python
config = {"m_translation_enabled": True}
engine = LocalizationEngine(lang_code="fi", config=config)

text = engine.ui_text("new_key", "Hello World!")
# → "Hei maailma!"
```

--- 

# Dynamic Language Switching
```python
engine = LocalizationEngine(lang_code="en")
engine.set_language("fi")
print(engine.ui_text("greeting", "Hello!"))  # "Hei!"
```

--- 

# Prompt Templates
```python
prompt = engine.template("summarize_task", "Please summarize the following text:")
```

---
