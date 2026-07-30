"""
SHL engine package.
"""

from shl.engine.core import LocalizationEngine
from shl.engine.localizer import Localizer
from shl.engine.template_localizer import TemplateLocalizer
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

__all__ = [
    'LocalizationEngine',
    'Localizer',
    'TemplateLocalizer',
    'AITranslator',
    'TranslationCache',
    'translate_text',
    'get_supported_languages',
    'get_all_supported_languages',
    'get_best_provider',
    'RateLimitExceededError',
    'ServiceUnavailableError',
    'LanguageNotSupportedError',
    'ProviderAccessError',
    'InvalidRequestError',
    'TranslationError',
]
