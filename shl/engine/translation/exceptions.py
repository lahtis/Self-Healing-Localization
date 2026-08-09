"""
File: exceptions.py — module for Translation exceptions for SHL.
Author: Tuomas Lähteenmäki
Version: 0.2.0
License: MIT
Description: Explicit error taxonomy for isolating, capturing, and managing
             upstream client network errors, quotas, and structural anomalies.
"""


class TranslationError(Exception):
    """Base exception for all translation lifecycle errors within the SHL ecosystem."""
    pass


class ServiceUnavailableError(TranslationError):
    """Raised when an external translation microservice or mirror is down, timed out, or unreachable."""
    pass


class RateLimitExceededError(TranslationError):
    """Raised when an endpoint quota is depleted, IP limits trigger, or rate throttles activate."""
    pass


class LanguageNotSupportedError(TranslationError):
    """Raised when the mapped language pair or structural locale variant is rejected by the provider."""
    pass


class ProviderAccessError(TranslationError):
    """Raised when credentials fail, API keys are rejected, or endpoint access tokens expire."""
    pass


class InvalidRequestError(TranslationError):
    """Raised when internal input parameter shapes, bad payloads, or corrupted strings trigger rejection."""
    pass
