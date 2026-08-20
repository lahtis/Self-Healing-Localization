# UI Text Localizer — API Documentation

## Module Overview

**File:** `localizer.py`

Self-Healing Localizer for UI text translations. Manages per-language JSON files for storing and retrieving localized strings. Supports automatic language detection (with `config.conf` override), corrupted file backup, legacy file migration, in-memory caching of loaded languages, and a full dictionary-like interface.

---

## Metadata

| Attribute | Value |
|-----------|-------|
| Author | Tuomas Lähteenmäki |
| Version | 0.2.1 |
| License | MIT |
| Description | Self-Healing Localizer for UI text. `SETTINGS.language` overrides OS locale and GLFM completely. |

---

## Dependencies

| Module | Usage |
|--------|-------|
| `atexit` | Automatic save on program exit. |
| `json` | JSON file serialization and deserialization. |
| `logging` | Debug, info, warning, and error log output. |
| `os` | File/directory operations and environment variable access. |
| `shutil` | Corrupted file backup via `copy2`. |
| `datetime` | Timestamp generation for backup file names. |
| `typing.Any`, `typing.Dict`, `typing.Optional` | Type annotations. |
| `shl.utils.lang_utils.base_language` | Extract base language from a tag. |
| `shl.utils.lang_utils.normalize_full_tag` | Normalize language codes to canonical form. |

---

## Class: `Localizer`

```python
class Localizer
```

Manages UI text translations stored as JSON files in a per-language structure. Each language has its own `{lang_code}.json` file. Supports key-based lookups, lazy creation, fallback to base language, and automatic persistence.

---

### Constructor

```python
def __init__(
    self,
    lang_code: Optional[str] = None,
    base_lang: str = "en",
    folder: str = "locales",
) -> None
```

Initializes the localizer, detects the active language, ensures the storage directory exists, and loads or creates the language file.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lang_code` | `Optional[str]` | `None` | Target language code. Auto-detected if omitted (see `_detect_language()`). |
| `base_lang` | `str` | `"en"` | Base/source language for fallback lookups. |
| `folder` | `str` | `"locales"` | Directory for storing JSON translation files. |

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
| `texts` | `Dict[str, Any]` | In-memory dictionary of the active language's translations. |
| `_loaded_langs` | `Dict[str, Dict[str, Any]]` | Cache of other languages loaded via `get_text()`. |
| `_dirty` | `bool` | Whether `texts` has unsaved changes. |
| `_alive` | `bool` | Whether the localizer is active (used by cleanup). |
| `_shutting_down` | `bool` | Whether an atexit save is in progress. |

---

### Language Detection

#### `_detect_language()`

```python
def _detect_language(self) -> Optional[str]
```

Detects the active language using a priority cascade. `SETTINGS.language` in `config.conf` takes absolute precedence over all other sources.

**Detection Order**
1. **`config.conf` `[SETTINGS]` section** — `language` key. If present, returned immediately.
2. **`SHL_LANGUAGE` environment variable** — If set, returned.
3. **`LANG` environment variable** — Parsed: encoding suffix stripped (`fi_FI.UTF-8` → `fi_FI`), underscores converted to hyphens (`fi_FI` → `fi-FI`).
4. **`None`** — No language detected; caller falls back to `base_lang`.

**Returns**
- `Optional[str]` — Detected language code, or `None`.

**Logging**
- `DEBUG` — Source of detected language (`SETTINGS`, `SHL_LANGUAGE`, locale).
- `DEBUG` — Detection failure reason.

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
- Root is not a `dict` → logs error, backs up file, returns `None`.
- `JSONDecodeError` / `UnicodeDecodeError` → logs error, backs up file, returns `None`.
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
locales/fi.json → locales/fi.json.20240820_143052.bak
```

---

#### `_save_texts()`

```python
def _save_texts(
    self,
    texts: Dict[str, Any],
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

Persists the active language's `texts` dictionary to disk.

| Method | Behavior |
|--------|----------|
| `_save()` | Unconditionally saves `self.texts` to `self.lang_file`. |
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
- `Dict[str, Any]` — Loaded or newly created translation dictionary.

---

### Public API — Core Methods

#### `L()`

```python
def L(self, key: str, default: str = "") -> str
```

Primary method for retrieving UI text. Creates the key with `default` value if it does not exist.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `key` | `str` | — | Localization key. |
| `default` | `str` | `""` | Default text to set if the key is missing. |

**Returns**
- `str` — The localized text, or `default` / empty string.

**Behavior**
1. Validates the key.
2. If key not in `texts`:
   - Sets `texts[key] = default`.
   - Marks dirty.
   - Invalidates cache.
   - **Saves to disk immediately.**
3. Returns the value.

**Note:** This method saves to disk on every key creation. For batch operations, consider using `set_text()` directly and calling `save()` once at the end.

**Example**
```python
from shl.engine.localizer import Localizer

localizer = Localizer(lang_code="fi")

