"""
File: shl/engine/errors/providers.py
Author: Tuomas Lähteenmäki
Version: 0.2.10
License: MIT
Description:
    Provider-specific error response definitions for SHL.

    Defines declarative mappings for translation service error
    responses, including multiple failure conditions, prioritized
    error code paths, message paths, and provider-specific error
    code mappings.

    Provider-specific parsing logic is intentionally excluded from
    this module. The generic ErrorParser uses these definitions to
    normalize provider errors into SHL error codes.
"""

from .codes import (
    ACCESS_DENIED,
    API_NOT_FOUND,
    AUTH_BLOCKED,
    AUTH_EXPIRED,
    AUTH_FAILED,
    INVALID_REQUEST,
    LANG_PAIR_UNSUPPORTED,
    LANG_UNSUPPORTED,
    METHOD_NOT_ALLOWED,
    NOT_FOUND,
    QUOTA_EXCEEDED,
    RATE_LIMIT_EXCEEDED,
    REQUEST_TOO_LONG,
    SERVICE_UNAVAILABLE,
    TEXT_TOO_LONG,
    TIMEOUT,
)


PAPAGO = {
    "failure_conditions": [
        {
            "path": ("data", "status"),
            "operator": "eq",
            "value": "FAILED",
        },
    ],
    "code_paths": (
        ("data", "errCode"),
    ),
    "message_paths": (
        ("data", "errMsg"),
    ),
    "error_codes": {
        "N2MT01": INVALID_REQUEST,
        "N2MT02": LANG_UNSUPPORTED,
        "N2MT03": INVALID_REQUEST,
        "N2MT04": LANG_UNSUPPORTED,
        "N2MT05": INVALID_REQUEST,
        "N2MT06": LANG_PAIR_UNSUPPORTED,
        "N2MT07": INVALID_REQUEST,
        "N2MT08": TEXT_TOO_LONG,
        "N2MT99": SERVICE_UNAVAILABLE,
        "LD01": INVALID_REQUEST,
        "LD99": SERVICE_UNAVAILABLE,
        "024": AUTH_FAILED,
        "051": API_NOT_FOUND,
        "200": AUTH_FAILED,
    },
}


MYMEMORY = {
    "failure_conditions": [
        {
            "path": ("responseStatus",),
            "operator": "ne",
            "value": 200,
        },
        {
            "path": ("quotaReached",),
            "operator": "eq",
            "value": True,
            "code": QUOTA_EXCEEDED,
        },
        {
            "path": ("responseData", "warning"),
            "operator": "exists",
        },
    ],
    "code_paths": (
        ("responseStatus",),
    ),
    "message_paths": (
        ("responseDetails",),
        ("responseData", "warning"),
    ),
    "error_codes": {
        400: INVALID_REQUEST,
        403: ACCESS_DENIED,
        404: NOT_FOUND,
        413: TEXT_TOO_LONG,
        414: REQUEST_TOO_LONG,
        429: RATE_LIMIT_EXCEEDED,
        500: SERVICE_UNAVAILABLE,
        502: SERVICE_UNAVAILABLE,
        503: SERVICE_UNAVAILABLE,
        504: SERVICE_UNAVAILABLE,
    },
}


LIBRETRANSLATE = {
    "failure_conditions": [
        {
            "path": ("error",),
            "operator": "exists",
        },
    ],
    "code_paths": (
        ("error", "code"),
    ),
    "message_paths": (
        ("error",),
    ),
    "error_codes": {
        400: INVALID_REQUEST,
        403: ACCESS_DENIED,
        404: NOT_FOUND,
        405: METHOD_NOT_ALLOWED,
        413: TEXT_TOO_LONG,
        414: REQUEST_TOO_LONG,
        429: RATE_LIMIT_EXCEEDED,
        500: SERVICE_UNAVAILABLE,
        503: SERVICE_UNAVAILABLE,
        1010: ACCESS_DENIED,
    },
}


