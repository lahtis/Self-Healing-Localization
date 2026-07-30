"""
Self-Healing Localization Layer (SHL)
A lightweight, dependency-free Python library that eliminates missing translations forever.
"""

from shl.logging_config import setup_logging, get_logger
from shl.language_validator import LanguageValidator
from shl.utils.lang_utils import (
    parse_bcp47,
    normalize_full_tag,
    base_language,
    has_region,
    get_parent,
    split_tag
)
from shl.engine.ai_translation import (
    translate_text,
    AITranslator,
    TranslationCache,
    get_supported_languages,
    get_all_supported_languages,
    get_best_provider,
    RateLimitExceededError,
    ServiceUnavailableError,
    LanguageNotSupportedError,
    ProviderAccessError,
    InvalidRequestError,
    TranslationError
)

__version__ = "0.2.0"
__author__ = "Tuomas Lähteenmäki"
__license__ = "MIT"

__all__ = [
    # Core
    'LanguageValidator',
    'setup_logging',
    'get_logger',
    # Lang utils
    'parse_bcp47',
    'normalize_full_tag',
    'base_language',
    'has_region',
    'get_parent',
    'split_tag',
    # Translation
    'translate_text',
    'AITranslator',
    'TranslationCache',
    'get_supported_languages',
    'get_all_supported_languages',
    'get_best_provider',
    # Errors
    'RateLimitExceededError',
    'ServiceUnavailableError',
    'LanguageNotSupportedError',
    'ProviderAccessError',
    'InvalidRequestError',
    'TranslationError',
]
