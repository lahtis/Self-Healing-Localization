# Translation Metadata — API Documentation

## Module Overview

**File:** `metadata.py`

Data transfer objects (DTOs) for standardizing localized text payloads, context preservation markers, and external provider results across the SHL translation pipeline. Defines the canonical request and response schemas used by all provider adapters and the routing engine.

---

## Metadata

| Attribute | Value |
|-----------|-------|
| Author | Tuomas Lähteenmäki |
| Version | 0.2.4 |
| License | MIT |
| Description | Data transfer objects (DTO) for standardizing localized text payloads, context preservation markers, and external provider results. |

---

## Dependencies

| Module | Usage |
|--------|-------|
| `dataclasses.dataclass`, `dataclasses.field` | Automatic `__init__`, `__repr__`, and equality generation. |
| `typing.Optional`, `typing.Dict`, `typing.Any` | Type annotations for optional and dynamic fields. |

---

## Dataclass: `TranslationRequest`

```python
@dataclass
class TranslationRequest
```

Standardized schema for translation requests. Carries the source text, language codes, and rich contextual metadata through the entire SHL pipeline — from the application layer down to individual provider adapters.

### Attribute Tiers

The fields are organized into three tiers based on support breadth across providers:

#### Tier 1: Core Pipeline

Supported by **all** provider adapters. These fields are mandatory for every translation.

| Field | Type | Description |
|-------|------|-------------|
| `text` | `str` | The source text to translate. |
| `source_lang` | `str` | Source language code (e.g., `"en"`, `"fi"`). |
| `target_lang` | `str` | Target language code (e.g., `"ja"`, `"de"`). |

#### Tier 2: Context Controls

Supported by **advanced adapters** (DeepL, Google Cloud, Papago, Microsoft Translator, LLM-backed routers). Adapters that do not support a specific field should safely ignore it rather than raise an error.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `context_type` | `Optional[str]` | `None` | UI element type. Examples: `"button"`, `"label"`, `"menu"`, `"tooltip"`, `"heading"`. |
| `domain` | `Optional[str]` | `None` | Application domain. Examples: `"desktop_ui"`, `"web"`, `"mobile"`, `"game"`. |
| `formality` | `Optional[str]` | `None` | Formality level. Examples: `"formal"`, `"informal"`, `"more"`, `"less"`. |
| `honorific` | `Optional[bool]` | `None` | Papago-specific honorific flag. `True` = polite/honorific style. |
| `glossary` | `Optional[Dict[str, Any]]` | `None` | Inline term mappings. Example: `{"Save": "Tallenna", "Cancel": "Peruuta"}`. |
| `glossary_id` | `Optional[str]` | `None` | DeepL-specific glossary ID for server-side terminology. |
| `html_format` | `bool` | `False` | Whether the text contains HTML markup that should be preserved. |

#### Tier 3: Engine Internal Tracking

Used by the SHL engine for routing, caching, logging, and debugging. Providers typically ignore these fields.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `key` | `Optional[str]` | `None` | Localization key identifier. Example: `"settings.save"`. |
| `screen` | `Optional[str]` | `None` | UI screen or page name. Example: `"settings"`, `"main"`, `"login"`. |
| `component` | `Optional[str]` | `None` | UI component name. Example: `"save_button"`, `"header_label"`. |
| `source_id` | `Optional[str]` | `None` | Unique source identifier. Example: `"shl://settings/save_button"`. |
| `metadata` | `Dict[str, Any]` | `{}` | Flexible extension dictionary for custom data. |

---

### Constructor

```python
TranslationRequest(
    text: str,
    source_lang: str,
    target_lang: str,
    context_type: Optional[str] = None,
    domain: Optional[str] = None,
    formality: Optional[str] = None,
    honorific: Optional[bool] = None,
    glossary: Optional[Dict[str, Any]] = None,
    glossary_id: Optional[str] = None,
    html_format: bool = False,
    key: Optional[str] = None,
    screen: Optional[str] = None,
    component: Optional[str] = None,
    source_id: Optional[str] = None,
    metadata: Dict[str, Any] = <factory>,
)
```

**Example**
```python
from shl.metadata import TranslationRequest

request = TranslationRequest(
    text="Welcome to our application!",
    source_lang="en",
    target_lang="de",
    formality="formal",
    domain="desktop_ui",
    screen="user_onboarding",
    component="welcome_label",
    key="onboarding.welcome",
)
```

---

### Dataclass Features

As a `@dataclass`, `TranslationRequest` automatically provides:

