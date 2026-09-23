
"""
File: test_detection_router.py
Author: Tuomas Lähteenmäki
License: MIT
Description:
    Tests for SHL language detection router policy handling,
    error parsing, and retry behavior.
"""

from unittest.mock import Mock, patch

import pytest

from shl.engine.language_detection.detection_router import (
    _get_error_parser,
    get_provider_retry,
)


def test_detectlanguage_policy_retry_is_resolved():
    """DetectLanguage retry count must be read from policy."""

    with patch(
        "shl.engine.language_detection.detection_router._USE_POLICY",
        True,
    ), patch(
        "shl.engine.language_detection.detection_router._policy"
    ) as policy:

        policy.get.return_value = {
            "providers": {
                "DetectLanguage": {
                    "enabled": True,
                    "retry": 2,
                }
            }
        }

        policy.get_retry.return_value = 2

        retry_count = get_provider_retry(
            "detectlanguage",
        )

        assert retry_count == 2

        policy.get_retry.assert_called_once_with(
            "DetectLanguage",
            default=0,
        )


def test_detectlanguage_uses_central_error_definition():
    """DetectLanguage must use its central provider error definition."""

    parser = _get_error_parser(
        "detectlanguage",
    )

    assert parser.provider == "detectlanguage"
    assert parser.config is not None

    assert parser.config["error_codes"][429] == (
        "RATE_LIMIT_EXCEEDED"
    )


def test_retryable_detectlanguage_error_is_retryable():
    """HTTP 429 must normalize as a retryable error."""

    parser = _get_error_parser(
        "detectlanguage",
    )

    error = parser.parse(
        exception=RuntimeError(
            "DetectLanguage rate limit"
        ),
        http_status=429,
    )

    assert error is not None
    assert error.code == "RATE_LIMIT_EXCEEDED"
    assert error.retryable is True
    assert error.temporary is True


def test_non_retryable_detectlanguage_error_is_not_retryable():
    """HTTP 401 must not trigger a retry."""

    parser = _get_error_parser(
        "detectlanguage",
    )

    error = parser.parse(
        exception=RuntimeError(
            "DetectLanguage authentication failed"
        ),
        http_status=401,
    )

    assert error is not None
    assert error.code == "AUTH_FAILED"
    assert error.retryable is False


def test_detectlanguage_retry_loop_retries_retryable_error():
    """Router must retry a retryable provider error according to policy."""

    from shl.engine.language_detection import detection_router

    adapter = Mock()

    adapter.detect.side_effect = [
        RuntimeError("temporary failure"),
        [
            Mock(
                language="fi",
                score=0.99,
                provider="detectlanguage",
            )
        ],
    ]

    with patch(
        "shl.engine.language_detection.detection_router._USE_POLICY",
        True,
    ), patch(
        "shl.engine.language_detection.detection_router._policy"
    ) as policy, patch(
        "shl.engine.language_detection.detection_router._create_provider",
        return_value=adapter,
    ), patch(
        "shl.engine.language_detection.detection_router._get_error_parser"
    ) as get_parser:

        policy.get.return_value = {
            "providers": {
                "DetectLanguage": {
                    "enabled": True,
                    "retry": 2,
                }
            }
        }

        policy.get_retry.return_value = 2
        policy.get_timeout.return_value = 10.0

        parser = Mock()

        normalized_error = Mock()
        normalized_error.retryable = True

        parser.parse.return_value = normalized_error
        get_parser.return_value = parser

        with patch(
            "shl.engine.language_detection.detection_router.get_provider_priority",
            return_value=["detectlanguage"],
        ):

            results = detection_router.detect_language(
                "Hello world",
                total_timeout=30.0,
            )

    assert results
    assert adapter.detect.call_count == 2
    parser.parse.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])

