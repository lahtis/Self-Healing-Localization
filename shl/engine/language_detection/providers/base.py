"""
File: shl/engine/language_detection/providers/base.py
Author: Tuomas Lähteenmäki
Version: 0.3.0
License: MIT
Description: Base provider interface for language detection adapters.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


def mask_api_key(key: str | None) -> str:
    """Mask API key for safe logging.

    Returns:
        "(not set)" for None or empty
        "*****" for keys of 8 characters or less
        First 4 and last 4 characters visible for longer keys.
    """
    if not key:
        return "(not set)"

    key_str = key.strip()
    if not key_str:
        return "(not set)"

    if len(key_str) <= 8:
        return "*" * len(key_str)

    return key_str[:4] + "*" * (len(key_str) - 8) + key_str[-4:]


@dataclass
class LanguageDetectionResult:
    """Result returned by a language detection provider."""

    language: str
    score: float | None = None
    provider: str | None = None


class LanguageDetectionProvider(ABC):
    """Abstract base class for language detection providers."""

    # CHANGED: `timeout` added so the router can pass the policy-
    # configured value. Providers that do not support a runtime
    # timeout override should accept the argument and ignore it.
    @abstractmethod
    def detect(
        self,
        text: str,
        timeout: float | None = None,
    ) -> list[LanguageDetectionResult]:
        """Detect the language(s) present in the supplied text.

        Args:
            text: Text to analyze.
            timeout: Optional override for the provider's network
                timeout, in seconds. When None, the provider uses
                its own configured default.

        Returns:
            List of detected language candidates. An empty list
            means the provider answered successfully but did not
            identify any language; the router treats this as a
            definitive (non-retryable) result.
        """
        ...

    @abstractmethod
    def build_request(self, text: str) -> dict[str, Any]:
        """Build the raw API request payload."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider name identifier."""
        ...

    @property
    def supported_features(self) -> list[str]:
        """Optional features supported by this provider."""
        return []

    def supports_feature(self, feature: str) -> bool:
        """Check whether a specific feature is supported."""
        return feature.lower() in [
            item.lower() for item in self.supported_features
        ]

    @staticmethod
    def _mask_credential(credential: str | None) -> str:
        """Mask a credential for secure logging."""
        return mask_api_key(credential)
