"""
Translation module for SHL.
"""

from shl import __version__

# Pääfunktiot
from .router import (
    translate_text,
    get_best_provider,
    get_all_supported_languages,
    get_libretranslate_mirror_stats,
    clear_unavailable_cache,
    get_unavailable_cache_stats,
)

# Välimuisti
from .cache import TranslationCache

# Metadata
from .metadata import TranslationRequest, TranslationResult

# Poikkeukset
from .exceptions import (
    TranslationError,
    ServiceUnavailableError,
    RateLimitExceededError,
    LanguageNotSupportedError,
    ProviderAccessError,
    InvalidRequestError,
)

# Providerit
from .providers.mymemory import MyMemoryAdapter
from .providers.libretranslate import LibreTranslateAdapter
from .providers.libretranslate import get_supported_languages

# Deprecated AITranslator (yhteensopivuus)
from .ai_translation_deprecated import AITranslator

__all__ = [
    "__version__",
    # Pääfunktiot
    "translate_text",
    "get_best_provider",
    "get_all_supported_languages",
    "get_supported_languages",
    "get_libretranslate_mirror_stats",
    "clear_unavailable_cache",
    "get_unavailable_cache_stats",
    # Välimuisti
    "TranslationCache",
    # Metadata
    "TranslationRequest",
    "TranslationResult",
    # Providerit
    "MyMemoryAdapter",
    "LibreTranslateAdapter",
    # Deprecated
    "AITranslator",
    # Poikkeukset
    "TranslationError",
    "ServiceUnavailableError",
    "RateLimitExceededError",
    "LanguageNotSupportedError",
    "ProviderAccessError",
    "InvalidRequestError",
]
