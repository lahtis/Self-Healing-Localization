# tests/test_parser.py
"""
File: tests/test_parser.py
Author: Tuomas Lähteenmäki
Version: 0.2.9
License: MIT
Description:
Tests for the provider-independent SHL error parser.

Verifies successful responses, HTTP error normalization,
provider-specific error mappings, declarative failure conditions,
exception handling, and retry semantics.
"""

import pytest

from shl.engine.errors.codes import (
    ACCESS_DENIED,
    AUTH_FAILED,
    INVALID_REQUEST,
    INVALID_RESPONSE,
    LANG_UNSUPPORTED,
    METHOD_NOT_ALLOWED,
    NOT_FOUND,
    QUOTA_EXCEEDED,
    RATE_LIMIT_EXCEEDED,
    REQUEST_TOO_LONG,
    SERVICE_UNAVAILABLE,
    TEXT_TOO_LONG,
    TIMEOUT,
    UNKNOWN_ERROR,
)
from shl.engine.errors.parser import ErrorParser


def test_successful_response_returns_none():
    """Successful HTTP responses must not produce an error."""
    parser = ErrorParser("test_provider")

    result = parser.parse(
        response={"translatedText": "Hello"},
        http_status=200,
    )

    assert result is None


def test_successful_response_without_http_status_returns_invalid_response():
    """A response without status information cannot be assumed successful."""
    parser = ErrorParser("test_provider")

    result = parser.parse(
        response={"translatedText": "Hello"},
    )

    assert result is not None
    assert result.code == INVALID_RESPONSE


def test_http_400_maps_to_invalid_request():
    """HTTP 400 must map to INVALID_REQUEST."""
    parser = ErrorParser("test_provider")

    result = parser.parse(
        response={"error": "bad request"},
        http_status=400,
    )

    assert result is not None
    assert result.code == INVALID_REQUEST
    assert result.http_status == 400


def test_http_401_maps_to_auth_failed():
    """HTTP 401 must map to AUTH_FAILED."""
    parser = ErrorParser("test_provider")

    result = parser.parse(
        response={"error": "unauthorized"},
        http_status=401,
    )

    assert result is not None
    assert result.code == AUTH_FAILED


def test_http_403_maps_to_access_denied():
    """HTTP 403 must map to ACCESS_DENIED."""
    parser = ErrorParser("test_provider")

    result = parser.parse(
        response={"error": "forbidden"},
        http_status=403,
    )

    assert result is not None
    assert result.code == ACCESS_DENIED


def test_http_404_maps_to_not_found():
    """HTTP 404 must map to NOT_FOUND."""
    parser = ErrorParser("test_provider")

    result = parser.parse(
        response={"error": "not found"},
        http_status=404,
    )

    assert result is not None
    assert result.code == NOT_FOUND

def test_http_405_maps_to_method_not_allowed():
    """HTTP 405 must map to METHOD_NOT_ALLOWED."""
    parser = ErrorParser("test_provider")

    result = parser.parse(
        response={"error": "method not allowed"},
        http_status=405,
    )

    assert result is not None
    assert result.code == METHOD_NOT_ALLOWED

def test_http_408_maps_to_timeout():
    """HTTP 408 must map to TIMEOUT."""
    parser = ErrorParser("test_provider")

    result = parser.parse(
        response={"error": "timeout"},
        http_status=408,
    )

    assert result is not None
    assert result.code == TIMEOUT
    assert result.temporary is True
    assert result.retryable is True


def test_http_413_maps_to_text_too_long():
    """HTTP 413 must map to TEXT_TOO_LONG."""
    parser = ErrorParser("test_provider")

    result = parser.parse(
        response={"error": "payload too large"},
        http_status=413,
    )

    assert result is not None
    assert result.code == TEXT_TOO_LONG


def test_http_414_maps_to_request_too_long():
    """HTTP 414 must map to REQUEST_TOO_LONG."""
    parser = ErrorParser("test_provider")

    result = parser.parse(
        response={"error": "URI too long"},
        http_status=414,
    )

    assert result is not None
    assert result.code == REQUEST_TOO_LONG


def test_http_429_maps_to_rate_limit_exceeded():
    """HTTP 429 must map to RATE_LIMIT_EXCEEDED."""
    parser = ErrorParser("test_provider")

    result = parser.parse(
        response={"error": "too many requests"},
        http_status=429,
    )

    assert result is not None
    assert result.code == RATE_LIMIT_EXCEEDED
    assert result.temporary is True
    assert result.retryable is True


