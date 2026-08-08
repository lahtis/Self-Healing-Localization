"""
Deprecated: AITranslator has been replaced by the new translation module.
"""

import warnings
from typing import Dict, Any, Optional

warnings.warn(
    "AITranslator is deprecated. Use the new translation module functions: "
    "translate_text(), get_best_provider(), etc.",
    DeprecationWarning,
    stacklevel=2,
)


class AITranslator:
    """
    Deprecated translator class.

    Use the new translation module functions instead:
    - translate_text()
    - get_best_provider()
    - get_all_supported_languages()
    """

    def __init__(
        self,
        provider: str = "auto",
        libretranslate_url: Optional[str] = None,
        libretranslate_api_key: Optional[str] = None,
        mymemory_email: Optional[str] = None,
    ):
        self.provider = provider
        self.libretranslate_url = libretranslate_url
        self.libretranslate_api_key = libretranslate_api_key
        self.mymemory_email = mymemory_email
        self._cache = None

    def translate(self, text: str, target_lang: str = "fi", source_lang: str = "en") -> str:
        """Translate text (deprecated)."""
        from .router import translate_text
        return translate_text(
            text=text,
            target_lang=target_lang,
            source_lang=source_lang,
            libretranslate_url=self.libretranslate_url,
            libretranslate_api_key=self.libretranslate_api_key,
            mymemory_email=self.mymemory_email,
        )

    def batch_translate(
        self,
        texts: Dict[str, str],
        target_lang: str,
        source_lang: str = "en",
    ) -> Dict[str, str]:
        """Batch translate texts (deprecated)."""
        result = {}
        for key, text in texts.items():
            result[key] = self.translate(text, target_lang, source_lang)
        return result

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics (deprecated)."""
        return {"cache_size": 0, "provider": self.provider}

    def clear_cache(self) -> None:
        """Clear cache (deprecated)."""
        pass
