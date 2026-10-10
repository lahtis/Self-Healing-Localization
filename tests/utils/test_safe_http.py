"""Tests for shl.utils.safe_http (outbound / public path)."""
from __future__ import annotations

import socket
import urllib.request
from unittest.mock import MagicMock

import pytest

from shl.utils.safe_http import (
    _SafeRedirectHandler,
    is_safe_url,
    safe_http_post,
)
from shl.utils.safe_http_common import SafeHTTPError


def _make_info(ip: str, port: int = 0):
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    return (family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (ip, port))


def _resolver_for(ips):
    """Return a getaddrinfo replacement that always returns the given IPs."""
    def _inner(host, port, **kwargs):
        return [_make_info(ip, port or 0) for ip in ips]
    return _inner


# ---------------------------------------------------------------- is_safe_url


class TestIsSafeUrl:
    def test_public_https_ok(self, monkeypatch):
        monkeypatch.setattr("socket.getaddrinfo",
                            _resolver_for(["8.8.8.8"]))
        assert is_safe_url("https://api.example.com/v1") is True

    def test_uppercase_scheme_ok(self, monkeypatch):
        monkeypatch.setattr("socket.getaddrinfo",
                            _resolver_for(["8.8.8.8"]))
        assert is_safe_url("HTTPS://api.example.com/") is True

    def test_http_rejected(self):
        assert is_safe_url("http://api.example.com/") is False

    @pytest.mark.parametrize("url", [
        "https://127.0.0.1/",
        "https://10.0.0.5/",
        "https://192.168.1.1/",
        "https://172.16.0.1/",
        "https://169.254.169.254/",   # cloud metadata
        "https://[::1]/",
    ])
    def test_non_global_ip_rejected(self, monkeypatch, url):
        # Resolver echoes whatever literal IP appears in the URL,
        # matching real getaddrinfo behavior for literal addresses.
        def _inner(host, port, **kwargs):
            return [_make_info(host, port or 0)]
        monkeypatch.setattr("socket.getaddrinfo", _inner)
        assert is_safe_url(url) is False

    def test_named_localhost_rejected(self, monkeypatch):
        monkeypatch.setattr("socket.getaddrinfo",
                            _resolver_for(["127.0.0.1"]))
        assert is_safe_url("https://localhost/") is False

    def test_userinfo_rejected(self):
        assert is_safe_url("https://user:pass@api.example.com/") is False
        assert is_safe_url("https://user@api.example.com/") is False

    def test_empty_host_rejected(self):
        assert is_safe_url("https:///path") is False
        assert is_safe_url("https://") is False

    def test_garbage_url_rejected(self):
        assert is_safe_url("") is False
        assert is_safe_url("not a url") is False

    def test_dns_failure_fails_closed(self, monkeypatch):
        def _raise(*a, **kw):
            raise socket.gaierror("DNS down")
        monkeypatch.setattr("socket.getaddrinfo", _raise)
        assert is_safe_url("https://api.example.com/") is False

    def test_mixed_dns_answer_rejected(self, monkeypatch):
        # One global + one non-global → reject the whole name.
        monkeypatch.setattr(
            "socket.getaddrinfo",
            _resolver_for(["8.8.8.8", "127.0.0.1"]),
        )
        assert is_safe_url("https://api.example.com/") is False


# ------------------------------------------------------ _SafeRedirectHandler


class TestSafeRedirectHandler:
    def test_safe_redirect_allowed(self, monkeypatch):
        monkeypatch.setattr("socket.getaddrinfo",
                            _resolver_for(["8.8.8.8"]))
        handler = _SafeRedirectHandler()
        req = urllib.request.Request("https://example.com/")
        new_req = handler.redirect_request(
            req, None, 302, "Found", {}, "https://other.example.com/",
        )
        assert new_req.full_url == "https://other.example.com/"

    def test_unsafe_redirect_blocked(self, monkeypatch):
        # Any DNS name resolving to loopback → rejected by is_safe_url.
        monkeypatch.setattr("socket.getaddrinfo",
                            _resolver_for(["127.0.0.1"]))
        handler = _SafeRedirectHandler()
        req = urllib.request.Request("https://example.com/")
        with pytest.raises(SafeHTTPError) as excinfo:
            handler.redirect_request(
                req, None, 302, "Found", {}, "https://internal.example/",
            )
        assert excinfo.value.kind == "security"

    def test_http_redirect_blocked(self, monkeypatch):
        monkeypatch.setattr("socket.getaddrinfo",
                            _resolver_for(["8.8.8.8"]))
        handler = _SafeRedirectHandler()
        req = urllib.request.Request("https://example.com/")
        with pytest.raises(SafeHTTPError) as excinfo:
            handler.redirect_request(
                req, None, 302, "Found", {}, "http://example.com/",
            )
        assert excinfo.value.kind == "security"


