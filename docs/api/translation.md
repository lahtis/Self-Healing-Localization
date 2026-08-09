# Translation API

## translate_text()

```python
from shl.engine.translation import translate_text

result = translate_text(
    text="Hello",
    target_lang="fi",
    source_lang="en",		# Optional, auto-detected if omitted
    use_cache=True,			# Cache results to reduce API calls
    smart_routing=True,		# Route request dynamically to best provider
    max_retries=2,
    retry_delay=1,
)
```

---

## Translation Functions

| Function | Description |
|---|---|
| `translate_text()` | Main translation function with smart provider routing and caching. |
| `get_best_provider()` | Select the best available translation provider for a language pair. |
| `get_all_supported_languages()` | Get combined list of supported languages from all configured providers. |
| `get_supported_languages()` | Get list of supported languages specifically from LibreTranslate. |

---

## Exceptions

| Exception | Description |
|---|---|
| `TranslationError` | Base exception for all translation-related errors. |
| `RateLimitExceededError` | Raised when a provider rate limit or daily character quota is exceeded. |
| `ServiceUnavailableError` | Raised when a translation provider or mirror is completely unreachable. |
| `LanguageNotSupportedError` | Raised when the requested language pair is not supported by available providers. |
| `ProviderAccessError` | Raised when access to a provider is denied or API key authentication fails. |
| `InvalidRequestError` | Raised when the translation payload or parameters are malformed. |

---
