## `doc/api/translation.md`

# Translation API

## translate_text()

```python
from shl.engine.translation import translate_text

result = translate_text(
    text="Hello",
    target_lang="fi",
    source_lang="en",
    use_cache=True,
    smart_routing=True,
    max_retries=2,
    retry_delay=1,
)
```

---

## Translation Functions

| Function | Description |
|---|---|
| `translate_text()` | Main translation function with smart routing. |
| `get_best_provider()` | Select the best provider for a language pair. |
| `get_all_supported_languages()` | Get supported languages from all providers. |
| `get_supported_languages()` | Get supported languages from LibreTranslate. |

---

## Exceptions

| Exception | Description |
|---|---|
| `TranslationError` | Base exception for translation errors. |
| `RateLimitExceededError` | Raised when a provider rate limit or quota is exceeded. |
| `ServiceUnavailableError` | Raised when a translation provider is unavailable. |
| `LanguageNotSupportedError` | Raised when the requested language is not supported. |
| `ProviderAccessError` | Raised when access to a provider is denied or authentication fails. |
| `InvalidRequestError` | Raised when the translation request is invalid. |

---
