# GLFM Database Loader — API Documentation

## Module Overview

**File:** `glfm_load_database.py`

Zero-dependency loader for the GLFM (Global Language Family Mapper) database. Supports both uncompressed JSON and gzip-compressed JSON files, automatic format detection, path-based caching, and fallback resolution between Lite and Full database variants. Uses only the Python standard library.

---

## Metadata

| Attribute | Value |
|-----------|-------|
| Author | Tuomas Lähteenmäki |
| Version | 0.2.0 |
| License | MIT |

---

## Dependencies

| Module | Usage |
|--------|-------|
| `gzip` | Decompression of `.json.gz` database files. |
| `json` | Parsing database files into Python dictionaries. |
| `logging` | Info and error log output for database loading. |
| `pathlib.Path` | Cross-platform path construction and resolution. |
| `typing.Any`, `typing.Dict`, `typing.Optional` | Type annotations. |

---

## Module Constants

| Name | Type | Value | Description |
|------|------|-------|-------------|
| `DATA_DIR` | `Path` | `Path(__file__).resolve().parent.parent / "data"` | Directory containing GLFM database files, resolved relative to this module (`shl/data/`). |
| `LITE_DB_PATH` | `Path` | `DATA_DIR / "languages_top20.json.gz"` | Default path to the GLFM Lite database. |
| `FULL_DB_PATH` | `Path` | `DATA_DIR / "unified_languages.json.gz"` | Default path to the Full GLFM database. |

---

## Module-Level State

| Name | Type | Description |
|------|------|-------------|
| `_glfm_cache` | `Dict[str, Dict[str, Any]]` | In-memory cache mapping resolved database paths to parsed language data. Supports multiple concurrent databases (e.g., Lite + custom test databases). |

---

## Internal Functions

### `_cache_key()`

```python
def _cache_key(db_path: Path) -> str
```

Generates a stable cache key for a database file path.

| Parameter | Type | Description |
|-----------|------|-------------|
| `db_path` | `Path` | Database file path. |

**Returns**
- `str` — Resolved absolute path string, or `absolute()` fallback if resolution fails.

---

### `_is_gzip_file()`

```python
def _is_gzip_file(db_path: Path) -> bool
```

Detects whether a file is gzip-compressed by reading its magic bytes.

| Parameter | Type | Description |
|-----------|------|-------------|
| `db_path` | `Path` | File to inspect. |

**Returns**
- `bool` — `True` if the file starts with gzip magic bytes `0x1f 0x8b`, `False` otherwise.

**Note:** Only reads the first 2 bytes. Efficient for large files.

---

### `_load_json_file()`

```python
def _load_json_file(db_path: Path) -> Dict[str, Any]
```

Loads an ordinary uncompressed JSON file.

| Parameter | Type | Description |
|-----------|------|-------------|
| `db_path` | `Path` | Path to the `.json` file. |

**Returns**
- `Dict[str, Any]` — Parsed JSON data.

**Raises**
- `json.JSONDecodeError` — If the file contains invalid JSON.
- `OSError` — If the file cannot be read.

---

### `_load_gzip_json_file()`

```python
def _load_gzip_json_file(db_path: Path) -> Dict[str, Any]
```

Loads a gzip-compressed JSON file.

| Parameter | Type | Description |
|-----------|------|-------------|
| `db_path` | `Path` | Path to the `.json.gz` file. |

**Returns**
- `Dict[str, Any]` — Parsed JSON data from the decompressed stream.

**Raises**
- `gzip.BadGzipFile` — If the file is not a valid gzip archive.
- `json.JSONDecodeError` — If the decompressed content is invalid JSON.
- `OSError` — If the file cannot be read.

---

## Public Functions

### `load_language_data()`

```python
def load_language_data(
    db_path: Optional[Path] = None,
) -> Dict[str, Any]
```

Loads GLFM language data from a JSON or gzip-compressed JSON file. Results are cached by resolved path for subsequent calls.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `db_path` | `Optional[Path]` | `None` | Path to the database file. If omitted, attempts Lite first, then Full. |

**Returns**
- `Dict[str, Any]` — Dictionary containing language data, keyed by language ID.

