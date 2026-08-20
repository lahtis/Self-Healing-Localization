# Prompt Template Localizer — API Documentation

## Module Overview

**File:** `template_localizer.py`

Self-Healing Localizer for AI prompt templates. Manages per-language JSON files for storing and retrieving localized prompt templates. Supports automatic language detection (with `config.conf` override), corrupted file backup, legacy file migration, in-memory caching of loaded languages, Python string formatting, and a full dictionary-like interface.

---

## Metadata

| Attribute | Value |
|-----------|-------|
| Author | Tuomas Lähteenmäki |
| Version | 0.2.0 |
| License | MIT |
| Description | Self-Healing Localizer for AI prompt templates. Creates missing files automatically, copies base language as fallback, adds missing keys on the fly, validates keys, handles corruption gracefully, uses atomic saves, supports dirty flag for batch saves, and caches loaded languages. |

---

## Dependencies

| Module | Usage |
|--------|-------|
| `atexit` | Automatic save on program exit. |
| `json` | JSON file serialization and deserialization. |
| `logging` | Debug, warning, and error log output. |
| `os` | File/directory operations and environment variable access. |
| `shutil` | Corrupted file backup via `copy2`. |
| `datetime` | Timestamp generation for backup file names. |
| `typing.Any`, `typing.Dict`, `typing.Optional` | Type annotations. |
| `shl.utils.lang_utils.base_language` | Extract base language from a tag. |
| `shl.utils.lang_utils.normalize_full_tag` | Normalize language codes to canonical form. |

---

## Class: `TemplateLocalizer`

```python
class TemplateLocalizer
```

Manages AI prompt template translations stored as JSON files in a per-language structure. Each language has its own `{lang_code}.json` file. Supports key-based lookups, lazy creation, fallback to base language, automatic persistence, and template formatting with Python's `.format()`.

---

### Constructor

```python
def __init__(
    self,
    lang_code: Optional[str] = None,
    base_lang: str = "en",
    folder: str = "prompts",
) -> None
```