DEEPL = {
    "failure_conditions": [
        {
            "path": ("message",),
            "operator": "exists",
        },
    ],
    "code_paths": (
        ("code",),
        ("status",),
    ),
    "message_paths": (
        ("message",),
        ("detail",),
    ),
    "error_codes": {
        400: INVALID_REQUEST,
        403: AUTH_FAILED,
        404: NOT_FOUND,
        413: TEXT_TOO_LONG,
        414: REQUEST_TOO_LONG,
        429: RATE_LIMIT_EXCEEDED,
        456: QUOTA_EXCEEDED,
        500: SERVICE_UNAVAILABLE,
        502: SERVICE_UNAVAILABLE,
        503: SERVICE_UNAVAILABLE,
        504: SERVICE_UNAVAILABLE,
    },
}


GOOGLE = {
    "failure_conditions": [
        {
            "path": ("error",),
            "operator": "exists",
        },
    ],
    "code_paths": (
        ("error", "status"),
        ("error", "code"),
    ),
    "message_paths": (
        ("error", "message"),
        ("error", "details"),
    ),
    "error_codes": {
        400: INVALID_REQUEST,
        403: ACCESS_DENIED,
        404: NOT_FOUND,
        429: RATE_LIMIT_EXCEEDED,
        500: SERVICE_UNAVAILABLE,
        503: SERVICE_UNAVAILABLE,
        "INVALID_ARGUMENT": INVALID_REQUEST,
        "PERMISSION_DENIED": ACCESS_DENIED,
        "RESOURCE_EXHAUSTED": QUOTA_EXCEEDED,
        "INTERNAL": SERVICE_UNAVAILABLE,
        "UNAVAILABLE": SERVICE_UNAVAILABLE,
    },
}


MICROSOFT = {
    "failure_conditions": [
        {
            "path": ("error",),
            "operator": "exists",
        },
    ],
    "code_paths": (
        ("error", "code"),
    ),
    "message_paths": (
        ("error", "message"),
    ),
    "error_codes": {
        400036: LANG_UNSUPPORTED,
        400074: INVALID_REQUEST,
        401000: AUTH_FAILED,
        401001: AUTH_FAILED,
        401002: AUTH_EXPIRED,
        403000: ACCESS_DENIED,
        403001: QUOTA_EXCEEDED,
        413000: TEXT_TOO_LONG,
        429000: RATE_LIMIT_EXCEEDED,
        500000: SERVICE_UNAVAILABLE,
        502000: SERVICE_UNAVAILABLE,
        503000: SERVICE_UNAVAILABLE,
        504000: SERVICE_UNAVAILABLE,
    },
}


YANDEX = {
    "failure_conditions": [
        {
            "path": ("code",),
            "operator": "exists",
        },
    ],
    "code_paths": (
        ("code",),
    ),
    "message_paths": (
        ("message",),
    ),
    "error_codes": {
        400: INVALID_REQUEST,
        401: AUTH_FAILED,
        402: AUTH_BLOCKED,
        403: RATE_LIMIT_EXCEEDED,
        404: NOT_FOUND,
        413: TEXT_TOO_LONG,
        415: INVALID_REQUEST,
        422: LANG_UNSUPPORTED,
        501: LANG_PAIR_UNSUPPORTED,
        503: SERVICE_UNAVAILABLE,
    },
}
LOCAL = {
    "failure_conditions": [
        {
            "path": ("error",),
            "operator": "exists",
        },
    ],
    "code_paths": (
        ("error", "code"),
    ),
    "message_paths": (
        ("error", "message"),
        ("error",),
    ),
    "error_codes": {
        400: INVALID_REQUEST,
        401: ACCESS_DENIED,
        402: ACCESS_DENIED,
        403: ACCESS_DENIED,
        408: TIMEOUT,
        413: TEXT_TOO_LONG,
        414: REQUEST_TOO_LONG,
        429: RATE_LIMIT_EXCEEDED,
        456: QUOTA_EXCEEDED,
        500: SERVICE_UNAVAILABLE,
        502: SERVICE_UNAVAILABLE,
        503: SERVICE_UNAVAILABLE,
        504: SERVICE_UNAVAILABLE,
    },
}
