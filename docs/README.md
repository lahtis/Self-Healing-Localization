# SHL — Self-Healing Localization Documentation
## Complete Technical API Reference

> **Version:** 0.2.0  
> **Author:** Tuomas Lähteenmäki  
> **License:** MIT  
> **Scope:** Core engine, translation subsystem, providers, utilities, and GLFM integration.

---

Welcome to the Self-Healing Localization Library documentation. SHL is a smart, zero-overhead localization library featuring automated missing-key translation and robust language fallback chains.

## Quick Links

- [Getting Started](guides/getting_started.md)
- [Configuration Guide](guides/configuration.md)
- [Usage Guide](guides/usage.md)
- [API Reference](api/engine.md)
- [Full Guide] (SHL_Complete_API_Reference.md)

---

## Contents

### Guides
- [Getting Started](guides/getting_started.md) - Installation and basic code integration.
- [Configuration](guides/configuration.md) - Setting up `config.conf`, environment variables, and translation providers.
- [Usage Guide](guides/usage.md) - Deep dive into dynamic switching, prompt templates, and GLFM data modes.

### API Reference
- [LocalizationEngine API](api/engine.md) - Main interface for UI text, templates, and runtime state.
- [Translation API](api/translation.md) - Standalone translation utilities, smart routing, and error boundaries.

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
