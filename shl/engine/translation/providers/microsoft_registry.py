# microsoft_registry.py

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