# ------------------------------------------------------------ safe_http_post


class _FakeHTTPResponse:
    def __init__(self, status=200, body=b"{}",
                 content_type="application/json; charset=utf-8"):
        self.status = status
        self.headers = {"Content-Type": content_type}
        self._body = body

    def read(self, amt: int = -1) -> bytes:
        return self._body if amt < 0 else self._body[:amt]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class TestSafeHttpPost:
    def _patch(self, monkeypatch, response=None, side_effect=None):
        monkeypatch.setattr("socket.getaddrinfo",
                            _resolver_for(["8.8.8.8"]))
        opener = MagicMock()
        if side_effect is not None:
            opener.open.side_effect = side_effect
        else:
            opener.open.return_value = response
        monkeypatch.setattr("shl.utils.safe_http._opener", opener)
        return opener

    def test_success(self, monkeypatch):
        self._patch(monkeypatch,
                    response=_FakeHTTPResponse(body=b'{"ok": true}'))
        result = safe_http_post("https://api.example.com/v1", {"x": 1})
        assert result == {"ok": True}

    def test_unsafe_url_rejected_before_network(self, monkeypatch):
        monkeypatch.setattr("socket.getaddrinfo",
                            _resolver_for(["127.0.0.1"]))
        opener = MagicMock()
        monkeypatch.setattr("shl.utils.safe_http._opener", opener)
        with pytest.raises(SafeHTTPError) as excinfo:
            safe_http_post("https://internal.example/", {"x": 1})
        assert excinfo.value.kind == "security"
        opener.open.assert_not_called()

    def test_non_200_rejected(self, monkeypatch):
        self._patch(monkeypatch,
                    response=_FakeHTTPResponse(status=500, body=b"{}"))
        with pytest.raises(SafeHTTPError) as excinfo:
            safe_http_post("https://api.example.com/", {"x": 1})
        assert excinfo.value.kind == "http_status"
        assert excinfo.value.status_code == 500

    def test_non_json_content_type_rejected(self, monkeypatch):
        self._patch(
            monkeypatch,
            response=_FakeHTTPResponse(
                body=b"<html>", content_type="text/html",
            ),
        )
        with pytest.raises(SafeHTTPError) as excinfo:
            safe_http_post("https://api.example.com/", {"x": 1})
        assert excinfo.value.kind == "invalid_content_type"

    def test_oversized_response_rejected(self, monkeypatch):
        from shl.utils.safe_http_common import MAX_RESPONSE_BYTES
        big = b"x" * (MAX_RESPONSE_BYTES + 1)
        self._patch(monkeypatch,
                    response=_FakeHTTPResponse(body=big))
        with pytest.raises(SafeHTTPError) as excinfo:
            safe_http_post("https://api.example.com/", {"x": 1})
        assert excinfo.value.kind == "response_too_large"

    def test_invalid_json_rejected(self, monkeypatch):
        self._patch(monkeypatch,
                    response=_FakeHTTPResponse(body=b"not json"))
        with pytest.raises(SafeHTTPError) as excinfo:
            safe_http_post("https://api.example.com/", {"x": 1})
        assert excinfo.value.kind == "invalid_response"

    def test_non_dict_json_rejected(self, monkeypatch):
        self._patch(monkeypatch,
                    response=_FakeHTTPResponse(body=b"[1, 2, 3]"))
        with pytest.raises(SafeHTTPError) as excinfo:
            safe_http_post("https://api.example.com/", {"x": 1})
        assert excinfo.value.kind == "invalid_response"

    def test_unserializable_payload_rejected(self, monkeypatch):
        self._patch(monkeypatch,
                    response=_FakeHTTPResponse(body=b"{}"))
        with pytest.raises(SafeHTTPError) as excinfo:
            safe_http_post(
                "https://api.example.com/", {"x": object()},
            )
        assert excinfo.value.kind == "invalid_response"

    def test_timeout_converted(self, monkeypatch):
        self._patch(monkeypatch, side_effect=TimeoutError("slow"))
        with pytest.raises(SafeHTTPError) as excinfo:
            safe_http_post("https://api.example.com/", {"x": 1})
        assert excinfo.value.kind == "timeout"

    def test_oserror_converted_to_transport(self, monkeypatch):
        self._patch(monkeypatch, side_effect=OSError("connection refused"))
        with pytest.raises(SafeHTTPError) as excinfo:
            safe_http_post("https://api.example.com/", {"x": 1})
        assert excinfo.value.kind == "transport"
