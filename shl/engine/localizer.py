"""
File: localizer.py
Author: Tuomas Lähteenmäki
Version: 0.1.7
License: MIT
Description:
    Self-Healing Localizer for UI text.
    - Creates missing language files automatically
    - Adds missing keys on the fly
    - Falls back to default language (English)
    - Handles corrupted JSON files gracefully
    - Validates and normalizes all keys
    - Migrates legacy file format (lang_xx.json → xx.json)
    - Preserves region subtags in file names (zh-TW → zh-tw.json)
"""

import json
import os
import shutil
import logging
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class Localizer:
    """
    Self-Healing Localizer for UI text.
    - Creates missing language files automatically
    - Adds missing keys on the fly
    - Falls back to default language (English)
    - Handles corrupted JSON files gracefully
    - Validates and normalizes all keys
    - Migrates legacy file format automatically
    - Preserves region subtags for language variants
    """

    def __init__(self, lang_code=None, base_lang="en", folder="locales"):
        self.folder = folder
        self.base_lang = base_lang

        # Determine language (persistent base fallback)
        if lang_code is None:
            lang_code = self._detect_language() or base_lang

        # Validate and normalize language code
        self.lang_code = self._validate_lang_code(lang_code)
        self.base_lang = self._validate_lang_code(base_lang)

        # Ensure folder exists
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)
            logger.info(f"Created folder: {self.folder}")

        # File paths (e.g., fi.json, zh-tw.json)
        self.lang_file = os.path.join(self.folder, f"{self.lang_code}.json")
        self.base_file = os.path.join(self.folder, f"{self.base_lang}.json")

        # Load or create language file
        self.texts = self._load_or_create()

        logger.debug(f"Localizer initialized: lang={self.lang_code}, keys={len(self.texts)}")

    def _detect_language(self) -> Optional[str]:
        """Detect language from config.conf"""
        import configparser
        try:
            if os.path.exists("config.conf"):
                config = configparser.ConfigParser()
                config.read("config.conf")
                return config.get("SETTINGS", "language", fallback=None)
        except Exception as e:
            logger.debug(f"Language detection from config failed: {e}")
        return None

    def _validate_lang_code(self, lang_code: str) -> str:
        """
        Validate and normalize language code.
        Preserves region subtags for file naming (zh-TW → zh-tw.json).
        """
        if not isinstance(lang_code, str) or not lang_code.strip():
            logger.warning(f"Invalid language code: {lang_code}, using 'en'")
            return "en"

        code = lang_code.strip().lower()

        # If code contains hyphen, preserve the region (zh-TW → zh-tw)
        if '-' in code:
            parts = code.split('-')
            if len(parts) == 2 and len(parts[0]) == 2 and len(parts[1]) == 2:
                return f"{parts[0]}-{parts[1]}"
            return parts[0]

        # If code contains underscore (from LANG env), convert to hyphen
        if '_' in code:
            parts = code.split('_')
            if len(parts) == 2 and len(parts[0]) == 2 and len(parts[1]) == 2:
                return f"{parts[0]}-{parts[1]}"
            return parts[0]

        return code

    def _validate_key(self, key: str) -> str:
        """
        Validate and normalize key.
        Consistent None vs '' policy: always returns a string.
        """
        if not isinstance(key, str):
            logger.warning(f"Invalid key type: {type(key)}")
            return ""

        normalized = key.strip()

        if not normalized:
            logger.debug("Empty key detected")
            return ""

        if normalized != key:
            logger.debug(f"Key normalized: '{key}' → '{normalized}'")

        return normalized

    def _load_json_safe(self, filepath: str) -> Dict[str, Any]:
        """
        Safely load a JSON file.
        If the file is corrupted, create a backup and return an empty dict.
        """
        try:
            if not os.path.exists(filepath):
                return {}

            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                logger.error(f"JSON file does not contain a dictionary: {filepath}")
                self._backup_corrupted_file(filepath)
                return {}

            return data

        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Corrupted JSON file: {filepath} - {e}")
            self._backup_corrupted_file(filepath)
            return {}
        except Exception as e:
            logger.error(f"Unexpected error loading file: {filepath} - {e}")
            return {}

    def _backup_corrupted_file(self, filepath: str):
        """Create a backup of a corrupted file"""
        try:
            if os.path.exists(filepath):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"{filepath}.{timestamp}.bak"
                shutil.copy2(filepath, backup_path)
                logger.info(f"Backup created: {backup_path}")
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")

    def _migrate_legacy_file(self, legacy_path: str, new_path: str) -> Optional[Dict[str, Any]]:
        """
        Migrate legacy file format (lang_xx.json) to new format (xx.json).
        Returns the loaded data if successful, None otherwise.
        """
        if not os.path.exists(legacy_path):
            return None

        if legacy_path == new_path:
            return None

        logger.info(f"Found legacy file: {legacy_path}")
        legacy_texts = self._load_json_safe(legacy_path)

        if legacy_texts:
            try:
                self._save_texts(legacy_texts, new_path)
                logger.info(f"Migrated {len(legacy_texts)} keys from '{legacy_path}' to '{new_path}'")
                return legacy_texts
            except Exception as e:
                logger.error(f"Migration failed: {e}")

        return None

    def _load_or_create(self) -> Dict[str, Any]:
        """Load or create language file with base fallback and legacy migration"""
        if os.path.exists(self.lang_file):
            texts = self._load_json_safe(self.lang_file)
            if texts:
                logger.debug(f"Loaded {len(texts)} keys from file: {self.lang_file}")
                return texts
            logger.warning(f"Language file corrupted, loading base: {self.lang_file}")

        # Check for legacy format (lang_xx.json → xx.json)
        legacy_file = os.path.join(self.folder, f"lang_{self.lang_code}.json")
        legacy_texts = self._migrate_legacy_file(legacy_file, self.lang_file)
        if legacy_texts:
            return legacy_texts

        # Load base file
        base_texts = {}
        if os.path.exists(self.base_file):
            base_texts = self._load_json_safe(self.base_file)
            if base_texts:
                logger.info(f"Loading from base language: {self.base_file} ({len(base_texts)} keys)")
            else:
                logger.warning(f"Base file corrupted or empty: {self.base_file}")
        else:
            legacy_base = os.path.join(self.folder, f"lang_{self.base_lang}.json")
            base_texts = self._migrate_legacy_file(legacy_base, self.base_file) or {}

        try:
            self._save_texts(base_texts, self.lang_file)
            logger.info(f"Created new language file from base: {self.lang_file}")
        except Exception as e:
            logger.error(f"Language file save failed: {e}")

        return base_texts

    def _save_texts(self, texts: Dict[str, Any], filepath: str = None):
        """Safely save texts to a JSON file"""
        if filepath is None:
            filepath = self.lang_file

        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(texts, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Save failed: {filepath} - {e}")

    def _save(self):
        """Save current texts (backwards compatibility)"""
        self._save_texts(self.texts)

    def set_language(self, lang_code: str):
        """Switch active language and load new texts"""
        validated_lang = self._validate_lang_code(lang_code)
        if validated_lang != self.lang_code:
            self.lang_code = validated_lang
            self.lang_file = os.path.join(self.folder, f"{self.lang_code}.json")
            self.texts = self._load_or_create()
            logger.info(f"Language switched to: {validated_lang}")

    def L(self, key, default=""):
        """
        Self-healing key lookup.
        If key is missing, add it automatically.
        Consistent None vs '' policy: always returns a string.
        """
        validated_key = self._validate_key(key)
        if not validated_key:
            return default if default else ""

        if validated_key not in self.texts:
            self.texts[validated_key] = default if default else ""
            self._save()
            logger.debug(f"Added missing key: '{validated_key}' = '{default}'")

        text = self.texts.get(validated_key, default)
        return text if text is not None else ""

    def get(self, key, default=""):
        """Get key value (same as L)"""
        return self.L(key, default)

    def get_text(self, key: str, lang_code: str = None) -> Optional[str]:
        """
        Return text or None if key doesn't exist.
        Checks own language first, then base language.
        """
        validated_key = self._validate_key(key)
        if not validated_key:
            return None

        if lang_code and lang_code != self.lang_code:
            return self._get_text_from_lang(validated_key, lang_code)

        text = self.texts.get(validated_key)

        if text is None and self.lang_code != self.base_lang:
            logger.debug(f"UI key '{validated_key}' missing, fallback to base language")
            text = self._get_text_from_lang(validated_key, self.base_lang)

        return text

    def _get_text_from_lang(self, key: str, lang_code: str) -> Optional[str]:
        """Get text from a specific language file"""
        try:
            lang_file = os.path.join(self.folder, f"{lang_code}.json")
            if os.path.exists(lang_file):
                with open(lang_file, "r", encoding="utf-8") as f:
                    texts = json.load(f)
                    return texts.get(key)
        except Exception as e:
            logger.error(f"Error fetching from language {lang_code}: {e}")
        return None

    def set_text(self, key: str, value: str):
        """Set text and save (consistent None vs '' handling)"""
        validated_key = self._validate_key(key)
        if not validated_key:
            logger.warning("Attempted to set text for empty key")
            return

        normalized_value = value if value is not None else ""
        self.texts[validated_key] = normalized_value
        self._save()
        logger.debug(f"Set: '{validated_key}' = '{normalized_value}'")

    def has_key(self, key: str) -> bool:
        """Check if key exists (normalized)"""
        validated_key = self._validate_key(key)
        if not validated_key:
            return False
        return validated_key in self.texts

    def keys(self):
        """Return all keys"""
        return list(self.texts.keys())

    def values(self):
        """Return all values (None → '' normalized)"""
        return [v if v is not None else "" for v in self.texts.values()]

    def items(self):
        """Return all key-value pairs (None → '' normalized)"""
        return [(k, v if v is not None else "") for k, v in self.texts.items()]

    def __contains__(self, key):
        return self.has_key(key)

    def __getitem__(self, key):
        return self.L(key)

    def __setitem__(self, key, value):
        self.set_text(key, value)

    def __len__(self):
        return len(self.texts)

    def __repr__(self):
        return f"Localizer(lang='{self.lang_code}', keys={len(self.texts)})"
