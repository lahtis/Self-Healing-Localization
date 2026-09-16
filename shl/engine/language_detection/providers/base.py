"""
File: base.py — Base provider interface for language detection adapters.
Author: Tuomas Lähteenmäki
Version: 0.2.10
License: MIT
Description: Base provider interface for language detection adapters.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


def mask_api_key(key: Optional[str]) -> str:
    """
    Mask API key for safe logging.

    Args:
        key: API key string or None.

    Returns:
        Masked string:
        - "(not set)" if key is None or empty
        - "*****" if key is 8 characters or less
        - First 4 and last 4 characters visible for longer keys.
    """
    if not key:
        return "(not set)"

    key_str = str(key).strip()

    if not key_str:
        return "(not set)"

    if len(key_str) <= 8:
        return "*" * len(key_str)

    return key_str[:4] + "*" * (len(key_str) - 8) + key_str[-4:]


@dataclass
class LanguageDetectionResult:
    """
    Result returned by a language detection provider.

    Attributes:
        language: Detected language code.
        score: Detection confidence score when provided by the provider.
        provider: Name of the provider that produced the result.
    """

    language: str
    score: Optional[float] = None
    provider: Optional[str] = None


class LanguageDetectionProvider(ABC):
    """
    Abstract base class for language detection providers.

    Providers implement the provider-specific API communication while SHL
    handles provider selection and fallback separately through the
    Language Detection Router.

    Core operation:
        text -> detected language candidates
    """

    @abstractmethod
    def detect(self, text: str) -> List[LanguageDetectionResult]:
        """
        Detect the language or languages present in the supplied text.

        The provider pipeline should:

        1. Validate the input text.
        2. Build the provider-specific request.
        3. Execute the network call.
        4. Validate the response structure.
        5. Convert provider-specific results into
           LanguageDetectionResult objects.

        Args:
            text: Text whose language should be detected.

        Returns:
            List of detected language candidates.

        Raises:
            Provider-specific exceptions are handled by the
            Language Detection Router.
        """
        pass

    @abstractmethod
    def build_request(self, text: str) -> Dict[str, Any]:
        """
        Build the raw API request payload or parameter dictionary.

        Args:
            text: Text to send to the language detection service.

        Returns:
            Dictionary containing provider-specific request parameters.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique provider name identifier.

        Examples:
            'detectlanguage'
            'azure'
            'google'
        """
        pass

    @property
    def supported_features(self) -> List[str]:
        """
        List of optional features supported by this provider.

        This allows the Language Detection Router or other SHL components
        to inspect provider capabilities without hardcoding provider names.
        """
        return []

    def supports_feature(self, feature: str) -> bool:
        """
        Check whether a specific feature is supported by this adapter.
        """
        return feature.lower() in [
            item.lower() for item in self.supported_features
        ]

    def _mask_credential(self, credential: Optional[str]) -> str:
        """
        Mask a credential for secure logging.

        Args:
            credential: Credential string or None.

        Returns:
            Masked credential string.
        """
        return mask_api_key(credential)
