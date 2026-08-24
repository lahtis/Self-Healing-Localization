"""
File: base.py — Base provider interface for translation adapters.
Author: Tuomas Lähteenmäki
Version: 0.2.6
License: MIT
Description: Base provider interface for translation adapters.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from ..metadata import TranslationRequest
def mask_api_key(key: Optional[str]) -> str:
    """
    Mask API key for safe logging.
    Args:
        key: API key string or None
    Returns:
        Masked string:
        - "(not set)" if key is None or empty
        - "*****" if key is 8 characters or less
        - "abcd***********wxyz" for longer keys (first 4 + last 4 visible)
    Examples:
        >>> mask_api_key("my-secret-key-12345")
        'my-s*****************12345'
        >>> mask_api_key("short")
        '*****'
        >>> mask_api_key(None)
        '(not set)'
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
class TranslationResult:
    """
    Rich result envelope returned by translate_with_metadata().

    Single-engine providers (MyMemory, LibreTranslate, DeepL, ...) never need
    to build this themselves - the default TranslationProvider.translate_with_metadata()
    wraps their translate() output automatically, leaving engine/fallback/confidence
    at their defaults.

    Multi-engine providers (e.g. LocalTranslatorAdapter, whose backing server may
    route between DeepL and a LibreTranslate mirror pool) override
    translate_with_metadata() directly and populate engine/fallback/confidence
    from what the backend actually did.
    """
    text: str
    provider: str
    engine: Optional[str] = None
    fallback: bool = False
    confidence: Optional[float] = None
class TranslationProvider(ABC):
    """
    Abstract base class for translation providers.
    Each provider decides which metadata fields it supports:
    - Core parameters: text, source_lang, target_lang
    - Extended features: context_type, domain, screen, component, formality, glossary, html_format
    - SHL internal metadata: key, source_id, metadata
    All providers should use mask_api_key() for secure logging of credentials.
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
    def translate_with_metadata(self, request: TranslationRequest) -> TranslationResult:
        """
        Translate text and return the full TranslationResult envelope.

        Default implementation: call translate() and wrap the string with
        this provider's name, leaving engine/fallback/confidence at their
        defaults. Providers with multiple internal engines should override
        this instead of relying on the default wrapping.

        :param request: Fully populated TranslationRequest data structure.
        :return: TranslationResult with at least text and provider populated.
        """
        text = self.translate(request)
        return TranslationResult(text=text, provider=self.name)
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
        Examples: 'mymemory', 'libretranslate', 'deepl', 'googlev2', 'papago',
        """
        pass
    @property
    def supported_features(self) -> List[str]:
        """
        List of non-standard metadata keys supported by this provider adapter.
        
        Override in subclasses to declare capability support for dynamic routing.
        Examples: ['formality', 'honorific', 'context', 'glossary', 'html_format', 'labels']
        """
        return []
    def supports_feature(self, feature: str) -> bool:
        """Check whether a specific metadata feature is supported by this adapter."""
        return feature.lower() in [f.lower() for f in self.supported_features]
    def _mask_credential(self, credential: Optional[str]) -> str:
        """
        Mask a credential for secure logging.
        Convenience wrapper around mask_api_key().
        Args:
            credential: Credential string or None
        Returns:
            Masked credential string
        Example:
            >>> provider._mask_credential("my-secret-key")
            'my-s*****************ey'
        """
        return mask_api_key(credential)