text = localizer.L("welcome_message", "Welcome!")
# If "welcome_message" didn't exist, it is created with "Welcome!" and saved.
```

---

#### `get()`

```python
def get(self, key: str, default: str = "") -> str
```

Alias for `L()`. Provided for dictionary-like API consistency.

---

#### `get_text()`

```python
def get_text(
    self,
    key: str,
    lang_code: Optional[str] = None,
    fallback: bool = True,
) -> Optional[str]
```

Retrieves text from a specific language file, with optional fallback to the base language.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `key` | `str` | — | Localization key. |
| `lang_code` | `Optional[str]` | `None` | Target language. Defaults to active language. |
| `fallback` | `bool` | `True` | Whether to fall back to base language if key is missing. |

**Returns**
- `Optional[str]` — The localized text, or `None` if not found in target or base language.

**Behavior**
1. Validates key.
2. Normalizes target language code.
3. Attempts to load text from target language file.
4. If not found and `fallback=True` and target ≠ base → attempts base language file.
5. Returns `None` if all fallbacks exhausted.

**Performance Note:** When reading a language other than the active one, the file is read from disk and cached in `_loaded_langs`. However, the active language (`self.lang_code`) is served directly from `self.texts` without disk access.

---

#### `_get_text_from_lang()`

```python
def _get_text_from_lang(
    self,
    key: str,
    lang_code: str,
) -> Optional[str]
```

Internal method that loads a language file from disk and retrieves a specific key.

**Returns**
- `Optional[str]` — The text value, or `None` if the file or key is missing.

**Caching**
- Loaded languages are stored in `_loaded_langs` to avoid repeated disk reads.
- If a file is missing, an empty dict is cached for that language.

**Note:** Unlike `_load_json_safe()`, this method does **not** back up corrupted JSON files. Corrupted files are silently treated as empty.

---

#### `set_text()`

```python
def set_text(
    self,
    key: str,
    value: Optional[str],
) -> bool
```

Sets a key's value in the active language and persists to disk.

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | `str` | Localization key. |
| `value` | `Optional[str]` | Text value. `None` is stored as empty string `""`. |

**Returns**
- `bool` — `True` if saved successfully, `False` otherwise.

**Behavior**
1. Validates key.
2. Normalizes `None` to `""`.
3. Sets `texts[key] = value`.
4. Marks dirty and invalidates cache.
5. Saves to disk immediately.

**Example**
```python
localizer.set_text("greeting", "Hei!")
localizer.set_text("empty_key", None)  # Stored as ""
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

**Note:** The old `texts` dictionary is replaced but not explicitly freed from memory. In long-running applications with frequent language switches, this may accumulate memory.

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
if "welcome" in localizer:
    print("Key exists")
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

Returns a string representation: `Localizer(lang='fi', keys=42)`.

---

#### `__getitem__()` / `__setitem__()`

```python
def __getitem__(self, key: str) -> str
def __setitem__(self, key: str, value: Optional[str]) -> None
```

Dictionary-style access.

```python
localizer["greeting"] = "Hei!"
print(localizer["greeting"])  # "Hei!"
```

---

## Complete Usage Example

```python
from shl.engine.localizer import Localizer

# Initialize for Finnish
localizer = Localizer(
    lang_code="fi",
    base_lang="en",
    folder="locales",
)

# Primary lookup (creates key if missing)
text = localizer.L("welcome", "Welcome!")
print(text)  # "Welcome!" (or existing Finnish translation)

# Dictionary-style access
localizer["farewell"] = "Näkemiin!"
print(localizer["farewell"])  # "Näkemiin!"

# Check existence
if "welcome" in localizer:
    print(f"Welcome text: {localizer['welcome']}")

# Get from another language with fallback
text = localizer.get_text("welcome", lang_code="sv", fallback=True)

# Set explicitly
localizer.set_text("new_feature", "Uusi ominaisuus!")

# Switch language
localizer.set_language("sv")

# Introspection
print(f"Keys: {len(localizer)}")
print(f"All keys: {localizer.keys()}")

# Clean shutdown
localizer.close()
```

---

## File Structure

```
locales/
├── en.json          ← Base language
├── fi.json          ← Active language (Finnish)
├── sv.json          ← Swedish (loaded on demand)
└── lang_fi.json     ← Legacy file (migrated but not deleted)
```

---

## Thread Safety

| Component | Status | Notes |
|-----------|--------|-------|
| `texts` dictionary reads | Generally safe | CPython dict reads are atomic. |
| `texts` dictionary writes | Not safe | `L()`, `set_text()`, and `set_language()` mutate `texts`. Concurrent writes may race. |
| File I/O | Not safe | `_save_texts()` writes to disk without locking. Concurrent saves may corrupt the file. |
| `_loaded_langs` cache | Not safe | Mutated by `_get_text_from_lang()` without synchronization. |

**Recommendation:** Use one `Localizer` instance per thread, or wrap mutating operations with a `threading.Lock` in multi-threaded environments.

---

## Performance Notes

| Concern | Behavior | Recommendation |
|---------|----------|----------------|
| Disk I/O on `L()` | Saves to disk **every time** a new key is created. | For batch inserts, use `set_text()` in a loop and call `save()` once at the end. |
| Disk I/O on `get_text()` | Reads other language files from disk on first access, then caches. | Cache is per-instance; create instance once and reuse. |
| Memory | Old `texts` dicts are not freed on `set_language()`. | Call `del localizer` or recreate the instance if switching languages frequently. |
| Legacy files | Left in place after migration. | Clean up manually if disk space is a concern. |

---

## Logging

The module uses Python's standard `logging` module under the logger name `__name__`.

**Log Levels Used**

| Level | Event |
|-------|-------|
| `DEBUG` | Initialization, language detection source, cache invalidation, key set, save completion. |
| `INFO` | Legacy file migration, corrupted file backup. |
| `WARNING` | Invalid key type, empty key. |
| `ERROR` | Corrupted JSON, save failure, backup failure, unexpected load error. |

---

## Changelog

| Version | Notes |
|---------|-------|
| 0.2.1 | Current — `SETTINGS.language` overrides OS locale and GLFM completely. Legacy migration, corrupted file backup, in-memory cache, and dictionary-like API. |
