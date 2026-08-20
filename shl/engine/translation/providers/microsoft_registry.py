"""
File: microsoft_registry.py — module for Microsoft Translator adapter.
Author: Tuomas Lähteenmäki
Version: 0.2.5
License: MIT
Description: Robust translation provider adapter for the Microsoft Translator API.
"""

import time
from typing import Optional


class MicrosoftServiceRegistry:
    def __init__(self, ttl_seconds: int = 600):
        self.ttl = ttl_seconds
        self.unavailable_until: float = 0.0

    def mark_unavailable(self) -> None:
        self.unavailable_until = time.time() + self.ttl

    def is_available(self) -> bool:
        return time.time() >= self.unavailable_until

    def clear(self) -> None:
        self.unavailable_until = 0.0


