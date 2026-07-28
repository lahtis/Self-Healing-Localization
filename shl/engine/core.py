"""
File: core.py
Author: Tuomas Lähteenmäki
Version: 0.1.7
License: MIT
Description:
    Central engine that unifies the Self-Healing Localization Layer.
    - Manages UI localization (Localizer)
    - Manages AI prompt template localization (TemplateLocalizer)
    - Ensures languages exist across both systems
    - Optional GLFM language validation
    - Provides a clean API for higher-level applications
"""

import os
import logging
from shl.engine.localizer import Localizer
from shl.engine.template_localizer import TemplateLocalizer
from shl.engine.ai_translation import translate_text, TranslationCache
from shl.language_validator import LanguageValidator

logger = logging.getLogger(__name__)


class LocalizationEngine:
    def __init__(
        self,
        lang_code=None,
        base_lang="en",
        ui_folder="locales",
        template_folder="prompts",
        config=None,
        glfm_path=None
    ):
        # Configuration handling
        self.config = config or self._load_default_config()

        # If lang_code is None, use config or auto-detection
        if lang_code is None:
            lang_code = self._detect_language()

        # Validate and normalize lang_code
        self.lang_code = self._validate_lang_code(lang_code)
        self.base_lang = self._validate_lang_code(base_lang)
        self.ui_folder = ui_folder
        self.template_folder = template_folder

        # Initialize GLFM validator if available
        self.validator = LanguageValidator(glfm_path)

        # Validate language code against GLFM
        if self.validator.is_loaded and not self.validator.is_valid(self.lang_code):
            logger.warning(
                f"Language '{self.lang_code}' not found in GLFM, "
                f"falling back to base language '{self.base_lang}'"
            )
            self.lang_code = self.base_lang

        # Get fallback chain from GLFM
        if self.validator.is_loaded:
            glfm_fallback = self.validator.get_fallback(self.lang_code)
            if glfm_fallback and glfm_fallback != self.lang_code:
                logger.debug(f"GLFM fallback for '{self.lang_code}': '{glfm_fallback}'")

        # Initialize cache
        self.cache = TranslationCache()

        # Initialize localizers
        self.ui_localizer = Localizer(
            lang_code=self.lang_code,
            base_lang=self.base_lang,
            folder=ui_folder
        )
        self.template_localizer = TemplateLocalizer(
            lang_code=self.lang_code,
            base_lang=self.base_lang,
            folder=template_folder
        )

        logger.info(f"LocalizationEngine initialized: lang={self.lang_code}, base={self.base_lang}")

    # --- Configuration handling ---

    def _load_default_config(self) -> dict:
        """Load default configuration"""
        return {
            "ai_translation_enabled": False,
            "translation_cache_ttl": 3600,
            "fallback_to_base": True,
            "strict_mode": False
        }

    def _detect_language(self) -> str:
        """Auto-detect language (config, environment, default)"""
        # Try config
        if self.config and "default_language" in self.config:
            return self.config["default_language"]

        # Try SHL_LANGUAGE env var
        env_lang = os.environ.get("SHL_LANGUAGE")
        if env_lang:
            return env_lang

        # Try LANG env var (e.g., zh_TW.UTF-8 → zh-TW)
        raw_lang = os.environ.get("LANG", "")
        if raw_lang:
            base = raw_lang.split(".")[0]
            if "_" in base:
                parts = base.split("_")
                if len(parts) == 2:
                    return f"{parts[0].lower()}-{parts[1].upper()}"
            return base.lower()

        return "en"

    def _validate_lang_code(self, lang_code: str) -> str:
        """Validate and normalize language code"""
        if not isinstance(lang_code, str) or not lang_code.strip():
            logger.warning(f"Invalid language code: {lang_code}, using 'en'")
            return "en"
        return lang_code.strip().lower()

    # --- Language Management ---

    def ensure_language(self, lang_code):
        """Ensure language files exist."""
        validated_lang = self._validate_lang_code(lang_code)
        logger.debug(f"Ensuring language: {validated_lang}")

        Localizer(lang_code=validated_lang, base_lang=self.base_lang, folder=self.ui_folder)
        TemplateLocalizer(lang_code=validated_lang, base_lang=self.base_lang, folder=self.template_folder)

    def set_language(self, lang_code: str):
        """Dynamically switch active language"""
        validated_lang = self._validate_lang_code(lang_code)
        self.lang_code = validated_lang

        self.ui_localizer.set_language(validated_lang)
        self.template_localizer.set_language(validated_lang)

        logger.info(f"Language switched to: {validated_lang}")

    # --- Key Validation ---

    def _validate_key(self, key: str) -> str:
        """Validate and normalize key - consistent None vs '' handling"""
        if not isinstance(key, str):
            logger.warning(f"Invalid key type: {type(key)}, returning ''")
            return ""

        normalized = key.strip()

        if not normalized:
            logger.debug("Empty key detected")
            return ""

        if normalized != key:
            logger.debug(f"Key normalized: '{key}' → '{normalized}'")

        return normalized

    # --- Key Management ---

    def ensure_ui_key(self, key, default=""):
        """Ensure UI key exists."""
        validated_key = self._validate_key(key)
        if not validated_key:
            return ""

        text = self._get_text_with_fallback(validated_key)
        if text is None or text == "":
            self.ui_localizer.set_text(validated_key, default)
            return default
        return text

    def ensure_template_key(self, key, default=""):
        """Ensure prompt template key exists."""
        validated_key = self._validate_key(key)
        if not validated_key:
            return ""

        text = self.template_localizer.get_template(validated_key)
        if text is None or text == "":
            self.template_localizer.set_template(validated_key, default)
            return default
        return text

    # --- Retrieval & Self-Healing ---

    def ui_text(self, key, default_value=""):
        """Retrieve UI text with self-healing and base fallback"""
        validated_key = self._validate_key(key)
        if not validated_key:
            return default_value

        cached = self.cache.get(validated_key, "ui", self.lang_code)
        if cached:
            return cached

        text = self._get_text_with_fallback(validated_key)

        if text is None:
            if self.lang_code != self.base_lang and default_value:
                translated = translate_text(default_value, self.lang_code, self.base_lang)
                if translated:
                    self.ui_localizer.set_text(validated_key, translated)
                    self.cache.set(validated_key, translated, "ui", self.lang_code)
                    return translated

            self.ui_localizer.set_text(validated_key, default_value)
            self.cache.set(validated_key, default_value, "ui", self.lang_code)
            return default_value

        self.cache.set(validated_key, text, "ui", self.lang_code)
        return text

    def template(self, key, default="", **kwargs):
        """Retrieve prompt template with self-healing and variable substitution"""
        validated_key = self._validate_key(key)
        if not validated_key:
            return default if default else key

        text = self._get_template_with_fallback(validated_key)

        if text is None:
            logger.info(f"Template '{validated_key}' missing, using default")
            self.template_localizer.set_template(validated_key, default if default else key)
            text = default if default else key

        try:
            if kwargs:
                return text.format(**kwargs)
            return text
        except (KeyError, ValueError) as e:
            logger.warning(f"Template '{validated_key}' format error: {e}")
            return text

    # --- Fallback mechanisms ---

    def _get_text_with_fallback(self, key: str) -> str:
        """Get UI text with fallback chain: lang_code → base_lang → None"""
        text = self.ui_localizer.get_text(key, self.lang_code)
        if text and text.strip():
            return text

        if self.lang_code != self.base_lang and self.config.get("fallback_to_base", True):
            logger.debug(f"UI fallback: '{key}' → base_lang ({self.base_lang})")
            text = self.ui_localizer.get_text(key, self.base_lang)
            if text and text.strip():
                return text

        return None

    def _get_template_with_fallback(self, key: str) -> str:
        """Get template with fallback chain: lang_code → base_lang → None"""
        text = self.template_localizer.get_template(key, self.lang_code)
        if text and text.strip():
            return text

        if self.lang_code != self.base_lang and self.config.get("fallback_to_base", True):
            logger.debug(f"Template fallback: '{key}' → base_lang ({self.base_lang})")
            text = self.template_localizer.get_template(key, self.base_lang)
            if text and text.strip():
                return text

        return None

    # --- Synchronization ---

    def sync(self):
        """Synchronize all keys from base language to current language using ui_text()"""
        logger.info(f"Synchronizing from '{self.base_lang}' to '{self.lang_code}'")

        base_ui = Localizer(
            lang_code=self.base_lang,
            base_lang=self.base_lang,
            folder=self.ui_folder
        )

        synced_count = 0
        for key, value in base_ui.texts.items():
            validated_key = self._validate_key(key)
            if validated_key and validated_key not in self.ui_localizer.texts:
                self.ui_text(validated_key, value)
                synced_count += 1

        base_templates = TemplateLocalizer(
            lang_code=self.base_lang,
            base_lang=self.base_lang,
            folder=self.template_folder
        )

        template_synced = 0
        for key, value in base_templates.templates.items():
            validated_key = self._validate_key(key)
            if validated_key and validated_key not in self.template_localizer.templates:
                self.template(validated_key, default=value)
                template_synced += 1

        logger.info(f"Synchronization complete: {synced_count} UI keys, {template_synced} templates")
        return synced_count + template_synced

    # --- Statistics and diagnostics ---

    def get_stats(self) -> dict:
        """Return engine statistics"""
        return {
            "lang_code": self.lang_code,
            "base_lang": self.base_lang,
            "ui_keys_count": len(self.ui_localizer.texts),
            "template_keys_count": len(self.template_localizer.templates),
            "cache_size": len(self.cache.cache) if hasattr(self.cache, 'cache') else 0,
            "glfm_loaded": self.validator.is_loaded if self.validator else False,
            "config": self.config
        }
