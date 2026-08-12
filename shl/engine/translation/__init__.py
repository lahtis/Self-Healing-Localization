"""
File: __init__.py — translation module initialization for SHL.
Author: Tuomas Lähteenmäki
Version: 0.2.0
License: MIT
Description: Central export manifest for the SHL translation subsystem.
             Exposes routing interfaces, provider adapters, caching mechanics,
             and exception taxonomy under a unified public API namespace.
"""

from shl._version import __version__

# Core Routing Functions
from .router import (
    translate_text,
    translate_text_with_metadata,
    get_best_provider,
    get_provider_priority,
    get_all_supported_languages,
    get_libretranslate_mirror_stats,
    clear_unavailable_cache,
    get_unavailable_cache_stats,
)

# Cache Management
from .cache import TranslationCache

# Metadata and Data Structures
from .metadata import TranslationRequest, TranslationResult

# Exception Taxonomy
from .exceptions import (
    TranslationError,
    ServiceUnavailableError,
    RateLimitExceededError,
    LanguageNotSupportedError,
    ProviderAccessError,
    InvalidRequestError,
)

# Provider Adapters and Language Utilities
from .providers.mymemory import MyMemoryAdapter
from .providers.libretranslate import (
    LibreTranslateAdapter,
    get_supported_languages,
)
from .providers.deepl import DeepLAdapter
from .providers.googlev2 import GoogleV2Adapter

__all__ = [
    "__version__",
    
    # Core Routing Functions
    "translate_text",
    "translate_text_with_metadata",
    "get_best_provider",
    "get_provider_priority",
    "get_all_supported_languages",
    "get_supported_languages",
    "get_libretranslate_mirror_stats",
    "clear_unavailable_cache",
    "get_unavailable_cache_stats",
    
    # Cache Management
    "TranslationCache",
    
    # Metadata and Data Structures
    "TranslationRequest",
    "TranslationResult",
    
    # Provider Adapters
    "MyMemoryAdapter",
    "LibreTranslateAdapter",
    "DeepLAdapter",
    "GoogleV2Adapter",
        
    # Exception Taxonomy
    "TranslationError",
    "ServiceUnavailableError",
    "RateLimitExceededError",
    "LanguageNotSupportedError",
    "ProviderAccessError",
    "InvalidRequestError",
]
