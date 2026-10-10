"""
File: shl/utils/safe_http.py
Author: Tuomas Lähteenmäki
Version: 0.3.0
License: MIT
Description: Safe, dependency-free HTTP helpers for outbound public
internet requests. Endpoints originate directly from code — no user
input, no configuration file. The security checks are defense-in-depth:
they primarily guard against typos and future refactoring errors, not
active attackers.

Security model:
- Outbound path (public internet only)
- HTTPS only
- IP-level SSRF prevention: is_global is required for every DNS response
- Redirects validated by a handler with a hard cap
- Response size limit for both successful and error responses
- Explicit timeouts
- JSON Content-Type validation for safe_http_post()

Known limitation — DNS rebinding:
    The hostname is resolved once for validation and then again by urllib
    for the actual connection. This is accepted because endpoints are
    hard-coded in the source.

    If endpoints become configurable from outside the code, this
    limitation must be addressed by pinning the resolved IP to the
    connection while preserving the original hostname for TLS and HTTP.

Callers should use safe_urlopen() or safe_http_post() instead of
urllib directly.
"""

# CHANGED: added http.client import for the response type hint.
import http.client
import json
import ssl
# CHANGED: removed `socket` import — no longer used (socket.timeout
# is an alias for TimeoutError in Python 3.10+, our minimum).
import urllib.error
import urllib.request
from typing import cast, NoReturn
from urllib.parse import urlsplit

from .safe_http_common import (
    SafeHTTPError,
    MAX_REDIRECTS,
    MAX_RESPONSE_BYTES,
    SHL_USER_AGENT,
    resolve_all_ips,
    read_limited_response,
)


# CHANGED: cap on the length of response_body stored in SafeHTTPError,
# so a 64 KB error page does not end up in logs verbatim.
_MAX_ERROR_BODY_CHARS = 2048


def _ip_is_global(hostname: str) -> bool:
    """Return True only if every resolved IP is globally routable."""
    ips = resolve_all_ips(hostname)
    return bool(ips) and all(ip.is_global for ip in ips)


def is_safe_url(url: str) -> bool:
    """Return True if URL is a safe HTTPS address on the public internet."""
    try:
        parsed = urlsplit(url)
    except (ValueError, TypeError):
        return False

    if parsed.scheme.lower() != "https":
        return False

    hostname = parsed.hostname
    if not hostname:
        return False

    if parsed.username is not None or parsed.password is not None:
        return False

    return _ip_is_global(hostname)


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Validate every redirect target and cap the number of hops."""

    max_redirections = MAX_REDIRECTS

    def redirect_request(self, req, fp, code, msg, hdrs, newurl):
        if not is_safe_url(newurl):
            raise SafeHTTPError(
                "Redirect to an unsafe URL was blocked.",
                kind="security",
            )

        return super().redirect_request(
            req,
            fp,
            code,
            msg,
            hdrs,
            newurl,
        )


_SSL_CONTEXT = ssl.create_default_context()

_opener = urllib.request.build_opener(
    urllib.request.HTTPSHandler(context=_SSL_CONTEXT),
    _SafeRedirectHandler(),
)


def _read_http_error_body(
    error: urllib.error.HTTPError,
) -> str | None:
    """Read a bounded HTTP error body for provider-specific parsing.

    The body is truncated to _MAX_ERROR_BODY_CHARS characters so it
    stays loggable. SafeHTTPError from the size limiter is re-raised
    with the original status code attached.
    """
    try:
        raw = read_limited_response(error, MAX_RESPONSE_BYTES)
    except SafeHTTPError as exc:
        # CHANGED: removed redundant `if exc.kind == "response_too_large"`
        # branch — the general branch produces the same result because
        # exc.kind already carries the value through.
        raise SafeHTTPError(
            str(exc),
            kind=exc.kind,
            status_code=error.code,
        ) from exc

    if not raw:
        return None

    text = raw.decode("utf-8", errors="replace")
    # CHANGED: truncate response_body so logs stay manageable.
    if len(text) > _MAX_ERROR_BODY_CHARS:
        text = text[:_MAX_ERROR_BODY_CHARS] + "... (truncated)"
    return text


# CHANGED: return type NoReturn tells mypy (and readers) that this
# function always raises; callers can rely on it not returning.
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
    # CHANGED: socket.timeout removed — it is an alias for TimeoutError
    # in Python 3.10+, which is our minimum supported version.
    if isinstance(error, TimeoutError):
        return SafeHTTPError(
            f"HTTP request timed out: {error}",
            kind="timeout",
        )

    if isinstance(error, urllib.error.URLError):
        reason = error.reason

        if isinstance(reason, TimeoutError):
            return SafeHTTPError(
                f"HTTP request timed out: {reason}",
                kind="timeout",
            )

    return SafeHTTPError(
        f"HTTP transport failure: {error}",
        kind="transport",
    )


# CHANGED: added parameter and return type hints so mypy can check
# callers and the response is known to be an HTTPResponse.
def safe_urlopen(
    request: str | urllib.request.Request,
    timeout: float = 10.0,
) -> http.client.HTTPResponse:
    """Open a request to a public HTTPS endpoint safely.

    Accepts a URL string or urllib.request.Request, preserving the
    request method, body, and headers.

    The returned response must be closed by the caller, preferably by
    using it as a context manager:

        with safe_urlopen(req) as response:
            ...

    Raises SafeHTTPError for URL validation, HTTP, transport, timeout,
    redirect, and response-size failures.
    """
    if isinstance(request, str):
        url = request
    elif isinstance(request, urllib.request.Request):
        url = request.full_url
    else:
        raise TypeError(
            "request must be a URL string or urllib.request.Request"
        )

    if not is_safe_url(url):
        raise SafeHTTPError(
            "Insecure or forbidden URL requested.",
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

    # urllib returns Any from open(); we know it is an HTTPResponse
    # because HTTPSHandler.https_open() constructs one internally.
    return cast(http.client.HTTPResponse, response)


def safe_http_post(
    url: str,
    json_data: dict,
    timeout: float = 10.0,
) -> dict:
    """POST JSON to a public HTTPS endpoint.

    Returns a decoded JSON object. Raises SafeHTTPError on failure.
    Only HTTP 200 responses with a JSON object are accepted.
    """
    if not is_safe_url(url):
        raise SafeHTTPError(
            "Insecure or forbidden URL requested.",
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

    # CHANGED: removed the `except SafeHTTPError: raise` guard — it was
    # redundant, because SafeHTTPError is not a subclass of any of the
    # exceptions caught below, so it propagates on its own.
    try:
        with safe_urlopen(req, timeout=timeout) as response:
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
    # CHANGED: same merge as in safe_urlopen — OSError covers
    # TimeoutError and any socket-level failures.
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
