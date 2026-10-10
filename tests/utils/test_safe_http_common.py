"""Tests for shl.utils.safe_http_common."""
from __future__ import annotations

import socket

import pytest

from shl.utils.safe_http_common import (
    SafeHTTPError,
    resolve_all_ips,
    read_limited_response,
)


def _make_info(ip: str, port: int = 0):
    """Build a getaddrinfo-shaped tuple for the given IP."""
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    return (family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (ip, port))


class TestSafeHTTPError:
    def test_defaults(self):
        err = SafeHTTPError("boom")
        assert str(err) == "boom"
        assert err.kind == "http_error"
        assert err.status_code is None
        assert err.response_body is None

    def test_all_attributes(self):
        err = SafeHTTPError(
            "boom",
            kind="timeout",
            status_code=503,
            response_body="service unavailable",
        )
        assert err.kind == "timeout"
        assert err.status_code == 503
        assert err.response_body == "service unavailable"

    def test_is_exception_subclass(self):
        assert issubclass(SafeHTTPError, Exception)


class TestResolveAllIps:
    def test_single_ipv4(self, monkeypatch):
        monkeypatch.setattr(
            "socket.getaddrinfo",
            lambda *a, **kw: [_make_info("93.184.216.34")],
        )
        ips = resolve_all_ips("example.com")
        assert len(ips) == 1
        assert str(ips[0]) == "93.184.216.34"

    def test_multiple_ips(self, monkeypatch):
        monkeypatch.setattr(
            "socket.getaddrinfo",
            lambda *a, **kw: [
                _make_info("93.184.216.34"),
                _make_info("93.184.216.35"),
            ],
        )
        ips = resolve_all_ips("example.com")
        assert len(ips) == 2

    def test_dns_failure_returns_empty(self, monkeypatch):
        def _raise(*a, **kw):
            raise socket.gaierror("NXDOMAIN")
        monkeypatch.setattr("socket.getaddrinfo", _raise)
        assert resolve_all_ips("nope.invalid") == []

    def test_empty_response_returns_empty(self, monkeypatch):
        monkeypatch.setattr("socket.getaddrinfo", lambda *a, **kw: [])
        assert resolve_all_ips("empty.example") == []

    def test_invalid_ip_returns_empty(self, monkeypatch):
        monkeypatch.setattr(
            "socket.getaddrinfo",
            lambda *a, **kw: [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("not-an-ip", 0))
            ],
        )
        assert resolve_all_ips("bad.example") == []


class _FakeResponse:
    """Minimal stand-in for HTTPResponse / HTTPError."""

    def __init__(self, data: bytes = b"", raise_exc: Exception | None = None):
        self._data = data
        self._raise = raise_exc

    def read(self, amt: int = -1) -> bytes:
        if self._raise is not None:
            raise self._raise
        if amt < 0:
            return self._data
        return self._data[:amt]


class TestReadLimitedResponse:
    def test_under_limit(self):
        resp = _FakeResponse(b"hello")
        assert read_limited_response(resp, max_bytes=100) == b"hello"

    def test_exactly_at_limit(self):
        resp = _FakeResponse(b"x" * 100)
        assert read_limited_response(resp, max_bytes=100) == b"x" * 100

    def test_over_limit_raises(self):
        resp = _FakeResponse(b"x" * 101)
        with pytest.raises(SafeHTTPError) as excinfo:
            read_limited_response(resp, max_bytes=100)
        assert excinfo.value.kind == "response_too_large"

    def test_timeout_raises(self):
        resp = _FakeResponse(raise_exc=TimeoutError("slow"))
        with pytest.raises(SafeHTTPError) as excinfo:
            read_limited_response(resp)
        assert excinfo.value.kind == "timeout"

    def test_oserror_raises_transport(self):
        resp = _FakeResponse(raise_exc=OSError("broken pipe"))
        with pytest.raises(SafeHTTPError) as excinfo:
            read_limited_response(resp)
        assert excinfo.value.kind == "transport"
