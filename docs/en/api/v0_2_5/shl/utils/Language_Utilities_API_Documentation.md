# Language Utilities — API Documentation

## Module Overview

**File:** `lang_utils.py`

Shared BCP-47 language tag parsing and normalization utilities for the Self-Healing Localization Layer (SHL). Provides a single source of truth for region/script subtag handling, language code validation, and tag normalization. Uses only the Python standard library.

---

## Metadata

| Attribute | Value |
|-----------|-------|
| Description | Shared BCP-47 language tag parsing and normalization for SHL. |

---

## Dependencies

| Module | Usage |
|--------|-------|
| `logging` | Warning log output for unparseable language codes. |
| `re` | BCP-47 tag parsing via compiled regular expression. |
| `typing.Any`, `typing.Dict`, `typing.Optional`, `typing.Tuple` | Type annotations. |

---

## Module Constants

| Name | Type | Value | Description |
|------|------|-------|-------------|
| `_BCP47_RE` | `re.Pattern` | `re.compile(r"^([a-z]{2,3})(?:-([a-z]{4}))?(?:-([a-z]{2}|\d{3}))?$")` | Compiled regex for parsing BCP-47 language tags. Captures language (2–3 letters), optional script (4 letters), and optional region (2 letters or 3 digits). |

**Regex Breakdown**

| Group | Pattern | Matches |
|-------|---------|---------|
| 1 | `[a-z]{2,3}` | Language subtag (e.g., `fi`, `zh`, `eng`). |
| 2 | `[a-z]{4}` | Script subtag (e.g., `Hant`, `Latn`). |
| 3 | `[a-z]{2}` or `\d{3}` | Region subtag (e.g., `FI`, `TW`, `419`). |

---

## Functions

### `parse_bcp47()`

```python
def parse_bcp47(
    lang_code: str,
) -> Tuple[
    Optional[str],
    Optional[str],
    Optional[str],
]
```

Parses a language code into its BCP-47 components: language, script, and region.

| Parameter | Type | Description |
|-----------|------|-------------|
| `lang_code` | `str` | Raw language code string. |

**Returns**
- `Tuple[Optional[str], Optional[str], Optional[str]]` — `(language, script, region)`. Missing components are `None`.

**Input Normalization**
1. Strips whitespace.
2. Lowercases.
3. Replaces underscores with hyphens.
4. Removes encoding suffixes (e.g., `.UTF-8`).

**Examples**
```python
>>> parse_bcp47("fi-FI")
('fi', None, 'fi')

>>> parse_bcp47("zh-Hant-TW")
('zh', 'hant', 'tw')

>>> parse_bcp47("en")
('en', None, None)

>>> parse_bcp47("zh_TW")
('zh', None, 'tw')  # underscore normalized to hyphen

>>> parse_bcp47("fi_FI.UTF-8")
('fi', None, 'fi')  # encoding suffix stripped

>>> parse_bcp47("invalid")
(None, None, None)

>>> parse_bcp47("")
(None, None, None)
```

---

### `normalize_full_tag()`

```python
def normalize_full_tag(
    lang_code: str,
    default: str = "en",
) -> str
```

Normalizes a language tag to canonical lowercase hyphen-separated form suitable for file names and GLFM lookups.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lang_code` | `str` | — | Language code to normalize. |
| `default` | `str` | `"en"` | Fallback language if the code is unparseable. |

**Returns**
- `str` — Normalized tag (e.g., `"zh-hant-tw"`, `"fi"`), or `default.lower()` on failure.

**Behavior**
- Parses the tag via `parse_bcp47()`.
- Reconstructs with hyphens in lowercase.
- Logs a warning if the code is unparseable.

**Examples**
```python
>>> normalize_full_tag("zh-TW")
'zh-tw'

>>> normalize_full_tag("zh-Hant-TW")
'zh-hant-tw'

>>> normalize_full_tag("es-419")
'es-419'

>>> normalize_full_tag("FI")
'fi'

>>> normalize_full_tag("invalid")
'en'  # falls back to default, logs warning
```

---

### `base_language()`

```python
def base_language(
    lang_code: str,
    default: str = "en",
) -> str
```

Extracts only the base language subtag, stripping script and region.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lang_code` | `str` | — | Language code to process. |
| `default` | `str` | `"en"` | Fallback if the code is unparseable. |

**Returns**
- `str` — Base language code (e.g., `"zh"`, `"fi"`), or `default`.

**Examples**
```python
>>> base_language("zh-Hant-TW")
'zh'

>>> base_language("fi-FI")
'fi'

>>> base_language("en-US")
'en'

>>> base_language("invalid")
'en'
```

---

### `has_region()`

```python
def has_region(
    lang_code: str,
) -> bool
```

Checks whether a language code contains a region subtag.

| Parameter | Type | Description |
|-----------|------|-------------|
| `lang_code` | `str` | Language code to check. |

**Returns**
- `bool` — `True` if a region subtag is present, `False` otherwise.

**Examples**
```python
>>> has_region("fi-FI")
True

>>> has_region("zh-Hant-TW")
True

>>> has_region("en")
False

>>> has_region("zh-Hant")
False
```

---

### `get_parent()`

```python
def get_parent(
    lang_code: str,
    default: str = "en",
) -> str
```

