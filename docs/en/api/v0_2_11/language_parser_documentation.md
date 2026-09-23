# `language_parser.py` — Technical Documentation

| Field | Value |
|---|---|
| File | `shl/language_parser.py` |
| Author | Tuomas Lähteenmäki |
| License | MIT |
| Version | 0.2.11 |

## Overview

`language_parser.py` implements SHL's language resolution layer. It takes a
user-supplied language identifier (name, ISO 639-1, ISO 639-3, BCP 47, or a
GLFM identifier) and resolves it into SHL's canonical internal identity
(ISO 639-3), and optionally into a provider-native language code via a
locally cached provider language table.

Resolution pipeline:

```
User input
    ↓
GLFM
    ↓
ISO 639-3
    ↓
Provider language cache
    ↓
Provider-native code
```

The module does not hard-code any provider-specific aliases. All provider
matching is derived from the GLFM-resolved identity plus whatever codes are
present in the provider cache file.

## Class Under Test

### `ParsedLanguage`

A plain data container returned by `LanguageParser.parse()`.

```python
class ParsedLanguage:
    def __init__(
        self,
        input_value: str,
        iso639_3: str,
        bcp47: Optional[str],
        input_bcp47: Optional[str],
        script: Optional[str],
        region: Optional[str],
        name: Optional[str],
        glfm_info: Dict[str, Any],
    ) -> None: ...
```

| Attribute | Type | Description |
|---|---|---|
| `input` | `str` | The raw string passed to `parse()` |
| `iso639_3` | `str` | Canonical SHL language identity (lowercase) |
| `bcp47` | `Optional[str]` | GLFM-provided BCP 47 tag for the language |
| `input_bcp47` | `Optional[str]` | Normalized form of the input, if it parsed as BCP 47 |
| `script` | `Optional[str]` | Script subtag from the input, title-cased |
| `region` | `Optional[str]` | Region subtag from the input, upper-cased |
| `name` | `Optional[str]` | Human-readable language name from GLFM |
| `glfm_info` | `Dict[str, Any]` | Raw GLFM record used for resolution |

### `LanguageParser`

```python
class LanguageParser:
    DEFAULT_CACHE_FILENAME = ".languages_cache.json"

    def __init__(
        self,
        validator: Optional[LanguageValidator] = None,
        cache_path: Optional[str | Path] = None,
    ) -> None: ...
```

| Method | Signature | Purpose |
|---|---|---|
| `parse` | `parse(language: str) -> ParsedLanguage` | Resolves any accepted input form through GLFM |
| `normalize` | `normalize(language: str) -> str` | Shortcut returning only the canonical ISO 639-3 code |
| `get_bcp47` | `get_bcp47(language: str) -> Optional[str]` | Shortcut returning only the GLFM BCP 47 tag |
| `load_provider_cache` | `load_provider_cache() -> Dict[str, Any]` | Loads and memoizes the provider language cache JSON |
| `get_provider_code` | `get_provider_code(language: str, provider: str) -> Optional[str]` | Resolves a language to a provider-native code |
| `_find_best_provider_match` | `_find_best_provider_match(language, supported_codes) -> Optional[str]` | Internal 7-tier matching ladder (private) |
| `_find_case_insensitive` | `_find_case_insensitive(value, candidates) -> Optional[str]` | Static case-insensitive lookup helper (private) |

The provider-matching ladder in `_find_best_provider_match`, in priority
order:

1. Exact match on the input's explicit BCP 47 form (when script/region given)
2. Exact script+region match, then region-only match, then script-only match
3. Exact GLFM BCP 47 match
4. Exact ISO 639-1 match (if GLFM supplies one)
5. Exact ISO 639-3 match
6. Exact match on the BCP 47 base language subtag
7. Prefix match on the BCP 47 base language subtag

## Test Cases

The scenarios below describe the expected behavior of each public method and
are suitable as a basis for a unit test suite.

