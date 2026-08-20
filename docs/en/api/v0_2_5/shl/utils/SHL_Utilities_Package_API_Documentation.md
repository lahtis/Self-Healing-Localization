# SHL Utilities Package — API Documentation

## Module Overview

**File:** `shl/utils/__init__.py`

Package-level initialization for the `shl.utils` subpackage. Re-exports language utility functions and environment loader utilities, providing a single import point for all SHL helper functions.

---

## Public API

### Language Utilities

Imported from `shl.utils.lang_utils`:

| Export | Description |
|--------|-------------|
| `parse_bcp47` | Parse a BCP-47 language tag into language, script, and region components. |
| `normalize_full_tag` | Normalize a language tag to canonical BCP-47 form. |
| `base_language` | Extract the base language code from a BCP-47 tag (strips script and region). |
| `has_region` | Check whether a language tag contains a region subtag. |
| `get_parent` | Get the parent language of a given tag (e.g., `zh-TW` → `zh`). |
| `split_tag` | Split a language tag into its structural parts (language, script, region, variants). |
| `is_valid` | Validate whether a string is a well-formed language code. |
| `normalize_language` | Normalize a language code to a standard form (lowercase, replace underscores with hyphens). |

### Environment Loader

Imported from `shl.utils.env_loader`:

| Export | Description |
|--------|-------------|
| `load_shl_env` | Load the SHL `.env` file from `./.env/shl/.env` with fallback to `./.env`. |
| `get_env_value` | Retrieve an environment variable, auto-loading `.env` if needed. |
| `get_env_value_masked` | Retrieve an environment variable and return it in masked form for safe logging. |
| `mask_api_key` | Mask an API key for secure log output. |

---

## `__all__` Export List

```python
__all__ = [
    # Language utilities
    "parse_bcp47",
    "normalize_full_tag",
    "base_language",
    "has_region",
    "get_parent",
    "split_tag",
    "is_valid",
    "normalize_language",
    # Environment loader
    "load_shl_env",
    "get_env_value",
    "get_env_value_masked",
    "mask_api_key",
]
```

---

## Usage Examples

### Language Utilities

```python
from shl.utils import (
    parse_bcp47,
    normalize_full_tag,
    base_language,
    has_region,
    get_parent,
    split_tag,
    is_valid,
    normalize_language,
)

# Parse BCP-47 tag
lang, script, region = parse_bcp47("zh-Hant-TW")
# lang="zh", script="Hant", region="TW"

# Normalize to canonical form
tag = normalize_full_tag("zh-tw")
# "zh-TW"

# Extract base language
base = base_language("zh-Hant-TW")
# "zh"

# Check for region
has_region("en-US")   # True
has_region("fi")      # False

# Get parent language
get_parent("zh-TW")   # "zh"
get_parent("en")      # "en"

# Split into parts
parts = split_tag("zh-Hant-TW")
# {"language": "zh", "script": "Hant", "region": "TW"}

# Validate language code
is_valid("fi")        # True
is_valid("invalid")   # False

# Normalize code
normalize_language("zh_CN")  # "zh-cn"
```

### Environment Loader

```python
from shl.utils import (
    load_shl_env,
    get_env_value,
    get_env_value_masked,
    mask_api_key,
)

# Load environment (idempotent)
load_shl_env()

# Read API key
api_key = get_env_value("DEEPL_API_KEY")

# Safe logging
masked = get_env_value_masked("MICROSOFT_TRANSLATOR_KEY")
print(f"Using key: {masked}")
# Using key: abcd****************wxyz

# Direct masking
print(mask_api_key("my-secret-key-12345"))
# my-s*****************12345
```

---

## Import Map

| Public Name | Internal Source |
|-------------|-----------------|
| `parse_bcp47` | `shl.utils.lang_utils.parse_bcp47` |
| `normalize_full_tag` | `shl.utils.lang_utils.normalize_full_tag` |
| `base_language` | `shl.utils.lang_utils.base_language` |
| `has_region` | `shl.utils.lang_utils.has_region` |
| `get_parent` | `shl.utils.lang_utils.get_parent` |
| `split_tag` | `shl.utils.lang_utils.split_tag` |
| `is_valid` | `shl.utils.lang_utils.is_valid` |
| `normalize_language` | `shl.utils.lang_utils.normalize_language` |
| `load_shl_env` | `shl.utils.env_loader.load_shl_env` |
| `get_env_value` | `shl.utils.env_loader.get_env_value` |
| `get_env_value_masked` | `shl.utils.env_loader.get_env_value_masked` |
| `mask_api_key` | `shl.utils.env_loader.mask_api_key` |

---

## Changelog

| Version | Notes |
|---------|-------|
| Current | Exports language utilities and environment loader at the `shl.utils` package level. |
