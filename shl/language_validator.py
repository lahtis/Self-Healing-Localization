"""
File: language_validator.py
Author: Tuomas Lähteenmäki
Version: 0.1.7
License: MIT
Description:
    Optional language validation using GLFM (Global Language Family Mapper).
    Provides language code validation, BCP-47 tags, and fallback chains
    for over 7,900 languages.
"""

import json
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class LanguageValidator:
    """Validates language codes against GLFM database (optional)."""

    def __init__(self, glfm_path: Optional[str] = None):
        """
        Initialize validator with optional GLFM database.

        Args:
            glfm_path: Path to unified_languages.json. If None, uses bundled file.
        """
        self.languages: Dict[str, Any] = {}
        self._loaded = False
        self._load_glfm(glfm_path)

    def _load_glfm(self, path: Optional[str] = None) -> None:
        """Load GLFM database from JSON file."""
        if path is None:
            path = os.path.join(
                os.path.dirname(__file__), 'data', 'unified_languages.json'
            )

        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.languages = json.load(f)
                self._loaded = True
                logger.info(f"GLFM loaded: {len(self.languages)} languages")
            except Exception as e:
                logger.warning(f"Failed to load GLFM: {e}")
                self.languages = {}
        else:
            logger.debug(f"GLFM not found at {path}, validation disabled")

    @property
    def is_loaded(self) -> bool:
        """Check if GLFM database is loaded."""
        return self._loaded and len(self.languages) > 0

    def _find_language(self, lang_code: str) -> Optional[Dict[str, Any]]:
        """
        Find a language in GLFM by ISO 639-1 or ISO 639-3 code.

        Args:
            lang_code: Language code (e.g., 'fi', 'zh')

        Returns:
            Language info dict or None
        """
        if not self.is_loaded:
            return None

        base = lang_code.lower().split('-')[0]

        for lang_id, info in self.languages.items():
            if info.get('iso639_1', '').lower() == base:
                return info

        if base in self.languages:
            return self.languages[base]

        return None

    def is_valid(self, lang_code: str) -> bool:
        """
        Check if language code exists in GLFM.

        Args:
            lang_code: Language code to validate

        Returns:
            True if found in GLFM, True if GLFM not loaded (pass-through)
        """
        if not self.is_loaded:
            return True

        return self._find_language(lang_code) is not None

    def get_bcp47(self, lang_code: str) -> Optional[str]:
        """
        Get BCP-47 tag for a language code.

        Args:
            lang_code: Language code (e.g., 'fi', 'zh')

        Returns:
            BCP-47 tag (e.g., 'fi-Latn-FI') or None
        """
        info = self._find_language(lang_code)
        if info:
            return info.get('bcp47')
        return None

    def get_fallback(self, lang_code: str) -> Optional[str]:
        """
        Get fallback language from GLFM.

        Args:
            lang_code: Language code

        Returns:
            Fallback language ISO 639-1 code or None
        """
        info = self._find_language(lang_code)
        if not info:
            return None

        fallback = info.get('fallback', '')
        if not fallback or fallback == lang_code:
            return None

        if fallback in self.languages:
            fb_info = self.languages[fallback]
            fb_iso1 = fb_info.get('iso639_1', '')
            if fb_iso1:
                return fb_iso1

        return fallback

    def get_language_info(self, lang_code: str) -> Optional[Dict[str, Any]]:
        """
        Get full language information from GLFM.

        Args:
            lang_code: Language code

        Returns:
            Language info dict or None
        """
        return self._find_language(lang_code)

    def get_name(self, lang_code: str) -> Optional[str]:
        """
        Get language name from GLFM.

        Args:
            lang_code: Language code

        Returns:
            Language name (e.g., 'Finnish') or None
        """
        info = self._find_language(lang_code)
        if info:
            return info.get('name')
        return None
