"""
File: core.py
Author: Tuomas Lähteenmäki
Version: 0.2.2
License: MIT
Description:
    Central engine that unifies the Self-Healing Localization Layer.

    - Manages UI localization through Localizer
    - Manages AI prompt templates through TemplateLocalizer
    - Ensures languages exist across both systems
    - Optional GLFM language validation with fallback chains
    - Smart translation routing with automatic fallback
    - Machine translation only when enabled
    - Provides a clean API for higher-level applications
"""

import logging
import os
from typing import Any, Callable, Dict, List, Optional

from shl.engine.localizer import Localizer
from shl.engine.template_localizer import TemplateLocalizer

from shl.engine.translation import (
    translate_text,
    TranslationCache,
    MyMemoryAdapter,
    LibreTranslateAdapter,
    TranslationError,
    ServiceUnavailableError,
    RateLimitExceededError,
    LanguageNotSupportedError,
    ProviderAccessError,
    InvalidRequestError,
)

from shl.language_validator import LanguageValidator
from shl.utils.lang_utils import (
    base_language,
    normalize_full_tag,
)


logger = logging.getLogger(__name__)


class LocalizationEngine:
    """Central localization engine for UI text and templates."""

    def __init__(
        self,
        lang_code: Optional[str] = None,
        base_lang: Optional[str] = None,
        ui_folder: str = "locales",
        template_folder: str = "prompts",
        config: Optional[Dict[str, Any]] = None,
        glfm_path: Optional[str] = None,
        glfm_lite: bool = True,
        libretranslate_url: Optional[str] = None,
        libretranslate_api_key: Optional[str] = None,
        mymemory_email: Optional[str] = None,
        libretranslate_mirrors: Optional[
            List[Dict[str, Any]]
        ] = None,
    ):
        default_config = self._load_default_config()

        if config:
            default_config.update(config)

        self.config = default_config

        if base_lang is None:
            base_lang = self.config.get(
                "base_lang",
                "en",
            )

        if lang_code is None:
            lang_code = self._detect_language()

        self.lang_code = normalize_full_tag(lang_code)
        self.base_lang = base_language(base_lang)

        self.ui_folder = ui_folder
        self.template_folder = template_folder

        self.validator = LanguageValidator(
            glfm_path=glfm_path,
            base_language=self.base_lang,
            use_lite=glfm_lite,
        )

        self.glfm_fallback: Optional[str] = None
        self.glfm_fallback_chain: List[str] = []

        if self.validator.is_loaded:
            if not self.validator.is_valid(self.lang_code):
                logger.warning(
                    "Language '%s' not found in GLFM",
                    self.lang_code,
                )

            else:
                self.glfm_fallback_chain = (
                    self.validator.get_fallback_chain(
                        self.lang_code,
                        base_language=self.base_lang,
                        max_nearest=None,
                    )
                )

                if len(self.glfm_fallback_chain) > 1:
                    self.glfm_fallback = (
                        self.glfm_fallback_chain[1]
                    )

                logger.debug(
                    "GLFM fallback chain for '%s': %s",
                    self.lang_code,
                    self.glfm_fallback_chain,
                )

        self.cache = TranslationCache()

        resolved_mymemory_email = (
            mymemory_email
            or os.environ.get("MYMEMORY_EMAIL")
        )

        resolved_libretranslate_url = (
            libretranslate_url
            or os.environ.get("LIBRETRANSLATE_URL")
        )

        resolved_libretranslate_api_key = (
            libretranslate_api_key
            or os.environ.get("LIBRETRANSLATE_API_KEY")
        )

        self.mymemory_adapter = MyMemoryAdapter(
            email=resolved_mymemory_email,
        )

        self.libretranslate_adapter = (
            LibreTranslateAdapter(
                base_url=resolved_libretranslate_url,
                api_key=resolved_libretranslate_api_key,
                mirrors=libretranslate_mirrors,
            )
        )

        self._libretranslate_url = (
            resolved_libretranslate_url
        )
        self._libretranslate_api_key = (
            resolved_libretranslate_api_key
        )
        self._mymemory_email = (
            resolved_mymemory_email
        )
        self._libretranslate_mirrors = (
            libretranslate_mirrors
        )

        self.ui_localizer = Localizer(
            lang_code=self.lang_code,
            base_lang=self.base_lang,
            folder=self.ui_folder,
        )

        self.template_localizer = TemplateLocalizer(
            lang_code=self.lang_code,
            base_lang=self.base_lang,
            folder=self.template_folder,
        )

        logger.info(
            "LocalizationEngine initialized: "
            "lang=%s, base=%s%s",
            self.lang_code,
            self.base_lang,
            " (GLFM Lite)"
            if glfm_lite
            else " (GLFM Full)",
        )

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration and config.conf values."""
        config: Dict[str, Any] = {
            "m_translation_enabled": False,
            "translation_cache_ttl": 3600,
            "fallback_to_base": True,
            "strict_mode": False,
            "default_language": None,
            "glfm_lite": True,
        }

        try:
            import configparser

            if os.path.exists("config.conf"):
                parser = configparser.ConfigParser()
                parser.read(
                    "config.conf",
                    encoding="utf-8",
                )

                if parser.has_section("SETTINGS"):
                    language = parser.get(
                        "SETTINGS",
                        "language",
                        fallback=None,
                    )

                    if language:
                        config["default_language"] = (
                            language.strip()
                        )

                    if parser.has_option(
                        "SETTINGS",
                        "m_translation_enabled",
                    ):
                        config[
                            "m_translation_enabled"
                        ] = parser.getboolean(
                            "SETTINGS",
                            "m_translation_enabled",
                            fallback=False,
                        )

                    if parser.has_option(
                        "SETTINGS",
                        "fallback_to_base",
                    ):
                        config[
                            "fallback_to_base"
                        ] = parser.getboolean(
                            "SETTINGS",
                            "fallback_to_base",
                            fallback=True,
                        )

                    if parser.has_option(
                        "SETTINGS",
                        "glfm_lite",
                    ):
                        config["glfm_lite"] = (
                            parser.getboolean(
                                "SETTINGS",
                                "glfm_lite",
                                fallback=True,
                            )
                        )

                    configured_base = parser.get(
                        "SETTINGS",
                        "base_lang",
                        fallback=None,
                    )

                    if configured_base:
                        config["base_lang"] = (
                            configured_base.strip()
                        )

                    logger.debug(
                        "Loaded settings from config.conf"
                    )

        except Exception as error:
            logger.debug(
                "Could not read config.conf: %s",
                error,
            )

        return config

    # ------------------------------------------------------------------
    # Language detection
    # ------------------------------------------------------------------

    def _detect_language(self) -> str:
        """Detect the active language."""
        configured_language = self.config.get(
            "default_language"
        )

        if configured_language:
            return configured_language

        environment_language = os.environ.get(
            "SHL_LANGUAGE"
        )

        if environment_language:
            return environment_language

        raw_language = os.environ.get(
            "LANG",
            "",
        )

        if raw_language:
            language = raw_language.split(".")[0]

            if "_" in language:
                parts = language.split("_")

                if len(parts) == 2:
                    return (
                        f"{parts[0].lower()}-"
                        f"{parts[1].upper()}"
                    )

            return language.lower()

        return "en"

    # ------------------------------------------------------------------
    # Key validation
    # ------------------------------------------------------------------

    def _validate_key(self, key: str) -> str:
        """Validate and normalize a localization key."""
        if not isinstance(key, str):
            logger.warning(
                "Invalid key type: %s",
                type(key),
            )
            return ""

        normalized_key = key.strip()

        if not normalized_key:
            logger.debug(
                "Empty key detected"
            )
            return ""

        if normalized_key != key:
            logger.debug(
                "Key normalized: '%s' -> '%s'",
                key,
                normalized_key,
            )

        return normalized_key

    # ------------------------------------------------------------------
    # Language management
    # ------------------------------------------------------------------

    def ensure_language(
        self,
        lang_code: str,
    ) -> None:
        """Ensure UI and template files exist."""
        validated_lang = normalize_full_tag(lang_code)

        logger.debug(
            "Ensuring language: %s",
            validated_lang,
        )

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

    def set_language(
        self,
        lang_code: str,
    ) -> None:
        """Switch active language."""
        validated_lang = normalize_full_tag(lang_code)

        self.lang_code = validated_lang

        self.ui_localizer.set_language(
            validated_lang
        )

        self.template_localizer.set_language(
            validated_lang
        )

        if self.validator.is_loaded:
            self.glfm_fallback_chain = (
                self.validator.get_fallback_chain(
                    validated_lang,
                    base_language=self.base_lang,
                    max_nearest=None,
                )
            )

            if len(self.glfm_fallback_chain) > 1:
                self.glfm_fallback = (
                    self.glfm_fallback_chain[1]
                )
            else:
                self.glfm_fallback = None

        logger.info(
            "Language switched to: %s",
            validated_lang,
        )

    # ------------------------------------------------------------------
    # Key management
    # ------------------------------------------------------------------

    def ensure_ui_key(
        self,
        key: str,
        default: str = "",
    ) -> str:
        """Ensure a UI key exists."""
        validated_key = self._validate_key(key)

        if not validated_key:
            return ""

        text = self._get_with_fallback(
            self.ui_localizer.get_text,
            validated_key,
        )

        if text is None or text == "":
            self.ui_localizer.set_text(
                validated_key,
                default,
            )
            return default

        return text

    def ensure_template_key(
        self,
        key: str,
        default: str = "",
    ) -> str:
        """Ensure a template key exists."""
        validated_key = self._validate_key(key)

        if not validated_key:
            return ""

        text = self._get_with_fallback(
            self.template_localizer.get_template,
            validated_key,
        )

        if text is None or text == "":
            self.template_localizer.set_template(
                validated_key,
                default,
            )
            return default

        return text

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------

    def _get_with_fallback(
        self,
        getter: Callable[
            [str, Optional[str], bool],
            Optional[str],
        ],
        key: str,
    ) -> Optional[str]:
        """
        Retrieve a key through the fallback chain.

        If fallback_to_base is False, only the active language is
        checked. GLFM and base-language fallback are both disabled.
        """
        fallback_enabled = self.config.get(
            "fallback_to_base",
            True,
        )

        # 1. Active language is always checked.
        text = getter(
            key,
            self.lang_code,
            fallback=False,
        )

        if text and text.strip():
            return text

        # 2. Fallback disabled: stop here.
        if not fallback_enabled:
            return None

        # 3. GLFM fallback languages.
        if (
            self.glfm_fallback_chain
            and len(self.glfm_fallback_chain) > 1
        ):
            for fallback_lang in (
                self.glfm_fallback_chain[1:]
            ):
                if fallback_lang == self.lang_code:
                    continue

                logger.debug(
                    "Fallback: '%s' -> GLFM language '%s'",
                    key,
                    fallback_lang,
                )

                text = getter(
                    key,
                    fallback_lang,
                    fallback=False,
                )

                if text and text.strip():
                    return text

        # 4. Base language.
        if self.lang_code != self.base_lang:
            logger.debug(
                "Fallback: '%s' -> base language '%s'",
                key,
                self.base_lang,
            )

            text = getter(
                key,
                self.base_lang,
                fallback=False,
            )

            if text and text.strip():
                return text

        return None

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def ui_text(
        self,
        key: str,
        default_value: str = "",
    ) -> str:
        """
        Retrieve UI text with fallback and optional translation.
        """
        validated_key = self._validate_key(key)

        if not validated_key:
            return default_value

        cached = self.cache.get(
            validated_key,
            self.base_lang,
            self.lang_code,
        )

        if cached is not None:
            return cached

        text = self._get_with_fallback(
            self.ui_localizer.get_text,
            validated_key,
        )

        if text is None:
            if (
                self.config.get(
                    "m_translation_enabled",
                    False,
                )
                and self.lang_code != self.base_lang
                and default_value
            ):
                try:
                    translated = translate_text(
                        text=default_value,
                        target_lang=self.lang_code,
                        source_lang=self.base_lang,
                        mymemory_email=self._mymemory_email,
                    )

                    if (
                        translated
                        and translated != default_value
                    ):
                        self.ui_localizer.set_text(
                            validated_key,
                            translated,
                        )

                        self.cache.set(
                            validated_key,
                            translated,
                            self.base_lang,
                            self.lang_code,
                        )

                        return translated

                except Exception as error:
                    logger.warning(
                        "Machine translation failed: %s",
                        error,
                    )

            self.ui_localizer.set_text(
                validated_key,
                default_value,
            )

            self.cache.set(
                validated_key,
                default_value,
                self.base_lang,
                self.lang_code,
            )

            return default_value

        self.cache.set(
            validated_key,
            text,
            self.base_lang,
            self.lang_code,
        )

        return text

    def template(
        self,
        key: str,
        default: str = "",
        **kwargs: Any,
    ) -> str:
        """Retrieve and format a prompt template."""
        validated_key = self._validate_key(key)

        if not validated_key:
            return default if default else key

        text = self._get_with_fallback(
            self.template_localizer.get_template,
            validated_key,
        )

        if text is None:
            text = default if default else key

            self.template_localizer.set_template(
                validated_key,
                text,
            )

        try:
            if kwargs:
                return text.format(**kwargs)

            return text

        except (
            KeyError,
            ValueError,
        ) as error:
            logger.warning(
                "Template '%s' format error: %s",
                validated_key,
                error,
            )

            return text

    # ------------------------------------------------------------------
    # Synchronization
    # ------------------------------------------------------------------

    def _sync_from_lang(
        self,
        source_lang: str,
    ) -> int:
        """
        Synchronize keys from source language.

        Existing keys are counted as synchronized because Localizer may
        already have copied them from the base language.
        """
        if source_lang == self.lang_code:
            return 0

        logger.debug(
            "Syncing from '%s' to '%s'",
            source_lang,
            self.lang_code,
        )

        source_ui = Localizer(
            lang_code=source_lang,
            base_lang=self.base_lang,
            folder=self.ui_folder,
        )

        ui_count = 0

        for key, value in source_ui.texts.items():
            validated_key = self._validate_key(key)

            if not validated_key:
                continue

            if validated_key not in self.ui_localizer.texts:
                self.ui_localizer.set_text(
                    validated_key,
                    value,
                )

            ui_count += 1

        source_templates = TemplateLocalizer(
            lang_code=source_lang,
            base_lang=self.base_lang,
            folder=self.template_folder,
        )

        template_count = 0

        for key, value in source_templates.templates.items():
            validated_key = self._validate_key(key)

            if not validated_key:
                continue

            if (
                validated_key
                not in self.template_localizer.templates
            ):
                self.template_localizer.set_template(
                    validated_key,
                    value,
                )

            template_count += 1

        total_count = ui_count + template_count

        if total_count:
            logger.debug(
                "Synchronized %s UI keys and %s templates "
                "from '%s'",
                ui_count,
                template_count,
                source_lang,
            )

        return total_count

    def sync(self) -> int:
        """Synchronize keys from fallback and base languages."""
        logger.info(
            "Synchronizing to '%s'",
            self.lang_code,
        )

        total_synced = 0

        if (
            self.glfm_fallback_chain
            and len(self.glfm_fallback_chain) > 1
        ):
            for fallback_lang in (
                self.glfm_fallback_chain[1:]
            ):
                if fallback_lang != self.lang_code:
                    total_synced += (
                        self._sync_from_lang(
                            fallback_lang
                        )
                    )

        if self.base_lang != self.lang_code:
            logger.info(
                "Syncing from base language: '%s'",
                self.base_lang,
            )

            total_synced += self._sync_from_lang(
                self.base_lang
            )

        if total_synced == 0:
            logger.info(
                "No new keys to synchronize"
            )
        else:
            logger.info(
                "Synchronization complete: %s keys synced",
                total_synced,
            )

        return total_synced

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return engine statistics."""
        return {
            "lang_code": self.lang_code,
            "base_lang": self.base_lang,
            "glfm_fallback": self.glfm_fallback,
            "glfm_fallback_chain": (
                self.glfm_fallback_chain.copy()
            ),
            "glfm_lite": (
                self.validator.is_lite
                if self.validator
                else True
            ),
            "glfm_loaded": (
                self.validator.is_loaded
                if self.validator
                else False
            ),
            "ui_keys_count": len(
                self.ui_localizer.texts
            ),
            "template_keys_count": len(
                self.template_localizer.templates
            ),
            "cache_size": self.cache.size(),
            "m_translation_enabled": self.config.get(
                "m_translation_enabled",
                False,
            ),
            "config": self.config.copy(),
        }

    # ------------------------------------------------------------------
    # LibreTranslate
    # ------------------------------------------------------------------

    def get_mirror_stats(
        self,
    ) -> List[Dict[str, Any]]:
        """Return LibreTranslate mirror statistics."""
        return self.libretranslate_adapter.get_mirror_stats()

    def clear_mirror_cache(self) -> None:
        """Clear LibreTranslate mirror cache."""
        self.libretranslate_adapter.clear_mirror_cache()

    # ------------------------------------------------------------------
    # GLFM
    # ------------------------------------------------------------------

    def reload_glfm(
        self,
        glfm_path: Optional[str] = None,
        glfm_lite: Optional[bool] = None,
    ) -> bool:
        """Reload the GLFM database."""
        if glfm_lite is None:
            glfm_lite = self.config.get(
                "glfm_lite",
                True,
            )

        self.validator = LanguageValidator(
            glfm_path=glfm_path,
            base_language=self.base_lang,
            use_lite=glfm_lite,
        )

        if not self.validator.is_loaded:
            self.glfm_fallback = None
            self.glfm_fallback_chain = []

            logger.warning(
                "GLFM reload failed"
            )

            return False

        self.glfm_fallback_chain = (
            self.validator.get_fallback_chain(
                self.lang_code,
                base_language=self.base_lang,
                max_nearest=None,
            )
        )

        if len(self.glfm_fallback_chain) > 1:
            self.glfm_fallback = (
                self.glfm_fallback_chain[1]
            )
        else:
            self.glfm_fallback = None

        logger.info(
            "GLFM reloaded: %s languages",
            len(self.validator.languages),
        )

        return True
