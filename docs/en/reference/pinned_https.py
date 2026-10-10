"""
Reference implementation: HTTPS with pinned IP.

Status: REFERENCE ONLY — not imported, not part of the package.

Purpose
-------
This file exists as a documented answer to a question that will come up
again if SHL's endpoint model ever changes:

    "What if endpoints come from outside the code?"

In the current design, endpoints are hard-coded. DNS rebinding is
therefore not a realistic threat: an attacker would have to control
both DNS for a public domain AND the code that references it.

If endpoints ever become configurable (config file, environment
variable, user input), that assumption breaks. An attacker who
controls DNS could return a public IP on the validation lookup
(is_global passes) and an internal IP on the connection lookup
(SSRF succeeds).

The fix is to resolve the hostname exactly once and pin the resolved
IP to the connection, presenting the original hostname via SNI and
the Host header. This file shows how.

How to use
----------
1. Copy the classes below into shl/utils/safe_http.py (or a new
   shl/utils/pinned_http.py).
2. Add tests that monkeypatch socket.getaddrinfo to return a mixed
   answer (public on first call, private on second) and assert the
   request is rejected or that only the pinned IP is used.
3. Update the module docstring of safe_http.py to remove the
   "Known limitation — DNS rebinding" section.
4. If a local/internal path also becomes configurable, mirror the
   same approach in safe_local_http.py.

Tested against: Python 3.9+ (uses http.client.HTTPSConnection with
the private _context attribute, which has been stable since 3.4 but
is not part of the public API).

Caveats
-------
- The code uses self._context from http.client.HTTPSConnection, which
  is a private attribute. If CPython changes it, this needs updating.
- IPv6 hosts must be handled via urlsplit, not string split — see the
  https_open method below for the correct approach.
- The connection timeout is inherited from the opener, not set here.
- urllib's do_open() contract is not documented as stable, though it
  has been stable for many years.
"""
import http.client
import socket
import ssl
import urllib.request
from urllib.parse import urlsplit

from shl.utils.safe_http_common import SafeHTTPError


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """HTTPSConnection that connects to a fixed IP but presents the
    original hostname via SNI and the Host header.
    """

    def __init__(self, host, *, connect_ip, sni_hostname, **kwargs):
        super().__init__(host, **kwargs)
        self._connect_ip = connect_ip
        self._sni_hostname = sni_hostname

    def connect(self):
        self.sock = socket.create_connection(
            (self._connect_ip, self.port), self.timeout
        )
        self.sock = self._context.wrap_socket(
            self.sock, server_hostname=self._sni_hostname
        )


class _PinnedHTTPSHandler(urllib.request.HTTPSHandler):
    """HTTPSHandler that connects to a pre-resolved IP for each host.

    The pinned_ips dict maps lowercase hostname -> IP string. Any
    request whose host is not in the dict is refused.
    """

    def __init__(self, pinned_ips, **kwargs):
        super().__init__(**kwargs)
        self._pinned_ips = pinned_ips

    def https_open(self, req):
        # Use urlsplit so IPv6 literals ([::1]) are handled correctly.
        # req.host is "hostname:port" or "[::1]:port" or just "hostname".
        parsed = urlsplit(f"//{req.host}")
        host = parsed.hostname
        if host is None:
            raise SafeHTTPError("Malformed Host header")
        host = host.lower()

        ip = self._pinned_ips.get(host)
        if ip is None:
            raise SafeHTTPError(f"No pinned IP for host: {host}")

        sni = host

        def factory(h, **kw):
            return _PinnedHTTPSConnection(
                h, connect_ip=ip, sni_hostname=sni, **kw
            )

        return self.do_open(factory, req)
