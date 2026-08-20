# Provider Language Cache — API Documentation

## Module Overview

**File:** `provider_cache.py`

Manages language support discovery and caching for SHL translation providers. Fetches live language lists from remote APIs (Microsoft Translator, LibreTranslate) and combines them with static configuration data (Papago, MyMemory) into a unified, disk-persisted cache. The module separates offline cache reading from online cache generation to ensure fast cold starts and minimal network usage.

---

## Metadata

| Attribute | Value |
|-----------|-------|
| Author | Tuomas Lähteenmäki |
| Version | 0.2.5 |
| License | MIT |

---

## Dependencies

| Module | Usage |
|--------|-------|
| `json` | Serialization and deserialization of cache and static data files. |
| `os` | File existence checks for cache loading. |
| `requests` | HTTP POST requests to Microsoft Translator and LibreTranslate language endpoints. |

---

## Module Constants

| Name | Type | Value | Description |
|------|------|-------|-------------|
| `CACHE_FILE` | `str` | `"languages_cache.json"` | Path to the generated provider language cache file. |
| `PM_FILE` | `str` | `"data/papago_mymemory.json"` | Path to the static JSON file containing Papago and MyMemory language code lists. |

---

## Cache Structure

The generated cache file (`languages_cache.json`) has the following structure:

```json
{
    "providers": {
        "microsoft_translator": {
            "en": "English",
            "fi": "Finnish",
            "ja": "Japanese"
        },
        "libretranslate": {
            "en": "English",
            "fi": "Finnish"
        },
        "papago": ["en", "ja", "ko", "zh-cn"],
        "mymemory": ["en", "fi", "de", "fr"]
    }
}
```

| Provider | Value Type | Source |
|----------|-----------|--------|
| `microsoft_translator` | `dict[str, str]` | Live API — code → display name mapping. |
| `libretranslate` | `dict[str, str]` | Live API — code → display name mapping. |
| `papago` | `list[str]` | Static file — sorted lowercase language codes. |
| `mymemory` | `list[str]` | Static file — sorted lowercase language codes. |

---

## Functions

### `load_cache()`

```python
def load_cache() -> dict
```

Loads the existing provider language cache from disk **without making any network calls**.

**Returns**
- `dict` — The parsed cache dictionary. Returns an empty dict `{}` if the cache file does not exist.

**Behavior**
- Checks if `CACHE_FILE` (`"languages_cache.json"`) exists.
- If it exists, reads and parses it as UTF-8 JSON.
- If it does not exist, returns `{}` and lets the caller (typically the router) decide the fallback behavior.

**Side Effects**
- None (read-only disk access).

**Network Usage**
- None.

**Example**
```python
cache = load_cache()
if cache:
    ms_langs = cache["providers"]["microsoft_translator"]
    print(f"Microsoft supports {len(ms_langs)} languages")
else:
    print("No cache found — consider calling generate_cache()")
```

---

### `generate_cache()`

```python
def generate_cache() -> dict
```

Generates a fresh provider language cache by fetching live data from remote APIs and reading static configuration files, then persists the result to disk.

**Returns**
- `dict` — The newly generated and saved cache dictionary.

**Behavior**
1. Fetches Microsoft Translator language list via `fetch_microsoft_translator()`.
2. Fetches LibreTranslate language list via `fetch_libretranslate()`.
3. Loads static Papago and MyMemory language codes via `load_papago_mymemory()`.
4. Assembles the unified cache structure.
5. Writes the result to `CACHE_FILE` as indented UTF-8 JSON.

**Side Effects**
- Writes to `CACHE_FILE` on disk.
- Makes up to 2 HTTP POST requests to external APIs.

**Network Usage**
- Microsoft Translator API — 1 POST request.
- LibreTranslate API — 1 POST request.

**Raises**
- `requests.HTTPError` — If either live API returns a non-2xx status code.
- `requests.Timeout` — If either API request exceeds the 10-second timeout.
- `json.JSONDecodeError` — If the API response or static file contains invalid JSON.
- `FileNotFoundError` — If `PM_FILE` does not exist.

**Example**
```python
try:
    cache = generate_cache()
    print("Cache generated successfully")
    for provider, data in cache["providers"].items():
        print(f"  {provider}: {len(data)} languages")
except requests.RequestException as e:
    print(f"Network error during cache generation: {e}")
```

---

### `fetch_microsoft_translator()`

```python
def fetch_microsoft_translator() -> dict
```

Fetches the list of supported languages from the Microsoft Translator API.

**Returns**
- `dict` — Mapping of lowercase language codes to their display names.
  ```python
  {"en": "English", "fi": "Finnish", "ja": "Japanese"}
  ```

**API Details**

| Attribute | Value |
|-----------|-------|
| Endpoint | `https://api.cognitive.microsofttranslator.com/languages?api-version=3.0` |
| Method | `POST` |
| Timeout | `10` seconds |

**Response Parsing**
- Extracts the `"translation"` object from the JSON response.
- Maps each language code (lowercased) to its `"name"` field.

**Raises**
- `requests.HTTPError` — On non-2xx response.
- `requests.Timeout` — On timeout.
- `KeyError` — If the response JSON lacks the expected `"translation"` key.

**Example**
```python
ms_langs = fetch_microsoft_translator()
print(ms_langs.get("fi"))  # "Finnish"
```

---

### `fetch_libretranslate()`

```python
def fetch_libretranslate() -> dict
```

