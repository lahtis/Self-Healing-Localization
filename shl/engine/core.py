"""
File: core.py
Author: Tuomas Lähteenmäki
Version: 0.2.0
License: MIT
Description:
    Central engine that unifies the Self-Healing Localization Layer.
    - Manages UI localization (Localizer)
    - Manages AI prompt template localization (TemplateLocalizer)
    - Ensures languages exist across both systems
    - Optional GLFM language validation with fallback chains
    - Smart translation routing with automatic fallback
    - AI translation only when enabled (ai_translation_enabled=False by default)
    - Provides a clean API for higher-level applications
"""

import os
import logging
from typing import Optional, Dict, Any, List, Callable

from shl.engine.localizer import Localizer
from shl.engine.template_localizer import TemplateLocalizer

# Uusi translation-moduuli (korvaa vanhan ai_translation)
from shl.engine.translation import (
    translate_text,
    TranslationCache,
    MyMemoryAdapter,
    LibreTranslateAdapter,
    # Poikkeukset
    TranslationError,
    ServiceUnavailableError,
    RateLimitExceededError,
    LanguageNotSupportedError,
    ProviderAccessError,
    InvalidRequestError,
)

from shl.language_validator import LanguageValidator
from shl.utils.lang_utils import normalize_full_tag, base_language

logger = logging.getLogger(__name__)