Initializes the template localizer, detects the active language, ensures the storage directory exists, and loads or creates the language file.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lang_code` | `Optional[str]` | `None` | Target language code. Auto-detected if omitted (see `_detect_language()`). |
| `base_lang` | `str` | `"en"` | Base/source language for fallback lookups. |
| `folder` | `str` | `"prompts"` | Directory for storing JSON template files. |

**Initialization Flow**
1. Detect language (if `lang_code` is `None`) via `_detect_language()`.
2. Normalize `lang_code` and `base_lang` via `normalize_full_tag()`.
3. Ensure `folder` directory exists.
4. Resolve file paths: `{folder}/{lang_code}.json` and `{folder}/{base_lang}.json`.
5. Load or create the language file via `_load_or_create()`.
6. Register `atexit` handler for automatic dirty-data save.

**Attributes**

| Attribute | Type | Description |
|-----------|------|-------------|
| `folder` | `str` | Storage directory path. |
| `lang_code` | `str` | Active (normalized) language code. |
| `base_lang_tag` | `str` | Normalized base language tag (full form). |
| `base_lang` | `str` | Base language code (script/region stripped). |
| `lang_file` | `str` | Path to the active language JSON file. |
| `base_file` | `str` | Path to the base language JSON file. |
| `templates` | `Dict[str, Any]` | In-memory dictionary of the active language's templates. |
| `_loaded_langs` | `Dict[str, Dict[str, Any]]` | Cache of other languages loaded via `get_template()`. |
| `_dirty` | `bool` | Whether `templates` has unsaved changes. |
| `_alive` | `bool` | Whether the localizer is active (used by cleanup). |
| `_shutting_down` | `bool` | Whether an atexit save is in progress. |

---

### Language Detection

#### `_detect_language()`

```python
def _detect_language(self) -> Optional[str]
```

Detects the active language using a priority cascade. `SETTINGS.language` in `config.conf` takes absolute precedence.

**Detection Order**
1. **`config.conf` `[SETTINGS]` section** — `language` key. If present, returned immediately.
2. **`SHL_LANGUAGE` environment variable** — If set, returned.
3. **`LANG` environment variable** — Parsed: encoding suffix stripped (`fi_FI.UTF-8` → `fi_FI`), underscores converted to hyphens (`fi_FI` → `fi-FI`).
4. **`None`** — No language detected; caller falls back to `base_lang`.

**Returns**
- `Optional[str]` — Detected language code, or `None`.

---

### File Operations

#### `_load_json_safe()`

```python
def _load_json_safe(self, filepath: str) -> Optional[Dict[str, Any]]
```

Safely loads a JSON file with corruption detection and automatic backup.

**Returns**
- `Optional[Dict[str, Any]]` — Parsed dictionary, or `None` on failure.

**Error Handling**
- File not found → `None`.
- Root is not a `dict` → backs up file, returns `None`.
- `JSONDecodeError` / `UnicodeDecodeError` / `OSError` → logs error, backs up file, returns `None`.
- Any other exception → logs error, returns `None`.

---

#### `_backup_corrupted_file()`

```python
def _backup_corrupted_file(self, filepath: str) -> None
```

Creates a timestamped backup of a corrupted JSON file before it is discarded.

**Backup Naming**
```
{filepath}.{YYYYMMDD_HHMMSS}.bak
```

**Example**
```
prompts/fi.json → prompts/fi.json.20240820_143052.bak
```

---

#### `_save_templates()`

```python
def _save_templates(
    self,
    templates: Dict[str, Any],
    filepath: Optional[str] = None,
) -> bool
```

Atomically saves a dictionary to a JSON file using write-to-temp-then-replace.

**Atomic Save Process**
1. Write to `{filepath}.tmp`.
2. Flush and `fsync` the file handle.
3. `os.replace(tmp_path, filepath)` — atomic on most filesystems.
4. On failure, remove the temporary file.

**Returns**
- `bool` — `True` on success, `False` on failure.

---

#### `_save()` / `save()` / `_save_if_dirty()`

```python
def _save(self) -> bool
def save(self) -> bool
def _save_if_dirty(self) -> bool
```

Persists the active language's `templates` dictionary to disk.

| Method | Behavior |
|--------|----------|
| `_save()` | Unconditionally saves `self.templates` to `self.lang_file`. |
| `save()` | Calls `_save()` and clears `_dirty` flag on success. |
| `_save_if_dirty()` | Saves only if `_dirty` is `True`; clears flag on success. |

**Returns**
- `bool` — `True` if saved successfully, `False` otherwise.

---

#### `_atexit_save()`

```python
def _atexit_save(self) -> None
```

Registered with `atexit` to automatically save dirty data when the program exits.

**Behavior**
- Skips if `_alive` is `False` or `_dirty` is `False`.
- Sets `_shutting_down = True` during the save.
- Clears `_dirty` on success.

---

#### `close()`

```python
def close(self) -> bool
```

Explicitly closes the localizer, saving any pending changes.

**Returns**
- `bool` — `True` on successful close, `False` if save failed.

**Side Effects**
- Sets `_alive = False`.

---

### Migration and Creation

#### `_migrate_legacy_file()`

```python
def _migrate_legacy_file(
    self,
    legacy_path: str,
    new_path: str,
) -> Optional[Dict[str, Any]]
```

Migrates data from a legacy `lang_{code}.json` file to the new `{code}.json` format.

| Parameter | Type | Description |
|-----------|------|-------------|
| `legacy_path` | `str` | Path to the old `lang_xx.json` file. |
| `new_path` | `str` | Path to the new `{code}.json` file. |

**Returns**
- `Optional[Dict[str, Any]]` — Migrated data if successful, `None` otherwise.

**Note:** The legacy file is **not deleted** after migration. It remains in place.

---

#### `_load_or_create()`

```python
def _load_or_create(self) -> Dict[str, Any]
```

Loads the active language file, or creates it from fallback sources.

**Resolution Order**
1. Load `{lang_code}.json` if it exists.
2. If missing or corrupted → try migrating from `lang_{lang_code}.json` (legacy).
3. If no legacy file → copy `{base_lang}.json` if it exists.
4. If nothing found → create an empty dictionary and save it.

**Returns**
- `Dict[str, Any]` — Loaded or newly created template dictionary.

---

### Public API — Core Methods

#### `ensure_key()`

```python
def ensure_key(
    self,
    key: str,
    default_value: str = "",
) -> str
```

Primary method for retrieving a prompt template. Creates the key with `default_value` if it does not exist.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `key` | `str` | — | Template key. |
| `default_value` | `str` | `""` | Default template to set if the key is missing. |

**Returns**
- `str` — The template string, or `default_value` / empty string.

**Behavior**
1. Validates the key.
2. If key not in `templates`:
   - Sets `templates[key] = default_value`.
   - Marks dirty.
   - Invalidates cache.
   - **Saves to disk immediately.**
3. Returns the value.

**Note:** This method saves to disk on every key creation. For batch operations, consider using `set_template()` directly and calling `save()` once at the end.

**Example**
```python
from shl.engine.template_localizer import TemplateLocalizer

templates = TemplateLocalizer(lang_code="fi")

