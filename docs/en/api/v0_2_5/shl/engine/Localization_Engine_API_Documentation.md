# LocalizationEngine API Documentation

## Overview

`LocalizationEngine` is the central engine that unifies the Self-Healing Localization Layer (SHL). It manages UI localization through `Localizer`, AI prompt templates through `TemplateLocalizer`, ensures languages exist across both systems, provides optional GLFM language validation with fallback chains, smart translation routing with automatic fallback, and machine translation (only when enabled). It supports `.env` files for API keys and configuration.

---

## Module Metadata

| Field | Value |
|-------|-------|
| **File** | `core.py` |
| **Author** | Tuomas Lähteenmäki |
| **Version** | `0.2.5` |
| **License** | MIT |

---

## Dependencies and Imports

### Standard Library

- `logging`
- `os`
- `typing` (`Any`, `Callable`, `Dict`, `List`, `Optional`)
- `configparser` (imported inside methods)

### SHL Internal Modules

- `shl.engine.localizer.Localizer`
- `shl.engine.template_localizer.TemplateLocalizer`
- `shl.engine.translation.translate_text`
- `shl.engine.translation.TranslationCache`
- `shl.engine.translation.MyMemoryAdapter`
- `shl.engine.translation.LibreTranslateAdapter`
- `shl.engine.translation.TranslationError`
- `shl.engine.translation.ServiceUnavailableError`
- `shl.engine.translation.RateLimitExceededError`
- `shl.engine.translation.LanguageNotSupportedError`
- `shl.engine.translation.ProviderAccessError`
- `shl.engine.translation.InvalidRequestError`
- `shl.language_validator.LanguageValidator`
- `shl.utils.lang_utils.base_language`
- `shl.utils.lang_utils.normalize_full_tag`
- `shl.utils.env_loader.load_shl_env`
- `shl.utils.env_loader.get_env_value`
- `shl.config.config.get_cache_config`

---

## Class: `LocalizationEngine`

### Constructor

```python
LocalizationEngine(
    lang_code: Optional[str] = None,
    base_lang: Optional[str] = None,
    ui_folder: str = "locales",
    template_folder: str = "prompts",
    config: Optional[Dict[str, Any]] = None,
    glfm_path: Optional[str] = None,
    glfm_lite: bool = True,
    libretranslate_url: Optional[str] = None,
    libretranslate_api_key: Optional[str] = None,
    mymemory_email: Optional[str] = None,
    libretranslate_mirrors: Optional[List[Dict[str, Any]]] = None,
    deepl_key: Optional[str] = None,
    google_api_key: Optional[str] = None,
    google_backup_api_key: Optional[str] = None,
    papago_client_id: Optional[str] = None,
    papago_client_secret: Optional[str] = None,
)
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lang_code` | `Optional[str]` | `None` | Active language code. Auto-detected if not provided (in normal flow). |
| `base_lang` | `Optional[str]` | `None` | Base language code. Defaults to `"en"` or config value (in normal flow). |
| `ui_folder` | `str` | `"locales"` | Folder for UI localization files. |
| `template_folder` | `str` | `"prompts"` | Folder for template localization files. |
| `config` | `Optional[Dict[str, Any]]` | `None` | Override dictionary merged into default config. |
| `glfm_path` | `Optional[str]` | `None` | Path to the GLFM database file. |
| `glfm_lite` | `bool` | `True` | Whether to use GLFM lite mode. |
| `libretranslate_url` | `Optional[str]` | `None` | LibreTranslate base URL. |
| `libretranslate_api_key` | `Optional[str]` | `None` | LibreTranslate API key. |
| `mymemory_email` | `Optional[str]` | `None` | MyMemory email address. |
| `libretranslate_mirrors` | `Optional[List[Dict[str, Any]]]` | `None` | List of LibreTranslate mirror configurations. |
| `deepl_key` | `Optional[str]` | `None` | DeepL API key. |
| `google_api_key` | `Optional[str]` | `None` | Google Cloud Translation API key. |
| `google_backup_api_key` | `Optional[str]` | `None` | Google Cloud Translation backup API key. |
| `papago_client_id` | `Optional[str]` | `None` | Papago (Naver) client ID. |
| `papago_client_secret` | `Optional[str]` | `None` | Papago (Naver) client secret. |

