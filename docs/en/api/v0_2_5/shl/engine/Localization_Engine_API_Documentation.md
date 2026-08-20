# Localization Engine — API Documentation

## Module Overview

**File:** `core.py`

The central engine of the Self-Healing Localization Layer (SHL). Unifies UI text localization, AI prompt template localization, GLFM language validation with fallback chains, and smart machine translation routing. Provides a single, clean API for higher-level applications to manage multilingual content across both user interfaces and AI prompts.

---

## Metadata

| Attribute | Value |
|-----------|-------|
| Author | Tuomas Lähteenmäki |
| Version | 0.2.4 |
| License | MIT |

---

## Dependencies

| Module | Usage |
|--------|-------|
| `logging` | Engine-level log output. |
| `os` | Environment variable access and file existence checks. |
| `typing.Any`, `typing.Callable`, `typing.Dict`, `typing.List`, `typing.Optional` | Type annotations. |
| `shl.engine.localizer.Localizer` | UI text localization management. |
| `shl.engine.template_localizer.TemplateLocalizer` | AI prompt template localization. |
| `shl.engine.translation` | Machine translation adapters and exceptions. |
| `shl.language_validator.LanguageValidator` | GLFM-based language validation and fallback chains. |
| `shl.utils.lang_utils` | Language tag normalization and base extraction. |
| `shl.utils.env_loader` | `.env` file loading and environment variable access. |

---

## Class: `LocalizationEngine`

```python
class LocalizationEngine
```

Central localization engine that coordinates UI text, prompt templates, language validation, and machine translation. Supports two initialization modes: **SETTINGS-forced** (via `config.conf`) and **auto-detected** (via environment or GLFM).

---

### Constructor

```python
def __init__(
    self,
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
) -> None
```

Initializes the localization engine, loading configuration, detecting language, setting up GLFM validation, and configuring translation adapters.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lang_code` | `Optional[str]` | `None` | Target language code. Auto-detected if omitted (unless overridden by `config.conf`). |
| `base_lang` | `Optional[str]` | `None` | Developer's base/source language. Defaults to `"en"` or `config.conf` value. |
| `ui_folder` | `str` | `"locales"` | Directory for UI translation JSON files. |
| `template_folder` | `str` | `"prompts"` | Directory for prompt template JSON files. |
| `config` | `Optional[Dict[str, Any]]` | `None` | Runtime configuration overrides. Merged with defaults and `config.conf`. |
| `glfm_path` | `Optional[str]` | `None` | Custom path to GLFM database. |
| `glfm_lite` | `bool` | `True` | Use GLFM Lite mode (~428 KB). |
| `libretranslate_url` | `Optional[str]` | `None` | LibreTranslate API endpoint URL. |
| `libretranslate_api_key` | `Optional[str]` | `None` | LibreTranslate API key. |
| `mymemory_email` | `Optional[str]` | `None` | MyMemory API email for higher quota. |
| `libretranslate_mirrors` | `Optional[List[Dict[str, Any]]]` | `None` | List of LibreTranslate mirror configurations. |
| `deepl_key` | `Optional[str]` | `None` | DeepL API key. |
| `google_api_key` | `Optional[str]` | `None` | Google Translate v2 API key. |
| `google_backup_api_key` | `Optional[str]` | `None` | Backup Google API key for failover. |
| `papago_client_id` | `Optional[str]` | `None` | Naver Papago client ID. |
| `papago_client_secret` | `Optional[str]` | `None` | Naver Papago client secret. |

**Initialization Flow**

```
1. Load .env file (if not already loaded)
2. Load default config + config.conf
3. Check config.conf [SETTINGS] section:
   ├── If "language" exists → SETTINGS-forced mode
   │   ├── lang_code = SETTINGS.language
   │   ├── base_lang = SETTINGS.base_lang (default "en")
   │   ├── GLFM disabled (path=None)
   │   └── Initialize localizers and adapters
   └── Else → Normal mode
       ├── Detect language (config → SHL_LANGUAGE → LANG → "en")
       ├── Normalize lang_code and base_lang
       ├── Initialize GLFM validator
       ├── Build fallback chain
       └── Initialize localizers and adapters
