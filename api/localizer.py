"""
File: localizer.py
Author: Tuomas Lähteenmäki
Version: 0.1
License: MIT
Description:
    Self-Healing Localizer for UI text.
    - Creates missing language files automatically
    - Adds missing keys on the fly
    - Falls back to default language (English)
"""

import json
import os
import configparser


class Localizer:
    """
    Self-Healing Localizer for UI text.
    - Creates missing language files automatically
    - Adds missing keys on the fly
    - Falls back to default language (English)
    """

    def __init__(self, lang_code=None, base_lang="en", folder="locales"):
        self.folder = folder
        self.base_lang = base_lang

        # Determine language
        if lang_code is None:
            config = configparser.ConfigParser()
            if os.path.exists("config.conf"):
                config.read("config.conf")
                lang_code = config.get("SETTINGS", "language", fallback=base_lang)
            else:
                lang_code = base_lang

        self.lang_code = lang_code

        # Ensure folder exists
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)

        # File paths
        self.lang_file = os.path.join(self.folder, f"lang_{self.lang_code}.json")
        self.base_file = os.path.join(self.folder, f"lang_{self.base_lang}.json")

        # Load or create language file
        self.texts = self._load_or_create()

    def _load_or_create(self):
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

        with open(self.lang_file, "w", encoding="utf-8") as f:
            json.dump(base, f, indent=4, ensure_ascii=False)

        return base

    def _save(self):
        with open(self.lang_file, "w", encoding="utf-8") as f:
            json.dump(self.texts, f, indent=4, ensure_ascii=False)

    def L(self, key, default=""):
        """
        Self-healing key lookup.
        If key is missing, add it automatically.
        """
        if key not in self.texts:
            self.texts[key] = default
            self._save()

        return self.texts.get(key, default)

    def get(self, key, default=""):
        return self.L(key, default)

    def __contains__(self, key):
        return key in self.texts

    def __getitem__(self, key):
        return self.L(key)