| # | Method | Input | Expected Result |
|---|---|---|---|
| 1 | `parse` | Valid language name, e.g. `"Finnish"` | Returns `ParsedLanguage` with `iso639_3="fin"` and populated `bcp47`/`name` |
| 2 | `parse` | Valid ISO 639-1 code, e.g. `"fi"` | Resolves to the same canonical `iso639_3` as the full name |
| 3 | `parse` | Valid BCP 47 tag with region, e.g. `"pt-BR"` | `input_bcp47="pt-BR"`, `region="BR"` set |
| 4 | `parse` | Valid BCP 47 tag with script, e.g. `"zh-Hant"` | `script="Hant"` set (title-cased) |
| 5 | `parse` | Unknown identifier, e.g. `"xx-not-a-language"` | Raises `ValueError` |
| 6 | `parse` | Non-string input, e.g. `42` | Raises `TypeError` |
| 7 | `parse` | Empty or whitespace-only string | Raises `ValueError` |
| 8 | `parse` | GLFM record missing `iso639_3` | Raises `ValueError` |
| 9 | `normalize` | Any valid input | Returns only the `iso639_3` string |
| 10 | `get_bcp47` | Any valid input | Returns only the `bcp47` string (or `None`) |
| 11 | `load_provider_cache` | Cache file missing | Returns `{"providers": {}, "last_updated": None}`, logs a warning |
| 12 | `load_provider_cache` | Cache file contains invalid JSON | Returns empty default structure, logs a warning |
| 13 | `load_provider_cache` | Cache file is valid but not a JSON object | Returns empty default structure, logs a warning |
| 14 | `load_provider_cache` | Called twice | Second call returns the memoized in-memory result (no re-read) |
| 15 | `get_provider_code` | Provider not present in cache (case-insensitive) | Returns `None` |
| 16 | `get_provider_code` | Provider value is neither `dict` nor `list` | Returns `None` |
| 17 | `get_provider_code` | Input matches a provider code exactly by script+region | Returns that exact provider code |
| 18 | `get_provider_code` | Input matches only by region (e.g. Papago-style regional codes) | Returns the region-matched provider code |
| 19 | `get_provider_code` | No script/region given, exact BCP 47 present in provider codes | Returns the BCP 47-matched code |
| 20 | `get_provider_code` | No BCP 47 match, ISO 639-1 present in provider codes | Returns the ISO 639-1-matched code |
| 21 | `get_provider_code` | No higher-tier match, ISO 639-3 present in provider codes | Returns the ISO 639-3-matched code |
| 22 | `get_provider_code` | Provider codes only contain a base-language prefix match | Returns the prefix-matched code |
| 23 | `get_provider_code` | No match found at any tier | Returns `None`, logs a debug message |
| 24 | `_find_case_insensitive` | Candidate present with differing case | Returns the candidate in its originally stored form |

## Error Handling

| Condition | Exception / Behavior | Raised By |
|---|---|---|
| `language` argument is not a `str` | `TypeError("Language identifier must be a string.")` | `parse` |
| `language` is empty after stripping | `ValueError("Language identifier cannot be empty.")` | `parse` |
| GLFM has no record for the input | `ValueError(f"Unknown language identifier: {language}")` | `parse` |
| GLFM record lacks an `iso639_3` field | `ValueError(f"GLFM record does not contain ISO 639-3 code: {language}")` | `parse` |
| Provider cache file does not exist | Logged as `warning`; falls back to an empty cache structure (no exception) | `load_provider_cache` |
| Provider cache file is unreadable or malformed JSON | `OSError` / `json.JSONDecodeError` caught internally, logged as `warning`; falls back to an empty cache structure | `load_provider_cache` |
| Provider cache JSON root is not an object | Logged as `warning`; falls back to an empty cache structure | `load_provider_cache` |
| Requested provider is not in the cache | Logged as `debug`; returns `None` (no exception) | `get_provider_code` |
| No provider code matches at any tier | Logged as `debug`; returns `None` (no exception) | `_find_best_provider_match` |

All cache-related failures are handled defensively and never propagate as
exceptions — they degrade to an empty cache plus a log entry. Only
`parse()` raises exceptions, and only for malformed or unresolvable input.

## Summary

`LanguageParser` is the single entry point SHL uses to turn arbitrary
user-facing language identifiers into two things: a stable internal
identity (ISO 639-3, via GLFM) and, optionally, a provider-specific code
looked up from a local cache. Input validation is strict (`TypeError` /
`ValueError` on bad input), while provider-cache handling is
fault-tolerant and never raises — a missing or corrupt cache simply yields
no provider match. The provider-matching logic favors the most specific
available signal (explicit script/region) before falling back through
BCP 47, ISO 639-1, ISO 639-3, and finally a bare language-prefix match.