prompt = templates.ensure_key("summarize", "Summarize this: {text}")
# If "summarize" didn't exist, it is created with the default and saved.
```

---

#### `get()`

```python
def get(
    self,
    key: str,
    default_value: str = "",
) -> str
```

Alias for `ensure_key()`. Provided for dictionary-like API consistency.

---

#### `get_template()`

```python
def get_template(
    self,
    key: str,
    lang_code: Optional[str] = None,
    fallback: bool = True,
) -> Optional[str]
```

Retrieves a template from a specific language file, with optional fallback to the base language.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `key` | `str` | — | Template key. |
| `lang_code` | `Optional[str]` | `None` | Target language. Defaults to active language. |
| `fallback` | `bool` | `True` | Whether to fall back to base language if key is missing. |

**Returns**
- `Optional[str]` — The template string, or `None` if not found in target or base language.

**Behavior**
1. Validates key.
2. Normalizes target language code.
3. Attempts to load template from target language file.
4. If not found and `fallback=True` and target ≠ base → attempts base language file.
5. Returns `None` if all fallbacks exhausted.

**Performance Note:** When reading a language other than the active one, the file is read from disk and cached in `_loaded_langs`. However, the active language (`self.lang_code`) is served directly from `self.templates` without disk access.

**Important:** Unlike `_load_json_safe()`, `_get_template_from_lang()` does **not** back up corrupted JSON files. Corrupted files are silently treated as empty dictionaries.

---

#### `_get_template_from_lang()`

```python
def _get_template_from_lang(
    self,
    key: str,
    lang_code: str,
) -> Optional[str]
```

Internal method that loads a language file from disk and retrieves a specific template key.

**Returns**
- `Optional[str]` — The template value, or `None` if the file or key is missing.

**Caching**
- Loaded languages are stored in `_loaded_langs` to avoid repeated disk reads.
- If a file is missing, an empty dict is cached for that language.

---

#### `set_template()`

```python
def set_template(
    self,
    key: str,
    value: Optional[str],
) -> str
```

Sets a key's value in the active language and persists to disk.

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | `str` | Template key. |
| `value` | `Optional[str]` | Template string. `None` is stored as empty string `""`. |

**Returns**
- `str` — The stored value (empty string if `value` was `None`).

**Behavior**
1. Validates key.
2. Normalizes `None` to `""`.
3. Sets `templates[key] = value`.
4. Marks dirty and invalidates cache.
5. Saves to disk immediately.

**Example**
```python
templates.set_template("summarize", "Summarize in {language}: {text}")
templates.set_template("empty_key", None)  # Stored as ""
```

---

#### `set_language()`

```python
def set_language(self, lang_code: str) -> bool
```

Switches the active language, saving the current language first.

| Parameter | Type | Description |
|-----------|------|-------------|
| `lang_code` | `str` | New active language code. |

**Returns**
- `bool` — `True` on success, `False` if the current language could not be saved.

**Behavior**
1. Normalizes the new language code.
2. If same as current → returns `True` immediately.
3. Saves current language.
4. Updates `lang_code` and `lang_file`.
5. Loads or creates the new language file.
6. Clears cache and dirty flag.

**Note:** The old `templates` dictionary is replaced but not explicitly freed from memory. In long-running applications with frequent language switches, this may accumulate memory.

---

#### `format_template()`

```python
def format_template(
    self,
    key: str,
    **kwargs: Any,
) -> str
```

Retrieves a template and formats it using Python's `.format()` method.

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | `str` | Template key. |
| `**kwargs` | `Any` | Format arguments for the template string. |

**Returns**
- `str` — Formatted template string, or the raw template if formatting fails, or the key itself if the template is not found.

**Behavior**
1. Validates key.
2. Retrieves template via `get_template(key)`.
3. If template not found → returns the key string.
4. If `kwargs` is empty → returns the raw template.
5. Attempts `template.format(**kwargs)`.
6. On `KeyError` or `ValueError` → logs warning and returns the raw template.

**Example**
```python
templates = TemplateLocalizer(lang_code="fi")

# Store a template
templates.set_template(
    "summarize",
    "Summarize the following text in {language}:

{text}"
)

# Retrieve and format
result = templates.format_template(
    "summarize",
    language="Finnish",
    text="Long article here..."
)
# "Summarize the following text in Finnish:

Long article here..."

# Missing key returns the key itself
result = templates.format_template("nonexistent")
# "nonexistent"

