"""
File: __init__.py
Author: Tuomas Lähteenmäki
Version: 0.2.12
License: MIT
Description:
    Translation memory providers for SHL.

    Provides provider-independent memory backends for storing
    translation results and optionally publishing translations
    to external translation memory services.
"""

from .private_mymemory import (
    MyMemoryAlreadyExistsError,      
    MyMemoryAuthError,
    MyMemoryError,
    MyMemoryHTTPError,
    MyMemoryNotFoundError,
    MyMemoryValidationError,
    PrivateMyMemoryBackend,
)

__all__ = [
    "MyMemoryAlreadyExistsError",    
    "MyMemoryAuthError",
    "MyMemoryError",
    "MyMemoryHTTPError",
    "MyMemoryNotFoundError",
    "MyMemoryValidationError",
    "PrivateMyMemoryBackend",
]
