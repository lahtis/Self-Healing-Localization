## `doc/api/engine.md`

# LocalizationEngine API

## Initialization

```python
engine = LocalizationEngine(
    lang_code=None,          # None = auto-detect
    base_lang=None,          # None = from config.conf, fallback "en"
    ui_folder="locales",
    template_folder="prompts",
    config=None,
    glfm_path=None,
    glfm_lite=True,
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
| `ui_text(key, default="")` | Retrieve UI text with self-healing. |
| `template(key, default="", **kwargs)` | Retrieve a prompt template. |
| `set_language(lang_code)` | Switch the active language dynamically. |
| `ensure_language(lang_code)` | Ensure that language files exist. |
| `sync()` | Synchronize all localization keys. |
| `get_stats()` | Return engine statistics. |
| `reload_glfm(glfm_path, glfm_lite)` | Reload the GLFM database. |
| `get_mirror_stats()` | Return LibreTranslate mirror statistics. |
| `clear_mirror_cache()` | Clear the LibreTranslate mirror cache. |

---
