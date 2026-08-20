# Base Provider Interface — API Documentation

## Module Overview

**File:** `base.py`

Defines the abstract base class and shared utilities for all SHL translation provider adapters. Establishes the contract that every provider must implement, along with common helpers for secure credential masking and feature capability reporting.

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
| `abc.ABC`, `abc.abstractmethod` | Abstract base class enforcement. |
| `typing.Dict`, `typing.Any`, `typing.List`, `typing.Optional` | Type annotations. |
| `..metadata.TranslationRequest` | Core request data structure passed to all providers. |

---

## Utility Functions

### `mask_api_key()`

```python
def mask_api_key(key: Optional[str]) -> str
```

Masks an API key for safe logging, preventing credential leakage in log files or console output.

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | `Optional[str]` | Raw API key string, or `None`. |

**Returns**
- `str` — Masked representation of the key.

**Masking Rules**

| Input Condition | Output |
|-----------------|--------|
| `None` or empty string (`""`) | `"(not set)"` |
| Length ≤ 8 characters | `"*" * len(key)` (fully masked) |
| Length > 8 characters | First 4 chars + `*` padding + last 4 chars |

**Examples**
```python
>>> mask_api_key("my-secret-key-12345")
'my-s*****************12345'
>>> mask_api_key("short")
'*****'
>>> mask_api_key(None)
'(not set)'
>>> mask_api_key("abcd1234xyz")
'abcd***xyz'
```

**Security Note**
This function is the canonical way to log API keys across all SHL provider adapters. All providers should use `mask_api_key()` (or the `_mask_credential()` wrapper) before including credentials in log messages.

---

## Abstract Class: `TranslationProvider`

```python
class TranslationProvider(ABC)
```

Abstract base class that defines the interface every translation provider adapter must implement. Subclasses are responsible for mapping SHL's `TranslationRequest` metadata into provider-specific API payloads and executing the actual network call.

### Supported Metadata Fields

Providers may optionally support the following fields from `TranslationRequest`:

| Category | Fields | Description |
|----------|--------|-------------|
| **Core** | `text`, `source_lang`, `target_lang` | Always required; every provider must handle these. |
| **Extended** | `context_type`, `domain`, `screen`, `component`, `formality`, `glossary`, `html_format` | Optional metadata for context-aware translation. |
| **SHL Internal** | `key`, `source_id`, `metadata` | Internal tracking fields; providers may ignore. |

Providers should safely ignore metadata fields they do not support rather than raising errors.

---

### Abstract Methods

#### `translate()`

```python
@abstractmethod
def translate(self, request: TranslationRequest) -> str
```

Executes the translation using the provider's backend API.

| Parameter | Type | Description |
|-----------|------|-------------|
| `request` | `TranslationRequest` | Fully populated request object containing source text, language codes, and optional metadata. |

**Returns**
- `str` — The translated text returned by the provider.

**Implementation Pipeline**
1. Extract and validate supported fields from the `TranslationRequest`.
2. Build the provider-specific payload using `build_request()`.
3. Execute the network call and validate the response structure.
4. Safely ignore non-critical metadata fields unsupported by the backend.

**Note:** Concrete implementations should raise appropriate SHL exceptions (`TranslationError`, `ServiceUnavailableError`, etc.) on failure rather than returning raw error strings.

---

#### `build_request()`

```python
@abstractmethod
def build_request(self, request: TranslationRequest) -> Dict[str, Any]
```

Constructs the raw API request payload or parameter dictionary from the `TranslationRequest` metadata.

| Parameter | Type | Description |
|-----------|------|-------------|
| `request` | `TranslationRequest` | Source request containing all translation parameters. |

**Returns**
- `Dict[str, Any]` — Dictionary formatted for the provider's API endpoint. Structure is provider-specific.

**Purpose**
This method reflects the exact schema sent to the provider endpoint. It separates request construction from execution, making the adapter easier to test and debug.

---

#### `name`

```python
@property
@abstractmethod
def name(self) -> str
```

Returns the unique provider identifier string.

