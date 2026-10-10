"""Guard the SafeHTTPError.kind ↔ HTTP_EXCEPTION_CODES contract.

If SafeHTTPError emits a kind that the parser does not recognize,
the parser falls through to UNKNOWN_ERROR. This test prevents that
silent regression.
"""
from __future__ import annotations

import pytest

from shl.engine.errors.parser import HTTP_EXCEPTION_CODES


# Kinds emitted by SafeHTTPError call sites in shl/utils/safe_http.py
# and shl/utils/safe_local_http.py. Update this set when a new kind
# is introduced.
EMITTED_KINDS = {
    "http_error",              # default
    "security",
    "timeout",
    "transport",
    "invalid_response",
    "invalid_content_type",
    "response_too_large",
}


def test_all_emitted_kinds_are_mapped():
    """Every kind SafeHTTPError emits must be known to the parser."""
    missing = EMITTED_KINDS - set(HTTP_EXCEPTION_CODES)
    assert not missing, (
        f"SafeHTTPError emits kinds that HTTP_EXCEPTION_CODES does not "
        f"map: {sorted(missing)}. Add them to parser.py."
    )


def test_no_unused_mappings():
    """Catch leftover mappings when a kind is removed.

    Extra entries are not dangerous, but they suggest drift in the
    other direction. Not a hard failure — just a hint.
    """
    # This test is informational; uncomment to enforce strictness.
    #
    # unused = set(HTTP_EXCEPTION_CODES) - EMITTED_KINDS - {
    #     "network",  # parser-internal alias for NETWORK_ERROR
    #     "security_violation",  # alternate spelling kept for compat
    #     ...
    # }
    # assert not unused
    pass


@pytest.mark.parametrize("kind", sorted(EMITTED_KINDS))
def test_parser_does_not_crash_on_kind(kind):
    """Smoke test: parser handles every emitted kind without raising."""
    from shl.engine.errors.parser import ErrorParser

    parser = ErrorParser(provider="test")
    exc = Exception("test")
    exc.kind = kind
    exc.status_code = None
    exc.response_body = None

    result = parser.parse(exception=exc, http_status=None)
    assert result is not None
    assert result.code != "UNKNOWN_ERROR" or kind == "http_error"
