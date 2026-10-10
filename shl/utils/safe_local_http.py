"""
File: shl/utils/safe_local_http.py
Author: Tuomas Lähteenmäki
Version: 0.3.0
License: MIT
Description: Safe, dependency-free HTTP helpers for the local path
(localhost + internal network). Endpoints originate directly from code.

Security model:
- Local path (localhost + internal network only)
- Explicit hostname allowlist (not "any internal IP")
- Explicit port allowlist
- http and https allowed (internal services often lack TLS)
- DNS name must NOT resolve to a global IP — prevents an allowed name
  (e.g. ollama.internal) from silently pointing to the public internet
- Redirects are NOT followed (internal APIs do not redirect)
- Response size limit, timeout, and Content-Type check

Known limitation — DNS rebinding:
    Same as safe_http.py: the hostname is resolved once for validation
    and again by urllib for the connection. For the current allowlist
    (localhost, 127.0.0.1, ::1, ollama.internal) this is accepted
    because three of the four entries are literal loopback addresses
    that skip DNS entirely, and ollama.internal is expected to be a
    stable internal name.

    If the allowlist ever grows to include names under attacker-
    influenced DNS, the same pinning approach described in safe_http.py
    must be applied.
"""

import json
import ssl
import urllib.error
import urllib.request
from typing import NoReturn
from urllib.parse import urlsplit

from .safe_http_common import (
    SafeHTTPError,
    DEFAULT_TIMEOUT,
    MAX_RESPONSE_BYTES,
    SHL_USER_AGENT,
    resolve_all_ips,
    read_limited_response,
)


_ALLOWED_LOCAL_HOSTS = {
    "localhost",
    "127.0.0.1",
    "::1",
    "ollama.internal",
    "libretranslate.internal",
}

_ALLOWED_LOCAL_PORTS = {80, 443, 8000, 8080, 11434, 5000}

# Numeric loopback addresses do not require DNS resolution.
_LOOPBACK_LITERALS = {"127.0.0.1", "::1"}

# Cap on the length of response_body stored in SafeHTTPError,
# matching the outbound path so both stay loggable.
_MAX_ERROR_BODY_CHARS = 2048


def _resolve_safe(
    hostname: str,
    port: int,
) -> str | None:
    """Return one approved internal IP, or None if resolution is unsafe.

    Fail-closed. For localhost, every resolved address must be a loopback
    address. For other allowlisted names, global IPs are rejected.
    """
    ips = resolve_all_ips(hostname, port)

    if not ips:
        return None

    if hostname == "localhost":
        if not all(ip.is_loopback for ip in ips):
            return None
    elif any(ip.is_global for ip in ips):
        return None

    return str(ips[0])


