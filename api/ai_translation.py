"""
ai_translation.py — Optional module for future AI-powered translations.

This module is intentionally lightweight and dependency-free.
It provides a clean interface for future expansion without affecting
the core functionality of the Self-Healing Localization Layer (SHLL).

Planned features for v0.2:
- Automatic translation of missing keys
- Batch translation tools
- Provider-specific adapters (OpenAI, Azure, etc.)
- CLI integration

For now, this module acts as a placeholder and safe extension point.
"""


class AITranslator:
    """
    Placeholder class for future AI translation features.

    The interface is intentionally minimal and stable so that
    future implementations can be added without breaking compatibility.
    """

    def __init__(self, provider: str = "none"):
        """
        Initialize the translator.

        Parameters:
            provider (str): Name of the translation provider.
                            Currently unused.
        """
        self.provider = provider

    def translate(self, text: str, target_lang: str) -> str:
        """
        Placeholder translation method.

        Parameters:
            text (str): The text to translate.
            target_lang (str): Target language code (e.g., 'fi', 'sv', 'de').

        Returns:
            str: The original text (no translation performed).
        """
        # Future implementation will call an AI provider here.
        return text

    def batch_translate(self, items: dict, target_lang: str) -> dict:
        """
        Placeholder batch translation method.

        Parameters:
            items (dict): A dictionary of key -> text pairs.
            target_lang (str): Target language code.

        Returns:
            dict: The original dictionary (no translation performed).
        """
        # Future implementation will translate all values.
        return items
