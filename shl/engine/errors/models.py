"""
File: shl/engine/errors/models.py
Author: Tuomas Lähteenmäki
Version: 0.2.10
License: MIT
Description:
    Data models for normalized SHL translation service errors.

    Defines immutable data structures used to represent normalized
    provider errors after they have been processed by the generic
    error parser.

    The models are provider-independent and contain both the SHL
    normalized error information and relevant provider-specific
    diagnostic details.
"""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class NormalizedError:
    code: str
    provider: str
    message: Optional[str] = None
    temporary: bool = False
    retryable: bool = False
    http_status: Optional[int] = None
    provider_code: Optional[str] = None
    details: Optional[Any] = None
