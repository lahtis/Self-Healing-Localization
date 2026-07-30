"""
File: language_validator.py
Author: Tuomas Lähteenmäki
Version: 0.2.0
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

from shl.utils.lang_utils import base_language, normalize_full_tag, parse_bcp47, split_tag

logger = logging.getLogger(__name__)


class LanguageValidator:
    """Validates language codes against GLFM database (optional)."""

    def __init__(self, glfm_path: Optional[str] = None):
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
                    data = json.load(f)
                    # Ensure data is a dictionary
                    if isinstance(data, dict):
                        self.languages = data
                        self._loaded = True
                        logger.info(f"GLFM loaded: {len(self.languages)} languages")
                    else:
                        logger.warning(f"GLFM file does not contain a dictionary: {path}")
                        self.languages = {}
                        self._loaded = False
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse GLFM JSON: {e}")
                self.languages = {}
                self._loaded = False
            except Exception as e:
                logger.warning(f"Failed to load GLFM: {e}")
                self.languages = {}
                self._loaded = False
        else:
            logger.debug(f"GLFM not found at {path}, validation disabled")
            self.languages = {}
            self._loaded = False

    @property
    def is_loaded(self) -> bool:
        """Check if GLFM database is loaded and contains data."""
        return self._loaded and len(self.languages) > 0

    def _find_language(self, lang_code: str) -> Optional[Dict[str, Any]]:
        """
        Find a language in GLFM by ISO 639-1 or ISO 639-3 code.
        Uses lang_utils to get base language.
        """
        if not self.is_loaded or not lang_code or not isinstance(lang_code, str):
            return None

        # Get base language (strip script/region)
        base = base_language(lang_code)

        # Try to find by ISO 639-1
        for lang_id, info in self.languages.items():
            if info.get('iso639_1', '').lower() == base:
                return info

        # Try direct lookup by ID
        if base in self.languages:
            return self.languages[base]

        # Try full tag
        full_tag = normalize_full_tag(lang_code)
        if full_tag in self.languages:
            return self.languages[full_tag]

        return None

    def is_valid(self, lang_code: str) -> bool:
        """
        Check if language code exists in GLFM.
        
        Args:
            lang_code: Language code to validate
            
        Returns:
            True if found in GLFM, True if GLFM not loaded (pass-through)
            False if lang_code is empty or None
        """
        # Empty or None is always invalid
        if not lang_code or not isinstance(lang_code, str):
            return False
        
        # If GLFM not loaded, pass-through (assume valid)
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
        if not lang_code or not isinstance(lang_code, str):
            return None
        
        info = self._find_language(lang_code)
        if info:
            return info.get('bcp47')
        
        # If GLFM doesn't have it, generate from lang_utils
        return normalize_full_tag(lang_code)

    def get_fallback(self, lang_code: str) -> Optional[str]:
        """
        Get fallback language from GLFM.
        
        Args:
            lang_code: Language code
            
        Returns:
            Fallback language ISO 639-1 code or None
        """
        if not lang_code or not isinstance(lang_code, str):
            return None
        
        info = self._find_language(lang_code)
        if not info:
            return None

        fallback = info.get('fallback', '')
        if not fallback or fallback == lang_code:
            return None

        # Try to resolve fallback to ISO 639-1
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
        if not lang_code or not isinstance(lang_code, str):
            return None
        
        return self._find_language(lang_code)

    def get_name(self, lang_code: str) -> Optional[str]:
        """
        Get language name from GLFM.
        
        Args:
            lang_code: Language code
            
        Returns:
            Language name (e.g., 'Finnish') or None
        """
        if not lang_code or not isinstance(lang_code, str):
            return None
        
        info = self._find_language(lang_code)
        if info:
            return info.get('name')
        
        # If GLFM doesn't have it, return None
        if self.is_loaded:
            return None
        
        # If GLFM not loaded, return a generated name
        parts = split_tag(lang_code)
        if parts.get("language"):
            return f"Language: {parts['language']}"
        return None

    def get_region(self, lang_code: str) -> Optional[str]:
        """
        Get region from language code using lang_utils.
        
        Args:
            lang_code: Language code
            
        Returns:
            Region code or None
        """
        _, _, region = parse_bcp47(lang_code)
        return region
