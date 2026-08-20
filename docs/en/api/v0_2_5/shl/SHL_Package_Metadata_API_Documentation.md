# SHL Package Metadata — API Documentation

## Module Overview

**File:** `_version.py` (or package metadata module)

Defines the canonical metadata constants for the Self-Healing Localization Layer (SHL) Python package. These values are used across the codebase for versioning, attribution, and license identification.

---

## Metadata Constants

| Constant | Type | Value | Description |
|----------|------|-------|-------------|
| `__version__` | `str` | `"0.2.5"` | Current version of the SHL package. Follows semantic versioning. |
| `__author__` | `str` | `"Tuomas Lähteenmäki"` | Author and maintainer of the package. |
| `__license__` | `str` | `"MIT"` | Software license under which SHL is distributed. |

---

## Usage

These constants are typically imported by other SHL modules for inclusion in HTTP headers, log messages, and user-agent strings.

```python
from shl._version import __version__

print(f"SHL version: {__version__}")
# SHL version: 0.2.5
```

### Common Consumers

| Module | Usage |
|--------|-------|
| `shl.providers.microsoft_translator` | `User-Agent: SHL-Client/{__version__}` |
| `shl.providers.papago` | `User-Agent: SHL-Client/{__version__}` |
| `shl.providers.libretranslate` | `User-Agent: SHL-Client/{__version__}` |
| `shl.providers.mymemory` | `User-Agent: SHL-Client/{__version__}` |

---

## Versioning Policy

SHL uses a simple three-part version scheme:

```
MAJOR.MINOR.PATCH
```

| Segment | Meaning |
|---------|---------|
| `MAJOR` | Breaking changes to public API. |
| `MINOR` | New features, providers, or capabilities. Backward compatible. |
| `PATCH` | Bug fixes, documentation updates, or minor internal improvements. |

**Current:** `0.2.5` — pre-1.0 development phase. Minor increments indicate significant new provider adapters or routing features; patch increments indicate fixes and refinements.

---

## Changelog

| Version | Notes |
|---------|-------|
| 0.2.5 | Current — package metadata for SHL translation ecosystem. |
