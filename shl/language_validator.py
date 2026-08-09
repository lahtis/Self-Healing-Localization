"""
File: language_validator.py
Author: Tuomas Lähteenmäki
Version: 0.2.0
License: MIT
Description:
    Optional language validation using GLFM (Global Language Family Mapper).
    Provides language code validation, BCP-47 tags, and fallback chains.
    
    Two modes:
    1. GLFM Lite (default): Uses languages_top20.json.gz (~428 KB)
       - Fallback: 20 nearest related languages
    2. Full GLFM: Uses unified_languages.json.gz (~51.6 MB)
       - Fallback: All 7,900+ related languages
    
    The full GLFM database can be enabled via configuration.
"""

import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any, List

from shl.utils.lang_utils import (
    base_language as extract_base_language,
    normalize_full_tag,
    parse_bcp47,
    split_tag,
)

logger = logging.getLogger(__name__)


class LanguageValidator:
    """Validates language codes against GLFM database (optional)."""

    def __init__(
        self,
        glfm_path: Optional[str] = None,
        base_language: str = "en",
        use_lite: bool = True,
    ):
        """
        Initialize language validator.
        
        Args:
            glfm_path: Custom path to GLFM database (if None, uses default)
            base_language: Default fallback language
            use_lite: Use GLFM Lite (~428 KB) instead of full GLFM (~800 MB)
        """
        self.base_language = base_language
        self._loaded = False
        self.languages: Dict[str, Any] = {}
        self._use_lite = use_lite
        self._glfm_path = glfm_path
        
        # Lite: 20 lähintä, Full: kaikki (None = kaikki)
        self._max_nearest = 20 if use_lite else None
        
        # O(1)-hakuindeksi ISO 639-1 -> language ID
        self._iso1_index: Dict[str, str] = {}
        
        # Yritä ladata GLFM
        self._load_glfm()

    def _load_glfm(self) -> None:
        """Load GLFM database from gzipped JSON."""
        try:
            from shl.data.glfm_load_database import load_language_data
            
            # Determine which database to load
            if self._glfm_path:
                # Custom path (could be full or lite)
                db_path = Path(self._glfm_path)
            elif self._use_lite:
                # Default: GLFM Lite
                db_path = Path(__file__).resolve().parent / "data" / "languages_top20.json.gz"
            else:
                # Full GLFM (if available)
                db_path = Path(__file__).resolve().parent / "data" / "unified_languages.json.gz"
            
            self.languages = load_language_data(db_path)
            self._loaded = True
            
            # Rakenna O(1)-hakuindeksi
            self._build_iso1_index()
            
            mode = 'Lite' if self._use_lite else 'Full'
            nearest = self._max_nearest if self._max_nearest is not None else 'all'
            logger.info(
                f"GLFM loaded: {len(self.languages)} languages "
                f"(mode: {mode}, nearest: {nearest})"
            )
            
        except FileNotFoundError as e:
            if not self._use_lite:
                logger.warning(f"Full GLFM not found, falling back to Lite mode: {e}")
                # Try Lite as fallback
                self._use_lite = True
                self._max_nearest = 20
                self._load_glfm()
            else:
                logger.debug(f"GLFM Lite not found, validation disabled: {e}")
                self.languages = {}
                self._loaded = False
        except Exception as e:
            logger.warning(f"Failed to load GLFM: {e}")
            self.languages = {}
            self._loaded = False

    def _build_iso1_index(self) -> None:
        """Build ISO 639-1 index for O(1) lookups."""
        self._iso1_index = {}
        for lang_id, info in self.languages.items():
            iso1 = info.get('iso639_1', '').lower()
            if iso1 and iso1 not in self._iso1_index:
                self._iso1_index[iso1] = lang_id
        logger.debug(f"Built ISO 639-1 index: {len(self._iso1_index)} entries")

    @property
    def is_loaded(self) -> bool:
        """Check if GLFM database is loaded and contains data."""
        return self._loaded and len(self.languages) > 0

    @property
    def is_lite(self) -> bool:
        """Check if using GLFM Lite mode."""
        return self._use_lite

    @property
    def max_nearest(self) -> Optional[int]:
        """Maximum number of nearest languages in fallback chain."""
        return self._max_nearest

    def _find_language(self, lang_code: str) -> Optional[Dict[str, Any]]:
        """
        Find a language in GLFM by ISO 639-1, ISO 639-3, or BCP-47 tag.
        
        Uses O(1) lookup via ISO 639-1 index when possible.
        """
        if not self.is_loaded or not lang_code or not isinstance(lang_code, str):
            return None

        # Get base language (strip script/region)
        base = extract_base_language(lang_code)

        # 1. O(1) lookup by ISO 639-1
        if base in self._iso1_index:
            lang_id = self._iso1_index[base]
            return self.languages.get(lang_id)

        # 2. Direct lookup by ID
        if base in self.languages:
            return self.languages[base]

        # 3. Try full tag
        full_tag = normalize_full_tag(lang_code)
        if full_tag in self.languages:
            return self.languages[full_tag]

        # 4. Fallback: linear search (rare, but safe)
        for lang_id, info in self.languages.items():
            if info.get('iso639_3', '').lower() == base:
                return info

        return None

    def is_valid(self, lang_code: str, strict: bool = False) -> bool:
        """
        Check if language code exists in GLFM.
        
        Args:
            lang_code: Language code to validate
            strict: If True, return False when GLFM is not loaded.
                    If False (default), pass-through (assume valid).
        
        Returns:
            True if found in GLFM or (not strict and GLFM not loaded)
            False if lang_code is empty, None, or (strict and GLFM not loaded)
        """
        if not lang_code or not isinstance(lang_code, str):
            return False
        
        if not self.is_loaded:
            return not strict  # False if strict=True, True if strict=False
        
        return self._find_language(lang_code) is not None

    def get_bcp47(self, lang_code: str) -> Optional[str]:
        """Get BCP-47 tag for a language code."""
        if not lang_code or not isinstance(lang_code, str):
            return None
        
        info = self._find_language(lang_code)
        if info and info.get('bcp47'):
            return info['bcp47']
        
        return normalize_full_tag(lang_code)

    def get_fallback(self, lang_code: str) -> Optional[str]:
        """Get fallback language from GLFM."""
        if not lang_code or not isinstance(lang_code, str):
            return None
        
        info = self._find_language(lang_code)
        if not info:
            return None

        fallback = info.get('fallback', '')
        if not fallback or fallback == lang_code:
            return None

        # If fallback is already ISO 639-1, return it directly
        if len(fallback) == 2:
            return fallback

        # Try to resolve fallback to ISO 639-1
        if fallback in self.languages:
            fb_info = self.languages[fallback]
            fb_iso1 = fb_info.get('iso639_1', '')
            if fb_iso1:
                return fb_iso1

        return fallback

    def get_language_info(self, lang_code: str) -> Optional[Dict[str, Any]]:
        """Get full language information from GLFM."""
        if not lang_code or not isinstance(lang_code, str):
            return None
        return self._find_language(lang_code)

    def get_name(self, lang_code: str) -> Optional[str]:
        """Get language name from GLFM."""
        if not lang_code or not isinstance(lang_code, str):
            return None
        
        info = self._find_language(lang_code)
        if info:
            return info.get('name')
        
        if self.is_loaded:
            return None
        
        parts = split_tag(lang_code)
        if parts.get("language"):
            return f"Language: {parts['language']}"
        return None

    def get_region(self, lang_code: str) -> Optional[str]:
        """
        Get region from language code.
        
        Note: This is a convenience wrapper around parse_bcp47.
        For more detailed region data, use get_language_info().
        """
        _, _, region = parse_bcp47(lang_code)
        return region

    def get_written_scripts(self, lang_code: str) -> Optional[List[str]]:
        """Get scripts used to write this language."""
        if not lang_code or not isinstance(lang_code, str):
            return None
        
        info = self._find_language(lang_code)
        if info:
            return info.get('written_scripts', [])
        return None

    def get_default_script(self, lang_code: str) -> Optional[str]:
        """Get default script for a language."""
        if not lang_code or not isinstance(lang_code, str):
            return None
        
        info = self._find_language(lang_code)
        if info:
            return info.get('default_script')
        return None

    def get_family(self, lang_code: str) -> Optional[str]:
        """Get language family."""
        if not lang_code or not isinstance(lang_code, str):
            return None
        
        info = self._find_language(lang_code)
        if info:
            return info.get('family') or None
        return None

    def get_fallback_chain(
        self,
        lang_code: str,
        base_language: Optional[str] = None,
        max_nearest: Optional[int] = None,
    ) -> List[str]:
        """
        Get complete fallback chain for a language.
        
        Order:
        1. Full normalized tag (e.g., 'zh-TW')
        2. Base language (e.g., 'zh')
        3. GLFM fallback (if defined)
        4. Nearest languages (max_nearest: 20 for Lite, all for Full)
        5. ISO 639-5 family (if available)
        6. User's base_language (from SHL)
        7. English (absolute last resort)
        
        Args:
            lang_code: Language to find fallback for
            base_language: SHL's base language (developer-defined)
            max_nearest: Number of nearest languages to include
                        (None = use default: 20 for Lite, all for Full)
        
        Returns:
            List of language codes from most specific to most general
        """
        if not lang_code or not isinstance(lang_code, str):
            return [base_language or self.base_language or "en"]
        
        chain = []
        seen = set()
        
        # 1. Full normalized tag first
        full_tag = normalize_full_tag(lang_code)
        if full_tag and full_tag not in seen:
            chain.append(full_tag)
            seen.add(full_tag)

        # 2. Base language (e.g., 'zh-TW' -> 'zh')
        base_tag = extract_base_language(lang_code)
        if base_tag and base_tag not in seen:
            chain.append(base_tag)
            seen.add(base_tag)
        
        info = self.get_language_info(lang_code)
        
        # 3. GLFM fallback
        if info:
            fallback = info.get('fallback', '')
            if fallback and fallback not in seen:
                chain.append(fallback)
                seen.add(fallback)
        
        # 4. Nearest languages
        # Lite: max 20, Full: all (None = all)
        limit = max_nearest if max_nearest is not None else self._max_nearest
        if info and 'nearest_languages' in info:
            nearest_langs = info['nearest_languages']
            if limit is not None:
                nearest_langs = nearest_langs[:limit]
            
            for nearest in nearest_langs:
                lang = nearest.get('lang')
                if lang and lang not in seen:
                    chain.append(lang)
                    seen.add(lang)
        
        # 5. ISO 639-5 family
        if info and info.get('iso639_5'):
            family = info['iso639_5']
            if family and family not in seen:
                chain.append(family)
                seen.add(family)
        
        # 6. Developer's base_language
        fallback_lang = base_language or self.base_language
        if fallback_lang:
            fallback_base = extract_base_language(fallback_lang)
            if fallback_base and fallback_base not in seen:
                chain.append(fallback_base)
                seen.add(fallback_base)
        
        # 7. English (absolute last resort)
        if 'en' not in seen:
            chain.append('en')
        
        return chain

    def get_best_available_fallback(
        self,
        lang_code: str,
        available_languages: List[str],
        base_language: Optional[str] = None
    ) -> Optional[str]:
        """
        Find the best available fallback language from a list of supported languages.
        
        Args:
            lang_code: Current language
            available_languages: List of languages supported by the provider/app
            base_language: SHL's base language
        
        Returns:
            Best matching language code or None
        """
        chain = self.get_fallback_chain(lang_code, base_language)
        
        for candidate in chain:
            if candidate in available_languages:
                return candidate
        
        # Last resort: any available language
        return available_languages[0] if available_languages else None
