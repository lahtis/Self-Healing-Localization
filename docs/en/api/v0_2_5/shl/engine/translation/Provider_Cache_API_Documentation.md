# ProviderCache API Documentation

## Overview

`provider_cache.py` checks the language support of service providers and saves it to a local JSON cache. It fetches live language data from Microsoft Translator and LibreTranslate APIs, loads static Papago and MyMemory language data from a local JSON file, and persists the combined result to disk.

---

## Module Metadata

| Field | Value |
|-------|-------|
| **File** | `provider_cache.py` |
| **Author** | Tuomas Lähteenmäki |
| **License** | MIT |
| **Version** | `0.2.5-fix` |

---

## Module Constants

### Paths

| Constant | Value | Description |
|----------|-------|-------------|
| `SHL_DIR` | `Path(__file__).resolve().parents[2]` | The SHL package root directory, resolved two levels above this file. |
| `CACHE_FILE` | `SHL_DIR / "languages_cache.json"` | Path to the generated language cache file. |
| `PM_FILE` | `SHL_DIR / "data" / "papago_mymemory.json"` | Path to the static Papago and MyMemory language data file. |

---

## Dependencies and Imports

### Standard Library

- `json`
- `shutil`
- `pathlib.Path`
- `urllib.request.urlopen`

---

## Functions

### `load_cache() -> dict`

Loads the existing language cache from disk.

#### Behavior

- If `CACHE_FILE` exists, attempts to open and parse it as JSON.
- If parsing succeeds, returns the parsed dictionary.
- If parsing fails (`json.JSONDecodeError` or `OSError`):
  - Creates a backup by copying the broken file to `CACHE_FILE.with_suffix(".json.bak")`.
  - If the backup copy fails (`OSError`), the error is silently ignored.
  - Falls through to `generate_cache()`.
- If `CACHE_FILE` does not exist, calls `generate_cache()` to create it.

#### Returns

- `dict` — The loaded or newly generated cache dictionary.

---

### `fetch_json(url: str) -> object`

Fetches JSON data from a URL using Python's standard library.

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `url` | `str` | The URL to fetch JSON from. |

#### Behavior

- Opens the URL with `urlopen(url, timeout=10)`.
- Reads the response, decodes as UTF-8, and parses with `json.loads`.

#### Returns

- `object` — The parsed JSON data (type depends on the response).

---

### `generate_cache() -> dict`

Generates the provider language cache by fetching live data and loading static data.

#### Behavior

1. **Microsoft Translator**: Calls `fetch_microsoft_translator()` inside a `try/except`. On any exception, falls back to an empty dict `{}`.
2. **LibreTranslate**: Calls `fetch_libretranslate()` inside a `try/except`. On any exception, falls back to an empty dict `{}`.
3. **Papago / MyMemory**: Calls `load_papago_mymemory()`.
4. Constructs the cache dictionary with the following structure:

```json
{
  "providers": {
    "microsoft_translator": { "code": "Name", ... },
    "libretranslate": { "code": "Name", ... },
    "papago": ["code1", "code2", ...],
    "mymemory_iso_639_1": ["code1", "code2", ...]
  }
}
```

   - `"microsoft_translator"`: The dict returned by `fetch_microsoft_translator()`.
   - `"libretranslate"`: The dict returned by `fetch_libretranslate()`.
   - `"papago"`: A sorted list of lowercase language codes from `papago_mymemory.get("papago", [])`.
   - `"mymemory_iso_639_1"`: A sorted list of lowercase language codes from `papago_mymemory.get("mymemory_iso_639_1", [])`.
5. Creates parent directories for `CACHE_FILE` if they do not exist (`mkdir(parents=True, exist_ok=True)`).
6. Writes the cache to `CACHE_FILE` as JSON with `indent=4` and `ensure_ascii=False`.
7. Returns the cache dictionary.

#### Returns

- `dict` — The generated cache dictionary.

---

### `fetch_microsoft_translator() -> dict`

Fetches Microsoft Translator language information.

#### Behavior

- Calls `fetch_json("https://api.cognitive.microsofttranslator.com/languages?api-version=3.0")`.
- Extracts the `"translation"` field from the response (defaults to `{}` if missing).
- Returns a dictionary mapping each language code (lowercased) to its `"name"` field.

#### Returns

- `dict` — `{ "code_lower": "Language Name", ... }`

---

### `fetch_libretranslate() -> dict`

Fetches LibreTranslate language information.

#### Behavior

- Calls `fetch_json("https://libretranslate.com/languages")`.
- Does not use an API key.
- Does not use localhost.
- Returns a dictionary mapping each language's `"code"` (lowercased) to its `"name"`.

#### Returns

- `dict` — `{ "code_lower": "Language Name", ... }`

---

### `load_papago_mymemory(path: Path = PM_FILE) -> dict`

Loads Papago and MyMemory language data from a local JSON file.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | `Path` | `PM_FILE` | Path to the Papago / MyMemory JSON file. |

#### Behavior

- If `path` does not exist, returns a default dictionary:
  ```python
  {
      "papago": [],
      "mymemory_iso_639_1": [],
  }
  ```
- Otherwise, opens the file and parses it as JSON.

#### Returns

- `dict` — The parsed JSON dictionary, expected to contain `"papago"` and `"mymemory_iso_639_1"` keys.

---

## Cache File Format

The generated `languages_cache.json` has the following structure:

```json
{
  "providers": {
    "microsoft_translator": {
      "en": "English",
      "fi": "Finnish",
      "..."
    },
    "libretranslate": {
      "en": "English",
      "fi": "Finnish",
      "..."
    },
    "papago": ["en", "fi", "..."],
    "mymemory_iso_639_1": ["en", "fi", "..."]
  }
}
```

- `microsoft_translator` and `libretranslate` are dictionaries of `{code: name}`.
- `papago` and `mymemory_iso_639_1` are sorted lists of lowercase language codes.

---

## Error Handling

- `load_cache()`: If the existing cache file is corrupted, it is backed up to `.json.bak` and regenerated.
- `generate_cache()`: Failures in `fetch_microsoft_translator()` or `fetch_libretranslate()` are caught with bare `except Exception`, causing those provider entries to be empty dictionaries.
- `fetch_json()`: Uses a 10-second timeout. Any network or parsing errors propagate to the caller.

---

## Usage Example

```python
from shl.engine.translation.provider_cache import load_cache, generate_cache

# Load existing cache or generate if missing/broken
cache = load_cache()

# Access provider language data
microsoft_langs = cache["providers"]["microsoft_translator"]
libre_langs = cache["providers"]["libretranslate"]
papago_codes = cache["providers"]["papago"]
mymemory_codes = cache["providers"]["mymemory_iso_639_1"]

# Force regeneration
cache = generate_cache()
```

---

## Version

**Module version:** `0.2.5-fix`

**Author:** Tuomas Lähteenmäki

**License:** MIT