**Raises**
- `FileNotFoundError` — If the specified file does not exist, or if neither default database is found when `db_path` is `None`.
- `json.JSONDecodeError` — If the file contains invalid JSON.
- `ValueError` — If the JSON root is not a dictionary.
- `gzip.BadGzipFile` — If a gzip file is corrupted.
- `OSError` — If the file cannot be read due to permissions or I/O errors.

**Auto-Detection Logic**
1. If `db_path` is provided → use that file.
2. If `db_path` is `None`:
   - Check if `LITE_DB_PATH` exists → use it.
   - Else check if `FULL_DB_PATH` exists → use it.
   - Else raise `FileNotFoundError`.
3. Check cache → return cached data if hit.
4. Detect gzip format via magic bytes.
5. Load via appropriate loader (`_load_gzip_json_file` or `_load_json_file`).
6. Validate that root is a `dict`.
7. Store in cache and return.

**Caching**
- Each unique resolved path is cached independently.
- Subsequent calls with the same path return cached data without re-reading the file.
- Use `clear_glfm_cache()` to invalidate.

**Example**
```python
from shl.utils.glfm_load_database import load_language_data
from pathlib import Path

# Load default database (Lite preferred, Full fallback)
data = load_language_data()
print(f"Loaded {len(data)} languages")

# Load specific file
custom = load_language_data(Path("/path/to/custom.json"))
```

---

### `get_glfm_data()`

```python
def get_glfm_data(
    db_path: Optional[Path] = None,
) -> Optional[Dict[str, Any]]
```

Retrieves cached GLFM data without triggering a load.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `db_path` | `Optional[Path]` | `None` | Specific database path to look up. |

**Returns**
- `Optional[Dict[str, Any]]` — Cached language data, or `None` if not in cache.

**Behavior**
- If `db_path` is provided → returns cached data for that specific path.
- If `db_path` is `None` and cache is not empty → returns the first cached entry.
- If `db_path` is `None` and cache is empty → returns `None`.

**Example**
```python
from shl.utils.glfm_load_database import get_glfm_data

data = get_glfm_data()
if data:
    print(f"Cache has {len(data)} languages")
```

---

### `clear_glfm_cache()`

```python
def clear_glfm_cache(
    db_path: Optional[Path] = None,
) -> None
```

Clears the GLFM database cache.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `db_path` | `Optional[Path]` | `None` | If provided, removes only that database from cache. If `None`, clears all entries. |

**Example**
```python
from shl.utils.glfm_load_database import clear_glfm_cache
from pathlib import Path

# Clear specific database
clear_glfm_cache(Path("/path/to/custom.json"))

# Clear everything
clear_glfm_cache()
```

---

### `get_language_count()`

```python
def get_language_count(
    db_path: Optional[Path] = None,
) -> int
```

Returns the number of languages in the cached database.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `db_path` | `Optional[Path]` | `None` | Specific database to count. |

**Returns**
- `int` — Number of language entries, or `0` if the database is not loaded.

**Example**
```python
from shl.utils.glfm_load_database import get_language_count

count = get_language_count()
print(f"Database contains {count} languages")
```

---

### `find_language()`

```python
def find_language(
    lang_code: str,
    db_path: Optional[Path] = None,
) -> Optional[Dict[str, Any]]
```

Finds a language entry by ISO 639-1, ISO 639-3, or BCP-47 tag. Automatically loads the default database if not already cached.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lang_code` | `str` | — | Language code to look up. |
| `db_path` | `Optional[Path]` | `None` | Specific database to search. Loads default if omitted and cache is empty. |

**Returns**
- `Optional[Dict[str, Any]]` — Language information dictionary, or `None` if not found.

**Lookup Order**
1. **ISO 639-1 match** — Compares `info['iso639_1']` against the base language code (case-insensitive).
2. **Direct base code lookup** — Checks if the base language code exists as a top-level key.
3. **Normalized BCP-47 tag** — Looks up the canonical full tag.
4. **Case-insensitive key search** — Iterates all keys for a case-insensitive match.

**Example**
```python
from shl.utils.glfm_load_database import find_language