def test_http_500_maps_to_service_unavailable():
    """HTTP 500 must map to SERVICE_UNAVAILABLE."""
    parser = ErrorParser("test_provider")

    result = parser.parse(
        response={"error": "server error"},
        http_status=500,
    )

    assert result is not None
    assert result.code == SERVICE_UNAVAILABLE
    assert result.temporary is True
    assert result.retryable is True


def test_http_502_maps_to_service_unavailable():
    """HTTP 502 must map to SERVICE_UNAVAILABLE."""
    parser = ErrorParser("test_provider")

    result = parser.parse(
        response={"error": "bad gateway"},
        http_status=502,
    )

    assert result is not None
    assert result.code == SERVICE_UNAVAILABLE


def test_http_503_maps_to_service_unavailable():
    """HTTP 503 must map to SERVICE_UNAVAILABLE."""
    parser = ErrorParser("test_provider")

    result = parser.parse(
        response={"error": "service unavailable"},
        http_status=503,
    )

    assert result is not None
    assert result.code == SERVICE_UNAVAILABLE


def test_http_504_maps_to_service_unavailable():
    """HTTP 504 must map to SERVICE_UNAVAILABLE."""
    parser = ErrorParser("test_provider")

    result = parser.parse(
        response={"error": "gateway timeout"},
        http_status=504,
    )

    assert result is not None
    assert result.code == SERVICE_UNAVAILABLE


def test_unknown_http_status_maps_to_unknown_error():
    """Unknown HTTP statuses must map to UNKNOWN_ERROR."""
    parser = ErrorParser("test_provider")

    result = parser.parse(
        response={"error": "unknown"},
        http_status=418,
    )

    assert result is not None
    assert result.code == UNKNOWN_ERROR


def test_broken_json_returns_invalid_response():
    """Invalid JSON must produce INVALID_RESPONSE."""
    parser = ErrorParser("test_provider")

    result = parser.parse(
        response="{this is not valid json}",
        http_status=200,
    )

    assert result is not None
    assert result.code == INVALID_RESPONSE


def test_empty_response_returns_invalid_response():
    """An empty response must produce INVALID_RESPONSE."""
    parser = ErrorParser("test_provider")

    result = parser.parse(
        response=None,
        http_status=200,
    )

    assert result is not None
    assert result.code == INVALID_RESPONSE


def test_provider_code_is_mapped():
    """Known provider codes must override generic HTTP classification."""
    parser = ErrorParser(
        "test_provider",
        {
            "code_paths": (
                ("error", "code"),
            ),
            "message_paths": (
                ("error", "message"),
            ),
            "error_codes": {
                "E_LANG": LANG_UNSUPPORTED,
            },
        },
    )

    result = parser.parse(
        response={
            "error": {
                "code": "E_LANG",
                "message": "Language is not supported.",
            },
        },
        http_status=400,
    )

    assert result is not None
    assert result.code == LANG_UNSUPPORTED
    assert result.provider_code == "E_LANG"
    assert result.message == "Language is not supported."


def test_numeric_provider_code_string_is_mapped():
    """Numeric provider codes represented as strings must be normalized."""
    parser = ErrorParser(
        "test_provider",
        {
            "code_paths": (
                ("error", "code"),
            ),
            "error_codes": {
                401002: AUTH_FAILED,
            },
        },
    )

    result = parser.parse(
        response={
            "error": {
                "code": "401002",
            },
        },
        http_status=401,
    )

    assert result is not None
    assert result.code == AUTH_FAILED
    assert result.provider_code == "401002"


def test_failure_condition_can_define_explicit_code():
    """A failure condition may provide its own SHL error code."""
    parser = ErrorParser(
        "test_provider",
        {
            "failure_conditions": (
                {
                    "path": ("quotaReached",),
                    "operator": "eq",
                    "value": True,
                    "code": QUOTA_EXCEEDED,
                },
            ),
        },
    )

    result = parser.parse(
        response={
            "quotaReached": True,
        },
        http_status=200,
    )

    assert result is not None
    assert result.code == QUOTA_EXCEEDED
    assert result.temporary is True
    assert result.retryable is False


def test_failure_condition_overrides_http_status():
    """An explicit failure condition must take priority over HTTP status."""
    parser = ErrorParser(
        "test_provider",
        {
            "failure_conditions": (
                {
                    "path": ("quotaReached",),
                    "operator": "eq",
                    "value": True,
                    "code": QUOTA_EXCEEDED,
                },
            ),
        },
    )

    result = parser.parse(
        response={
            "quotaReached": True,
        },
        http_status=200,
    )

    assert result is not None
    assert result.code == QUOTA_EXCEEDED


