# SHL Documentation

Welcome to the Self-Healing Localization (SHL) documentation.

## Quick Links

- [Getting Started](guides/getting_started.md)
- [API Reference](api/index.md)
- [Examples](examples/)
- [Configuration](guides/configuration.md)

## Contents

### Guides
- [Getting Started](guides/getting_started.md) - First steps with SHL
- [Configuration](guides/configuration.md) - Configuring SHL
- [Translation Services](guides/translation.md) - Using MyMemory, LibreTranslate, and mirrors
- [GLFM Integration](guides/glfm.md) - Language validation and fallback chains

### API Reference
- [LocalizationEngine](api/engine.md) - Main engine
- [Localizer](api/localizer.md) - UI text localization
- [TemplateLocalizer](api/template_localizer.md) - AI prompt templates
- [Translation Module](api/translation.md) - Translation services
- [LanguageValidator](api/language_validator.md) - Language validation with GLFM

### Examples
- [Basic Usage](examples/basic_usage.py)
- [Custom Language](examples/custom_language.py)
- [Translation Services](examples/translation_services.py)

## Building Documentation

```bash
# Install dependencies
pip install mkdocs mkdocs-material

# Serve locally
mkdocs serve

# Build
mkdocs build
