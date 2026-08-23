# SHL Package Entry Point API Documentation

## Overview

This module serves as the entry point for the **Self-Healing Localization Layer (SHL)** package — a lightweight, dependency-free Python library that eliminates missing translations forever.

---

## Module Description

```
Self-Healing Localization Layer (SHL)
A lightweight, dependency-free Python library that eliminates missing translations forever.
```

---

## Exports

The following names are imported and made available at the package level:

| Name | Source Module | Description |
|------|---------------|-------------|
| `get_ttl` | `.config` | Imported from the package configuration module. |
| `get_config_value` | `.config` | Imported from the package configuration module. |
| `ConfigManager` | `.policy_manager` | Imported from the package policy manager module. |

---

## Usage Example

```python
from shl import get_config_value, ConfigManager

# Access configuration values
ttl = get_config_value("cache_ttl", default=3600)

# Use the policy manager
manager = ConfigManager()
```

---

## Dependencies

- `.config` — Internal configuration module.
- `.policy_manager` — Internal policy management module.
