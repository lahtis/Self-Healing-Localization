"""
File: __init__.py
Author: Tuomas Lähteenmäki
Version: 0.2.10
License: MIT
Description:
    Translation memory providers for SHL.

    Provides provider-independent memory backends for storing
    translation results and optionally publishing translations
    to external translation memory services.
"""

from .mymemory import (
    MyMemoryAuthError,
    MyMemoryBackend,
    MyMemoryError,
    MyMemoryHTTPError,
    MyMemoryNotFoundError,
    MyMemoryValidationError,
)

__all__ = [
    "MyMemoryAuthError",
    "MyMemoryBackend",
    "MyMemoryError",
    "MyMemoryHTTPError",
    "MyMemoryNotFoundError",
    "MyMemoryValidationError",
]
