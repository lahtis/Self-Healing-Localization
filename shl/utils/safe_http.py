import socket
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, build_opener


class _SameHostRedirectHandler(HTTPRedirectHandler):
    """Follow redirects only within the same host, so credentials
    in headers are never forwarded to a different host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlparse(newurl).hostname != urlparse(req.full_url).hostname:
            return None
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_opener = build_opener(_SameHostRedirectHandler)


def safe_urlopen(url, data=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT):
    """Drop-in replacement for urllib.request.urlopen."""
    return _opener.open(url, data, timeout)
