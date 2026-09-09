"""
File: core.py
Author: Tuomas Lähteenmäki
Version: 0.2.10
License: MIT
Description:
    Central localization engine for the Self-Healing Localization Layer.

    Responsibilities:
    - Manages UI localization through Localizer.
    - Manages AI prompt templates through TemplateLocalizer.
    - Ensures languages exist across both systems.
    - Validates and normalizes language codes.
    - Manages GLFM language fallback chains.
    - Synchronizes localized keys and templates.
    - Provides optional machine translation through the translation layer.

    Translation providers, provider failover, provider policies, retries,
    provider registries, and translation caching are handled by the
    translation subsystem rather than by this class.
"""

import logging
import os
from typing import Any, Dict, List, Optional, Set, Tuple

from shl.engine.localizer import Localizer
from shl.engine.template_localizer import TemplateLocalizer
from shl.engine.translation import translate_text
from shl.engine.translation.exceptions import LanguageNotSupportedError

from shl.language_validator import LanguageValidator
from shl.utils.lang_utils import base_language, normalize_full_tag
from shl.utils.env_loader import get_env_value, load_shl_env


logger = logging.getLogger(__name__)


class LocalizationEngine:
    """High-level localization engine for UI text and prompt templates."""

    def __init__(
        self,
        lang_code: Optional[str] = None,
        base_lang: str = "en",
        ui_folder: str = "locales",
        template_folder: str = "prompts",
        config: Optional[Dict[str, Any]] = None,
        glfm_path: Optional[str] = None,
        glfm_lite: Optional[bool] = None,
    ) -> None:
        load_shl_env()

        self.config = self._build_config(config)

        self.ui_folder = ui_folder
        self.template_folder = template_folder

        self.base_lang = base_language(
            self.config.get("base_lang", base_lang)
        )

        selected_language = lang_code or self.config.get("language")

        if not selected_language:
            selected_language = self._detect_language()

        self.lang_code = normalize_full_tag(selected_language)

        self.fallback_to_base = bool(
            self.config.get("fallback_to_base", True)
        )

        self.m_translation_enabled = bool(
            self.config.get("m_translation_enabled", False)
        )

        # A bootstrap may introduce dozens of missing UI strings at once.
        # When the translation layer has conclusively rejected a language
        # pair, remember it for this engine instance instead of routing every
        # remaining key through the same unavailable providers.
        self._unavailable_translation_pairs: Set[Tuple[str, str]] = set()

        self.validator = LanguageValidator(glfm_path)

        self.glfm_fallback: List[str] = []

        self._validate_language()
        self._build_fallback_chain()

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
            "LocalizationEngine initialized: lang=%s, base=%s",
            self.lang_code,
            self.base_lang,
        )

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def _build_config(
        self,
        config: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build the localization configuration."""

        defaults = {
            "m_translation_enabled": False,
            "fallback_to_base": True,
            "strict_mode": False,
            "default_language": None,
            "glfm_lite": True,
        }

        if config:
            defaults.update(config)

        return defaults

    # ------------------------------------------------------------------
    # Language detection and validation
    # ------------------------------------------------------------------

    def _detect_language(self) -> str:
        """Detect the active language from configuration or environment."""

        language = get_env_value("SHL_LANGUAGE")

        if not language:
            language = get_env_value("LANG")

        if not language:
            language = self.config.get("default_language")

        return normalize_full_tag(language or "en")

    def _validate_language(self) -> None:
        """Validate the active language against GLFM when available."""

        if not self.validator.is_loaded:
            return

        if self.validator.is_valid(self.lang_code):
            return

        logger.warning(
            "Language '%s' not found in GLFM; using base language '%s'",
            self.lang_code,
            self.base_lang,
        )

        self.lang_code = self.base_lang

    def _build_fallback_chain(self) -> None:
        """Build the GLFM localization fallback chain."""

        self.glfm_fallback = []

        if not self.validator.is_loaded:
            return

        try:
            fallback = self.validator.get_fallback(self.lang_code)
        except Exception as error:
            logger.warning(
                "Unable to build GLFM fallback for '%s': %s",
                self.lang_code,
                error,
            )
            return

        if not fallback:
            return

        if isinstance(fallback, str):
            fallback = [fallback]

        for language in fallback:
            normalized = normalize_full_tag(language)

            if normalized == self.lang_code:
                continue

            if normalized not in self.glfm_fallback:
                self.glfm_fallback.append(normalized)

        logger.debug(
            "GLFM fallback chain for '%s': %s",
            self.lang_code,
            self.glfm_fallback,
        )

    # ------------------------------------------------------------------
    # Language management
    # ------------------------------------------------------------------

    def ensure_language(self, lang_code: str) -> None:
        """Ensure UI and template localization files exist."""

        normalized = normalize_full_tag(lang_code)

        Localizer(
            lang_code=normalized,
            base_lang=self.base_lang,
            folder=self.ui_folder,
        )

        TemplateLocalizer(
            lang_code=normalized,
            base_lang=self.base_lang,
            folder=self.template_folder,
        )

    def set_language(self, lang_code: str) -> None:
        """Switch the active localization language."""

        normalized = normalize_full_tag(lang_code)

        if normalized == self.lang_code:
            return

        self.lang_code = normalized

        self._validate_language()
        self._build_fallback_chain()

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
            "Localization language changed to '%s'",
            self.lang_code,
        )

    # ------------------------------------------------------------------
    # Key validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_key(key: Any) -> str:
        """Validate and normalize a localization key."""

        if not isinstance(key, str):
            raise TypeError("Localization key must be a string")

        key = key.strip()

        if not key:
            raise ValueError("Localization key cannot be empty")

        return key

    # ------------------------------------------------------------------
    # Localization fallback
    # ------------------------------------------------------------------

    def _get_with_fallback(
        self,
        localizer: Any,
        key: str,
    ) -> Optional[str]:
        """
        Resolve a localized value through the localization fallback chain.

        Order:
            active language
            GLFM fallback languages
            base language

        This is localization fallback, not translation-provider fallback.
        """

        value = localizer.get_text(key)

        if value is not None:
            return value

        if not self.fallback_to_base:
            return None

        for language in self.glfm_fallback:
            fallback_localizer = Localizer(
                lang_code=language,
                base_lang=self.base_lang,
                folder=self.ui_folder,
            )

            value = fallback_localizer.get_text(key)

            if value is not None:
                return value

        if self.lang_code != self.base_lang:
            base_localizer = Localizer(
                lang_code=self.base_lang,
                base_lang=self.base_lang,
                folder=self.ui_folder,
            )

            value = base_localizer.get_text(key)

            if value is not None:
                return value

        return None

    # ------------------------------------------------------------------
    # UI localization
    # ------------------------------------------------------------------

    def ensure_ui_key(
        self,
        key: str,
        default: str = "",
    ) -> str:
        """Ensure a UI key exists and return its localized value."""

        validated_key = self._validate_key(key)

        value = self._get_with_fallback(
            self.ui_localizer,
            validated_key,
        )

        if value is not None:
            return value

        self.ui_localizer.set_text(
            validated_key,
            default,
        )

        return default

    def ui_text(
        self,
        key: str,
        default_value: str = "",
    ) -> str:
        """
        Return localized UI text.

        Existing localization always has priority. Missing text may be
        machine-translated when translation is explicitly enabled.

        Translation failures are not converted into successful translations.
        The translation subsystem is responsible for provider failover and
        translation caching.
        """

        validated_key = self._validate_key(key)

        value = self._get_with_fallback(
            self.ui_localizer,
            validated_key,
        )

        if value is not None:
            return value

        if (
            self.m_translation_enabled
            and self.lang_code != self.base_lang
            and default_value
            and (
                self.base_lang,
                self.lang_code,
            ) not in self._unavailable_translation_pairs
        ):
            try:
                translated = translate_text(
                    text=default_value,
                    target_lang=self.lang_code,
                    source_lang=self.base_lang,
                    raise_on_language_not_supported=True,
                )

                if translated is not None:
                    self.ui_localizer.set_text(
                        validated_key,
                        translated,
                    )
                    return translated

            except LanguageNotSupportedError as error:
                language_pair = (
                    self.base_lang,
                    self.lang_code,
                )
                self._unavailable_translation_pairs.add(language_pair)

                logger.warning(
                    "Machine translation is unavailable for '%s' -> '%s'; "
                    "falling back to base language '%s': %s",
                    self.base_lang,
                    self.lang_code,
                    self.base_lang,
                    error,
                )
                self.set_language(self.base_lang)
                                
                return self.ui_text(
                    key=validated_key,
                    default_value=default_value,
                )
    				
            except Exception as error:
                logger.warning(
                    "Machine translation failed for key '%s': %s",
                    validated_key,
                    error,
                )

        self.ui_localizer.set_text(
            validated_key,
            default_value,
        )

        return default_value

    # ------------------------------------------------------------------
    # Prompt templates
    # ------------------------------------------------------------------

    def ensure_template_key(
        self,
        key: str,
        default: str = "",
    ) -> str:
        """Ensure a prompt template key exists."""

        validated_key = self._validate_key(key)

        value = self.template_localizer.get_text(validated_key)

        if value is not None:
            return value

        self.template_localizer.set_text(
            validated_key,
            default,
        )

        return default

    def template(
        self,
        key: str,
        default: str = "",
        **kwargs: Any,
    ) -> str:
        """Return a localized prompt template and format it."""

        validated_key = self._validate_key(key)

        value = self.template_localizer.get_text(
            validated_key
        )

        if value is None:
            value = default

            self.template_localizer.set_text(
                validated_key,
                value,
            )

        if not kwargs:
            return value

        try:
            return value.format(**kwargs)

        except (KeyError, ValueError) as error:
            logger.warning(
                "Template formatting failed for key '%s': %s",
                validated_key,
                error,
            )
            return value

    # ------------------------------------------------------------------
    # Synchronization
    # ------------------------------------------------------------------

    def _sync_from_lang(
        self,
        source_lang: str,
    ) -> None:
        """Synchronize missing UI and template keys from one language."""

        source_ui = Localizer(
            lang_code=source_lang,
            base_lang=self.base_lang,
            folder=self.ui_folder,
        )

        source_templates = TemplateLocalizer(
            lang_code=source_lang,
            base_lang=self.base_lang,
            folder=self.template_folder,
        )

        for key, value in source_ui.texts.items():
            if key not in self.ui_localizer.texts:
                self.ui_localizer.set_text(key, value)

        for key, value in source_templates.templates.items():
            if key not in self.template_localizer.templates:
                self.template_localizer.set_text(key, value)

    def sync(self) -> None:
        """Synchronize missing keys from fallback languages and base."""

        for language in self.glfm_fallback:
            if language != self.lang_code:
                self._sync_from_lang(language)

        if self.base_lang != self.lang_code:
            self._sync_from_lang(self.base_lang)

    # ------------------------------------------------------------------
    # GLFM
    # ------------------------------------------------------------------

    def reload_glfm(self) -> None:
        """Reload GLFM data and rebuild the localization fallback chain."""

        self.validator = LanguageValidator(
            self.validator.path
            if hasattr(self.validator, "path")
            else None
        )

        self._validate_language()
        self._build_fallback_chain()

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return localization engine statistics."""

        return {
            "lang_code": self.lang_code,
            "base_lang": self.base_lang,
            "glfm_loaded": self.validator.is_loaded,
            "glfm_fallback": self.glfm_fallback,
            "fallback_to_base": self.fallback_to_base,
            "m_translation_enabled": self.m_translation_enabled,
            "unavailable_translation_pairs": len(
                self._unavailable_translation_pairs
            ),
            "ui_keys": len(self.ui_localizer.texts),
            "template_keys": len(self.template_localizer.templates),
            "config": dict(self.config),
        }