#### Behavior

The constructor has **two distinct initialization paths**:

##### Path 1: SETTINGS Forced (config.conf override)

If `config.conf` exists and has a `[SETTINGS]` section with a `language` option:

1. Reads `language` and `base_lang` (fallback `"en"`) from `config.conf`.
2. Sets `self.lang_code = normalize_full_tag(forced_lang)`.
3. Sets `self.base_lang = base_language(forced_base)`.
4. **Disables GLFM completely** by passing `glfm_path=None` to `LanguageValidator`.
5. Sets `self.glfm_fallback = None` and `self.glfm_fallback_chain = []`.
6. Initializes folders, cache, adapters, and localizers.
7. Logs initialization as SETTINGS-forced and returns early.

##### Path 2: Normal Flow

1. Loads default config via `_load_default_config()` and merges the `config` parameter.
2. If `base_lang` is `None`, reads from config (default `"en"`).
3. If `lang_code` is `None`, calls `_detect_language()`.
4. Normalizes `lang_code` with `normalize_full_tag()` and `base_lang` with `base_language()`.
5. Initializes `LanguageValidator` with `glfm_path`, `base_language`, and `use_lite`.
6. Builds GLFM fallback chain if validator is loaded and language is valid.
7. Initializes cache, adapters (with API key resolution: parameter > `.env`), and localizers.
8. Logs initialization with GLFM mode.

#### API Key Resolution

For all API keys, the resolution order is **parameter > `.env` > default**:

| Attribute | Parameter | Environment Variable |
|-----------|-----------|---------------------|
| `_deepl_key` | `deepl_key` | `DEEPL_API_KEY` |
| `_google_api_key` | `google_api_key` | `GOOGLE_API_KEY` |
| `_google_backup_api_key` | `google_backup_api_key` | `GOOGLE_BACKUP_API_KEY` |
| `_papago_client_id` | `papago_client_id` | `NAVER_CLIENT_ID` |
| `_papago_client_secret` | `papago_client_secret` | `NAVER_CLIENT_SECRET` |
| `_mymemory_email` | `mymemory_email` | `MYMEMORY_EMAIL` |
| `_libretranslate_url` | `libretranslate_url` | `LIBRETRANSLATE_URL` |
| `_libretranslate_api_key` | `libretranslate_api_key` | `LIBRETRANSLATE_API_KEY` |

#### Instance Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `config` | `Dict[str, Any]` | Merged configuration dictionary. |
| `lang_code` | `str` | Normalized active language code. |
| `base_lang` | `str` | Normalized base language code. |
| `ui_folder` | `str` | UI localization folder path. |
| `template_folder` | `str` | Template localization folder path. |
| `validator` | `LanguageValidator` | GLFM language validator instance. |
| `glfm_fallback` | `Optional[str]` | The first fallback language from the GLFM chain (index 1), or `None`. |
| `glfm_fallback_chain` | `List[str]` | Full GLFM fallback chain for the active language. |
| `cache` | `TranslationCache` | Shared translation cache instance. |
| `mymemory_adapter` | `MyMemoryAdapter` | MyMemory translation adapter. |
| `libretranslate_adapter` | `LibreTranslateAdapter` | LibreTranslate translation adapter. |
| `ui_localizer` | `Localizer` | UI text localizer instance. |
| `template_localizer` | `TemplateLocalizer` | Template localizer instance. |
| `_deepl_key` | `Optional[str]` | Resolved DeepL API key. |
| `_google_api_key` | `Optional[str]` | Resolved Google API key. |
| `_google_backup_api_key` | `Optional[str]` | Resolved Google backup API key. |
| `_papago_client_id` | `Optional[str]` | Resolved Papago client ID. |
| `_papago_client_secret` | `Optional[str]` | Resolved Papago client secret. |
| `_libretranslate_url` | `Optional[str]` | Resolved LibreTranslate URL. |
| `_libretranslate_api_key` | `Optional[str]` | Resolved LibreTranslate API key. |
| `_mymemory_email` | `Optional[str]` | Resolved MyMemory email. |
| `_libretranslate_mirrors` | `Optional[List[Dict[str, Any]]]` | Mirror configurations. |

