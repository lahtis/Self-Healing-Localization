# LibreTranslateRegistry API Documentation

## Overview

`LibreTranslateRegistry` manages localized language validation and runtime learning for unsupported LibreTranslate language pairs. It uses a strict Argos OpenNMT index mapping (including codes such as `pb`, `zh`, `zt`) to avoid wasteful network API calls by maintaining a local blacklist of known-failing pairs.

---

## Module Constants

### `STANDARD_ISO_CODES`

```python
STANDARD_ISO_CODES: frozenset[str]
```

A frozen set of language codes officially supported by standard LibreTranslate instances. Strictly matches the official argosmin-index constraints.

Contains the following codes:

```
ar, az, bg, bn, ca, cs, da, de, el, en, eo, es, et, eu, fa, fi, fr, ga, gl,
he, hi, hu, id, it, ja, ko, ky, lt, lv, ms, nb, nl, pb, pl, pt, ro, ru, sk,
sl, sq, sv, th, tl, tr, uk, ur, vi, zh, zt
```

---

## Class: `LibreTranslateRegistry`

Handles runtime language pair support tracking and blacklisting for LibreTranslate.

### Constructor

```python
LibreTranslateRegistry(cache_ttl: float = 86400.0)
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
from shl.providers.libretranslate_registry import LibreTranslateRegistry

# Initialize with default 24-hour TTL
registry = LibreTranslateRegistry()

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
