# Language Validator — API Documentation

## Module Overview

**File:** `language_validator.py`

Optional language validation and fallback resolution using the GLFM (Global Language Family Mapper) database. Provides language code validation, BCP-47 tag normalization, fallback chain generation, and language metadata queries. Supports two operational modes: GLFM Lite (~428 KB, all 7,900+ languages and 20 nearest languages) and Full GLFM (~51.6 MB, all 7,900+ languages and 7,900+ nearest languages).

---

## Metadata

| Attribute | Value |
|-----------|-------|
| Author | Tuomas Lähteenmäki |
| Version | 0.2.4 |
| License | MIT |

---

## Dependencies

| Module | Usage |
|--------|-------|
| `logging` | Info, warning, and debug log output. |
| `os` | Environment variable access (reserved for future use). |
| `pathlib.Path` | Cross-platform database file path resolution. |
| `typing.Optional`, `typing.Dict`, `typing.Any`, `typing.List` | Type annotations. |
| `shl.utils.lang_utils.base_language` | Extracts base language from a BCP-47 tag. |
| `shl.utils.lang_utils.normalize_full_tag` | Normalizes a language tag to canonical BCP-47 form. |
| `shl.utils.lang_utils.parse_bcp47` | Parses BCP-47 tags into components. |
| `shl.utils.lang_utils.split_tag` | Splits a language tag into structural parts. |
| `shl.utils.glfm_load_database.load_language_data` | Loads gzipped JSON GLFM database files. |

---

## GLFM Database Modes

| Mode | File | Size | Fallback Depth | Use Case |
|------|------|------|----------------|----------|
| **Lite** (default) | `languages_top20.json.gz` | ~428 KB | 20 nearest languages | Desktop/UI apps, memory-constrained environments. |
| **Full** | `unified_languages.json.gz` | ~51.6 MB | All 7,900+ languages | Servers, comprehensive language support. |

The mode is selected at initialization via the `use_lite` parameter. If the Full database is not found, the validator automatically falls back to Lite mode.

---

## Class: `LanguageValidator`

```python
class LanguageValidator
```

Validates language codes against the GLFM database and provides fallback chain resolution. All lookups are case-insensitive and support ISO 639-1, ISO 639-3, and BCP-47 tags.

### Constructor

```python
def __init__(
    self,
    glfm_path: Optional[str] = None,
    base_language: str = "en",
    use_lite: bool = True,
) -> None
```

Initializes the validator and attempts to load the GLFM database.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `glfm_path` | `Optional[str]` | `None` | Custom path to a GLFM database file. If `None`, uses the default path based on `use_lite`. |
| `base_language` | `str` | `"en"` | Default fallback language for the developer's base locale. |
| `use_lite` | `bool` | `True` | Use GLFM Lite mode. `False` attempts to load the Full database. |

**Database Resolution Order**
1. If `glfm_path` is provided → use that file (Lite or Full).
2. If `use_lite=True` → load `data/languages_top20.json.gz` (relative to this module).
3. If `use_lite=False` → load `data/unified_languages.json.gz` (relative to this module).
4. If Full is not found → log warning and fall back to Lite.
5. If Lite is not found → log debug and disable validation (`_loaded=False`).

**Attributes**

| Attribute | Type | Description |
|-----------|------|-------------|
| `base_language` | `str` | The configured base fallback language. |
| `languages` | `Dict[str, Any]` | Loaded GLFM language data. Empty if loading failed. |
| `_loaded` | `bool` | Whether the database was successfully loaded. |
| `_use_lite` | `bool` | Current mode (may differ from constructor arg if fallback occurred). |
| `_max_nearest` | `Optional[int]` | Maximum nearest languages in fallback chain. `20` for Lite, `None` (unlimited) for Full. |
| `_iso1_index` | `Dict[str, str]` | O(1) lookup index: ISO 639-1 code → GLFM language ID. |

---

### Properties

#### `is_loaded`
```python
@property
def is_loaded(self) -> bool
```
Returns `True` if the GLFM database is loaded and contains at least one language entry.

---

