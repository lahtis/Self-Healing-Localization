"""
File: core.py
Author: Tuomas Lähteenmäki
Version: 0.1.5
License: MIT
Description:
    Central engine that unifies the Self-Healing Localization Layer.
    - Manages UI localization (Localizer)
    - Manages AI prompt template localization (TemplateLocalizer)
    - Ensures languages exist across both systems
    - Provides a clean API for higher-level applications
"""

import os
from shl.engine.localizer import Localizer
from shl.engine.template_localizer import TemplateLocalizer
from shl.engine.ai_translation import translate_text

class LocalizationEngine:
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

        # Nämä nimet pitää täsmätä myöhempiin metodeihin
        self.ui_localizer = Localizer(lang_code=lang_code, base_lang=base_lang, folder=ui_folder)
        self.template_localizer = TemplateLocalizer(lang_code=lang_code, base_lang=base_lang, folder=template_folder)

    # --- Language Management ---

    def ensure_language(self, lang_code):
        """Varmistaa, että kielitiedostot ovat olemassa."""
        Localizer(lang_code=lang_code, base_lang=self.base_lang, folder=self.ui_folder)
        TemplateLocalizer(lang_code=lang_code, base_lang=self.base_lang, folder=self.template_folder)

    # --- Key Management (Korjattu nimet vastaamaan __init__-metodia) ---

    def ensure_ui_key(self, key, default=""):
        """Varmistaa, että UI-avain on olemassa."""
        text = self.ui_localizer.get_text(key)
        if text is None:
            self.ui_localizer.set_text(key, default)
            return default
        return text

    def ensure_template_key(self, key, default=""):
        """Varmistaa, että prompt-avain on olemassa."""
        text = self.template_localizer.get_template(key)
        if text is None:
            self.template_localizer.set_template(key, default)
            return default
        return text

    # --- Retrieval & Self-Healing ---

    def ui_text(self, key, default_value=""):
        # Kutsuu nyt localizer.py:n uutta get_text-metodia
        text = self.ui_localizer.get_text(key)
        
        if text is None:
            if self.lang_code != self.base_lang:
                translated = translate_text(default_value, self.lang_code, self.base_lang)
                self.ui_localizer.set_text(key, translated)
                return translated
            else:
                self.ui_localizer.set_text(key, default_value)
                return default_value
        return text

    def template(self, key, default=""):
        """Hakee prompt-pohjan."""
        return self.template_localizer.get_template(key)

    # --- Synchronization ---

    def sync(self):
        """Synkronoi kaikki avaimet peruskielestä nykyiseen kieleen."""
        # UI synkronointi
        base_ui = Localizer(lang_code=self.base_lang, base_lang=self.base_lang, folder=self.ui_folder)
        for key, value in base_ui.texts.items():
            self.ensure_ui_key(key, value)

        # Template synkronointi
        base_templates = TemplateLocalizer(lang_code=self.base_lang, base_lang=self.base_lang, folder=self.template_folder)
        for key, value in base_templates.templates.items():
            self.ensure_template_key(key, value)
            
            
            
            
            
            
            
            
            
            
