"""
File: engine.py
Author: Tuomas Lähteenmäki
Version: 0.1
License: MIT
Description:
    Central engine that unifies the Self-Healing Localization Layer.
    - Manages UI localization (Localizer)
    - Manages AI prompt template localization (TemplateLocalizer)
    - Ensures languages exist across both systems
    - Provides a clean API for higher-level applications
"""

import os
from .localizer import Localizer
from .template_localizer import TemplateLocalizer


class LocalizationEngine:
    """
    High-level manager for self-healing localization.
    Provides a unified interface for:
    - UI text localization
    - Prompt template localization
    """

    def __init__(
        self,
        lang_code="en",
        base_lang="en",
        ui_folder="locales",
        template_folder="prompts"
    ):
        self.lang_code = lang_code
        self.base_lang = base_lang
        self.ui_folder = ui_folder
        self.template_folder = template_folder

        # Initialize components
        self.ui = Localizer(lang_code, base_lang, ui_folder)
        self.templates = TemplateLocalizer(lang_code, base_lang, template_folder)

    # ---------------------------------------------------------
    # Language Management
    # ---------------------------------------------------------

    def ensure_language(self, lang_code):
        """
        Ensures that both UI and template localization files exist
        for the given language.
        """
        # UI localization
        Localizer(lang_code, self.base_lang, self.ui_folder)

        # Template localization
        TemplateLocalizer(lang_code, self.base_lang, self.template_folder)

    # ---------------------------------------------------------
    # Key Management
    # ---------------------------------------------------------

    def ensure_ui_key(self, key, default=""):
        """Ensures a UI localization key exists."""
        return self.ui.L(key, default)

    def ensure_template_key(self, key, default=""):
        """Ensures a template localization key exists."""
        return self.templates.ensure_key(key, default)

    # ---------------------------------------------------------
    # Retrieval
    # ---------------------------------------------------------

    def ui_text(self, key, default=""):
        """Retrieve UI text with self-healing behavior."""
        return self.ui.L(key, default)

    def template(self, key, default=""):
        """Retrieve template text with self-healing behavior."""
        return self.templates.get(key, default)

    # ---------------------------------------------------------
    # Synchronization
    # ---------------------------------------------------------

    def sync(self):
        """
        Ensures that all languages have the same keys as the base language.
        Useful when adding new UI or template keys.
        """
        # Sync UI
        base_ui = Localizer(self.base_lang, self.base_lang, self.ui_folder)
        for key, value in base_ui.texts.items():
            self.ensure_ui_key(key, value)

        # Sync templates
        base_templates = TemplateLocalizer(self.base_lang, self.base_lang, self.template_folder)
        for key, value in base_templates.templates.items():
            self.ensure_template_key(key, value)
