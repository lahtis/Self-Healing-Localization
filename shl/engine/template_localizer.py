"""
File: template_localizer.py
Author: Tuomas Lähteenmäki
Version: 0.1.7
License: MIT
Description:
    Self-Healing Localizer for AI prompt templates.
    - Creates missing template language files automatically
    - Copies base language templates as fallback
    - Adds missing keys on the fly
    - Ensures template consistency across languages
    - Validates template keys and handles corruption gracefully
    - Consistent None vs "" handling
    - Preserves region subtags for language variants
"""

import json
import os
import shutil
import logging
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class TemplateLocalizer:
    """
    Self-Healing Localizer for AI prompt templates.
    - Creates missing template language files automatically
    - Copies base language templates as fallback
    - Adds missing keys on the fly
    - Handles corrupted JSON files gracefully
    - Validates and normalizes all template keys
    - Preserves region subtags for language variants
    """

    def __init__(self, lang_code=None, base_lang="en", folder="prompts"):
        self.folder = folder

        # Determine language (persistent base fallback)
        if lang_code is None:
            lang_code = self._detect_language() or base_lang

        # Validate and normalize language code
        self.lang_code = self._validate_lang_code(lang_code)
        self.base_lang = self._validate_lang_code(base_lang)

        # Ensure folder exists
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)
            logger.info(f"Created template folder: {self.folder}")

        # File paths (e.g., fi.json, zh-tw.json)
        self.lang_file = os.path.join(self.folder, f"{self.lang_code}.json")
        self.base_file = os.path.join(self.folder, f"{self.base_lang}.json")

        # Load or create template file
        self.templates = self._load_or_create()

        logger.debug(f"TemplateLocalizer initialized: lang={self.lang_code}, templates={len(self.templates)}")

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
        Validate and normalize template key.
        Consistent None vs '' policy: always returns a string.
        """
        if not isinstance(key, str):
            logger.warning(f"Invalid template key type: {type(key)}")
            return ""

        normalized = key.strip()

        if not normalized:
            logger.debug("Empty template key detected")
            return ""

        if normalized != key:
            logger.debug(f"Template key normalized: '{key}' → '{normalized}'")

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
            logger.error(f"Unexpected error loading template file: {filepath} - {e}")
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

    def _load_or_create(self) -> Dict[str, Any]:
        """
        Load the template file if it exists.
        If missing, create it from the base language template.
        """
        if os.path.exists(self.lang_file):
            templates = self._load_json_safe(self.lang_file)
            if templates:
                logger.debug(f"Loaded {len(templates)} templates from file: {self.lang_file}")
                return templates
            logger.warning(f"Template file corrupted, loading base: {self.lang_file}")

        base_templates = {}
        if os.path.exists(self.base_file):
            base_templates = self._load_json_safe(self.base_file)
            if base_templates:
                logger.info(f"Loading from base templates: {self.base_file} ({len(base_templates)} templates)")
            else:
                logger.warning(f"Base template file corrupted or empty: {self.base_file}")

        try:
            self._save_templates(base_templates, self.lang_file)
            logger.info(f"Created new template file from base: {self.lang_file}")
        except Exception as e:
            logger.error(f"Template file save failed: {e}")

        return base_templates

    def _save_templates(self, templates: Dict[str, Any], filepath: str = None):
        """Safely save templates to a JSON file"""
        if filepath is None:
            filepath = self.lang_file

        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(templates, f, indent=4, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Template save failed: {filepath} - {e}")

    def _save(self):
        """Save current templates (backwards compatibility)"""
        self._save_templates(self.templates)

    def set_language(self, lang_code: str):
        """Switch active language and load new templates"""
        validated_lang = self._validate_lang_code(lang_code)
        if validated_lang != self.lang_code:
            self.lang_code = validated_lang
            self.lang_file = os.path.join(self.folder, f"{self.lang_code}.json")
            self.templates = self._load_or_create()
            logger.info(f"Template language switched to: {validated_lang}")

    def ensure_key(self, key, default_value=""):
        """
        Ensure a template key exists.
        If missing, add it automatically.
        Consistent None vs '' policy.
        """
        validated_key = self._validate_key(key)
        if not validated_key:
            return default_value if default_value else ""

        normalized_default = default_value if default_value is not None else ""

        if validated_key not in self.templates:
            self.templates[validated_key] = normalized_default
            self._save()
            logger.debug(f"Added missing template key: '{validated_key}'")

        text = self.templates.get(validated_key, normalized_default)
        return text if text is not None else ""

    def get(self, key, default_value=""):
        """Retrieve a template key with self-healing behavior."""
        return self.ensure_key(key, default_value)

    def get_template(self, key: str, lang_code: str = None) -> Optional[str]:
        """
        Return template or None if key doesn't exist.
        Checks own language first, then base language.
        """
        validated_key = self._validate_key(key)
        if not validated_key:
            return None

        if lang_code and lang_code != self.lang_code:
            return self._get_template_from_lang(validated_key, lang_code)

        text = self.templates.get(validated_key)

        if text is None and self.lang_code != self.base_lang:
            logger.debug(f"Template key '{validated_key}' missing, fallback to base language")
            text = self._get_template_from_lang(validated_key, self.base_lang)

        return text

    def _get_template_from_lang(self, key: str, lang_code: str) -> Optional[str]:
        """Get template from a specific language file"""
        try:
            lang_file = os.path.join(self.folder, f"{lang_code}.json")
            if os.path.exists(lang_file):
                with open(lang_file, "r", encoding="utf-8") as f:
                    templates = json.load(f)
                    return templates.get(key)
        except Exception as e:
            logger.error(f"Error fetching template from language {lang_code}: {e}")
        return None

    def set_template(self, key: str, value: str):
        """Set template and save (consistent None vs '' handling)"""
        validated_key = self._validate_key(key)
        if not validated_key:
            logger.warning("Attempted to set template for empty key")
            return ""

        normalized_value = value if value is not None else ""

        self.templates[validated_key] = normalized_value
        self._save()
        logger.debug(f"Template set: '{validated_key}' = '{normalized_value}'")
        return normalized_value

    def format_template(self, key: str, **kwargs) -> str:
        """
        Retrieve template and fill in variables.
        Self-healing: returns key name if template not found.
        """
        validated_key = self._validate_key(key)
        if not validated_key:
            return ""

        template = self.get_template(validated_key)

        if template is None:
            logger.warning(f"Template '{validated_key}' not found for formatting")
            return validated_key

        try:
            return template.format(**kwargs)
        except (KeyError, ValueError) as e:
            logger.error(f"Template '{validated_key}' formatting error: {e}")
            return template

    def has_key(self, key: str) -> bool:
        """Check if template key exists (normalized)"""
        validated_key = self._validate_key(key)
        if not validated_key:
            return False
        return validated_key in self.templates

    def keys(self):
        """Return all template keys"""
        return list(self.templates.keys())

    def values(self):
        """Return all template values (None → '' normalized)"""
        return [v if v is not None else "" for v in self.templates.values()]

    def items(self):
        """Return all key-value pairs (None → '' normalized)"""
        return [(k, v if v is not None else "") for k, v in self.templates.items()]

    def __contains__(self, key):
        return self.has_key(key)

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        self.set_template(key, value)

    def __len__(self):
        return len(self.templates)

    def __repr__(self):
        return f"TemplateLocalizer(lang='{self.lang_code}', templates={len(self.templates)})"
