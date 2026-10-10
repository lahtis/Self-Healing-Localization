"""
File: shl/engine/errors/codes.py
Author: Tuomas Lähteenmäki
Version: 0.3.0
License: MIT
Description:
    Common error codes used by the SHL error handling system.

    Defines provider-independent error categories used to normalize
    translation service errors across different providers.

    Provider-specific error codes are mapped to these shared SHL
    codes by the provider definitions. The codes provide a stable
    error vocabulary for routing, fallback handling, retry logic,
    monitoring, and diagnostics.
"""

# Request errors
INVALID_REQUEST = "INVALID_REQUEST"
REQUEST_TOO_LONG = "REQUEST_TOO_LONG"
TEXT_TOO_LONG = "TEXT_TOO_LONG"
METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"

# Language errors
LANG_UNSUPPORTED = "LANG_UNSUPPORTED"
LANG_PAIR_UNSUPPORTED = "LANG_PAIR_UNSUPPORTED"

# Authentication and access errors
AUTH_FAILED = "AUTH_FAILED"
AUTH_EXPIRED = "AUTH_EXPIRED"
AUTH_BLOCKED = "AUTH_BLOCKED"
ACCESS_DENIED = "ACCESS_DENIED"
API_NOT_FOUND = "API_NOT_FOUND"

# Usage and quota errors
RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
QUOTA_EXCEEDED = "QUOTA_EXCEEDED"

# Resource errors
NOT_FOUND = "NOT_FOUND"
ALREADY_EXISTS = "ALREADY_EXISTS"

# Service errors
TIMEOUT = "TIMEOUT"
SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"

# Transport and security errors
NETWORK_ERROR = "NETWORK_ERROR"
SECURITY_VIOLATION = "SECURITY_VIOLATION"

# Response errors
INVALID_RESPONSE = "INVALID_RESPONSE"
RESPONSE_TOO_LARGE = "RESPONSE_TOO_LARGE"
INVALID_CONTENT_TYPE = "INVALID_CONTENT_TYPE"

# Unknown
UNKNOWN_ERROR = "UNKNOWN_ERROR"
