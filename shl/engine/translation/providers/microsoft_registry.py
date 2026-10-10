"""
File: shl/engine/translation/providers/microsoft_registry.py
Author: Tuomas Lähteenmäki
Version: 0.3.0
License: MIT
Description: Service availability registry for the Microsoft Translator
API.

Tracks a single TTL window during which the service is considered
unavailable, so repeated calls do not hammer an endpoint that has
already returned a service-level error.

This module performs no HTTP calls. It only tracks a timestamp.
"""

import time


class MicrosoftServiceRegistry:
    """Tracks Microsoft Translator service availability with a TTL.

    When the service returns a service-level error (5xx, timeout),
    the caller marks it unavailable. Subsequent calls within the TTL
    window are rejected without a network request. After the window
    elapses, the service is assumed to be available again.
    """

    def __init__(self, ttl_seconds: int = 600):
        self.ttl = ttl_seconds
        self.unavailable_until: float = 0.0

    def mark_unavailable(self) -> None:
        """Mark the service unavailable for the TTL duration."""
        self.unavailable_until = time.time() + self.ttl

    def is_available(self) -> bool:
        """Return True if the TTL window has elapsed."""
        return time.time() >= self.unavailable_until

    def clear(self) -> None:
        """Clear the unavailability window immediately."""
        self.unavailable_until = 0.0