Returns the parent tag with the region subtag removed. If a script is present, it is retained.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lang_code` | `str` | — | Language code to process. |
| `default` | `str` | `"en"` | Fallback if the code is unparseable. |

**Returns**
- `str` — Parent tag without region (e.g., `"zh-hant"`, `"fi"`), or `default`.

**Examples**
```python
>>> get_parent("zh-Hant-TW")
'zh-hant'

>>> get_parent("fi-FI")
'fi'

>>> get_parent("en")
'en'

>>> get_parent("invalid")
'en'
```

---

### `split_tag()`

```python
def split_tag(
    lang_code: str,
) -> Dict[str, Any]
```

Returns a structured dictionary representing the parsed language tag.

| Parameter | Type | Description |
|-----------|------|-------------|
| `lang_code` | `str` | Language code to process. |

**Returns**
- `Dict[str, Any]` — Dictionary with exactly these keys:

| Key | Type | Description |
|-----|------|-------------|
| `language` | `Optional[str]` | Base language subtag. |
| `script` | `Optional[str]` | Script subtag. |
| `region` | `Optional[str]` | Region subtag. |
| `tag` | `Optional[str]` | Full normalized tag, or `None` if unparseable. |

**Examples**
```python
>>> split_tag("fi-FI")
{
    'language': 'fi',
    'script': None,
    'region': 'fi',
    'tag': 'fi-fi',
}

>>> split_tag("zh-Hant-TW")
{
    'language': 'zh',
    'script': 'hant',
    'region': 'tw',
    'tag': 'zh-hant-tw',
}

>>> split_tag("invalid")
{
    'language': None,
    'script': None,
    'region': None,
    'tag': None,
}
```

---

### `is_valid()`

```python
def is_valid(
    lang_code: str,
) -> bool
```

Checks whether a language code is valid according to BCP-47 structure.

| Parameter | Type | Description |
|-----------|------|-------------|
| `lang_code` | `str` | Language code to validate. |

**Returns**
- `bool` — `True` if the code contains a parseable language subtag, `False` otherwise.

**Examples**
```python
>>> is_valid("fi-FI")
True

>>> is_valid("zh-Hant-TW")
True

>>> is_valid("invalid")
False

>>> is_valid("")
False

>>> is_valid(None)  # type: ignore
False
```

---

### `normalize_language()`

```python
def normalize_language(
    lang_code: str,
    default: str = "en",
) -> str
```

Alias for `normalize_full_tag()`. Provided for API consistency with external conventions.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lang_code` | `str` | — | Language code to normalize. |
| `default` | `str` | `"en"` | Fallback if unparseable. |

**Returns**
- `str` — Normalized tag, same as `normalize_full_tag()`.

**Example**
```python
>>> normalize_language("zh_TW")
'zh-tw'
```

---

## Complete Usage Example

```python
from shl.utils.lang_utils import (
    parse_bcp47,
    normalize_full_tag,
    base_language,
    has_region,
    get_parent,
    split_tag,
    is_valid,
    normalize_language,
)

# Process a complex BCP-47 tag
tag = "zh-Hant-TW"

print(parse_bcp47(tag))
# ('zh', 'hant', 'tw')

print(normalize_full_tag(tag))
# 'zh-hant-tw'

print(base_language(tag))
# 'zh'

print(has_region(tag))
# True

print(get_parent(tag))
# 'zh-hant'

print(split_tag(tag))
# {'language': 'zh', 'script': 'hant', 'region': 'tw', 'tag': 'zh-hant-tw'}

print(is_valid(tag))
# True

# Validate user input
user_input = "fi_FI.UTF-8"
if is_valid(user_input):
    normalized = normalize_language(user_input)
    print(f"Valid: {normalized}")  # Valid: fi-fi
else:
    print("Invalid language code")
```

---

## Supported Tag Formats

| Input | `parse_bcp47` | `normalize_full_tag` | `base_language` |
|-------|---------------|----------------------|-----------------|
| `fi` | `('fi', None, None)` | `'fi'` | `'fi'` |
| `fi-FI` | `('fi', None, 'fi')` | `'fi-fi'` | `'fi'` |
| `fi_FI` | `('fi', None, 'fi')` | `'fi-fi'` | `'fi'` |
| `zh-Hant-TW` | `('zh', 'hant', 'tw')` | `'zh-hant-tw'` | `'zh'` |
| `zh_TW` | `('zh', None, 'tw')` | `'zh-tw'` | `'zh'` |
| `EN-US` | `('en', None, 'us')` | `'en-us'` | `'en'` |
| `sr-Latn-RS` | `('sr', 'latn', 'rs')` | `'sr-latn-rs'` | `'sr'` |
| `es-419` | `('es', None, '419')` | `'es-419'` | `'es'` |
| `fi_FI.UTF-8` | `('fi', None, 'fi')` | `'fi-fi'` | `'fi'` |
| `invalid` | `(None, None, None)` | `'en'` (default) | `'en'` (default) |
| `''` | `(None, None, None)` | `'en'` (default) | `'en'` (default) |

---

## Thread Safety

All functions in this module are **pure functions** (no shared mutable state). They are fully thread-safe and safe for concurrent use without locking.

---

## Logging

The module uses Python's standard `logging` module under the logger name `__name__`.

**Log Levels Used**

| Level | Event |
|-------|-------|
| `WARNING` | `normalize_full_tag()` encounters an unparseable language code and falls back to default. |

---

## Changelog

| Version | Notes |
|---------|-------|
| Current | BCP-47 parsing with language/script/region extraction, tag normalization, parent resolution, and structured splitting. Zero external dependencies. |