| Feature | Description |
|---------|-------------|
| `__init__` | Constructor with all fields as parameters. |
| `__repr__` | Human-readable string representation. |
| `__eq__` | Equality comparison based on all fields. |
| `__hash__` | Not generated (mutable default `metadata` dict prevents it). |

**Example**
```python
print(request)
# TranslationRequest(text='Welcome to our application!', source_lang='en',
#   target_lang='de', context_type=None, domain='desktop_ui', ...)
```

---

## Dataclass: `TranslationResult`

```python
@dataclass
class TranslationResult
```

Standardized output container for translation responses. Encloses the translated string, provider attribution, optional confidence score, raw provider response, and the original request metadata for audit trails.

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `translated_text` | `str` | — | The final translated text. |
| `source` | `str` | — | Provider identifier. Examples: `"mymemory"`, `"libretranslate"`, `"deepl"`, `"google"`, `"microsoft_translator"`, `"papago"`. |
| `confidence` | `Optional[float]` | `None` | Provider-reported confidence score (0.0–1.0). Not all providers support this. |
| `raw_response` | `Optional[Dict[str, Any]]` | `None` | Raw provider API response for debugging and audit. |
| `request_metadata` | `Optional[TranslationRequest]` | `None` | The original `TranslationRequest` for traceability. |

---

### Constructor

```python
TranslationResult(
    translated_text: str,
    source: str,
    confidence: Optional[float] = None,
    raw_response: Optional[Dict[str, Any]] = None,
    request_metadata: Optional[TranslationRequest] = None,
)
```

**Example**
```python
from shl.metadata import TranslationResult

result = TranslationResult(
    translated_text="Willkommen in unserer Anwendung!",
    source="deepl",
    confidence=0.98,
    request_metadata=request,
)
```

---

### Dataclass Features

As a `@dataclass`, `TranslationResult` automatically provides:

| Feature | Description |
|---------|-------------|
| `__init__` | Constructor with all fields as parameters. |
| `__repr__` | Human-readable string representation. |
| `__eq__` | Equality comparison based on all fields. |

**Example**
```python
print(result)
# TranslationResult(translated_text='Willkommen in unserer Anwendung!',
#   source='deepl', confidence=0.98, raw_response=None, request_metadata=...)
```

---

## Provider Support Matrix

Which `TranslationRequest` fields each provider adapter typically uses:

| Field | MyMemory | LibreTranslate | DeepL | Google | Papago | Microsoft |
|-------|----------|----------------|-------|--------|--------|-----------|
| `text` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `source_lang` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `target_lang` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `context_type` | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| `domain` | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| `formality` | ❌ | ❌ | ✅ | ❌ | ✅* | ✅ |
| `honorific` | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| `glossary` | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ |
| `glossary_id` | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| `html_format` | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| `key` | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| `screen` | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| `component` | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

\* Papago maps `formality` to `honorific` for DeepL compatibility.

---

## Complete Usage Example

```python
from shl.metadata import TranslationRequest, TranslationResult

# 1. Build a rich translation request
request = TranslationRequest(
    text="Save changes before closing?",
    source_lang="en",
    target_lang="de",
    formality="formal",
    context_type="dialog",
    domain="desktop_ui",
    screen="settings",
    component="save_dialog",
    key="settings.save_dialog.confirm",
    html_format=False,
)

# 2. Pass to a provider adapter
from shl.providers.deepl import DeepLAdapter

adapter = DeepLAdapter(api_key="your-key")
result = adapter.translate(request)

# 3. Inspect the result
print(f"Translated: {result.translated_text}")
print(f"Provider: {result.source}")
print(f"Confidence: {result.confidence}")

# 4. Access original request metadata
if result.request_metadata:
    print(f"Original key: {result.request_metadata.key}")
    print(f"Screen: {result.request_metadata.screen}")
```

---

## Thread Safety

Both `TranslationRequest` and `TranslationResult` are **immutable after construction** (assuming the caller does not mutate the `metadata` dict or `raw_response` dict post-creation). They are safe to share across threads without locking.

**Warning:** The `metadata` field defaults to a mutable `dict`. If multiple threads mutate the same instance's `metadata`, race conditions may occur. Treat `metadata` as write-once or copy before mutation.

---

## Changelog

| Version | Notes |
|---------|-------|
| 0.2.4 | Current — `TranslationRequest` with three-tier metadata (core, context controls, engine internal) and `TranslationResult` with provider attribution and audit trail support. |
