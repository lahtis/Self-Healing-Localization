# SHL Engine Package — API Documentation

## Module Overview

**File:** `shl/engine/__init__.py`

Package-level initialization for the `shl.engine` subpackage. Re-exports the three core engine classes that form the backbone of SHL's localization system: the unified engine, the UI text localizer, and the prompt template localizer.

---

## Public API

### Core Classes

| Export | Source Module | Description |
|--------|--------------|-------------|
| `LocalizationEngine` | `shl.engine.core` | Central orchestration engine. Coordinates UI text, prompt templates, GLFM language validation, fallback chains, and machine translation routing. This is the primary entry point for most applications. |
| `Localizer` | `shl.engine.localizer` | Manages UI text translations stored as JSON files. Handles key-based lookups, lazy file creation, and JSON persistence. |
| `TemplateLocalizer` | `shl.engine.template_localizer` | Manages AI prompt template translations stored as JSON files. Handles key-based lookups, template formatting, and JSON persistence. |

---

## `__all__` Export List

```python
__all__ = [
    "LocalizationEngine",
    "Localizer",
    "TemplateLocalizer",
]
```

---

## Usage Examples

### Using LocalizationEngine (Recommended)

```python
from shl.engine import LocalizationEngine

# Initialize the full engine
engine = LocalizationEngine(
    lang_code="fi",
    base_lang="en",
    ui_folder="locales",
    template_folder="prompts",
    deepl_key="your-key",
)

# UI text with fallback and optional translation
text = engine.ui_text("welcome", "Welcome!")

# Prompt template with formatting
prompt = engine.template("summarize", "Summarize: {text}", text="Article...")
```

### Using Localizer Directly

```python
from shl.engine import Localizer

# Standalone UI text localizer
localizer = Localizer(
    lang_code="fi",
    base_lang="en",
    folder="locales",
)

# Get or create key
text = localizer.get_text("greeting", "Hello!")

# Set key explicitly
localizer.set_text("farewell", "Goodbye!")
```

### Using TemplateLocalizer Directly

```python
from shl.engine import TemplateLocalizer

# Standalone prompt template localizer
templates = TemplateLocalizer(
    lang_code="fi",
    base_lang="en",
    folder="prompts",
)

# Get template
template = templates.get_template("code_review", "Review: {code}")

# Get and format
template = templates.get_template("summarize", "Summarize in {lang}: {text}")
result = template.format(lang="Finnish", text="...")
```

---

## Class Hierarchy

```
shl.engine
├── LocalizationEngine      ← Unified API (uses both localizers + translation)
│   ├── ui_localizer        ← Localizer instance
│   └── template_localizer  ← TemplateLocalizer instance
├── Localizer               ← UI text JSON management
└── TemplateLocalizer       ← Prompt template JSON management
```

---

## When to Use Which

| Use Case | Recommended Class |
|----------|-------------------|
| Full application with UI + AI prompts + translation | `LocalizationEngine` |
| Simple UI text localization only | `Localizer` |
| AI prompt template management only | `TemplateLocalizer` |
| Custom integration with own routing logic | `Localizer` + `TemplateLocalizer` |

---

## Import Map

| Public Name | Internal Source |
|-------------|-----------------|
| `LocalizationEngine` | `shl.engine.core.LocalizationEngine` |
| `Localizer` | `shl.engine.localizer.Localizer` |
| `TemplateLocalizer` | `shl.engine.template_localizer.TemplateLocalizer` |

---

## Changelog

| Version | Notes |
|---------|-------|
| Current | Exports `LocalizationEngine`, `Localizer`, and `TemplateLocalizer` at the `shl.engine` package level. |