**Returns**
- `str` — Provider name slug used for routing, logging, and configuration lookups.

**Examples**
```python
"mymemory"
"libretranslate"
"deepl"
"googlev2"
"papago"
"microsoft_translator"
```

---

### Concrete Methods

#### `supported_features`

```python
@property
def supported_features(self) -> List[str]
```

Returns the list of non-standard metadata features supported by this provider adapter.

**Returns**
- `List[str]` — List of feature identifier strings. Defaults to an empty list `[]`.

**Override in Subclasses**

Subclasses should override this property to declare which extended features they support. This enables dynamic routing and UI capability detection.

**Examples**
```python
["formality", "honorific", "context", "glossary", "html_format", "labels"]
```

**Example Override**
```python
@property
def supported_features(self) -> list:
    return ["formality", "context", "html_format"]
```

---

#### `supports_feature()`

```python
def supports_feature(self, feature: str) -> bool
```

Checks whether a specific metadata feature is supported by this adapter.

| Parameter | Type | Description |
|-----------|------|-------------|
| `feature` | `str` | Feature identifier to check (case-insensitive). |

**Returns**
- `bool` — `True` if the feature is in `supported_features` (case-insensitive match), `False` otherwise.

**Example**
```python
provider = MicrosoftTranslatorAdapter()
provider.supports_feature("formality")   # True
provider.supports_feature("glossary")    # False
provider.supports_feature("FORMALITY")   # True (case-insensitive)
```

---

#### `_mask_credential()`

```python
def _mask_credential(self, credential: Optional[str]) -> str
```

Convenience wrapper around `mask_api_key()` for secure credential logging within provider instances.

| Parameter | Type | Description |
|-----------|------|-------------|
| `credential` | `Optional[str]` | Credential string to mask, or `None`. |

**Returns**
- `str` — Masked credential string following the same rules as `mask_api_key()`.

**Example**
```python
>>> provider._mask_credential("my-secret-key")
'my-s*****************ey'
```

**Usage in Providers**
```python
logger.debug(
    f"Provider {self.name} initialized "
    f"(api_key={self._mask_credential(self.api_key)})"
)
```

---

## Implementing a New Provider

To add a new translation provider to SHL, subclass `TranslationProvider` and implement all abstract members:

```python
from shl.providers.base import TranslationProvider
from shl.metadata import TranslationRequest
from shl.exceptions import TranslationError

class MyProviderAdapter(TranslationProvider):
    @property
    def name(self) -> str:
        return "my_provider"

    @property
    def supported_features(self) -> list:
        return ["formality", "html_format"]

    def build_request(self, request: TranslationRequest) -> dict:
        return {
            "text": request.text,
            "source": request.source_lang,
            "target": request.target_lang,
            "formality": request.formality,
        }

    def translate(self, request: TranslationRequest) -> str:
        payload = self.build_request(request)
        # Execute network call, validate, return translated text
        response = self._call_remote_api(payload)
        return response["translatedText"]
```

---

## Class Hierarchy

```
abc.ABC
    └── TranslationProvider (abstract)
            ├── MyMemoryAdapter
            ├── LibreTranslateAdapter
            ├── DeepLAdapter
            ├── GoogleV2Adapter
            ├── PapagoAdapter
            └── MicrosoftTranslatorAdapter
```

All concrete adapters inherit:
- `translate()` — must implement
- `build_request()` — must implement
- `name` — must implement
- `supported_features` — may override (default: `[]`)
- `supports_feature()` — inherited, case-insensitive lookup
- `_mask_credential()` — inherited, uses `mask_api_key()`

---

## Thread Safety

`TranslationProvider` itself is stateless and thread-safe. Thread safety of concrete implementations depends on whether the subclass maintains mutable instance state (e.g., connection pools, caches, registries). Stateless adapters are inherently safe for concurrent use.

---

## Changelog

| Version | Notes |
|---------|-------|
| 0.2.4 | Current — abstract base with `mask_api_key()`, `supported_features`, `supports_feature()`, and `_mask_credential()`. |
