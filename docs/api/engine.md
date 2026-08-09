# LocalizationEngine API

## Initialization

```python
from shl.engine.core import LocalizationEngine

engine = LocalizationEngine(
    lang_code=None,                # None = auto-detect (config.conf / ENV / "en")
    base_lang=None,                # None = from config.conf, fallback "en"
    ui_folder="locales",
    template_folder="prompts",
    m_translation_enabled=False,   # Enable automatic machine translation
    config=None,
    glfm_path=None,
    glfm_lite=True,                # True = 9.2 MB Lite mode, False = Full mode
    libretranslate_url=None,
    libretranslate_api_key=None,
    mymemory_email=None,
    libretranslate_mirrors=None,
)
```
---

## Methods

| Method | Description |
|---|---|
| `ui_text(key, default="")` | Retrieve UI text with automatic self-healing and translation fallback. |
| `template(key, default="", **kwargs)` | Retrieve or translate a prompt template, populating optional {variables}. |
| `set_language(lang_code)` | Switch the active target language dynamically at runtime. |
| `ensure_language(lang_code)` | Ensure that language files and structural fallbacks exist for the target language. |
| `sync()` | Synchronize all localization keys across all languages in the fallback chain. |
| `get_stats()` | Return engine statistics (loaded language, GLFM status, mode). |
| `reload_glfm(glfm_path, glfm_lite)` | Reload or switch the active GLFM database dynamically. |
| `get_mirror_stats()` | Return LibreTranslate mirror availability and latency statistics. |
| `clear_mirror_cache()` | Clear cached LibreTranslate mirror statuses. |

---
