# SHL Errors Package API Documentation

## Overview

`shl/engine/errors/__init__.py` is the entry point for the SHL translation services error handling package. It provides the public interface for normalized error models, provider-independent error parsing, common SHL error codes, and provider-specific error definitions.

---

## Module Metadata

| Field | Value |
|-------|-------|
| **File** | `shl/engine/errors/__init__.py` |
| **Author** | Tuomas Lähteenmäki |
| **Version** | `0.2.10` |
| **License** | MIT |
| **Description** | Error handling package for SHL translation services. |

---

## Dependencies and Imports

### Internal Modules

- `.models.NormalizedError` — Normalized error model class.
- `.parser.ErrorParser` — Provider-independent error parser class.

---

## Exports

The following names are imported and made available at the package level:

| Name | Source Module | Description |
|------|---------------|-------------|
| `NormalizedError` | `.models` | Normalized error model. |
| `ErrorParser` | `.parser` | Provider-independent error parser. |

---

## `__all__`

```python
__all__ = [
    "ErrorParser",
    "NormalizedError",
]
```

Explicitly defines the public API of the package. Only `ErrorParser` and `NormalizedError` are exported when `from shl.engine.errors import *` is used.

---

## Usage Example

```python
from shl.engine.errors import NormalizedError, ErrorParser

# Use the normalized error model
error = NormalizedError(...)

# Use the error parser
parser = ErrorParser(...)
```

---

## Version

**Module version:** `0.2.10`

**Author:** Tuomas Lähteenmäki

**License:** MIT
