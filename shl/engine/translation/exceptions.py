"""
Translation exceptions for SHL.
"""


class TranslationError(Exception):
    """Base exception for translation errors."""
    pass


class ServiceUnavailableError(TranslationError):
    """Translation service is down or unreachable."""
    pass


class RateLimitExceededError(TranslationError):
    """Rate limit or quota exceeded."""
    pass


class LanguageNotSupportedError(TranslationError):
    """Language not supported by the service."""
    pass


class ProviderAccessError(TranslationError):
    """Access denied (banned, invalid API key, etc.)."""
    pass


class InvalidRequestError(TranslationError):
    """Invalid request (bad parameters, etc.)."""
    pass
