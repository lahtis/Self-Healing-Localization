"""
File: template_localizer.py
Author: Tuomas Lähteenmäki
Version: 0.2.0
License: MIT
Description:
    Self-Healing Localizer for AI prompt templates.

    - Creates missing template language files automatically
    - Copies base language templates as fallback
    - Adds missing keys on the fly
    - Ensures template consistency across languages
    - Validates template keys and handles corruption gracefully
    - Uses atomic saves with temporary files
    - Supports dirty flag for batch saves
    - Caches loaded languages for performance
"""

import atexit
import json
import logging
import os
import shutil
from datetime import datetime
from typing import Any, Dict, Optional

from shl.utils.lang_utils import (
    base_language,
    normalize_full_tag,
)


logger = logging.getLogger(__name__)


class TemplateLocalizer:
    """Self-healing localizer for prompt templates."""

    def __init__(
        self,
        lang_code: Optional[str] = None,
        base_lang: str = "en",
        folder: str = "prompts",
    ):
        self.folder = folder
        self._dirty = False
        self._alive = True
        self._shutting_down = False
        self._loaded_langs: Dict[
            str,
            Dict[str, Any],
        ] = {}

        lang_code = (
            lang_code
            or self._detect_language()
            or base_lang
        )

        self.lang_code = normalize_full_tag(lang_code)
        self.base_lang_tag = normalize_full_tag(base_lang)
        self.base_lang = base_language(self.base_lang_tag)

        os.makedirs(self.folder, exist_ok=True)

        self.lang_file = os.path.join(
            self.folder,
            f"{self.lang_code}.json",
        )
        self.base_file = os.path.join(
            self.folder,
            f"{self.base_lang_tag}.json",
        )

        self.templates = self._load_or_create()
        atexit.register(self._atexit_save)

    # ------------------------------------------------------------------
    # Detection and validation
    # ------------------------------------------------------------------

    def _detect_language(self) -> Optional[str]:
        try:
            import configparser

            if os.path.exists("config.conf"):
                parser = configparser.ConfigParser()
                parser.read(
                    "config.conf",
                    encoding="utf-8",
                )

                value = parser.get(
                    "SETTINGS",
                    "language",
                    fallback=None,
                )

                if value:
                    return value.strip()

        except Exception as error:
            logger.debug(
                "Language detection failed: %s",
                error,
            )

        value = os.environ.get("SHL_LANGUAGE")

        if value:
            return value.strip()

        value = os.environ.get("LANG", "")

        if value:
            value = value.split(".")[0]

            if "_" in value:
                parts = value.split("_")

                if len(parts) == 2:
                    return (
                        f"{parts[0].lower()}-"
                        f"{parts[1].upper()}"
                    )

            return value.lower()

        return None

    def _validate_key(self, key: str) -> str:
        if not isinstance(key, str):
            logger.warning(
                "Invalid template key type: %s",
                type(key),
            )
            return ""

        return key.strip()

    def _mark_dirty(self) -> None:
        self._dirty = True

    def _invalidate_cache(self) -> None:
        self._loaded_langs.clear()

    # ------------------------------------------------------------------
    # JSON handling
    # ------------------------------------------------------------------

    def _load_json_safe(
        self,
        filepath: str,
    ) -> Optional[Dict[str, Any]]:
        if not os.path.exists(filepath):
            return None

        try:
            with open(
                filepath,
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

            if not isinstance(data, dict):
                self._backup_corrupted_file(filepath)
                return None

            return data

        except (
            json.JSONDecodeError,
            UnicodeDecodeError,
            OSError,
        ) as error:
            logger.error(
                "Could not load JSON file %s: %s",
                filepath,
                error,
            )
            self._backup_corrupted_file(filepath)
            return None

        except Exception as error:
            logger.error(
                "Unexpected loading error for %s: %s",
                filepath,
                error,
            )
            return None

    def _backup_corrupted_file(
        self,
        filepath: str,
    ) -> None:
        try:
            if not os.path.exists(filepath):
                return

            timestamp = datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )

            shutil.copy2(
                filepath,
                f"{filepath}.{timestamp}.bak",
            )

        except Exception:
            pass

    # ------------------------------------------------------------------
    # Saving
    # ------------------------------------------------------------------

    def _save_templates(
        self,
        templates: Dict[str, Any],
        filepath: Optional[str] = None,
    ) -> bool:
        filepath = filepath or self.lang_file
        tmp_path = f"{filepath}.tmp"

        try:
            directory = os.path.dirname(filepath)

            if directory:
                os.makedirs(
                    directory,
                    exist_ok=True,
                )

            with open(
                tmp_path,
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    templates,
                    file,
                    indent=4,
                    ensure_ascii=False,
                )
                file.flush()
                os.fsync(file.fileno())

            os.replace(
                tmp_path,
                filepath,
            )

            if not self._shutting_down:
                logger.debug(
                    "Saved %s templates to %s",
                    len(templates),
                    filepath,
                )

            return True

        except Exception as error:
            if not self._shutting_down:
                logger.error(
                    "Save failed for %s: %s",
                    filepath,
                    error,
                )

            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass

            return False

    def _save(self) -> bool:
        return self._save_templates(
            self.templates,
            self.lang_file,
        )

    def _save_if_dirty(self) -> bool:
        if not self._dirty:
            return True

        result = self._save()

        if result:
            self._dirty = False

        return result

    def save(self) -> bool:
        """Always save current in-memory templates."""
        result = self._save()

        if result:
            self._dirty = False

        return result

    def _atexit_save(self) -> None:
        if not self._alive or not self._dirty:
            return

        self._shutting_down = True

        try:
            if self._save():
                self._dirty = False
        except Exception:
            pass
        finally:
            self._shutting_down = False

    def close(self) -> bool:
        if not self._alive:
            return True

        if not self._save_if_dirty():
            return False

        self._alive = False
        return True

    def __del__(self):
        try:
            self._alive = False
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Loading and migration
    # ------------------------------------------------------------------

    def _migrate_legacy_file(
        self,
        legacy_path: str,
        new_path: str,
    ) -> Optional[Dict[str, Any]]:
        if not os.path.exists(legacy_path):
            return None

        data = self._load_json_safe(legacy_path)

        if data is None:
            return None

        if self._save_templates(data, new_path):
            return data

        return None

    def _load_or_create(self) -> Dict[str, Any]:
        if os.path.exists(self.lang_file):
            data = self._load_json_safe(self.lang_file)

            if data is not None:
                return data

        legacy_file = os.path.join(
            self.folder,
            f"lang_{self.lang_code}.json",
        )

        data = self._migrate_legacy_file(
            legacy_file,
            self.lang_file,
        )

        if data is not None:
            return data

        base_data: Dict[str, Any] = {}

        if os.path.exists(self.base_file):
            data = self._load_json_safe(self.base_file)

            if data is not None:
                base_data = data

        self._save_templates(
            base_data,
            self.lang_file,
        )

        return base_data

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ensure_key(
        self,
        key: str,
        default_value: str = "",
    ) -> str:
        key = self._validate_key(key)

        if not key:
            return default_value or ""

        value = (
            default_value
            if default_value is not None
            else ""
        )

        if key not in self.templates:
            self.templates[key] = value
            self._mark_dirty()
            self._invalidate_cache()
            self.save()

        return self.templates.get(key, value) or ""

    def get(
        self,
        key: str,
        default_value: str = "",
    ) -> str:
        return self.ensure_key(
            key,
            default_value,
        )

    def get_template(
        self,
        key: str,
        lang_code: Optional[str] = None,
        fallback: bool = True,
    ) -> Optional[str]:
        key = self._validate_key(key)

        if not key:
            return None

        language = normalize_full_tag(
            lang_code or self.lang_code
        )

        value = self._get_template_from_lang(
            key,
            language,
        )

        if value is not None:
            return value

        if (
            fallback
            and language != self.base_lang_tag
        ):
            return self._get_template_from_lang(
                key,
                self.base_lang_tag,
            )

        return None

    def _get_template_from_lang(
        self,
        key: str,
        lang_code: str,
    ) -> Optional[str]:
        language = normalize_full_tag(lang_code)

        if language == self.lang_code:
            return self.templates.get(key)

        if language in self._loaded_langs:
            return self._loaded_langs[language].get(key)

        filepath = os.path.join(
            self.folder,
            f"{language}.json",
        )

        data = self._load_json_safe(filepath) or {}
        self._loaded_langs[language] = data

        return data.get(key)

    def set_template(
        self,
        key: str,
        value: Optional[str],
    ) -> str:
        key = self._validate_key(key)

        if not key:
            return ""

        value = value if value is not None else ""

        self.templates[key] = value
        self._mark_dirty()
        self._invalidate_cache()
        self.save()

        return value

    def set_language(
        self,
        lang_code: str,
    ) -> bool:
        language = normalize_full_tag(lang_code)

        if language == self.lang_code:
            return True

        if not self.save():
            return False

        self.lang_code = language
        self.lang_file = os.path.join(
            self.folder,
            f"{language}.json",
        )

        self.templates = self._load_or_create()
        self._invalidate_cache()
        self._dirty = False

        return True

    def format_template(
        self,
        key: str,
        **kwargs: Any,
    ) -> str:
        key = self._validate_key(key)

        if not key:
            return ""

        value = self.get_template(key)

        if value is None:
            return key

        try:
            return value.format(**kwargs) if kwargs else value

        except (KeyError, ValueError) as error:
            logger.warning(
                "Template formatting failed: %s",
                error,
            )
            return value

    # ------------------------------------------------------------------
    # Mapping API
    # ------------------------------------------------------------------

    def has_key(self, key: str) -> bool:
        key = self._validate_key(key)
        return bool(key and key in self.templates)

    def keys(self):
        return list(self.templates.keys())

    def values(self):
        return [
            value if value is not None else ""
            for value in self.templates.values()
        ]

    def items(self):
        return [
            (
                key,
                value if value is not None else "",
            )
            for key, value in self.templates.items()
        ]

    def __contains__(self, key: str) -> bool:
        return self.has_key(key)

    def __getitem__(self, key: str) -> str:
        return self.get(key)

    def __setitem__(
        self,
        key: str,
        value: Optional[str],
    ) -> None:
        self.set_template(key, value)

    def __len__(self) -> int:
        return len(self.templates)

    def __repr__(self) -> str:
        return (
            "TemplateLocalizer("
            f"lang='{self.lang_code}', "
            f"templates={len(self.templates)}"
            ")"
        )
