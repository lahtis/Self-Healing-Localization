"""Tests for shl.utils.safe_local_http (localhost + internal path)."""
from __future__ import annotations

import socket
import urllib.request
from unittest.mock import MagicMock

import pytest

from shl.utils.safe_local_http import (
    _NoRedirectHandler,
    is_allowed_local_url,
    safe_local_http_post,
)
from shl.utils.safe_http_common import SafeHTTPError


def _make_info(ip: str, port: int = 0):
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    return (family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (ip, port))


def _resolver_for(ips):
    def _inner(host, port, **kwargs):
        return [_make_info(ip, port or 0) for ip in ips]
    return _inner


# ------------------------------------------------------- is_allowed_local_url


class TestIsAllowedLocalUrl:
    def test_loopback_literal_ipv4(self):
        # Literal IPs in _LOOPBACK_LITERALS skip DNS entirely.
        assert is_allowed_local_url("http://127.0.0.1:8080/") is True

    def test_loopback_literal_ipv6(self):
        assert is_allowed_local_url("http://[::1]:8080/") is True

    def test_localhost_http_default_port(self, monkeypatch):
        monkeypatch.setattr("socket.getaddrinfo",
                            _resolver_for(["127.0.0.1"]))
        assert is_allowed_local_url("http://localhost/") is True

    def test_localhost_https_default_port(self, monkeypatch):
        monkeypatch.setattr("socket.getaddrinfo",
                            _resolver_for(["127.0.0.1"]))
        assert is_allowed_local_url("https://localhost/") is True

    def test_localhost_explicit_allowed_port(self, monkeypatch):
        monkeypatch.setattr("socket.getaddrinfo",
                            _resolver_for(["127.0.0.1"]))
        assert is_allowed_local_url("http://localhost:11434/") is True

    def test_localhost_resolving_to_non_loopback_rejected(self, monkeypatch):
        # /etc/hosts override or DNS hijack — must fail closed.
        monkeypatch.setattr("socket.getaddrinfo",
                            _resolver_for(["192.168.1.50"]))
        assert is_allowed_local_url("http://localhost/") is False

    def test_ollama_internal_private_ip_ok(self, monkeypatch):
        monkeypatch.setattr("socket.getaddrinfo",
                            _resolver_for(["192.168.1.50"]))
        assert is_allowed_local_url("http://ollama.internal:11434/") is True

    def test_ollama_internal_public_ip_rejected(self, monkeypatch):
        # DNS returns a global IP → allowlist must not accept it.
        monkeypatch.setattr("socket.getaddrinfo",
                            _resolver_for(["8.8.8.8"]))
        assert is_allowed_local_url("http://ollama.internal:11434/") is False

    def test_unknown_host_rejected(self):
        assert is_allowed_local_url("http://evil.example.com/") is False

    def test_disallowed_port_rejected(self):
        assert is_allowed_local_url("http://localhost:22/") is False

    def test_https_disallowed_port_rejected(self):
        assert is_allowed_local_url("https://localhost:8443/") is False

    def test_invalid_port_rejected(self):
        assert is_allowed_local_url("http://localhost:99999/") is False

    def test_backslash_rejected(self):
        assert is_allowed_local_url("http://localhost\\@evil.example/") is False

    def test_userinfo_rejected(self):
        assert is_allowed_local_url("http://user:pass@localhost/") is False
        assert is_allowed_local_url("http://user@localhost/") is False

    def test_non_http_scheme_rejected(self):
        assert is_allowed_local_url("ftp://localhost/") is False
        assert is_allowed_local_url("file://localhost/") is False

    def test_non_string_rejected(self):
        assert is_allowed_local_url(None) is False
        assert is_allowed_local_url(123) is False


# ---------------------------------------------------------- _NoRedirectHandler


class TestNoRedirectHandler:
    def test_redirect_rejected(self):
        handler = _NoRedirectHandler()
        req = urllib.request.Request("http://localhost:8080/")
        with pytest.raises(SafeHTTPError) as excinfo:
            handler.redirect_request(
                req, None, 302, "Found", {},
                "http://localhost:8080/elsewhere",
            )
        assert excinfo.value.kind == "security"
        assert excinfo.value.status_code == 302


