"""
File: shl/utils/safe_http_common.py
Author: Tuomas Lähteenmäki
Version: 0.3.0
License: MIT
Description: Shared constants, exceptions, and helpers for SHL HTTP
utilities. Both the outbound (safe_http.py) and local (safe_local_http.py)
paths import from here so callers can catch a single SafeHTTPError.
"""
from __future__ import annotations

import ipaddress
import socket
from typing import Protocol

from shl._version import __version__


class SafeHTTPError(Exception):
    """SHL exception for HTTP, transport, and security errors."""

    def __init__(
        self,
        message: str,
        *,
        kind: str = "http_error",
        status_code: int | None = None,
        response_body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.status_code = status_code
        self.response_body = response_body


# Shared limits — both paths use the same values.
MAX_RESPONSE_BYTES = 65536  # 64 KB
MAX_REDIRECTS = 3
DEFAULT_TIMEOUT = 10.0

SHL_USER_AGENT = (
    f"Self-Healing-Localization/{__version__} "
    "(+https://codeberg.org/lahtis/Self_Healing_Localization)"
)


class _ReadableResponse(Protocol):
    """Anything with a bytes-returning read() method.

    Covers both http.client.HTTPResponse and urllib.error.HTTPError,
    which do not share a common base class for reading.
    """

    def read(self, amt: int = ...) -> bytes: ...


def resolve_all_ips(
    hostname: str,
    port: int = 443,
) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    """Resolve hostname to all IPs via getaddrinfo.

    Returns an empty list on any failure (fail-closed). Both the outbound
    and local paths use this so their DNS behavior stays identical.
    """
    try:
        infos = socket.getaddrinfo(
            hostname,
            port,
            proto=socket.IPPROTO_TCP,
        )
    except (OSError, UnicodeError):
        return []

    if not infos:
        return []

    ips: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []

    for info in infos:
        try:
            ips.append(ipaddress.ip_address(info[4][0]))
        except (ValueError, IndexError, TypeError):
            # Malformed getaddrinfo answer — treat as failure (fail-closed).
            return []

    return ips


def read_limited_response(
    response: _ReadableResponse,
    max_bytes: int = MAX_RESPONSE_BYTES,
) -> bytes:
    """Read a response body without exceeding the configured size limit.

    Reads one byte past the limit so overflow is detected cleanly instead
    of silently truncating the middle of a JSON payload.
    """
    try:
        raw = response.read(max_bytes + 1)
    except OSError as exc:
        # TimeoutError and socket.timeout are both OSError subclasses
        # in Python 3.10+ (our minimum), so a single handler covers them.
        kind = "timeout" if isinstance(exc, TimeoutError) else "transport"
        raise SafeHTTPError(
            f"Failed to read HTTP response: {exc}",
            kind=kind,
        ) from exc

    if len(raw) > max_bytes:
        raise SafeHTTPError(
            f"Response exceeds {max_bytes} byte limit.",
            kind="response_too_large",
        )

    return raw
