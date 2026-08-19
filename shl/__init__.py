"""
Self-Healing Localization Layer (SHL)
A lightweight, dependency-free Python library that eliminates missing translations forever.
"""

from shl._version import (
    __version__,
    __author__,
    __license__,
)

from shl.logging_config import (
    setup_logging,
    get_logger,
    set_level,
    get_log_stats,
)
from shl.language_validator import LanguageValidator
from shl.utils.lang_utils import (
    parse_bcp47,
    normalize_full_tag,
    base_language,
    has_region,
    get_parent,
    split_tag
)

# Uusi translation-moduuli
from shl.engine.translation import (
    # Pääfunktiot
    translate_text,
    get_best_provider,
    get_supported_languages,
    get_libretranslate_mirror_stats,
    # Välimuisti
    TranslationCache,
    # Metadata
    TranslationRequest,
    TranslationResult,
    # Apufunktiot
    clear_unavailable_cache,
    get_unavailable_cache_stats,
    # Providerit (suoraan)
    MyMemoryAdapter,
    LibreTranslateAdapter,
    # Poikkeukset
    TranslationError,
    RateLimitExceededError,
    ServiceUnavailableError,
    LanguageNotSupportedError,
    ProviderAccessError,
    InvalidRequestError,
)

__all__ = [
    # Versio
    "__version__",
    "__author__",
    "__license__",
    # Logging
    "setup_logging",
    "get_logger",
    "set_level",
    "get_log_stats",
    # Core
    "LanguageValidator",
    # Lang utils
    "parse_bcp47",
    "normalize_full_tag",
    "base_language",
    "has_region",
    "get_parent",
    "split_tag",
    # Translation - pääfunktiot
    "translate_text",
    "get_best_provider",
    "get_libretranslate_mirror_stats",
    # Translation - cache
    "TranslationCache",
    # Translation - metadata
    "TranslationRequest",
    "TranslationResult",
    # Translation - apufunktiot
    "clear_unavailable_cache",
    "get_unavailable_cache_stats",
    # Translation - providerit
    "MyMemoryAdapter",
    "LibreTranslateAdapter",
    "DeepLAdapter",
    "GoogleV2Adapter",
    "PapagoAdapter",
    "MicrosoftTranslatorAdapter",
    # Translation - poikkeukset
    "TranslationError",
    "RateLimitExceededError",
    "ServiceUnavailableError",
    "LanguageNotSupportedError",
    "ProviderAccessError",
    "InvalidRequestError",
]