```

**Credential Resolution**

All API keys follow the priority: **parameter > .env variable > default (None)**.

| Parameter | Environment Variable |
|-----------|---------------------|
| `mymemory_email` | `MYMEMORY_EMAIL` |
| `libretranslate_url` | `LIBRETRANSLATE_URL` |
| `libretranslate_api_key` | `LIBRETRANSLATE_API_KEY` |
| `deepl_key` | `DEEPL_API_KEY` |
| `google_api_key` | `GOOGLE_API_KEY` |
| `google_backup_api_key` | `GOOGLE_BACKUP_API_KEY` |
| `papago_client_id` | `NAVER_CLIENT_ID` |
| `papago_client_secret` | `NAVER_CLIENT_SECRET` |

---

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `config` | `Dict[str, Any]` | Merged configuration dictionary. |
| `lang_code` | `str` | Active target language code (normalized). |
| `base_lang` | `str` | Base/source language code (normalized). |
| `ui_folder` | `str` | UI translations directory path. |
| `template_folder` | `str` | Prompt templates directory path. |
| `validator` | `LanguageValidator` | GLFM language validator instance. |
| `glfm_fallback` | `Optional[str]` | Immediate GLFM fallback language (second in chain). |
| `glfm_fallback_chain` | `List[str]` | Complete GLFM fallback chain. |
| `cache` | `TranslationCache` | In-memory translation result cache. |
| `ui_localizer` | `Localizer` | UI text localizer instance. |
| `template_localizer` | `TemplateLocalizer` | Prompt template localizer instance. |
| `mymemory_adapter` | `MyMemoryAdapter` | MyMemory translation provider. |
| `libretranslate_adapter` | `LibreTranslateAdapter` | LibreTranslate provider with mirror support. |
| `_deepl_key` | `Optional[str]` | Resolved DeepL API key. |
| `_google_api_key` | `Optional[str]` | Resolved Google API key. |
| `_google_backup_api_key` | `Optional[str]` | Resolved Google backup API key. |
| `_papago_client_id` | `Optional[str]` | Resolved Papago client ID. |
| `_papago_client_secret` | `Optional[str]` | Resolved Papago client secret. |

---

### Internal Methods

#### `_load_default_config()`

```python
def _load_default_config(self) -> Dict[str, Any]
```

Loads default configuration values and merges with `config.conf` `[SETTINGS]` section.

**Default Values**

| Key | Default | Description |
|-----|---------|-------------|
| `m_translation_enabled` | `False` | Whether machine translation is enabled. |
| `translation_cache_ttl` | `3600` | Translation cache TTL in seconds. |
| `fallback_to_base` | `True` | Whether to fall back to base language when key is missing. |
| `strict_mode` | `False` | Strict validation mode. |
| `default_language` | `None` | Override language code from config. |
| `glfm_lite` | `True` | Use GLFM Lite database. |

**Config File (`config.conf`)**
```ini
[SETTINGS]
language = fi
base_lang = en
m_translation_enabled = false
fallback_to_base = true
glfm_lite = true
```

**Returns**
- `Dict[str, Any]` — Merged configuration dictionary.

---

#### `_detect_language()`

```python
def _detect_language(self) -> str
```

Detects the active language using a priority cascade.

**Detection Order**
1. `config["default_language"]` — if set.
2. `SHL_LANGUAGE` environment variable.
3. `LANG` environment variable (parsed: strips encoding suffix, converts `fi_FI` → `fi-FI`).
4. `"en"` — absolute fallback.

**Returns**
- `str` — Detected language code.

---

#### `_validate_key()`

```python
def _validate_key(self, key: str) -> str
```

Validates and normalizes a localization key.

**Returns**
- `str` — Stripped key string, or empty string if invalid.

**Logging**
- `WARNING` — Non-string key type.
- `DEBUG` — Empty key detected, key normalized.

---

#### `_get_with_fallback()`

```python
def _get_with_fallback(
    self,
    getter: Callable[[str, Optional[str], bool], Optional[str]],
    key: str,
) -> Optional[str]
```

Retrieves a localized string through the full fallback chain.

**Fallback Order**
1. **Active language** — always checked first.
2. **GLFM fallback chain** — iterates through nearest languages (skipped if `fallback_to_base=False`).
3. **Base language** — final fallback (skipped if already active language).

| Parameter | Type | Description |
|-----------|------|-------------|
| `getter` | `Callable` | Localizer getter function (`get_text` or `get_template`). |
| `key` | `str` | Localization key to retrieve. |

**Returns**
- `Optional[str]` — Localized text if found, `None` if all fallbacks exhausted.

---

#### `_sync_from_lang()`

```python
def _sync_from_lang(self, source_lang: str) -> int
```

Synchronizes missing keys from a source language to the active language.

| Parameter | Type | Description |
|-----------|------|-------------|
| `source_lang` | `str` | Source language to copy keys from. |

**Returns**
- `int` — Number of keys synchronized (UI + templates).

**Behavior**
- Copies keys that exist in the source language but are missing in the active language.
- Existing keys are left untouched.

---

### Public Methods

#### `ensure_language()`

```python
def ensure_language(self, lang_code: str) -> None
```

Ensures that UI and template JSON files exist for a given language. Creates the language directories and base files if they do not exist.

| Parameter | Type | Description |
|-----------|------|-------------|
| `lang_code` | `str` | Language code to ensure. |

**Example**
```python
engine.ensure_language("fi")
# Creates locales/fi.json and prompts/fi.json if missing
```

---

#### `set_language()`

```python
def set_language(self, lang_code: str) -> None
```

Switches the active language and rebuilds the GLFM fallback chain.

| Parameter | Type | Description |
|-----------|------|-------------|
| `lang_code` | `str` | New active language code. |

**Side Effects**
- Updates `self.lang_code`.
- Reinitializes `ui_localizer` and `template_localizer` with the new language.
- Rebuilds `glfm_fallback_chain` and `glfm_fallback`.

**Example**
```python
engine.set_language("ja")
# Language switched to: ja
```

---

#### `ensure_ui_key()`

```python
def ensure_ui_key(
    self,
    key: str,
    default: str = "",
) -> str
```

Ensures a UI localization key exists. If the key is missing, it is created with the provided default value.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `key` | `str` | — | Localization key. |
| `default` | `str` | `""` | Default text to set if the key does not exist. |

**Returns**
- `str` — Existing text if found, or `default` if created.

**Example**
```python
text = engine.ensure_ui_key("welcome_message", "Welcome!")
```

---

#### `ensure_template_key()`

```python
def ensure_template_key(
    self,
    key: str,
    default: str = "",
) -> str
```

Ensures a prompt template key exists. If the key is missing, it is created with the provided default value.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `key` | `str` | — | Template key. |
| `default` | `str` | `""` | Default template to set if the key does not exist. |

**Returns**
- `str` — Existing template if found, or `default` if created.

---

#### `ui_text()`

```python
def ui_text(
    self,
    key: str,
    default_value: str = "",
) -> str
```

Retrieves UI text with full fallback chain and optional machine translation.

**Execution Flow**
```
1. Validate key
2. Check translation cache
3. Try fallback chain (active → GLFM → base)
4. If not found and m_translation_enabled:
   └── Translate default_value via translate_text()
   └── Save translated text to localizer and cache