#### `is_lite`
```python
@property
def is_lite(self) -> bool
```
Returns `True` if the validator is operating in GLFM Lite mode.

---

#### `max_nearest`
```python
@property
def max_nearest(self) -> Optional[int]
```
Returns the maximum number of nearest languages included in fallback chains. `20` for Lite, `None` for Full (unlimited).

---

### Internal Methods

#### `_load_glfm()`

```python
def _load_glfm(self) -> None
```

Loads the GLFM database from a gzipped JSON file. Called automatically by the constructor.

**Behavior**
- Resolves the database file path.
- Calls `load_language_data()` to parse the gzipped JSON.
- Builds the ISO 639-1 O(1) lookup index via `_build_iso1_index()`.
- Handles `FileNotFoundError` with automatic Lite fallback.
- Catches all other exceptions and disables validation gracefully.

**Logging**
- `INFO` — Database loaded successfully with language count, mode, and nearest limit.
- `WARNING` — Full database not found, falling back to Lite.
- `DEBUG` — Lite database not found, validation disabled.
- `WARNING` — Unexpected loading failure.

---

#### `_build_iso1_index()`

```python
def _build_iso1_index(self) -> None
```

Builds an O(1) lookup index mapping ISO 639-1 codes to GLFM language IDs.

**Behavior**
- Iterates over all loaded languages.
- Maps `info['iso639_1'].lower()` → `lang_id`.
- Skips duplicates (first occurrence wins).

**Logging**
- `DEBUG` — Index entry count.

---

#### `_find_language()`

```python
def _find_language(self, lang_code: str) -> Optional[Dict[str, Any]]
```

Finds a language entry in the GLFM database using multiple lookup strategies.

**Lookup Order:**
1. **O(1) ISO 639-1 index** — Fast path for 2-letter codes.
2. **Direct ID lookup** — Exact match against GLFM language IDs.
3. **Full normalized tag** — Canonical BCP-47 form.
4. **Linear ISO 639-3 search** — Fallback for 3-letter codes (rare, but safe).

| Parameter | Type | Description |
|-----------|------|-------------|
| `lang_code` | `str` | Language code to look up. |

**Returns**
- `Optional[Dict[str, Any]]` — The GLFM language entry dictionary, or `None` if not found.

---

### Public Methods

#### `is_valid()`

```python
def is_valid(self, lang_code: str, strict: bool = False) -> bool
```

Checks whether a language code exists in the GLFM database.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lang_code` | `str` | — | Language code to validate. |
| `strict` | `bool` | `False` | If `True`, returns `False` when GLFM is not loaded. If `False`, passes through (assumes valid). |

**Returns**
- `bool` — Validation result.

**Behavior Matrix**

| Condition | `strict=True` | `strict=False` |
|-----------|---------------|----------------|
| Empty/invalid input | `False` | `False` |
| GLFM not loaded | `False` | `True` (pass-through) |
| Found in GLFM | `True` | `True` |
| Not found in GLFM | `False` | `False` |

**Example**
```python
validator = LanguageValidator()

# With loaded database
validator.is_valid("fi")      # True
validator.is_valid("invalid") # False