---

### Configuration

#### `_load_default_config() -> Dict[str, Any]`

Loads default configuration and `config.conf` values. This is an internal method.

##### Default Config

```python
{
    "m_translation_enabled": False,
    "translation_cache_ttl": 3600,
    "fallback_to_base": True,
    "strict_mode": False,
    "default_language": None,
    "glfm_lite": True,
    "cache": {
        "cache_persist": False,
        "cache_persist_path": ".shl_cache.json",
        "ttl": 3600,
        "max_size": 10000,
    },
}
```

##### config.conf Parsing

If `config.conf` exists, reads the `[SETTINGS]` section and overrides:

- `default_language` — from `language` option (stripped).
- `m_translation_enabled` — from `m_translation_enabled` option (boolean, default `False`).
- `fallback_to_base` — from `fallback_to_base` option (boolean, default `True`).
- `glfm_lite` — from `glfm_lite` option (boolean, default `True`).
- `base_lang` — from `base_lang` option (stripped).

Catches all exceptions during config reading and logs a debug message.

---

### Language Detection

#### `_detect_language() -> str`

Detects the active language using the following priority:

1. `self.config.get("default_language")` — if set, returns it.
2. `os.environ.get("SHL_LANGUAGE")` — if set, returns it.
3. `os.environ.get("LANG", "")` — if set:
   - Splits on `.` and takes the first part.
   - If contains `_`, splits into two parts and returns `{lang.lower()}-{region.upper()}`.
   - Otherwise returns the lowercased value.
4. Falls back to `"en"`.

---

### Key Validation

#### `_validate_key(key: str) -> str`

Validates and normalizes a localization key.

##### Behavior

- If `key` is not a `str`, logs a warning and returns `""`.
- Strips whitespace from `key`.
- If empty after stripping, logs a debug message and returns `""`.
- If normalization changed the key, logs a debug message.
- Returns the normalized key.

---

### Language Management

#### `ensure_language(lang_code: str) -> None`

Ensures UI and template files exist for the given language.

##### Behavior

- Normalizes `lang_code` via `normalize_full_tag()`.
- Instantiates `Localizer` and `TemplateLocalizer` with the validated language code, `self.base_lang`, and respective folders.
- Logs the operation at debug level.

---

#### `set_language(lang_code: str) -> None`

Switches the active language.

##### Behavior

- Normalizes `lang_code` via `normalize_full_tag()`.
- Updates `self.lang_code`.
- Calls `set_language()` on both `ui_localizer` and `template_localizer`.
- If `self.validator.is_loaded` is `True`, rebuilds `self.glfm_fallback_chain` via `validator.get_fallback_chain()`.
  - If the chain has more than 1 element, sets `self.glfm_fallback` to the second element (index 1).
  - Otherwise sets `self.glfm_fallback` to `None`.
- Logs the language switch at info level.

---

### Key Management

#### `ensure_ui_key(key: str, default: str = "") -> str`

Ensures a UI key exists.

##### Behavior

1. Validates the key via `_validate_key()`.
2. If invalid, returns `""`.
3. Retrieves the text via `_get_with_fallback(self.ui_localizer.get_text, validated_key)`.
4. If the text is `None` or empty, sets the key to `default` via `ui_localizer.set_text()` and returns `default`.
5. Otherwise returns the retrieved text.