5. If translation fails or disabled:
   └── Save default_value to localizer and cache
6. Return result
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `key` | `str` | — | UI localization key. |
| `default_value` | `str` | `""` | Default text to use if key is missing. Also used as source for machine translation. |

**Returns**
- `str` — Localized or translated text, or `default_value` if all methods fail.

**Machine Translation**
- Only triggered if `m_translation_enabled=True`, `lang_code != base_lang`, and `default_value` is non-empty.
- Uses the full provider routing (DeepL, Google, Papago, MyMemory, LibreTranslate) via `translate_text()`.
- Failed translations are logged as warnings and fall back to `default_value`.

**Example**
```python
# With machine translation disabled
text = engine.ui_text("greeting", "Hello!")
# Returns cached/fallback text, or stores "Hello!" if missing

# With machine translation enabled
text = engine.ui_text("greeting", "Hello!")
# If "greeting" missing in Finnish, translates "Hello!" → "Hei!"
```

---

#### `template()`

```python
def template(
    self,
    key: str,
    default: str = "",
    **kwargs: Any,
) -> str
```

Retrieves and optionally formats a prompt template.

**Execution Flow**
```
1. Validate key
2. Try fallback chain (active → GLFM → base)
3. If not found, use default
4. If kwargs provided, format with .format(**kwargs)
5. Return result
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `key` | `str` | — | Template key. |
| `default` | `str` | `""` | Default template if key is missing. |
| `**kwargs` | `Any` | — | Format arguments for Python string formatting. |

**Returns**
- `str` — Template string, with kwargs substituted if provided.

**Example**
```python
# Simple retrieval
prompt = engine.template("summarize_prompt", "Summarize: {text}")

