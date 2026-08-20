# SHL Exception Taxonomy — API Documentation

## Module Overview

**File:** `exceptions.py`

Explicit error taxonomy for the SHL translation subsystem. Provides a hierarchy of exception types that isolate, capture, and manage upstream client network errors, quota exhaustion, language pair rejection, credential failures, and malformed request payloads.

All exceptions inherit from `TranslationError`, enabling catch-all handling while still allowing fine-grained discrimination of specific failure modes.

---

## Metadata

| Attribute | Value |
|-----------|-------|
| Author | Tuomas Lähteenmäki |
| Version | 0.2.0 |
| License | MIT |
| Description | Explicit error taxonomy for isolating, capturing, and managing upstream client network errors, quotas, and structural anomalies. |

---

## Class Hierarchy

```
Exception (built-in)
    └── TranslationError
            ├── ServiceUnavailableError
            ├── RateLimitExceededError
            ├── LanguageNotSupportedError
            ├── ProviderAccessError
            └── InvalidRequestError
```

---

## Exception Classes

### `TranslationError`

```python
class TranslationError(Exception)
```

Base exception for all translation lifecycle errors within the SHL ecosystem. All other SHL exceptions inherit from this class.

**Use Case**
- Catch-all for any translation-related failure when specific error type is not important.
- Base class for custom provider-specific exceptions.

**Example**
```python
from shl.exceptions import TranslationError

try:
    result = adapter.translate(request)
except TranslationError as e:
    # Catches any SHL translation error
    print(f"Translation failed: {e}")
```

---

### `ServiceUnavailableError`

```python
class ServiceUnavailableError(TranslationError)
```

Raised when an external translation microservice or mirror is down, timed out, or unreachable.

**Typical Causes**
- HTTP 500, 502, 503, 504 responses from provider.
- Network timeout (`socket.timeout`, `TimeoutError`).
- Socket/URL errors (`URLError`).
- TTL registry marks the service as temporarily unavailable.
- All providers in the failover chain have failed.

**Router Behavior**
- Microsoft Translator: marks service unavailable in `MicrosoftServiceRegistry`.
- LibreTranslate: blacklists the failing mirror.
- Router skips to the next provider in the priority list.

**Example**
```python
from shl.exceptions import ServiceUnavailableError

try:
    result = translate_text("Hello", target_lang="fi")
except ServiceUnavailableError:
    print("All translation services are currently unavailable.")
    # Fallback: display original text or cached result
```

---

### `RateLimitExceededError`

```python
class RateLimitExceededError(TranslationError)
```

Raised when an endpoint quota is depleted, IP limits trigger, or rate throttles activate.

**Typical Causes**
- HTTP 429 (Too Many Requests) from provider.
- Daily/monthly API quota exceeded.
- Per-IP rate limiting triggered.

**Router Behavior**
- Router immediately skips to the next provider in the priority list.
- No retry is attempted for the same provider (quota will not reset immediately).
- Not added to blacklist (quota may recover over time).

**Example**
```python
from shl.exceptions import RateLimitExceededError

try:
    result = translate_text("Hello", target_lang="fi")
except RateLimitExceededError:
    print("API quota exceeded. Trying next provider...")
```

---

### `LanguageNotSupportedError`

```python
class LanguageNotSupportedError(TranslationError)
```

Raised when the mapped language pair or structural locale variant is rejected by the provider.

**Typical Causes**
- Provider does not support the source → target language pair.
- HTTP 400 with language-related error from provider.
- Language pair is in the provider's runtime unsupported cache (e.g., PapagoRegistry, GoogleRegistry).

**Router Behavior**
- Papago: pair is added to `PapagoRegistry` blacklist for TTL duration.
- Google: pair is added to `GoogleRegistry` blacklist.
- LibreTranslate: pair is added to `LibreTranslateRegistry` blacklist.
- Router skips to the next provider.

**Example**
```python
from shl.exceptions import LanguageNotSupportedError

try:
    result = adapter.translate(request)
except LanguageNotSupportedError:
    print("This language pair is not supported by the provider.")
    # Try a different provider or fall back to base language
```

---

### `ProviderAccessError`

```python
class ProviderAccessError(TranslationError)
```

Raised when credentials fail, API keys are rejected, or endpoint access tokens expire.

**Typical Causes**
- HTTP 401 (Unauthorized) or 403 (Forbidden) from provider.
- Missing or invalid API key.
- Expired access token.
- Account suspended or disabled.

**Router Behavior**
- Router skips to the next provider.
- No blacklist is updated (credential issue is persistent, not transient).

**Example**
```python
from shl.exceptions import ProviderAccessError

try:
    result = adapter.translate(request)
except ProviderAccessError:
    print("Invalid API credentials. Please check your configuration.")
```

---

### `InvalidRequestError`