def test_failure_condition_exists_operator():
    """The exists operator must detect configured fields."""
    parser = ErrorParser(
        "test_provider",
        {
            "failure_conditions": (
                {
                    "path": ("error",),
                    "operator": "exists",
                    "code": INVALID_REQUEST,
                },
            ),
        },
    )

    result = parser.parse(
        response={
            "error": "Invalid request",
        },
        http_status=200,
    )

    assert result is not None
    assert result.code == INVALID_REQUEST


def test_failure_condition_eq_operator():
    """The eq operator must match exact values."""
    parser = ErrorParser(
        "test_provider",
        {
            "failure_conditions": (
                {
                    "path": ("status",),
                    "operator": "eq",
                    "value": "FAILED",
                    "code": SERVICE_UNAVAILABLE,
                },
            ),
        },
    )

    result = parser.parse(
        response={
            "status": "FAILED",
        },
        http_status=200,
    )

    assert result is not None
    assert result.code == SERVICE_UNAVAILABLE


def test_failure_condition_ne_operator():
    """The ne operator must detect values different from expected."""
    parser = ErrorParser(
        "test_provider",
        {
            "failure_conditions": (
                {
                    "path": ("status",),
                    "operator": "ne",
                    "value": 200,
                    "code": INVALID_REQUEST,
                },
            ),
        },
    )

    result = parser.parse(
        response={
            "status": 500,
        },
        http_status=200,
    )

    assert result is not None
    assert result.code == INVALID_REQUEST


def test_failure_condition_in_operator():
    """The in operator must match one of several values."""
    parser = ErrorParser(
        "test_provider",
        {
            "failure_conditions": (
                {
                    "path": ("status",),
                    "operator": "in",
                    "value": [400, 401, 403],
                    "code": ACCESS_DENIED,
                },
            ),
        },
    )

    result = parser.parse(
        response={
            "status": 403,
        },
        http_status=200,
    )

    assert result is not None
    assert result.code == ACCESS_DENIED


def test_failure_condition_not_in_operator():
    """The not_in operator must reject configured values."""
    parser = ErrorParser(
        "test_provider",
        {
            "failure_conditions": (
                {
                    "path": ("status",),
                    "operator": "not_in",
                    "value": [200, 201],
                    "code": INVALID_REQUEST,
                },
            ),
        },
    )

    result = parser.parse(
        response={
            "status": 500,
        },
        http_status=200,
    )

    assert result is not None
    assert result.code == INVALID_REQUEST


def test_timeout_exception_is_normalized():
    """Timeout exceptions must map to TIMEOUT."""
    parser = ErrorParser("test_provider")

    result = parser.parse(
        exception=TimeoutError(
            "Provider request timed out.",
        ),
    )

    assert result is not None
    assert result.code == TIMEOUT
    assert result.temporary is True
    assert result.retryable is True


def test_connection_exception_is_normalized():
    """Connection exceptions must map to SERVICE_UNAVAILABLE."""
    parser = ErrorParser("test_provider")

    result = parser.parse(
        exception=ConnectionError(
            "Provider connection failed.",
        ),
    )

    assert result is not None
    assert result.code == SERVICE_UNAVAILABLE
    assert result.temporary is True
    assert result.retryable is True


def test_unknown_exception_is_normalized():
    """Unknown exceptions must map to UNKNOWN_ERROR."""
    parser = ErrorParser("test_provider")

    result = parser.parse(
        exception=RuntimeError(
            "Unexpected provider failure.",
        ),
    )

    assert result is not None
    assert result.code == UNKNOWN_ERROR


def test_parser_preserves_provider_name():
    """Normalized errors must preserve the provider name."""
    parser = ErrorParser("test_provider")

    result = parser.parse(
        response={"error": "bad request"},
        http_status=400,
    )

    assert result is not None
    assert result.provider == "test_provider"


def test_parser_preserves_error_message():
    """Normalized errors should preserve the available error message."""
    parser = ErrorParser(
        "test_provider",
        {
            "message_paths": (
                ("error", "message"),
            ),
        },
    )

    result = parser.parse(
        response={
            "error": {
                "message": "Something went wrong.",
            },
        },
        http_status=500,
    )

    assert result is not None
    assert result.message == "Something went wrong."

# ---------------------------------------------------------------------------
# Run tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main(["-v", __file__])