class LocalizationEngine:
    def __init__(
        self,
        lang_code: Optional[str] = None,
        base_lang: Optional[str] = None,  # ← None oletus!
        ui_folder: str = "locales",
        template_folder: str = "prompts",
        config: Optional[Dict[str, Any]] = None,
        glfm_path: Optional[str] = None,
        glfm_lite: bool = True,
        # Translation provider configuration
        libretranslate_url: Optional[str] = None,
        libretranslate_api_key: Optional[str] = None,
        mymemory_email: Optional[str] = None,
        libretranslate_mirrors: Optional[List[Dict[str, Any]]] = None,
    ):
        # Configuration handling - merge defaults with provided config
        default_config = self._load_default_config()
        if config:
            default_config.update(config)
        self.config = default_config

        # Determine base_lang: explicit parameter > config.conf > "en"
        if base_lang is None:
            base_lang = self.config.get("base_lang", "en")

        # If lang_code is None, use config or auto-detection
        if lang_code is None:
            lang_code = self._detect_language()

        # Validate and normalize using lang_utils
        self.lang_code = normalize_full_tag(lang_code)
        self.base_lang = base_language(base_lang)
        self.ui_folder = ui_folder
        self.template_folder = template_folder

        # Initialize GLFM validator with Lite mode
        self.validator = LanguageValidator(
            glfm_path=glfm_path,
            base_language=self.base_lang,
            use_lite=glfm_lite,
        )

        # Get GLFM fallback chain
        self.glfm_fallback = None
        self.glfm_fallback_chain: List[str] = []

        if self.validator.is_loaded:
            # Validate language code against GLFM
            if not self.validator.is_valid(self.lang_code):
                logger.warning(
                    f"Language '{self.lang_code}' not found in GLFM, "
                    f"using fallback chain"
                )
            else:
                # Get full fallback chain
                self.glfm_fallback_chain = self.validator.get_fallback_chain(
                    self.lang_code,
                    base_language=self.base_lang,
                    max_nearest=3,
                )
                # First fallback is the primary GLFM fallback
                if len(self.glfm_fallback_chain) > 1:
                    self.glfm_fallback = self.glfm_fallback_chain[1]
                    logger.debug(
                        f"GLFM fallback chain for '{self.lang_code}': "
                        f"{self.glfm_fallback_chain}"
                    )
                else:
                    logger.debug(
                        f"GLFM loaded but no fallback chain for '{self.lang_code}'"
                    )

        # Initialize translation cache
        self.cache = TranslationCache()

        # Initialize translation providers
        self.mymemory_adapter = MyMemoryAdapter(
            email=mymemory_email or os.environ.get("MYMEMORY_EMAIL")
        )

        self.libretranslate_adapter = LibreTranslateAdapter(
            base_url=libretranslate_url or os.environ.get("LIBRETRANSLATE_URL"),
            api_key=libretranslate_api_key or os.environ.get("LIBRETRANSLATE_API_KEY"),
            mirrors=libretranslate_mirrors,
        )

        # Store provider configuration for fallback
        self._libretranslate_url = libretranslate_url or os.environ.get("LIBRETRANSLATE_URL")
        self._libretranslate_api_key = libretranslate_api_key or os.environ.get("LIBRETRANSLATE_API_KEY")
        self._mymemory_email = mymemory_email or os.environ.get("MYMEMORY_EMAIL")
        self._libretranslate_mirrors = libretranslate_mirrors

        # Initialize localizers
        self.ui_localizer = Localizer(
            lang_code=self.lang_code,
            base_lang=self.base_lang,
            folder=ui_folder,
        )
        self.template_localizer = TemplateLocalizer(
            lang_code=self.lang_code,
            base_lang=self.base_lang,
            folder=template_folder,
        )

        logger.info(
            f"LocalizationEngine initialized: lang={self.lang_code}, base={self.base_lang}"
            f"{' (GLFM Lite)' if glfm_lite else ' (GLFM Full)'}"
        )

    # --- Configuration handling ---

    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration, optionally from config.conf"""
        config = {
            "m_translation_enabled": False,
            "translation_cache_ttl": 3600,
            "fallback_to_base": True,
            "strict_mode": False,
            "default_language": None,
            "glfm_lite": True,
        }

        # Try reading config.conf
        try:
            import configparser

            if os.path.exists("config.conf"):
                parser = configparser.ConfigParser()
                parser.read("config.conf", encoding="utf-8")
                if parser.has_section("SETTINGS"):
                    # Language
                    lang = parser.get("SETTINGS", "language", fallback=None)
                    if lang:
                        config["default_language"] = lang.strip()

                    # AI translation
                    if parser.has_option("SETTINGS", "ai_translation_enabled"):
                        config["ai_translation_enabled"] = parser.getboolean(
                            "SETTINGS", "ai_translation_enabled", fallback=False
                        )

                    # Fallback to base
                    if parser.has_option("SETTINGS", "fallback_to_base"):
                        config["fallback_to_base"] = parser.getboolean(
                            "SETTINGS", "fallback_to_base", fallback=True
                        )

                    # GLFM Lite
                    if parser.has_option("SETTINGS", "glfm_lite"):
                        config["glfm_lite"] = parser.getboolean(
                            "SETTINGS", "glfm_lite", fallback=True
                        )

                    # Optional: base_lang from config
                    base = parser.get("SETTINGS", "base_lang", fallback=None)
                    if base:
                        config["base_lang"] = base.strip()

                    logger.debug("Loaded settings from config.conf")
        except Exception as e:
            logger.debug(f"Could not read config.conf: {e}")

        return config

    # --- Language detection ---

    def _detect_language(self) -> str:
        """
        Auto-detect language.
        Priority:
          1. config.conf → [SETTINGS] language
          2. SHL_LANGUAGE environment variable
          3. LANG environment variable
          4. Default: "en"
        """
        # 1. From config.conf
        if self.config.get("default_language"):
            return self.config["default_language"]

        # 2. SHL_LANGUAGE env
        env_lang = os.environ.get("SHL_LANGUAGE")
        if env_lang:
            return env_lang

        # 3. LANG env (e.g. zh_TW.UTF-8 → zh-TW)
        raw_lang = os.environ.get("LANG", "")
        if raw_lang:
            base = raw_lang.split(".")[0]
            if "_" in base:
                parts = base.split("_")
                if len(parts) == 2:
                    return f"{parts[0].lower()}-{parts[1].upper()}"
            return base.lower()

        # 4. Default
        return "en"

    # --- Key Validation ---

    def _validate_key(self, key: str) -> str:
        """Validate and normalize key."""
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

    # --- Language Management ---

    def ensure_language(self, lang_code: str) -> None:
        """Ensure language files exist."""
        validated_lang = normalize_full_tag(lang_code)
        logger.debug(f"Ensuring language: {validated_lang}")
        Localizer(
            lang_code=validated_lang,
            base_lang=self.base_lang,
            folder=self.ui_folder,
        )
        TemplateLocalizer(
            lang_code=validated_lang,
            base_lang=self.base_lang,
            folder=self.template_folder,
        )

    def set_language(self, lang_code: str) -> None:
        """Dynamically switch active language"""
        validated_lang = normalize_full_tag(lang_code)
        self.lang_code = validated_lang
        self.ui_localizer.set_language(validated_lang)
        self.template_localizer.set_language(validated_lang)

        # Update GLFM fallback chain for new language
        if self.validator.is_loaded:
            self.glfm_fallback_chain = self.validator.get_fallback_chain(
                validated_lang,
                base_language=self.base_lang,
                max_nearest=3,
            )
            if len(self.glfm_fallback_chain) > 1:
                self.glfm_fallback = self.glfm_fallback_chain[1]
            else:
                self.glfm_fallback = None

        logger.info(f"Language switched to: {validated_lang}")

    # --- Key Management ---

    def ensure_ui_key(self, key: str, default: str = "") -> str:
        """Ensure UI key exists."""
        validated_key = self._validate_key(key)
        if not validated_key:
            return ""
        text = self._get_with_fallback(
            self.ui_localizer.get_text,
            validated_key,
        )
        if text is None or text == "":
            self.ui_localizer.set_text(validated_key, default)
            return default
        return text

    def ensure_template_key(self, key: str, default: str = "") -> str:
        """Ensure prompt template key exists."""
        validated_key = self._validate_key(key)
        if not validated_key:
            return ""
        text = self._get_with_fallback(
            self.template_localizer.get_template,
            validated_key,
        )
        if text is None or text == "":
            self.template_localizer.set_template(validated_key, default)
            return default
        return text

    # --- DRY: Generic fallback ---

    def _get_with_fallback(
        self,
        getter: Callable[[str, Optional[str], bool], Optional[str]],
        key: str,
    ) -> Optional[str]:
        """
        Generic fallback chain for UI texts and templates.

        Args:
            getter: Function to get text from a specific language
            key: Key to look up

        Returns:
            Text if found, None otherwise
        """
        fallback_enabled = self.config.get("fallback_to_base", True)

        # 1. Own language
        text = getter(key, self.lang_code, fallback=False)
        if text and text.strip():
            return text

        # 2. GLFM fallback chain
        if self.glfm_fallback_chain and len(self.glfm_fallback_chain) > 1:
            for fallback_lang in self.glfm_fallback_chain[1:]:
                if fallback_lang != self.lang_code:
                    logger.debug(
                        f"Fallback: '{key}' → GLFM fallback ({fallback_lang})"
                    )
                    text = getter(key, fallback_lang, fallback=False)
                    if text and text.strip():
                        return text

        # 3. Base language - only if fallback_to_base is True
        if fallback_enabled and self.lang_code != self.base_lang:
            logger.debug(f"Fallback: '{key}' → base_lang ({self.base_lang})")
            text = getter(key, self.base_lang, fallback=False)
            if text and text.strip():
                return text

        return None

    # --- Retrieval & Self-Healing ---

    def ui_text(self, key: str, default_value: str = "") -> str:
        """
        Retrieve UI text with self-healing and fallback chain.

        If text is missing and ai_translation_enabled=True, attempts AI translation.
        """
        validated_key = self._validate_key(key)
        if not validated_key:
            return default_value

        # Check cache
        cached = self.cache.get(default_value, self.base_lang, self.lang_code)
        if cached:
            return cached

        text = self._get_with_fallback(
            self.ui_localizer.get_text,
            validated_key,
        )

        if text is None:
            # AI translation only if enabled in config
            if (
                self.config.get("m_translation_enabled", False)
                and self.lang_code != self.base_lang
                and default_value
            ):
                try:
                    translated = translate_text(
                        default_value,
                        target_lang=self.lang_code,
                        source_lang=self.base_lang,
                        libretranslate_url=self._libretranslate_url,
                        libretranslate_api_key=self._libretranslate_api_key,
                        mymemory_email=self._mymemory_email,
                    )
                    if translated and translated != default_value:
                        self.ui_localizer.set_text(validated_key, translated)
                        self.cache.set(validated_key, translated, self.base_lang, self.lang_code)
                        return translated
                except Exception as e:
                    logger.warning(f"AI translation failed: {e}")

            self.ui_localizer.set_text(validated_key, default_value)
            self.cache.set(validated_key, default_value, self.base_lang, self.lang_code)
            return default_value

        self.cache.set(validated_key, text, self.base_lang, self.lang_code)
        return text

    def template(self, key: str, default: str = "", **kwargs) -> str:
        """Retrieve prompt template with self-healing and variable substitution"""
        validated_key = self._validate_key(key)
        if not validated_key:
            return default if default else key

        text = self._get_with_fallback(
            self.template_localizer.get_template,
            validated_key,
        )

        if text is None:
            logger.info(f"Template '{validated_key}' missing, using default")
            self.template_localizer.set_template(
                validated_key, default if default else key
            )
            text = default if default else key

        try:
            if kwargs:
                return text.format(**kwargs)
            return text
        except (KeyError, ValueError) as e:
            logger.warning(f"Template '{validated_key}' format error: {e}")
            return text

    # --- Synchronization ---

    def _sync_from_lang(self, source_lang: str) -> int:
        """
        Synchronize keys from source language to current language.

        Args:
            source_lang: Source language code to sync from

        Returns:
            Number of keys synchronized
        """
        if source_lang == self.lang_code:
            return 0

        logger.debug(f"Syncing from '{source_lang}' to '{self.lang_code}'")

        # Load source UI texts
        source_ui = Localizer(
            lang_code=source_lang,
            base_lang=self.base_lang,
            folder=self.ui_folder,
        )

        # Sync UI keys
        synced_count = 0
        for key, value in source_ui.texts.items():
            validated_key = self._validate_key(key)
            if validated_key and validated_key not in self.ui_localizer.texts:
                self.ui_text(validated_key, value)
                synced_count += 1

        # Load source templates
        source_templates = TemplateLocalizer(
            lang_code=source_lang,
            base_lang=self.base_lang,
            folder=self.template_folder,
        )

        # Sync template keys
        template_synced = 0
        for key, value in source_templates.templates.items():
            validated_key = self._validate_key(key)
            if (
                validated_key
                and validated_key not in self.template_localizer.templates
            ):
                self.template(validated_key, default=value)
                template_synced += 1

        total_synced = synced_count + template_synced
        if total_synced > 0:
            logger.debug(
                f"Synced {synced_count} UI keys and {template_synced} "
                f"templates from '{source_lang}'"
            )

        return total_synced

    def sync(self) -> int:
        """
        Synchronize all keys from fallback chain to current language.

        Fallback chain order:
        1. GLFM fallback chain (all)
        2. Base language

        Returns:
            Total number of keys synchronized
        """
        logger.info(f"Synchronizing to '{self.lang_code}'")

        total_synced = 0

        # 1. Sync from GLFM fallback chain (if available)
        if self.glfm_fallback_chain and len(self.glfm_fallback_chain) > 1:
            for fallback_lang in self.glfm_fallback_chain[1:]:
                if fallback_lang != self.lang_code:
                    logger.info(f"Syncing from GLFM fallback: '{fallback_lang}'")
                    total_synced += self._sync_from_lang(fallback_lang)

        # 2. Sync from base language (always)
        if self.base_lang != self.lang_code:
            logger.info(f"Syncing from base language: '{self.base_lang}'")
            total_synced += self._sync_from_lang(self.base_lang)

        if total_synced == 0:
            logger.info("No new keys to synchronize")
        else:
            logger.info(f"Synchronization complete: {total_synced} keys synced")

        return total_synced

    # --- Statistics and diagnostics ---

    def get_stats(self) -> Dict[str, Any]:
        """Return engine statistics (copy to prevent mutation)."""
        return {
            "lang_code": self.lang_code,
            "base_lang": self.base_lang,
            "glfm_fallback": self.glfm_fallback,
            "glfm_fallback_chain": self.glfm_fallback_chain.copy(),
            "glfm_lite": self.validator.is_lite if self.validator else True,
            "glfm_loaded": self.validator.is_loaded if self.validator else False,
            "ui_keys_count": len(self.ui_localizer.texts),
            "template_keys_count": len(self.template_localizer.templates),
            "cache_size": self.cache.size(),
            "ai_translation_enabled": self.config.get(
                "ai_translation_enabled", False
            ),
            "config": self.config.copy(),
        }

    # --- Mirror statistics ---

    def get_mirror_stats(self) -> List[Dict[str, Any]]:
        """Get LibreTranslate mirror statistics."""
        return self.libretranslate_adapter.get_mirror_stats()

    def clear_mirror_cache(self) -> None:
        """Clear LibreTranslate mirror cache."""
        self.libretranslate_adapter.clear_mirror_cache()

    # --- GLFM management ---

    def reload_glfm(
        self,
        glfm_path: Optional[str] = None,
        glfm_lite: Optional[bool] = None
    ) -> bool:
        """
        Reload GLFM database with new settings.

        Args:
            glfm_path: Custom path to GLFM database
            glfm_lite: Use GLFM Lite (True) or Full (False)

        Returns:
            True if reloaded successfully
        """
        if glfm_lite is None:
            glfm_lite = self.config.get("glfm_lite", True)

        self.validator = LanguageValidator(
            glfm_path=glfm_path,
            base_language=self.base_lang,
            use_lite=glfm_lite,
        )

        if self.validator.is_loaded:
            self.glfm_fallback_chain = self.validator.get_fallback_chain(
                self.lang_code,
                base_language=self.base_lang,
                max_nearest=3,
            )
            if len(self.glfm_fallback_chain) > 1:
                self.glfm_fallback = self.glfm_fallback_chain[1]
            else:
                self.glfm_fallback = None
            logger.info(f"GLFM reloaded: {len(self.validator.languages)} languages")
            return True
        else:
            self.glfm_fallback = None
            self.glfm_fallback_chain = []
            logger.warning("GLFM reload failed")
            return False