# With formatting
prompt = engine.template(
    "summarize_prompt",
    "Summarize this in {language}: {text}",
    language="Finnish",
    text="Long article here..."
)
# "Summarize this in Finnish: Long article here..."
```

---

#### `sync()`

```python
def sync(self) -> int
```

Synchronizes missing keys from fallback languages and base language into the active language.

**Sync Order**
1. GLFM fallback chain languages (excluding active language).
2. Base language (if different from active).

**Returns**
- `int` — Total number of keys synchronized (UI + templates).

**Example**
```python
count = engine.sync()
print(f"Synced {count} keys")
# Synchronized 150 UI keys and 20 templates from 'en'
```

---

#### `get_stats()`

```python
def get_stats(self) -> Dict[str, Any]
```

Returns comprehensive engine statistics.

**Returns**
- `Dict[str, Any]` — Dictionary with the following keys:

| Key | Type | Description |
|-----|------|-------------|
| `lang_code` | `str` | Active language code. |
| `base_lang` | `str` | Base language code. |
| `glfm_fallback` | `Optional[str]` | Immediate GLFM fallback language. |
| `glfm_fallback_chain` | `List[str]` | Complete fallback chain. |
| `glfm_lite` | `bool` | Whether GLFM Lite is in use. |
| `glfm_loaded` | `bool` | Whether GLFM database is loaded. |
| `ui_keys_count` | `int` | Number of UI keys loaded. |
| `template_keys_count` | `int` | Number of template keys loaded. |
| `cache_size` | `int` | Translation cache size. |
| `m_translation_enabled` | `bool` | Machine translation status. |
| `config` | `Dict[str, Any]` | Copy of current configuration. |
| `deepl_key_configured` | `bool` | Whether DeepL API key is set. |
| `google_api_key_configured` | `bool` | Whether Google API key is set. |
| `papago_configured` | `bool` | Whether Papago credentials are set. |

**Example**
```python
stats = engine.get_stats()
print(f"UI keys: {stats['ui_keys_count']}")
print(f"Templates: {stats['template_keys_count']}")
print(f"Cache size: {stats['cache_size']}")
print(f"Fallback chain: {stats['glfm_fallback_chain']}")
```

---

#### `get_mirror_stats()`

```python
def get_mirror_stats(self) -> List[Dict[str, Any]]
```

Returns LibreTranslate mirror health statistics.

**Returns**
- `List[Dict[str, Any]]` — List of mirror status dictionaries.

---

#### `clear_mirror_cache()`

```python
def clear_mirror_cache(self) -> None
```

Clears the LibreTranslate mirror cache, forcing fresh mirror discovery on next use.

---

#### `reload_glfm()`

```python
def reload_glfm(
    self,
    glfm_path: Optional[str] = None,
    glfm_lite: Optional[bool] = None,
) -> bool
```

Reloads the GLFM database and rebuilds the fallback chain.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `glfm_path` | `Optional[str]` | `None` | Custom database path. Uses current config if omitted. |
| `glfm_lite` | `Optional[bool]` | `None` | Force Lite/Full mode. Uses current config if omitted. |

**Returns**
- `bool` — `True` if GLFM loaded successfully, `False` otherwise.

**Example**
```python
# Switch to full database
success = engine.reload_glfm(glfm_lite=False)
if success:
    print(f"Loaded {len(engine.validator.languages)} languages")