Fetches the list of supported languages from the LibreTranslate API.

**Returns**
- `dict` — Mapping of lowercase language codes to their display names.
  ```python
  {"en": "English", "es": "Spanish", "de": "German"}
  ```

**API Details**

| Attribute | Value |
|-----------|-------|
| Endpoint | `https://libretranslate.com/languages` |
| Method | `POST` |
| Timeout | `10` seconds |

**Response Parsing**
- Expects a JSON array of language objects.
- Maps each object's `"code"` field (lowercased) to its `"name"` field.

**Raises**
- `requests.HTTPError` — On non-2xx response.
- `requests.Timeout` — On timeout.
- `KeyError` — If a language object lacks `"code"` or `"name"`.

**Example**
```python
lt_langs = fetch_libretranslate()
print(lt_langs.get("de"))  # "German"
```

---

### `load_papago_mymemory()`

```python
def load_papago_mymemory(path: str = PM_FILE) -> dict
```

Loads the static JSON file containing pre-defined language code lists for Papago and MyMemory providers.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | `str` | `PM_FILE` | Path to the static JSON file. |

**Returns**
- `dict` — Parsed JSON with expected keys `"papago"` and `"mymemory_iso_639_1"`, each containing a list of language code strings.
  ```python
  {
      "papago": ["en", "ja", "ko", "zh-cn", "zh-tw"],
      "mymemory_iso_639_1": ["en", "fi", "de", "fr", "es"]
  }
  ```

**Behavior**
- Reads the file at `path` as UTF-8 JSON.
- No network calls.

**Raises**
- `FileNotFoundError` — If the file at `path` does not exist.
- `json.JSONDecodeError` — If the file contains invalid JSON.

**Example**
```python
data = load_papago_mymemory()
papago_codes = data.get("papago", [])
mymemory_codes = data.get("mymemory_iso_639_1", [])
```

---

## Workflow Diagram

```
┌─────────────────┐
│   Application   │
│    Startup      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     Yes      ┌─────────────────┐
│  Cache exists?  │─────────────►│   load_cache()  │
│  (languages_    │              │  (offline, fast)│
│   cache.json)   │              └─────────────────┘
└────────┬────────┘
         │ No
         ▼
┌─────────────────┐
│ generate_cache()│
│  (network + IO) │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌──────────┐ ┌─────────────────────┐
│ fetch_ │ │ fetch_   │ │ load_papago_        │
│microsoft│ │libretrans│ │ mymemory()          │
│translator│ │late()    │ │ (static JSON)       │
└────────┘ └──────────┘ └─────────────────────┘
         │
         ▼
┌─────────────────┐
│  Save to disk   │
│languages_cache  │
│    .json        │
└─────────────────┘
```

---

## Usage Example

```python
from provider_cache import load_cache, generate_cache
import os

# Fast path: try to load existing cache
cache = load_cache()

# If no cache exists or it's stale, regenerate
if not cache:
    print("Cache missing — generating...")
    cache = generate_cache()

# Query provider support
providers = cache.get("providers", {})

# Microsoft: dict of code -> name
ms_langs = providers.get("microsoft_translator", {})
print(f"Microsoft Translator: {len(ms_langs)} languages")

# Papago: list of codes
papago_langs = providers.get("papago", [])
print(f"Papago: {len(papago_langs)} languages")

# Check if a specific language is supported
if "fi" in ms_langs:
    print("Finnish is supported by Microsoft Translator")
```

---

## Error Handling

| Function | Error Type | Cause | Recommended Action |
|----------|-----------|-------|-------------------|
| `load_cache()` | `json.JSONDecodeError` | Cache file is corrupted JSON. | Delete `CACHE_FILE` and call `generate_cache()`. |
| `generate_cache()` | `requests.HTTPError` | API returned non-2xx status. | Retry with exponential backoff or use stale cache. |
| `generate_cache()` | `requests.Timeout` | API did not respond within 10s. | Retry or mark provider unavailable. |
| `generate_cache()` | `FileNotFoundError` | `PM_FILE` missing. | Ensure `data/papago_mymemory.json` is present in the project. |
| `fetch_microsoft_translator()` | `KeyError` | Unexpected API response structure. | Check Microsoft API documentation for schema changes. |
| `fetch_libretranslate()` | `KeyError` | Unexpected API response structure. | Check LibreTranslate API documentation for schema changes. |

---

## Thread Safety & Concurrency

| Concern | Status | Notes |
|---------|--------|-------|
| `load_cache()` | Generally safe | Read-only file access. Concurrent reads are safe. |
| `generate_cache()` | Not safe | Writes to `CACHE_FILE`. Concurrent calls may corrupt the file or cause race conditions. |
| `fetch_*` functions | Safe per call | Stateless HTTP requests. Safe for concurrent execution. |

**Recommendation:** Ensure only one thread or process calls `generate_cache()` at a time. Use a file lock or a singleton coordinator if running in a multi-worker environment.

---

## File Locations

| File | Purpose | Generated? |
|------|---------|------------|
| `languages_cache.json` | Unified provider language cache. | Yes — by `generate_cache()`. |
| `data/papago_mymemory.json` | Static language code lists for Papago and MyMemory. | No — maintained manually or by external tooling. |

---

## Changelog

| Version | Notes |
|---------|-------|
| 0.2.5 | Current — separates offline `load_cache()` from online `generate_cache()`, supports Microsoft Translator, LibreTranslate, Papago, and MyMemory. |