---

#### `ensure_template_key(key: str, default: str = "") -> str`

Ensures a template key exists.

##### Behavior

Identical to `ensure_ui_key()` but uses `self.template_localizer.get_template` and `set_template()`.

---

### Fallback Retrieval

#### `_get_with_fallback(getter, key) -> Optional[str]`

Retrieves a key through the fallback chain. This is an internal method.

##### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `getter` | `Callable[[str, Optional[str], bool], Optional[str]]` | A getter function (e.g., `ui_localizer.get_text`). |
| `key` | `str` | The localization key. |

##### Fallback Order

1. **Active language** — Always checked first via `getter(key, self.lang_code, fallback=False)`.
2. **Fallback disabled** — If `self.config.get("fallback_to_base", True)` is `False`, returns `None`.
3. **GLFM fallback chain** — If `self.glfm_fallback_chain` has more than 1 element, iterates from index 1 onward, skipping `self.lang_code`. Calls `getter(key, fallback_lang, fallback=False)` for each.
4. **Base language** — If `self.lang_code != self.base_lang`, calls `getter(key, self.base_lang, fallback=False)`.
5. Returns `None` if nothing is found.

---

### Retrieval

#### `ui_text(key: str, default_value: str = "") -> str`

Retrieves UI text with fallback and optional machine translation.

##### Behavior

1. Validates the key via `_validate_key()`.
2. If invalid, returns `default_value`.
3. Checks the translation cache via `self.cache.get(validated_key, self.base_lang, self.lang_code)`.
   - If cached, returns the cached value.
4. Retrieves text via `_get_with_fallback(self.ui_localizer.get_text, validated_key)`.
5. If text is `None`:
   - If `m_translation_enabled` is `True`, `lang_code != base_lang`, and `default_value` is truthy:
     - Calls `translate_text()` with all resolved API keys.
     - If translation succeeds and differs from `default_value`, stores it via `ui_localizer.set_text()` and `cache.set()`, then returns it.
     - Catches all exceptions, logs a warning.
   - Stores `default_value` via `ui_localizer.set_text()` and `cache.set()`, then returns `default_value`.
6. If text is found, stores it in cache and returns it.

---

#### `template(key: str, default: str = "", **kwargs: Any) -> str`

Retrieves and formats a prompt template.

##### Behavior

1. Validates the key via `_validate_key()`.
2. If invalid, returns `default if default else key`.
3. Retrieves text via `_get_with_fallback(self.template_localizer.get_template, validated_key)`.
4. If text is `None`, uses `default if default else key`, stores it via `template_localizer.set_template()`, and uses that value.
5. If `kwargs` is provided, attempts `text.format(**kwargs)`.
   - On `KeyError` or `ValueError`, logs a warning and returns the unformatted text.
6. Returns the (formatted) text.

---

### Synchronization

#### `_sync_from_lang(source_lang: str) -> int`

Synchronizes keys from a source language. This is an internal method.

##### Behavior

- If `source_lang == self.lang_code`, returns `0`.
- Instantiates a new `Localizer` and `TemplateLocalizer` for `source_lang`.
- Iterates over `source_ui.texts.items()`:
  - Validates each key.
  - If the key does not exist in `self.ui_localizer.texts`, copies it via `set_text()`.
  - Counts copied keys.
- Iterates over `source_templates.templates.items()`:
  - Validates each key.
  - If the key does not exist in `self.template_localizer.templates`, copies it via `set_template()`.
  - Counts copied keys.
- Logs the sync count at debug level.
- Returns the total count of synchronized keys.

---

#### `sync() -> int`

Synchronizes keys from fallback and base languages.

##### Behavior

