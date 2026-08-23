# MyMemoryRegistry API Documentation

## Overview

`MyMemoryRegistry` manages localized language validation and runtime learning for unsupported MyMemory language pairs. It uses a complete ISO / regional language code mapping to avoid wasteful network API calls by maintaining a local blacklist of known-failing pairs.

---

## Module Constants

### `STANDARD_ISO_CODES`

```python
STANDARD_ISO_CODES: frozenset[str]
```

A frozen set of language codes supported by MyMemory. The frozenset is explicitly immutable and more performant than a standard set.

Contains the following codes:

```
af, sq, ar, hy, az, eu, be, bn, bs, bg, ca, ceb, zh-cn, zh-tw, hr, cs, da,
nl, en, eo, et, tl, fi, fr, gl, ka, de, el, gu, ht, ha, he, hi, hmn, hu, is,
ig, id, ga, it, ja, jw, kn, kk, km, ko, ku, ky, lo, la, lv, lt, lb, mk, mg,
ms, ml, mt, mi, mr, mn, my, ne, no, ny, ps, fa, pl, pt, pt-br, pa, ro, ru,
sm, gd, sr, st, sn, sd, si, sk, sl, so, es, su, sw, sv, tg, ta, te, th, tr,
uk, ur, uz, vi, cy, xh, yi, yo, zu
```

---

## Class: `MyMemoryRegistry`

Handles runtime language pair support tracking and blacklisting for MyMemory.

### Constructor

```python
MyMemoryRegistry(cache_ttl: float = 86400.0)
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
| `source_lang` | `str` | Source language code. |
| `target_lang` | `str` | Target language code. |

##### Behavior

1. Lowercases and strips whitespace from both `source_lang` and `target_lang`.
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

- Lowercases and strips whitespace from both inputs.
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
from shl.providers.mymemory_registry import MyMemoryRegistry

# Initialize with default 24-hour TTL
registry = MyMemoryRegistry()

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