```

---

## Complete Usage Example

```python
from shl.core import LocalizationEngine
import logging

# Initialize engine
engine = LocalizationEngine(
    lang_code="fi",
    base_lang="en",
    ui_folder="locales",
    template_folder="prompts",
    deepl_key="your-deepl-key",
    mymemory_email="user@example.com",
)

# Ensure language files exist
engine.ensure_language("fi")

# Get UI text with fallback and optional translation
greeting = engine.ui_text(
    "welcome_message",
    default_value="Welcome to our app!"
)
print(greeting)

# Get formatted prompt template
prompt = engine.template(
    "summarize",
    default="Summarize in {lang}: {text}",
    lang="Finnish",
    text="Long article here..."
)
print(prompt)

# Ensure keys exist (creates if missing)
engine.ensure_ui_key("new_feature", "Check out our new feature!")
engine.ensure_template_key("code_review", "Review this code: {code}")

# Switch language
engine.set_language("ja")

# Sync missing keys from fallback languages
synced = engine.sync()
print(f"Synced {synced} keys")

# Check statistics
stats = engine.get_stats()
print(f"Active: {stats['lang_code']}")
print(f"Base: {stats['base_lang']}")
print(f"Fallback chain: {stats['glfm_fallback_chain']}")
print(f"UI keys: {stats['ui_keys_count']}")
print(f"Templates: {stats['template_keys_count']}")

# Reload GLFM with full database
engine.reload_glfm(glfm_lite=False)
```

---

## Configuration File (`config.conf`)

```ini
[SETTINGS]
language = fi
base_lang = en
m_translation_enabled = false
fallback_to_base = true
glfm_lite = true
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `language` | `str` | — | Forces active language (disables auto-detection and GLFM). |
| `base_lang` | `str` | `"en"` | Developer's base/source language. |
| `m_translation_enabled` | `bool` | `false` | Enable machine translation for missing keys. |
| `fallback_to_base` | `bool` | `true` | Allow fallback to base language when key is missing. |
| `glfm_lite` | `bool` | `true` | Use GLFM Lite database. |

---

## Fallback Chain

```
Active Language (e.g., "fi")
    │
    ├── Key found? → Return text
    │
    └── Not found → GLFM Fallback Chain
            │
            ├── Nearest languages (e.g., "sv", "et", "de")
            │   ├── Key found? → Return text
            │   └── Not found → Next nearest
            │
            └── All GLFM fallbacks exhausted → Base Language (e.g., "en")
                    │
                    ├── Key found? → Return text
                    │
                    └── Not found → Return default / trigger translation
```

---

## Thread Safety

| Component | Status | Notes |
|-----------|--------|-------|
| `LocalizationEngine` instance | Caution | Not designed for concurrent mutation. `set_language()`, `sync()`, and `ui_text()` mutate internal state. |
| `ui_localizer` / `template_localizer` | Caution | File writes are not atomic. Concurrent writes may corrupt JSON files. |
| `cache` | Generally safe | Read operations are safe. Writes may race in multi-threaded use. |
| `validator` | Safe | Read-only after initialization. |

**Recommendation:** Use one `LocalizationEngine` instance per thread, or wrap mutating operations with locks in multi-threaded environments.

---

## Logging

The module uses Python's standard `logging` module under the logger name `__name__`.

**Log Levels Used**

| Level | Event |
|-------|-------|
| `INFO` | Engine initialization, language switch, sync completion. |
| `WARNING` | Unparseable language code, machine translation failure, template format error. |
| `DEBUG` | Key normalization, fallback attempts, config loading, sync details. |

---

## Changelog

| Version | Notes |
|---------|-------|
| 0.2.4 | Current — unified localization engine with UI/template management, GLFM fallback chains, machine translation integration, and SETTINGS-forced mode via config.conf. |