# Without loaded database (pass-through)
validator.is_valid("fi")              # True
validator.is_valid("fi", strict=True) # False
```

---

#### `get_bcp47()`

```python
def get_bcp47(self, lang_code: str) -> Optional[str]
```

Returns the canonical BCP-47 tag for a language code.

| Parameter | Type | Description |
|-----------|------|-------------|
| `lang_code` | `str` | Language code to resolve. |

**Returns**
- `Optional[str]` — BCP-47 tag from GLFM if available, otherwise the normalized full tag, or `None` for invalid input.

**Example**
```python
validator.get_bcp47("zh-tw")  # "zh-TW"
validator.get_bcp47("fi")     # "fi"
```

---

#### `get_fallback()`

```python
def get_fallback(self, lang_code: str) -> Optional[str]
```

Returns the GLFM-defined fallback language for a given code.

| Parameter | Type | Description |
|-----------|------|-------------|
| `lang_code` | `str` | Language code to look up. |

**Returns**
- `Optional[str]` — The fallback language code (ISO 639-1 if resolvable), or `None` if no fallback is defined or the language is not found.

**Resolution Logic**
1. If the fallback is already a 2-letter ISO 639-1 code → return directly.
2. If the fallback is a GLFM language ID → resolve to its ISO 639-1 code.
3. Otherwise → return the raw fallback value.

**Example**
```python
validator.get_fallback("zh-TW")  # "zh" (or similar, depending on GLFM data)
```

---

#### `get_language_info()`

```python
def get_language_info(self, lang_code: str) -> Optional[Dict[str, Any]]
```

Returns the complete GLFM language entry for a code.

| Parameter | Type | Description |
|-----------|------|-------------|
| `lang_code` | `str` | Language code to look up. |

**Returns**
- `Optional[Dict[str, Any]]` — Full language dictionary from GLFM, or `None`.

**Typical Entry Structure**
```python
{
    "name": "Finnish",
    "iso639_1": "fi",
    "iso639_3": "fin",
    "bcp47": "fi",
    "fallback": "",
    "family": "Uralic",
    "nearest_languages": [{"lang": "et", "distance": 0.8}, ...],
    "written_scripts": ["Latn"],
    "default_script": "Latn",
    "iso639_5": "urj"
}
```

---

#### `get_name()`

```python
def get_name(self, lang_code: str) -> Optional[str]
```

Returns the human-readable name of a language.

| Parameter | Type | Description |
|-----------|------|-------------|
| `lang_code` | `str` | Language code to look up. |

**Returns**
- `Optional[str]` — Language name from GLFM, or a generic placeholder if GLFM is not loaded, or `None`.

**Fallback Behavior**
- If GLFM is loaded but language not found → `None`.
- If GLFM is not loaded → returns `"Language: {base_language}"` if parseable.

---

#### `get_region()`

```python
def get_region(self, lang_code: str) -> Optional[str]
```

Extracts the region component from a BCP-47 language tag.

| Parameter | Type | Description |
|-----------|------|-------------|
| `lang_code` | `str` | BCP-47 tag to parse. |

**Returns**
- `Optional[str]` — Region code (e.g., `"TW"` for `"zh-TW"`), or `None`.

**Note:** This is a convenience wrapper around `parse_bcp47()`. For detailed region metadata, use `get_language_info()`.

**Example**
```python
validator.get_region("zh-TW")  # "TW"
validator.get_region("en-US")  # "US"
validator.get_region("fi")     # None
```

---

#### `get_written_scripts()`

```python
def get_written_scripts(self, lang_code: str) -> Optional[List[str]]
```

Returns the list of scripts used to write a language.

| Parameter | Type | Description |
|-----------|------|-------------|
| `lang_code` | `str` | Language code to look up. |

**Returns**
- `Optional[List[str]]` — List of ISO 15924 script codes (e.g., `["Latn", "Cyrl"]`), or `None`.

---

#### `get_default_script()`

```python
def get_default_script(self, lang_code: str) -> Optional[str]
```

Returns the default script for a language.

| Parameter | Type | Description |
|-----------|------|-------------|
| `lang_code` | `str` | Language code to look up. |

**Returns**
- `Optional[str]` — Default ISO 15924 script code (e.g., `"Latn"`), or `None`.

---

#### `get_family()`

```python
def get_family(self, lang_code: str) -> Optional[str]
```

Returns the language family classification.

| Parameter | Type | Description |
|-----------|------|-------------|
| `lang_code` | `str` | Language code to look up. |

**Returns**
- `Optional[str]` — Language family name (e.g., `"Uralic"`, `"Indo-European"`), or `None`.

---

#### `get_fallback_chain()`

```python
def get_fallback_chain(
    self,
    lang_code: str,
    base_language: Optional[str] = None,
    max_nearest: Optional[int] = None,
) -> List[str]
```

Generates a complete fallback chain for a language, ordered from most specific to most general.

**Fallback Chain Order:**
1. Full normalized tag (e.g., `"zh-TW"`)
2. Base language (e.g., `"zh"`)
3. GLFM-defined fallback (if any)
4. Nearest languages (up to `max_nearest`)
5. ISO 639-5 family code (if available)
6. Developer's `base_language`
7. English (`"en"`) — absolute last resort

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lang_code` | `str` | — | Language to build the fallback chain for. |
| `base_language` | `Optional[str]` | `None` | Overrides `self.base_language` for this call. |
| `max_nearest` | `Optional[int]` | `None` | Overrides the default nearest limit. `None` = use mode default. |