# ------------------------------------------------------- safe_local_http_post


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


class TestSafeLocalHttpPost:
    def _patch(self, monkeypatch, response=None, side_effect=None):
        monkeypatch.setattr("socket.getaddrinfo",
                            _resolver_for(["127.0.0.1"]))
        opener = MagicMock()
        if side_effect is not None:
            opener.open.side_effect = side_effect
        else:
            opener.open.return_value = response
        monkeypatch.setattr("shl.utils.safe_local_http._opener", opener)
        return opener

    def test_success(self, monkeypatch):
        self._patch(monkeypatch,
                    response=_FakeHTTPResponse(body=b'{"ok": true}'))
        result = safe_local_http_post(
            "http://localhost:8080/translate", {"text": "hi"},
        )
        assert result == {"ok": True}

    def test_unsafe_url_rejected_before_network(self, monkeypatch):
        opener = MagicMock()
        monkeypatch.setattr("shl.utils.safe_local_http._opener", opener)
        with pytest.raises(SafeHTTPError) as excinfo:
            safe_local_http_post("http://evil.example.com/", {"x": 1})
        assert excinfo.value.kind == "security"
        opener.open.assert_not_called()

    def test_non_200_rejected(self, monkeypatch):
        self._patch(monkeypatch,
                    response=_FakeHTTPResponse(status=503, body=b"{}"))
        with pytest.raises(SafeHTTPError) as excinfo:
            safe_local_http_post("http://localhost:8080/", {"x": 1})
        assert excinfo.value.kind == "http_status"
        assert excinfo.value.status_code == 503

    def test_non_json_content_type_rejected(self, monkeypatch):
        self._patch(
            monkeypatch,
            response=_FakeHTTPResponse(
                body=b"<html>", content_type="text/html",
            ),
        )
        with pytest.raises(SafeHTTPError) as excinfo:
            safe_local_http_post("http://localhost:8080/", {"x": 1})
        assert excinfo.value.kind == "invalid_content_type"

    def test_oversized_response_rejected(self, monkeypatch):
        from shl.utils.safe_http_common import MAX_RESPONSE_BYTES
        big = b"x" * (MAX_RESPONSE_BYTES + 1)
        self._patch(monkeypatch, response=_FakeHTTPResponse(body=big))
        with pytest.raises(SafeHTTPError) as excinfo:
            safe_local_http_post("http://localhost:8080/", {"x": 1})
        assert excinfo.value.kind == "response_too_large"

    def test_invalid_json_rejected(self, monkeypatch):
        self._patch(monkeypatch,
                    response=_FakeHTTPResponse(body=b"not json"))
        with pytest.raises(SafeHTTPError) as excinfo:
            safe_local_http_post("http://localhost:8080/", {"x": 1})
        assert excinfo.value.kind == "invalid_response"

    def test_non_dict_json_rejected(self, monkeypatch):
        self._patch(monkeypatch,
                    response=_FakeHTTPResponse(body=b'"just a string"'))
        with pytest.raises(SafeHTTPError) as excinfo:
            safe_local_http_post("http://localhost:8080/", {"x": 1})
        assert excinfo.value.kind == "invalid_response"

    def test_timeout_converted(self, monkeypatch):
        self._patch(monkeypatch, side_effect=TimeoutError("slow"))
        with pytest.raises(SafeHTTPError) as excinfo:
            safe_local_http_post("http://localhost:8080/", {"x": 1})
        assert excinfo.value.kind == "timeout"

    def test_oserror_converted_to_transport(self, monkeypatch):
        self._patch(monkeypatch, side_effect=OSError("connection refused"))
        with pytest.raises(SafeHTTPError) as excinfo:
            safe_local_http_post("http://localhost:8080/", {"x": 1})
        assert excinfo.value.kind == "transport"
