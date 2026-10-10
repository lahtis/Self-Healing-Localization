"""
File: shl/engine/translation/providers/base.py
Author: Tuomas Lähteenmäki
Version: 0.3.0
License: MIT
Description: Base provider interface for translation adapters.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from ..metadata import TranslationRequest


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
class TranslationResult:
    """Rich result envelope returned by translate_with_metadata().

    Single-engine providers (MyMemory, LibreTranslate, DeepL, ...) never
    need to build this themselves — the default
    TranslationProvider.translate_with_metadata() wraps their translate()
    output automatically, leaving engine/fallback/confidence at their
    defaults.

    Multi-engine providers (e.g. LocalTranslatorAdapter, whose backing
    server may route between DeepL and a LibreTranslate mirror pool)
    override translate_with_metadata() directly and populate
    engine/fallback/confidence from what the backend actually did.
    """

    text: str
    provider: str
    engine: str | None = None
    fallback: bool = False
    confidence: float | None = None


class TranslationProvider(ABC):
    """Abstract base class for translation providers.

    Each provider decides which metadata fields it supports:

    - Core parameters: text, source_lang, target_lang
    - Extended features: context_type, domain, screen, component,
      formality, glossary, html_format
    - SHL internal metadata: key, source_id, metadata

    All providers should use mask_api_key() for secure logging of
    credentials.
    """

    @abstractmethod
    def translate(self, request: TranslationRequest) -> str:
        """Translate text using this provider implementation.

        The provider pipeline should:

        1. Extract and validate supported fields from the
           TranslationRequest.
        2. Build the provider-specific payload using build_request().
        3. Execute the network call and validate the response structure.
        4. Safely ignore non-critical metadata fields unsupported by
           the backend.

        Args:
            request: Fully populated TranslationRequest data structure.

        Returns:
            Translated string returned by the provider.
        """
        ...

    def translate_with_metadata(
        self,
        request: TranslationRequest,
    ) -> TranslationResult:
        """Translate text and return the full TranslationResult envelope.

        Default implementation: call translate() and wrap the string
        with this provider's name, leaving engine/fallback/confidence
        at their defaults. Providers with multiple internal engines
        should override this instead of relying on the default
        wrapping.

        Args:
            request: Fully populated TranslationRequest data structure.

        Returns:
            TranslationResult with at least text and provider populated.
        """
        text = self.translate(request)
        return TranslationResult(text=text, provider=self.name)

    @abstractmethod
    def build_request(
        self,
        request: TranslationRequest,
    ) -> dict[str, Any]:
        """Build the raw API request payload from metadata.

        This method reflects the exact schema sent to the provider
        endpoint.

        Args:
            request: TranslationRequest containing source payload and
                context parameters.

        Returns:
            Dictionary containing key-value pairs formatted for the API
            endpoint.
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider name identifier.

        Examples:
            'mymemory'
            'libretranslate'
            'deepl'
            'googlev2'
            'papago'
        """
        ...

    @property
    def supported_features(self) -> list[str]:
        """List of non-standard metadata keys supported by this adapter.

        Override in subclasses to declare capability support for
        dynamic routing.

        Examples:
            ['formality', 'honorific', 'context', 'glossary',
             'html_format', 'labels']
        """
        return []

    def supports_feature(self, feature: str) -> bool:
        """Check whether a specific metadata feature is supported."""
        return feature.lower() in [
            f.lower() for f in self.supported_features
        ]

    @staticmethod
    def _mask_credential(credential: str | None) -> str:
        """Mask a credential for secure logging.

        Convenience wrapper around mask_api_key().
        """
        return mask_api_key(credential)