1. If `self.glfm_fallback_chain` has more than 1 element, iterates from index 1 and syncs from each fallback language (skipping `self.lang_code`).
2. If `self.base_lang != self.lang_code`, syncs from base language.
3. Logs the result at info level.
4. Returns the total count of synchronized keys.

---

### Statistics

#### `get_stats() -> Dict[str, Any]`

Returns engine statistics.

##### Returns

- `Dict[str, Any]` with the following keys:
  - `"lang_code"`: `self.lang_code`
  - `"base_lang"`: `self.base_lang`
  - `"glfm_fallback"`: `self.glfm_fallback`
  - `"glfm_fallback_chain"`: `self.glfm_fallback_chain.copy()`
  - `"glfm_lite"`: `self.validator.is_lite` if validator else `True`
  - `"glfm_loaded"`: `self.validator.is_loaded` if validator else `False`
  - `"ui_keys_count"`: `len(self.ui_localizer.texts)`
  - `"template_keys_count"`: `len(self.template_localizer.templates)`
  - `"cache_size"`: `self.cache.size()`
  - `"m_translation_enabled"`: `self.config.get("m_translation_enabled", False)`
  - `"config"`: `self.config.copy()`
  - `"deepl_key_configured"`: `bool(self._deepl_key)`
  - `"google_api_key_configured"`: `bool(self._google_api_key)`
  - `"papago_configured"`: `bool(self._papago_client_id and self._papago_client_secret)`

---

### LibreTranslate Mirror Methods

#### `get_mirror_stats() -> List[Dict[str, Any]]`

Returns LibreTranslate mirror statistics.

##### Returns

- `List[Dict[str, Any]]` — Delegates to `self.libretranslate_adapter.get_mirror_stats()`.

---

#### `clear_mirror_cache() -> None`

Clears the LibreTranslate mirror cache.

##### Behavior

- Delegates to `self.libretranslate_adapter.clear_mirror_cache()`.

---

### GLFM Management

#### `reload_glfm(glfm_path: Optional[str] = None, glfm_lite: Optional[bool] = None) -> bool`

Reloads the GLFM database.

##### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `glfm_path` | `Optional[str]` | `None` | New path to the GLFM database. |
| `glfm_lite` | `Optional[bool]` | `None` | Whether to use lite mode. Defaults to `self.config.get("glfm_lite", True)`. |

##### Behavior

1. Creates a new `LanguageValidator` with the given parameters.
2. If `validator.is_loaded` is `False`:
   - Sets `self.glfm_fallback = None` and `self.glfm_fallback_chain = []`.
   - Logs a warning and returns `False`.
3. Otherwise, rebuilds `self.glfm_fallback_chain` via `validator.get_fallback_chain()`.
   - If the chain has more than 1 element, sets `self.glfm_fallback` to index 1.
   - Otherwise sets it to `None`.
4. Logs the reload result with the language count.
5. Returns `True`.

---

## Usage Example

```python
from shl.engine.core import LocalizationEngine

# Initialize engine
engine = LocalizationEngine(
    lang_code="fi",
    base_lang="en",
    ui_folder="locales",
    template_folder="prompts",
    deepl_key="your-deepl-key",
)

# Retrieve UI text
text = engine.ui_text("greeting", default_value="Hello")

# Retrieve and format template
prompt = engine.template("summarize", default="Summarize: {text}", text="Article content")

# Ensure keys exist
engine.ensure_ui_key("new_key", default="Default text")
engine.ensure_template_key("new_template", default="Template text")

# Switch language
engine.set_language("sv")

# Sync keys from fallback and base languages
synced = engine.sync()
print(f"Synced {synced} keys")

# Get statistics
stats = engine.get_stats()
print(stats)

# Reload GLFM
success = engine.reload_glfm(glfm_path="/path/to/glfm.db")

# Clear mirror cache
engine.clear_mirror_cache()
```

---

## Version

**Module version:** `0.2.5`

**Author:** Tuomas Lähteenmäki

**License:** MIT
