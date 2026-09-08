# LocalizationEngine API Documentation

## Overview

`LocalizationEngine` is the high-level localization engine for the Self-Healing Localization Layer (SHL). It manages UI text and AI prompt templates through `Localizer` and `TemplateLocalizer`, validates and normalizes language codes, manages GLFM language fallback chains, synchronizes localized keys and templates, and provides optional machine translation through the translation subsystem.

Translation providers, provider failover, provider policies, retries, provider registries, and translation caching are handled by the translation subsystem rather than by this class.

---

## Module Metadata

| Field | Value |
|-------|-------|
| **File** | `core.py` |
| **Author** | Tuomas Lähteenmäki |
| **Version** | `0.2.10` |
| **License** | MIT |

---

## Dependencies and Imports

### Standard Library

- `logging`
- `os`
- `typing` (`Any`, `Dict`, `List`, `Optional`)

### SHL Internal Modules

- `shl.engine.localizer.Localizer`
- `shl.engine.template_localizer.TemplateLocalizer`
- `shl.engine.translation.translate_text`
- `shl.language_validator.LanguageValidator`
- `shl.utils.lang_utils.base_language`
- `shl.utils.lang_utils.normalize_full_tag`
- `shl.utils.env_loader.get_env_value`
- `shl.utils.env_loader.load_shl_env`

---

## Class: `LocalizationEngine`

### Constructor

```python
LocalizationEngine(
    lang_code: Optional[str] = None,
    base_lang: str = "en",
    ui_folder: str = "locales",
    template_folder: str = "prompts",
    config: Optional[Dict[str, Any]] = None,
    glfm_path: Optional[str] = None,
    glfm_lite: Optional[bool] = None,
) -> None
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lang_code` | `Optional[str]` | `None` | Active language code. Auto-detected if not provided. |
| `base_lang` | `str` | `"en"` | Base language code. |
| `ui_folder` | `str` | `"locales"` | Folder for UI localization files. |
| `template_folder` | `str` | `"prompts"` | Folder for template localization files. |
| `config` | `Optional[Dict[str, Any]]` | `None` | Override dictionary merged into default config. |
| `glfm_path` | `Optional[str]` | `None` | Path to the GLFM database file. |
| `glfm_lite` | `Optional[bool]` | `None` | Whether to use GLFM lite mode. Passed to `LanguageValidator`. |

#### Behavior

1. Calls `load_shl_env()` to load environment variables.
2. Builds configuration via `_build_config(config)`.
3. Stores `ui_folder` and `template_folder`.
4. Normalizes `base_lang` via `base_language()`.
5. Detects or selects the active language:
   - Uses `lang_code` parameter if provided.
   - Falls back to `config.get("language")`.
   - Falls back to `_detect_language()`.
6. Normalizes `lang_code` via `normalize_full_tag()`.
7. Reads `fallback_to_base` and `m_translation_enabled` from config as booleans.
8. Initializes `LanguageValidator(glfm_path)`.
9. Calls `_validate_language()` to validate against GLFM.
10. Calls `_build_fallback_chain()` to build the GLFM fallback list.
11. Initializes `ui_localizer` and `template_localizer`.
12. Logs initialization with `lang_code` and `base_lang`.

#### Instance Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `config` | `Dict[str, Any]` | Merged configuration dictionary. |
| `ui_folder` | `str` | UI localization folder path. |
| `template_folder` | `str` | Template localization folder path. |
| `base_lang` | `str` | Normalized base language code. |
| `lang_code` | `str` | Normalized active language code. |
| `fallback_to_base` | `bool` | Whether fallback to base language is enabled. |
| `m_translation_enabled` | `bool` | Whether machine translation is enabled. |
| `validator` | `LanguageValidator` | GLFM language validator instance. |
| `glfm_fallback` | `List[str]` | List of GLFM fallback language codes (excluding the active language). |
| `ui_localizer` | `Localizer` | UI text localizer instance. |
| `template_localizer` | `TemplateLocalizer` | Template localizer instance. |

---

### Configuration

#### `_build_config(config: Optional[Dict[str, Any]]) -> Dict[str, Any]`

Builds the localization configuration.

##### Default Config

