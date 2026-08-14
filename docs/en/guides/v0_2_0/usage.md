# Usage Guide

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

## Engine Initialization & Synchronization

### Region Subtag Support
SHL supports BCP-47 language tags with region subtags, allowing you to target specific locales.

```python
from shl.engine.core import LocalizationEngine

# Uses pt-br.json
engine_br = LocalizationEngine(lang_code="pt-BR")

# Uses pt-pt.json
engine_pt = LocalizationEngine(lang_code="pt-PT")
```

### Synchronize All Languages
Synchronize all localization keys from the fallback chain to the current language.

```python
engine_br.sync()
```

## GLFM Configuration & Data Modes
Both GLFM modes contain language data for all 7,900+ languages. The difference is the amount of fallback information stored for each language.

| Mode | File | Size packed | Unpacked | Fallback data |
| :--- | :--- | :---: | :---: | :--- |
| **Lite (default)** | `languages_top20.json.gz` | ~428 KB | 9.2 MB | Up to 20 fallback candidates per language |
| **Full** | `unified_languages.json.gz` | ~51.6 MB | 924.7 MB | Complete fallback information |


### 1. Default Mode (GLFM Lite)
GLFM Lite is active by default and lightweight.

```python
from shl.engine.core import LocalizationEngine

engine = LocalizationEngine(
    lang_code="fi",
    glfm_lite=True,  # Default behavior
)
```

### 2. Advanced Configuration (GLFM Full & Custom Path)
> **⚠️ Production Note:**  The Full data mode unpacks to nearly 1 GB. It is strictly recommended for AI applications, NLP data centers, backend services, or heavy data-science pipelines where complete linguistic fallback accuracy is required. For desktop or standard consumer applications, always use the default Lite mode.

Configure the engine to use the full dataset or point it to a specific custom GLFM file.

```python
from shl.engine.core import LocalizationEngine

# Load full fallback data from a custom path
engine = LocalizationEngine(
    lang_code="fi",
    glfm_lite=False,
    glfm_path="/path/to/your/glfm.json.gz",
)
```

### 3. GLFM Language Validation & Stats
You can inspect the engine's state and validate the loaded GLFM setup using `get_stats()`.

```python
stats = engine.get_stats()

print(stats["glfm_loaded"])    # True if GLFM data is available
print(stats["glfm_lite"])      # True when GLFM Lite is active, False if Full
print(stats["lang_code"])      # fi
print(stats["glfm_fallback"])  # en or another GLFM fallback language
```