def is_allowed_local_url(url: str) -> bool:
    """Return True if URL targets an allowlisted local/internal host."""
    if not isinstance(url, str) or "\\" in url:
        return False

    try:
        parsed = urlsplit(url)
        port = parsed.port
    except (ValueError, TypeError):
        return False

    if parsed.scheme.lower() not in ("http", "https"):
        return False

    if parsed.username is not None or parsed.password is not None:
        return False

    hostname = (parsed.hostname or "").lower()

    if hostname not in _ALLOWED_LOCAL_HOSTS:
        return False

    port = port or (443 if parsed.scheme.lower() == "https" else 80)

    if port not in _ALLOWED_LOCAL_PORTS:
        return False

    if hostname not in _LOOPBACK_LITERALS:
        if _resolve_safe(hostname, port) is None:
            return False

    return True


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Refuse to follow redirects on the local path."""

    def redirect_request(self, req, fp, code, msg, hdrs, newurl):
        raise SafeHTTPError(
            "Redirects are not followed on the local path.",
            kind="security",
            status_code=code,
        )


_SSL_CONTEXT = ssl.create_default_context()

# Internal services often use self-signed certificates. Verification stays
# enabled by default. Disable it only if a trusted deployment requires it.

_opener = urllib.request.build_opener(
    urllib.request.HTTPSHandler(context=_SSL_CONTEXT),
    _NoRedirectHandler(),
)


def _read_http_error_body(
    error: urllib.error.HTTPError,
) -> str | None:
    """Read a bounded HTTP error body for provider-specific parsing.

    The body is truncated to _MAX_ERROR_BODY_CHARS characters so it
    stays loggable.
    """
    try:
        raw = read_limited_response(error, MAX_RESPONSE_BYTES)
    except SafeHTTPError as exc:
        raise SafeHTTPError(
            str(exc),
            kind=exc.kind,
            status_code=error.code,
        ) from exc

    if not raw:
        return None

    text = raw.decode("utf-8", errors="replace")
    if len(text) > _MAX_ERROR_BODY_CHARS:
        text = text[:_MAX_ERROR_BODY_CHARS] + "... (truncated)"
    return text


def _raise_http_error(error: urllib.error.HTTPError) -> NoReturn:
    """Convert HTTPError while preserving status and response body."""
    body = _read_http_error_body(error)

    raise SafeHTTPError(
        f"API returned HTTP status {error.code}.",
        kind="http_status",
        status_code=error.code,
        response_body=body,
    ) from error


def _network_error(error: BaseException) -> SafeHTTPError:
    """Convert a network exception into an SHL HTTP error."""
    if isinstance(error, TimeoutError):
        return SafeHTTPError(
            f"Local HTTP request timed out: {error}",
            kind="timeout",
        )

    if isinstance(error, urllib.error.URLError):
        reason = error.reason

        if isinstance(reason, TimeoutError):
            return SafeHTTPError(
                f"Local HTTP request timed out: {reason}",
                kind="timeout",
            )

    return SafeHTTPError(
        f"Local HTTP transport failure: {error}",
        kind="transport",
    )


# ---------------------------------------------------------------------------
# Public API — mirrors safe_http.py
# ---------------------------------------------------------------------------

def safe_local_urlopen(
    request: str | urllib.request.Request,
    timeout: float = DEFAULT_TIMEOUT,
):
    """Open a request to an approved local/internal endpoint safely.

    Accepts a URL string or urllib.request.Request, preserving the
    request method, body, and headers. The URL is validated against
    the allowlist before the connection is attempted.

    The returned response must be closed by the caller, preferably by
    using it as a context manager:

        with safe_local_urlopen(req) as response:
            ...

    Raises SafeHTTPError for URL validation, HTTP, transport, timeout,
    and redirect failures.
    """
    if isinstance(request, str):
        url = request
    elif isinstance(request, urllib.request.Request):
        url = request.full_url
    else:
        raise TypeError(
            "request must be a URL string or urllib.request.Request"
        )

    if not is_allowed_local_url(url):
        raise SafeHTTPError(
            "Insecure or forbidden local URL requested.",
            kind="security",
        )

    try:
        response = _opener.open(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        _raise_http_error(exc)
    except urllib.error.URLError as exc:
        raise _network_error(exc) from exc
    except OSError as exc:
        raise _network_error(exc) from exc

    return response


def safe_local_http_post(
    url: str,
    json_data: dict,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict:
    """POST JSON to an approved local/internal endpoint.

    Returns a decoded JSON object. Raises SafeHTTPError on failure.
    Only HTTP 200 responses with a JSON object are accepted.
    """
    if not is_allowed_local_url(url):
        raise SafeHTTPError(
            "Insecure or forbidden local URL requested.",
            kind="security",
        )

    try:
        data_bytes = json.dumps(
            json_data,
            ensure_ascii=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise SafeHTTPError(
            f"Could not encode request JSON: {exc}",
            kind="invalid_response",
        ) from exc

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": SHL_USER_AGENT,
    }

    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers=headers,
        method="POST",
    )

    try:
        with safe_local_urlopen(req, timeout=timeout) as response:
            status = response.status

            if status != 200:
                raise SafeHTTPError(
                    f"API returned HTTP status {status}.",
                    kind="http_status",
                    status_code=status,
                )

            content_type = (
                response.headers.get("Content-Type") or ""
            ).lower()

            if not content_type.startswith("application/json"):
                raise SafeHTTPError(
                    f"Unexpected Content-Type: {content_type!r}",
                    kind="invalid_content_type",
                    status_code=status,
                )

            raw = read_limited_response(
                response,
                MAX_RESPONSE_BYTES,
            )

    except urllib.error.HTTPError as exc:
        _raise_http_error(exc)
    except urllib.error.URLError as exc:
        raise _network_error(exc) from exc
    except OSError as exc:
        raise _network_error(exc) from exc

    try:
        parsed_response = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SafeHTTPError(
            f"Failed to decode JSON response: {exc}",
            kind="invalid_response",
            status_code=200,
        ) from exc

    if not isinstance(parsed_response, dict):
        raise SafeHTTPError(
            "Invalid API response format: expected a JSON object.",
            kind="invalid_response",
            status_code=200,
        )

    return parsed_response