**Returns**
- `List[str]` — Ordered list of unique language codes. Never empty (always includes at least `base_language` or `"en"`).

**Example**
```python
validator = LanguageValidator(use_lite=True)
chain = validator.get_fallback_chain("zh-TW", base_language="fi")
# ["zh-TW", "zh", "zh-CN", "zh-Hans", ..., "fi", "en"]
```

---

#### `get_best_available_fallback()`

```python
def get_best_available_fallback(
    self,
    lang_code: str,
    available_languages: List[str],
    base_language: Optional[str] = None,
) -> Optional[str]
```

Finds the best matching fallback language from a list of supported languages.

| Parameter | Type | Description |
|-----------|------|-------------|
| `lang_code` | `str` | Current language code. |
| `available_languages` | `List[str]` | List of languages supported by the application or provider. |
| `base_language` | `Optional[str]` | Overrides `self.base_language` for this call. |

**Returns**
- `Optional[str]` — The first language in the fallback chain that exists in `available_languages`, or the first available language as a last resort, or `None` if `available_languages` is empty.

**Example**
```python
available = ["en", "fi", "sv", "de"]
best = validator.get_best_available_fallback("zh-TW", available)
# "en" (since Chinese variants are not in available, English is the last resort)
```

---

## Usage Example

```python
from shl.language_validator import LanguageValidator

# Initialize with GLFM Lite (default)
validator = LanguageValidator(
    base_language="fi",
    use_lite=True,
)

# Check if a language is valid
if validator.is_valid("ja"):
    print("Japanese is supported")

# Get language metadata
name = validator.get_name("fi")           # "Finnish"
scripts = validator.get_written_scripts("ja")  # ["Jpan", "Latn"]
family = validator.get_family("fi")       # "Uralic"

# Build fallback chain
chain = validator.get_fallback_chain("zh-TW")
print(chain)
# ["zh-TW", "zh", "zh-CN", "zh-Hans", "zh-Hant", ..., "fi", "en"]

# Find best available fallback
available = ["en", "fi", "de"]
best = validator.get_best_available_fallback("zh-TW", available)
print(best)  # "en"

# BCP-47 normalization
bcp47 = validator.get_bcp47("zh-tw")
print(bcp47)  # "zh-TW"
```

---

## Performance Characteristics

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| `_find_language` (ISO 639-1) | O(1) | Fast path via `_iso1_index`. |
| `_find_language` (ISO 639-3) | O(n) | Linear search, rare fallback. |
| `is_valid` | O(1)–O(n) | Depends on lookup path. |
| `get_fallback_chain` | O(k) | Where k = nearest languages limit (20 for Lite). |
| Database load | One-time | ~428 KB (Lite) or ~51.6 MB (Full) at initialization. |

---

## Thread Safety

`LanguageValidator` is **read-only after initialization**. The database is loaded once in `__init__` and never mutated thereafter. Multiple threads can safely call any public method concurrently without locking.

**Note:** If multiple instances are created simultaneously, each loads its own copy of the database. For memory efficiency in multi-threaded environments, consider sharing a single instance.

---

## Logging

The module uses Python's standard `logging` module under the logger name `__name__`.

**Log Levels Used**

| Level | Event |
|-------|-------|
| `INFO` | GLFM database loaded successfully (language count, mode). |
| `WARNING` | Full GLFM not found (Lite fallback), or unexpected loading failure. |
| `DEBUG` | Lite GLFM not found (validation disabled), ISO index built. |

---

## Changelog

| Version | Notes |
|---------|-------|
| 0.2.4 | Current — GLFM Lite/Full modes, O(1) ISO 639-1 index, BCP-47 support, fallback chains, and language metadata queries. |
