"""
Base provider interface for translation adapters.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from ..metadata import TranslationRequest


class TranslationProvider(ABC):
    """
    Abstract base class for translation providers.

    Each provider decides which metadata fields it supports:
    - All providers: text, source_lang, target_lang
    - Some providers: context_type, domain, screen, component, formality, glossary, html_format
    - SHL internal: key, source_id, metadata
    """

    @abstractmethod
    def translate(self, request: TranslationRequest) -> str:
        """
        Translate text using this provider.

        The provider should:
        1. Extract the fields it supports from the request
        2. Build the API call
        3. Return the translated text
        4. Ignore fields it doesn't support
        """
        pass

    @abstractmethod
    def build_request(self, request: TranslationRequest) -> Dict[str, Any]:
        """
        Build the API request payload from metadata.

        This method shows which fields are actually sent to the API.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name: 'mymemory', 'libretranslate', 'deepl', etc."""
        pass