```python
class InvalidRequestError(TranslationError)
```

Raised when internal input parameter shapes, bad payloads, or corrupted strings trigger rejection.

**Typical Causes**
- HTTP 400 (Bad Request) from provider.
- HTTP 409, 413, 415, 422 from provider.
- Malformed JSON payload.
- Text exceeds provider's maximum length limit.
- Invalid formality or context parameter.

**Router Behavior**
- Papago: pair may be marked as unsupported (HTTP 400 ambiguity).
- Router skips to the next provider.
- If the request itself is malformed, all providers will likely fail.

**Example**
```python
from shl.exceptions import InvalidRequestError

try:
    result = adapter.translate(request)
except InvalidRequestError:
    print("The translation request was rejected by the provider.")
```

---

## HTTP Status Code Mapping

| Status Code | Exception | Notes |
|-------------|-----------|-------|
| `400` | `InvalidRequestError` | May also trigger `LanguageNotSupportedError` for Papago. |
| `401`, `403` | `ProviderAccessError` | Credential or permission issue. |
| `429` | `RateLimitExceededError` | Quota or rate limit exceeded. |
| `500`, `502`, `503`, `504` | `ServiceUnavailableError` | Server or gateway failure. |
| Timeout / Network | `ServiceUnavailableError` | Connection or socket timeout. |

---

## Usage Patterns

### Pattern 1: Catch-All

```python
from shl.exceptions import TranslationError

try:
    result = translate_text("Hello", target_lang="fi")
except TranslationError as e:
    # Handles any SHL translation failure
    print(f"Translation failed: {type(e).__name__}: {e}")
```

### Pattern 2: Granular Handling

```python
from shl.exceptions import (
    TranslationError,
    ServiceUnavailableError,
    RateLimitExceededError,
    LanguageNotSupportedError,
    ProviderAccessError,
    InvalidRequestError,
)

try:
    result = translate_text("Hello", target_lang="fi")
except ServiceUnavailableError:
    print("Service down — using cached fallback")
except RateLimitExceededError:
    print("Quota exceeded — try again later")
except LanguageNotSupportedError:
    print("Language not supported — skipping translation")
except ProviderAccessError:
    print("Invalid credentials — check API keys")
except InvalidRequestError:
    print("Bad request — check input parameters")
except TranslationError as e:
    print(f"Unexpected translation error: {e}")
```

### Pattern 3: Type Checking

```python
from shl.exceptions import TranslationError

def handle_error(error: TranslationError) -> str:
    if isinstance(error, ServiceUnavailableError):
        return "Service unavailable"
    elif isinstance(error, RateLimitExceededError):
        return "Rate limited"
    elif isinstance(error, LanguageNotSupportedError):
        return "Language not supported"
    elif isinstance(error, ProviderAccessError):
        return "Access denied"
    elif isinstance(error, InvalidRequestError):
        return "Invalid request"
    else:
        return "Unknown translation error"
```

### Pattern 4: Provider-Specific Handling

```python
from shl.providers.microsoft_translator import MicrosoftTranslatorAdapter
from shl.exceptions import ServiceUnavailableError, ProviderAccessError

adapter = MicrosoftTranslatorAdapter(api_key="key")

try:
    result = adapter.translate(request)
except ServiceUnavailableError:
    # Microsoft-specific: service marked unavailable for TTL duration
    print("Microsoft Translator temporarily unavailable")
except ProviderAccessError:
    # Check API key validity
    print("Microsoft API key invalid or expired")
```

---

## Router Exception Handling

The `translate_text_with_metadata()` function in `router.py` handles exceptions as follows:

| Exception | Action | Registry Effect |
|-----------|--------|-----------------|
| `LanguageNotSupportedError` | Skip to next provider. | Blacklist pair (Google, LibreTranslate, Papago). |
| `RateLimitExceededError` | Skip to next provider. | None. |
| `TranslationError` | Retry with backoff. | None. |
| Other exception | Skip to next provider. | Mark Microsoft unavailable (if MS service). |

---

## Extending the Taxonomy

To create a provider-specific exception that still integrates with SHL's catch-all handling:

```python
from shl.exceptions import TranslationError

class CustomProviderError(TranslationError):
    """Raised when a custom provider encounters a specific error."""
    def __init__(self, message: str, provider_code: int):
        super().__init__(message)
        self.provider_code = provider_code
```

---

## Thread Safety

All exception classes are stateless and thread-safe. They can be raised and caught concurrently without synchronization concerns.

---

## Changelog

| Version | Notes |
|---------|-------|
| 0.2.0 | Current — six-tier exception hierarchy: `TranslationError` base with `ServiceUnavailableError`, `RateLimitExceededError`, `LanguageNotSupportedError`, `ProviderAccessError`, and `InvalidRequestError`. |
