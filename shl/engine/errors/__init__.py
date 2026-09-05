"""
File: shl/engine/errors/__init__.py
Author: Tuomas Lähteenmäki
Version: 0.2.10
License: MIT
Description:
    Error handling package for SHL translation services.

    Provides the public interface for normalized error models,
    provider-independent error parsing, common SHL error codes,
    and provider-specific error definitions.
"""

from .models import NormalizedError
from .parser import ErrorParser

__all__ = [
    "ErrorParser",
    "NormalizedError",
]
