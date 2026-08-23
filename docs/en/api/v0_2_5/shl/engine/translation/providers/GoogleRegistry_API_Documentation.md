# GoogleRegistry API Documentation

## Overview

`GoogleRegistry` manages localized language validation and runtime learning for unsupported Google Cloud Translation language pairs. It uses ISO 639-1 / BCP-47 standard language code mapping to avoid wasteful network API calls by maintaining a local blacklist of known-failing pairs.

---

## Module Constants

### `STANDARD_ISO_CODES_RAW`

```python
STANDARD_ISO_CODES_RAW: frozenset[str]
```

A frozen set of Google Cloud Translation language codes used for fast pre-validation before making a network request. The Google API remains the final authority for actual support.

Contains the following codes:

```
af, am, ar, az, be, bg, bn, bs, ca, ceb, co, cs, cy, da, de, el, en, eo, es, et,
eu, fa, fi, fr, fy, ga, gd, gl, gu, ha, haw, he, hi, hmn, hr, ht, hu, hy, id, ig,
is, it, ja, jv, ka, kk, km, kn, ko, ku, ky, la, lb, lo, lt, lv, mg, mi, mk, ml,
mn, mr, ms, mt, my, ne, nl, no, ny, or, pa, pl, ps, pt, pt-BR, pt-PT, ro, ru,
rw, sd, si, sk, sl, sm, sn, so, sq, sr, st, su, sv, sw, ta, te, tg, th, tk, tl,
tr, tt, ug, uk, ur, uz, vi, xh, yi, yo, zh, zh-CN, zh-TW, zu
```

### `STANDARD_ISO_CODES`

```python
STANDARD_ISO_CODES: frozenset[str]
```

A lowercased version of `STANDARD_ISO_CODES_RAW`. All lookups against this set are case-insensitive.

---

## Class: `GoogleRegistry`

Handles runtime language pair support tracking and blacklisting for Google Cloud Translation.

### Constructor

```python
GoogleRegistry(cache_ttl: float = 86400.0)
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cache_ttl` | `float` | `86400.0` | Time-to-live in seconds for blacklisted language pairs. Default is 24 hours. |

#### Instance Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `_unsupported_pairs_cache` | `Dict[Tuple[str, str], float]` | Dynamic memory cache mapping `(source, target)` pairs to expiry timestamps. |
| `cache_ttl` | `float` | The TTL value passed to the constructor. |

---

### Methods

#### `is_pair_supported(source_lang: str, target_lang: str) -> bool`

Validates if the language pair is supported using local ISO codes and the runtime error blacklist. Zero network overhead.

##### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `source_lang` | `str` | Source language code (ISO 639-1 / BCP-47). |
| `target_lang` | `str` | Target language code (ISO 639-1 / BCP-47). |

##### Behavior

1. Strips whitespace and lowercases both `source_lang` and `target_lang`.
2. Checks if the pair `(src, tgt)` exists in `_unsupported_pairs_cache`.
   - If found and the current time is before the expiry timestamp, returns `False` and logs a debug message.
   - If found but TTL has expired, removes the pair from the cache to allow re-testing.
3. Returns `True` only if **both** the source and target language codes are present in `STANDARD_ISO_CODES`.

##### Returns

- `bool` — `True` if the pair is considered supported locally; `False` otherwise.

---

#### `mark_pair_unsupported(source_lang: str, target_lang: str) -> None`

Blacklists an unmappable language pair for the duration of the TTL.

##### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `source_lang` | `str` | Source language code. |
| `target_lang` | `str` | Target language code. |

##### Behavior

- Strips whitespace and lowercases both inputs.
- Stores the pair in `_unsupported_pairs_cache` with an expiry timestamp of `time.time() + self.cache_ttl`.
- Logs a warning message indicating the pair has been blacklisted and for how long.

---

#### `clear_blacklist() -> None`

Resets the runtime tracking cache.

##### Behavior

- Clears all entries from `_unsupported_pairs_cache`.

---

## Dependencies and Imports

### Standard Library

- `time`
- `logging`
- `typing` (`Dict`, `Tuple`)

---

## Usage Example

```python
from shl.providers.google_registry import GoogleRegistry

# Initialize with default 24-hour TTL
registry = GoogleRegistry()

# Check if a language pair is supported
if registry.is_pair_supported("en", "fi"):
    print("Pair is supported locally.")
else:
    print("Pair is blacklisted or not in the known code set.")

# Blacklist a pair after an API failure
registry.mark_pair_unsupported("xx", "yy")

# Later, clear all blacklisted pairs
registry.clear_blacklist()
```

---

## Blacklist TTL Behavior

- When `is_pair_supported()` encounters a blacklisted pair whose TTL has expired, the pair is **automatically evicted** from the cache and the check proceeds to the ISO code validation step.
- This allows pairs to be re-tested after the TTL period without manual intervention.

---

## License

MIT

## Author

Tuomas Lähteenmäki
