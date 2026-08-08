## `doc/guides/usage.md`

# Usage Guide

## Synchronize All Languages

Synchronize all localization keys from the fallback chain to the current
language.

```python
engine.sync()
```

---

## GLFM Language Validation

```python
from shl.engine.core import LocalizationEngine

engine = LocalizationEngine(lang_code="fi")

stats = engine.get_stats()

print(stats["glfm_loaded"])    # True if GLFM data is available
print(stats["glfm_lite"])      # True when GLFM Lite is active
print(stats["lang_code"])      # fi
print(stats["glfm_fallback"])  # en or another GLFM fallback language
```

---

## GLFM Lite

GLFM Lite is the default mode.

```python
from shl.engine.core import LocalizationEngine

engine = LocalizationEngine(
    lang_code="fi",
    glfm_lite=True,
)

stats = engine.get_stats()

print(stats["glfm_loaded"])    # True if GLFM data is available
print(stats["glfm_lite"])      # True
print(stats["lang_code"])      # fi
print(stats["glfm_fallback"])  # en or another GLFM fallback language
```

---

## GLFM Full

Use GLFM Full when complete fallback information is required.

```python
from shl.engine.core import LocalizationEngine

engine = LocalizationEngine(
    lang_code="fi",
    glfm_lite=False,
)
```

---

## Custom GLFM Path

Use a custom path to load a specific GLFM data file.

```python
from shl.engine.core import LocalizationEngine

engine = LocalizationEngine(
    lang_code="fi",
    glfm_path="/path/to/your/glfm.json.gz",
)
```

---

## Language Data Modes

Both modes contain language data for all 7,900+ languages. The difference is
the amount of fallback information stored for each language.

| Mode | File | Size | Fallback data |
|---|---|---:|---|
| **Lite (default)** | `languages_top20.json.gz` | ~428 KB | Up to 20 fallback candidates per language |
| **Full** | `unified_languages.json.gz` | ~925 MB | Complete fallback information |

---

## Direct Translation

Use `translate_text()` for direct translation with smart provider routing.

```python
from shl.engine.translation import translate_text

result = translate_text(
    "Hello world",
    target_lang="fi",
)

print(result)  # "Hei maailma"
```

---

## Region Subtag Support

SHL supports BCP-47 language tags with region subtags.

```python
from shl.engine.core import LocalizationEngine

engine = LocalizationEngine(
    lang_code="pt-BR",
)
# Uses pt-br.json

engine = LocalizationEngine(
    lang_code="pt-PT",
)
# Uses pt-pt.json
```

---

## Translation Services

| Service | Role | Limits | Notes |
|---|---|---|---|
| MyMemory | Primary provider | 1,000 characters per day, or 30,000 with an email address | Translation memory with machine-translation fallback |
| LibreTranslate | Fallback provider | Public instances are rate-limited | Open-source machine-translation service |

Both services can be used without an API key. API keys and service-specific
configuration can be provided through environment variables or a `.env` file.
