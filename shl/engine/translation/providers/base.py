"""
Base provider interface for translation adapters.
file: base.py
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from ..metadata import TranslationRequest


class TranslationProvider(ABC):
    """
    Abstract base class for translation providers.

    Each provider decides which metadata fields it supports:
    - Core parameters: text, source_lang, target_lang
    - Extended features: context_type, domain, screen, component, formality, glossary, html_format
    - SHL internal metadata: key, source_id, metadata
    """

    @abstractmethod
    def translate(self, request: TranslationRequest) -> str:
        """
        Translate text using this provider implementation.

        The provider pipeline should:
        1. Extract and validate supported fields from the TranslationRequest.
        2. Build the provider-specific payload using `build_request`.
        3. Execute the network call and validate the response structure.
        4. Safely ignore non-critical metadata fields unsupported by the backend.

        :param request: Fully populated TranslationRequest data structure.
        :return: Translated string returned by the provider.
        """
        pass

    @abstractmethod
    def build_request(self, request: TranslationRequest) -> Dict[str, Any]:
        """
        Build the raw API request payload or parameter dictionary from metadata.

        This method reflects the exact schema sent to the provider endpoint.

        :param request: TranslationRequest containing source payload and context parameters.
        :return: Dictionary containing key-value pairs formatted for the API endpoint.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique provider name identifier.
        Examples: 'mymemory', 'libretranslate', 'deepl', 'google'.
        """
        pass

    @property
    def supported_features(self) -> List[str]:
        """
        List of non-standard metadata keys supported by this provider adapter.
        
        Override in subclasses to declare capability support for dynamic routing.
        Examples: ['formality', 'context', 'glossary', 'html_format', 'labels']
        """
        return []

    def supports_feature(self, feature: str) -> bool:
        """Check whether a specific metadata feature is supported by this adapter."""
        return feature.lower() in [f.lower() for f in self.supported_features]
