"""
File: template_localizer.py
Author: Tuomas Lähteenmäki
Version: 0.1
License: MIT
Description:
    Self-Healing Localizer for AI prompt templates.
    - Creates missing template language files automatically
    - Copies base language templates as fallback
    - Adds missing keys on the fly
    - Ensures template consistency across languages
"""

import json
import os


class TemplateLocalizer:
    """
    Self-Healing Localizer for AI prompt templates.
    - Creates missing template language files automatically
    - Copies base language templates as fallback
    - Adds missing keys on the fly
    """

    def __init__(self, lang_code, base_lang="en", folder="prompts"):
        self.folder = folder
        self.lang_code = lang_code
        self.base_lang = base_lang

        # Ensure folder exists
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)

        # File paths
        self.lang_file = os.path.join(self.folder, f"{self.lang_code}.json")
        self.base_file = os.path.join(self.folder, f"{self.base_lang}.json")

        # Load or create template file
        self.templates = self._load_or_create()

    def _load_or_create(self):
        """
        Loads the template file if it exists.
        If missing, creates it from the base language template.
        """
        # If file exists → load it
        if os.path.exists(self.lang_file):
            try:
                with open(self.lang_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {}

        # If missing → create from base language
        if os.path.exists(self.base_file):
            with open(self.base_file, "r", encoding="utf-8") as f:
                base = json.load(f)
        else:
            base = {}

        # Save new file
        with open(self.lang_file, "w", encoding="utf-8") as f:
            json.dump(base, f, indent=4, ensure_ascii=False)

        return base

    def _save(self):
        """Writes the current template dictionary to disk."""
        with open(self.lang_file, "w", encoding="utf-8") as f:
            json.dump(self.templates, f, indent=4, ensure_ascii=False)

    def ensure_key(self, key, default_value=""):
        """
        Ensures a template key exists.
        If missing, adds it automatically.
        """
        if key not in self.templates:
            self.templates[key] = default_value
            self._save()

        return self.templates[key]

    def get(self, key, default_value=""):
        """
        Retrieves a template key with self-healing behavior.
        """
        return self.ensure_key(key, default_value)

    def __contains__(self, key):
        return key in self.templates

    def __getitem__(self, key):
        return self.get(key)