```python
{
    "m_translation_enabled": False,
    "fallback_to_base": True,
    "strict_mode": False,
    "default_language": None,
    "glfm_lite": True,
}
```

##### Behavior

- Starts with the default dictionary.
- If `config` is provided, updates defaults with `defaults.update(config)`.
- Returns the merged dictionary.

---

### Language Detection and Validation

#### `_detect_language() -> str`

Detects the active language from configuration or environment.

##### Priority Order

1. `get_env_value("SHL_LANGUAGE")`
2. `get_env_value("LANG")`
3. `self.config.get("default_language")`
4. Falls back to `"en"`

##### Returns

- `str` — The detected language code, normalized via `normalize_full_tag()`.

---

#### `_validate_language() -> None`

Validates the active language against GLFM when available.

##### Behavior

- If `validator.is_loaded` is `False`, returns immediately.
- If `validator.is_valid(self.lang_code)` is `True`, returns immediately.
- Otherwise, logs a warning and resets `self.lang_code = self.base_lang`.

---

#### `_build_fallback_chain() -> None`

Builds the GLFM localization fallback chain.

##### Behavior

- Clears `self.glfm_fallback` to an empty list.
- If `validator.is_loaded` is `False`, returns immediately.
- Calls `validator.get_fallback(self.lang_code)`.
- Catches any exception, logs a warning, and returns.
- If the result is a string, wraps it in a list.
- Iterates over the fallback languages:
  - Normalizes each via `normalize_full_tag()`.
  - Skips the active language.
  - Deduplicates entries.
- Logs the resulting fallback chain at debug level.

---

### Language Management

#### `ensure_language(lang_code: str) -> None`

Ensures UI and template localization files exist for the given language.

##### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `lang_code` | `str` | Language code to ensure. |

##### Behavior

- Normalizes `lang_code` via `normalize_full_tag()`.
- Instantiates `Localizer` and `TemplateLocalizer` with the normalized language code, `self.base_lang`, and respective folders.

---

#### `set_language(lang_code: str) -> None`

Switches the active localization language.

##### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `lang_code` | `str` | New active language code. |

##### Behavior

- Normalizes `lang_code` via `normalize_full_tag()`.
- If the normalized code equals `self.lang_code`, returns immediately.
- Updates `self.lang_code`.
- Calls `_validate_language()` and `_build_fallback_chain()`.
- Re-instantiates `ui_localizer` and `template_localizer` with the new language.
- Logs the language change at info level.

---

### Key Validation

#### `_validate_key(key: Any) -> str`

Validates and normalizes a localization key.

##### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | `Any` | The key to validate. |

##### Returns

- `str` — The stripped key string.

##### Raises

- `TypeError` — If `key` is not a `str`.
- `ValueError` — If `key` is empty or whitespace-only after stripping.

---

### Localization Fallback

#### `_get_with_fallback(localizer: Any, key: str) -> Optional[str]`

Resolves a localized value through the localization fallback chain.

##### Fallback Order

1. **Active language** — Calls `localizer.get_text(key)`.
2. **Fallback disabled** — If `self.fallback_to_base` is `False`, returns `None`.
3. **GLFM fallback languages** — For each language in `self.glfm_fallback`, creates a new `Localizer` and calls `get_text(key)`.
4. **Base language** — If `self.lang_code != self.base_lang`, creates a new `Localizer` for the base language and calls `get_text(key)`.
5. Returns `None` if nothing is found.

##### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `localizer` | `Any` | The primary localizer instance (e.g., `self.ui_localizer`). |
| `key` | `str` | The localization key. |

##### Returns

- `Optional[str]` — The localized value, or `None` if not found in any fallback language.

---

### UI Localization

#### `ensure_ui_key(key: str, default: str = "") -> str`

Ensures a UI key exists and returns its localized value.

##### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `key` | `str` | — | The UI localization key. |
| `default` | `str` | `""` | Default value if the key does not exist. |

##### Behavior

1. Validates the key via `_validate_key()`.
2. Retrieves the value via `_get_with_fallback(self.ui_localizer, validated_key)`.
3. If found, returns the value.
4. If not found, stores `default` via `ui_localizer.set_text()` and returns `default`.

---

#### `ui_text(key: str, default_value: str = "") -> str`