# Formatting error returns raw template
templates.set_template("broken", "Hello {name}")
result = templates.format_template("broken", wrong_arg="value")
# "Hello {name}" (logged as warning)
```

---

### Public API — Introspection

#### `has_key()` / `__contains__()`

```python
def has_key(self, key: str) -> bool
def __contains__(self, key: str) -> bool
```

Checks whether a key exists in the active language.

**Returns**
- `bool` — `True` if the key exists and is non-empty after validation.

**Example**
```python
if "summarize" in templates:
    print("Template exists")
```

---

#### `keys()`

```python
def keys(self) -> List[str]
```

Returns all keys in the active language.

---

#### `values()`

```python
def values(self) -> List[str]
```

Returns all values in the active language. `None` values are returned as empty strings.

---

#### `items()`

```python
def items(self) -> List[Tuple[str, str]]
```

Returns all key-value pairs. `None` values are returned as empty strings.

---

#### `__len__()`

```python
def __len__(self) -> int
```

Returns the number of keys in the active language.

---

#### `__repr__()`

```python
def __repr__(self) -> str
```

Returns a string representation: `TemplateLocalizer(lang='fi', templates=42)`.

---

#### `__getitem__()` / `__setitem__()`

```python
def __getitem__(self, key: str) -> str
def __setitem__(self, key: str, value: Optional[str]) -> None
```

Dictionary-style access.

```python
templates["summarize"] = "Summarize: {text}"
print(templates["summarize"])  # "Summarize: {text}"
```

---

## Complete Usage Example

```python
from shl.engine.template_localizer import TemplateLocalizer

# Initialize for Finnish
templates = TemplateLocalizer(
    lang_code="fi",
    base_lang="en",
    folder="prompts",
)

# Primary lookup (creates key if missing)
prompt = templates.ensure_key(
    "summarize",
    "Summarize this: {text}"
)
print(prompt)

# Dictionary-style access
templates["code_review"] = "Review this code:

{code}"
print(templates["code_review"])

# Check existence
if "summarize" in templates:
    print(f"Summarize template: {templates['summarize']}")

# Get from another language with fallback
template = templates.get_template(
    "summarize",
    lang_code="sv",
    fallback=True
)

# Set explicitly
templates.set_template(
    "new_prompt",
    "Explain {topic} in simple terms."
)

# Format with arguments
result = templates.format_template(
    "new_prompt",
    topic="quantum computing"
)
# "Explain quantum computing in simple terms."

# Switch language
templates.set_language("sv")

# Introspection
print(f"Templates: {len(templates)}")
print(f"All keys: {templates.keys()}")

# Clean shutdown
templates.close()
```

---

## File Structure

```
prompts/
├── en.json          ← Base language
├── fi.json          ← Active language (Finnish)
├── sv.json          ← Swedish (loaded on demand)
└── lang_fi.json     ← Legacy file (migrated but not deleted)
```

---

## Thread Safety

| Component | Status | Notes |
|-----------|--------|-------|
| `templates` dictionary reads | Generally safe | CPython dict reads are atomic. |
| `templates` dictionary writes | Not safe | `ensure_key()`, `set_template()`, and `set_language()` mutate `templates`. Concurrent writes may race. |
| File I/O | Not safe | `_save_templates()` writes to disk without locking. Concurrent saves may corrupt the file. |
| `_loaded_langs` cache | Not safe | Mutated by `_get_template_from_lang()` without synchronization. |

**Recommendation:** Use one `TemplateLocalizer` instance per thread, or wrap mutating operations with a `threading.Lock` in multi-threaded environments.

---

## Performance Notes

| Concern | Behavior | Recommendation |
|---------|----------|----------------|
| Disk I/O on `ensure_key()` | Saves to disk **every time** a new key is created. | For batch inserts, use `set_template()` in a loop and call `save()` once at the end. |
| Disk I/O on `get_template()` | Reads other language files from disk on first access, then caches. | Cache is per-instance; create instance once and reuse. |
| Memory | Old `templates` dicts are not freed on `set_language()`. | Call `del templates` or recreate the instance if switching languages frequently. |
| Legacy files | Left in place after migration. | Clean up manually if disk space is a concern. |

---

## Logging

The module uses Python's standard `logging` module under the logger name `__name__`.

**Log Levels Used**

| Level | Event |
|-------|-------|
| `DEBUG` | Initialization, language detection source, cache invalidation, save completion. |
| `WARNING` | Invalid key type, template formatting failure (`KeyError`/`ValueError`). |
| `ERROR` | Corrupted JSON, save failure, unexpected load error. |

---

## Changelog

| Version | Notes |
|---------|-------|
| 0.2.0 | Current — Self-Healing Localizer for AI prompt templates with formatting support, legacy migration, corrupted file backup, in-memory cache, and dictionary-like API. |