info = find_language("fi")
if info:
    print(info["name"])        # "Finnish"
    print(info["iso639_1"])    # "fi"
    print(info["family"])      # "Uralic"

# BCP-47 tag
info = find_language("zh-TW")
```

---

### `is_lite_available()`

```python
def is_lite_available() -> bool
```

Checks whether the GLFM Lite database file exists on disk.

**Returns**
- `bool` — `True` if `languages_top20.json.gz` exists in the data directory.

---

### `is_full_available()`

```python
def is_full_available() -> bool
```

Checks whether the Full GLFM database file exists on disk.

**Returns**
- `bool` — `True` if `unified_languages.json.gz` exists in the data directory.

---

## Database File Locations

```
shl/
├── utils/
│   └── glfm_load_database.py   ← This module
└── data/
    ├── languages_top20.json.gz ← GLFM Lite (~428 KB)
    └── unified_languages.json.gz ← Full GLFM (~51.6 MB)
```

---

## Usage Example

```python
from shl.utils.glfm_load_database import (
    load_language_data,
    find_language,
    get_language_count,
    clear_glfm_cache,
    is_lite_available,
    is_full_available,
)

# Check availability
print(f"Lite available: {is_lite_available()}")
print(f"Full available: {is_full_available()}")

# Load default database
data = load_language_data()
print(f"Loaded {len(data)} languages")

# Find specific language
info = find_language("ja")
if info:
    print(f"Japanese: {info['name']}")
    print(f"Scripts: {info.get('written_scripts', [])}")
    print(f"Family: {info.get('family')}")

# Count languages
count = get_language_count()
print(f"Total entries: {count}")

# Clear cache when done
clear_glfm_cache()
```

---

## Supported Database Formats

| Format | Extension | Detection | Use Case |
|--------|-----------|-----------|----------|
| Gzip JSON | `.json.gz` | Magic bytes `0x1f 0x8b` | Production databases (Lite/Full). |
| Plain JSON | `.json` | No magic bytes | Custom/test databases. |

---

## Caching Behavior

```
First call to load_language_data()
    ├── Check cache (miss)
    ├── Detect format (gzip/plain)
    ├── Parse JSON
    ├── Validate root is dict
    ├── Store in _glfm_cache[path]
    └── Return data

Second call with same path
    ├── Check cache (hit)
    └── Return cached data (no disk I/O)
```

Multiple databases can coexist in the cache:
```python
lite = load_language_data()           # Cached as ".../languages_top20.json.gz"
custom = load_language_data(Path("custom.json"))  # Cached separately
```

---

## Error Handling

| Exception | Cause | Handling |
|-----------|-------|----------|
| `FileNotFoundError` | Database file missing. | Logged and re-raised with helpful message listing tried paths. |
| `json.JSONDecodeError` | Invalid JSON syntax. | Logged and re-raised. |
| `ValueError` | JSON root is not a dict. | Logged and re-raised. |
| `gzip.BadGzipFile` | Corrupted gzip archive. | Logged and re-raised. |
| `OSError` | Permission denied or I/O failure. | Logged and re-raised. |

---

## Thread Safety

| Component | Status | Notes |
|-----------|--------|-------|
| `_glfm_cache` | Caution | Dictionary mutation during `load_language_data()` is not atomic. Concurrent first-time loads of the same path may race. |
| `get_glfm_data()` | Safe | Read-only cache access after load. |
| `find_language()` | Caution | May trigger `load_language_data()` if cache is empty. |

**Recommendation:** Call `load_language_data()` once during application startup from a single thread. After initialization, all read operations are safe for concurrent use.

---

## Logging

The module uses Python's standard `logging` module under the logger name `__name__`.

**Log Levels Used**

| Level | Event |
|-------|-------|
| `INFO` | Database loaded successfully (language count, filename). |
| `ERROR` | Invalid gzip, invalid JSON, read failure, or unexpected error. |
| `DEBUG` | Cache cleared (specific or all). |

---

## Changelog

| Version | Notes |
|---------|-------|
| 0.2.0 | Current — zero-dependency GLFM loader with gzip auto-detection, path-based caching, Lite/Full fallback, and language lookup by ISO 639-1/3 and BCP-47. |