Returns localized UI text.

##### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `key` | `str` | — | The UI localization key. |
| `default_value` | `str` | `""` | Default text if localization is missing. |

##### Behavior

1. Validates the key via `_validate_key()`.
2. Retrieves the value via `_get_with_fallback(self.ui_localizer, validated_key)`.
3. If found, returns the value.
4. If not found and machine translation is enabled (`m_translation_enabled`), the language differs from base, and `default_value` is truthy:
   - Calls `translate_text(text=default_value, target_lang=self.lang_code, source_lang=self.base_lang)`.
   - If translation succeeds and is not `None`, stores the result and returns it.
   - Catches all exceptions, logs a warning.
5. Stores `default_value` via `ui_localizer.set_text()` and returns it.

---

### Prompt Templates

#### `ensure_template_key(key: str, default: str = "") -> str`

Ensures a prompt template key exists.

##### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `key` | `str` | — | The template key. |
| `default` | `str` | `""` | Default template if the key does not exist. |

##### Behavior

1. Validates the key via `_validate_key()`.
2. Retrieves the value via `template_localizer.get_text(validated_key)`.
3. If found, returns the value.
4. If not found, stores `default` via `template_localizer.set_text()` and returns `default`.

---

#### `template(key: str, default: str = "", **kwargs: Any) -> str`

Returns a localized prompt template and formats it.

##### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `key` | `str` | — | The template key. |
| `default` | `str` | `""` | Default template if the key does not exist. |
| `**kwargs` | `Any` | — | Keyword arguments for `str.format()`. |

##### Behavior

1. Validates the key via `_validate_key()`.
2. Retrieves the value via `template_localizer.get_text(validated_key)`.
3. If not found, uses `default` and stores it via `template_localizer.set_text()`.
4. If `kwargs` is empty, returns the template as-is.
5. Otherwise, attempts `value.format(**kwargs)`.
   - On `KeyError` or `ValueError`, logs a warning and returns the unformatted template.

---

### Synchronization

#### `_sync_from_lang(source_lang: str) -> None`

Synchronizes missing UI and template keys from one language.

##### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `source_lang` | `str` | Source language code to sync from. |

##### Behavior

- Instantiates new `Localizer` and `TemplateLocalizer` for `source_lang`.
- Iterates over `source_ui.texts.items()`:
  - If the key does not exist in `self.ui_localizer.texts`, copies it via `set_text()`.
- Iterates over `source_templates.templates.items()`:
  - If the key does not exist in `self.template_localizer.templates`, copies it via `set_text()`.

---

#### `sync() -> None`

Synchronizes missing keys from fallback languages and base language.

##### Behavior

1. Iterates over `self.glfm_fallback` and calls `_sync_from_lang()` for each language that differs from the active language.
2. If `self.base_lang != self.lang_code`, calls `_sync_from_lang(self.base_lang)`.

---

### GLFM Management

#### `reload_glfm() -> None`

Reloads GLFM data and rebuilds the localization fallback chain.

##### Behavior

- Creates a new `LanguageValidator` using the existing validator's path (if available).
- Calls `_validate_language()` and `_build_fallback_chain()`.

---

### Statistics

#### `get_stats() -> Dict[str, Any]`

Returns localization engine statistics.

##### Returns

- `Dict[str, Any]` with the following keys:
  - `"lang_code"`: `self.lang_code`
  - `"base_lang"`: `self.base_lang`
  - `"glfm_loaded"`: `self.validator.is_loaded`
  - `"glfm_fallback"`: `self.glfm_fallback`
  - `"fallback_to_base"`: `self.fallback_to_base`
  - `"m_translation_enabled"`: `self.m_translation_enabled`
  - `"ui_keys"`: `len(self.ui_localizer.texts)`
  - `"template_keys"`: `len(self.template_localizer.templates)`
  - `"config"`: `dict(self.config)` (shallow copy)

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
    config={"m_translation_enabled": True},
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
engine.sync()

# Get statistics
stats = engine.get_stats()
print(stats)

# Reload GLFM
engine.reload_glfm()
```

---

## Version

**Module version:** `0.2.6`

**Author:** Tuomas Lähteenmäki

**License:** MIT
