"""
File: localizer.py
Author: Tuomas Lähteenmäki
Version: 0.2.1
License: MIT
Description:
    Self-Healing Localizer for UI text.
    SETTINGS.language now overrides OS locale and GLFM completely.
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


class Localizer:
    """Self-Healing Localizer for UI text."""

    def __init__(
        self,
        lang_code: Optional[str] = None,
        base_lang: str = "en",
        folder: str = "locales",
    ):
        self.folder = folder
        self._dirty = False
        self._alive = True
        self._shutting_down = False

        # SETTINGS overrides everything
        if lang_code is None:
            lang_code = self._detect_language() or base_lang

        self.lang_code = normalize_full_tag(lang_code)
        self.base_lang_tag = normalize_full_tag(base_lang)
        self.base_lang = base_language(self.base_lang_tag)

        self._loaded_langs: Dict[str, Dict[str, Any]] = {}

        os.makedirs(self.folder, exist_ok=True)

        self.lang_file = os.path.join(self.folder, f"{self.lang_code}.json")
        self.base_file = os.path.join(self.folder, f"{self.base_lang_tag}.json")

        self.texts = self._load_or_create()

        atexit.register(self._atexit_save)

        logger.debug(
            "Localizer initialized: lang=%s, base=%s, base_tag=%s, keys=%s",
            self.lang_code,
            self.base_lang,
            self.base_lang_tag,
            len(self.texts),
        )

    # ------------------------------------------------------------------
    # Language detection (SETTINGS overrides locale)
    # ------------------------------------------------------------------

    def _detect_language(self) -> Optional[str]:
        """Detect language from config.conf or environment."""
        try:
            import configparser

            if os.path.exists("config.conf"):
                parser = configparser.ConfigParser()
                parser.read("config.conf", encoding="utf-8")

                # SETTINGS overrides locale and environment
                if parser.has_option("SETTINGS", "language"):
                    language = parser.get("SETTINGS", "language")
                    if language:
                        logger.debug("Language forced by SETTINGS: %s", language)
                        return language.strip()

        except Exception as error:
            logger.debug("Language detection failed: %s", error)

        # If SETTINGS had language, we would have returned already.
        # Now check SHL_LANGUAGE environment variable.
        language = os.environ.get("SHL_LANGUAGE")
        if language:
            logger.debug("Language forced by SHL_LANGUAGE: %s", language)
            return language.strip()

        # Locale is now used ONLY if SETTINGS and SHL_LANGUAGE are missing.
        raw_language = os.environ.get("LANG", "")
        if raw_language:
            language = raw_language.split(".")[0]

            if "_" in language:
                parts = language.split("_")
                if len(parts) == 2:
                    detected = f"{parts[0].lower()}-{parts[1].upper()}"
                    logger.debug("Language detected from locale: %s", detected)
                    return detected

            detected = language.lower()
            logger.debug("Language detected from locale: %s", detected)
            return detected

        return None

    # ------------------------------------------------------------------
    # Validation and cache
    # ------------------------------------------------------------------

    def _validate_key(self, key: str) -> str:
        if not isinstance(key, str):
            logger.warning("Invalid key type: %s", type(key))
            return ""

        normalized_key = key.strip()
        return normalized_key

    def _invalidate_cache(self) -> None:
        if self._loaded_langs:
            self._loaded_langs.clear()
            if not self._shutting_down:
                logger.debug("Loaded language cache cleared")

    # ------------------------------------------------------------------
    # JSON loading
    # ------------------------------------------------------------------

    def _load_json_safe(self, filepath: str) -> Optional[Dict[str, Any]]:
        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as file:
                data = json.load(file)

            if not isinstance(data, dict):
                logger.error("JSON file is not a dictionary: %s", filepath)
                self._backup_corrupted_file(filepath)
                return None

            return data

        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            logger.error("Corrupted JSON file: %s - %s", filepath, error)
            self._backup_corrupted_file(filepath)
            return None

        except Exception as error:
            logger.error("Unexpected error loading file: %s - %s", filepath, error)
            return None

    def _backup_corrupted_file(self, filepath: str) -> None:
        try:
            if not os.path.exists(filepath):
                return

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{filepath}.{timestamp}.bak"
            shutil.copy2(filepath, backup_path)

            logger.info("Backup created: %s", backup_path)

        except Exception as error:
            logger.error("Backup creation failed for %s: %s", filepath, error)

    # ------------------------------------------------------------------
    # Saving
    # ------------------------------------------------------------------

    def _save_texts(self, texts: Dict[str, Any], filepath: Optional[str] = None) -> bool:
        if filepath is None:
            filepath = self.lang_file

        tmp_path = f"{filepath}.tmp"

        try:
            directory = os.path.dirname(filepath)
            os.makedirs(directory, exist_ok=True)

            with open(tmp_path, "w", encoding="utf-8") as file:
                json.dump(texts, file, indent=4, ensure_ascii=False)
                file.flush()
                os.fsync(file.fileno())

            os.replace(tmp_path, filepath)

            if not self._shutting_down:
                logger.debug("Saved %s keys to %s", len(texts), filepath)

            return True

        except Exception as error:
            logger.error("Save failed for %s: %s", filepath, error)
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            return False

    def _save(self) -> bool:
        return self._save_texts(self.texts, self.lang_file)

    def _save_if_dirty(self) -> bool:
        if not self._dirty:
            return True
        saved = self._save()
        if saved:
            self._dirty = False
        return saved

    def save(self) -> bool:
        saved = self._save()
        if saved:
            self._dirty = False
        return saved

    def _atexit_save(self) -> None:
        if not self._alive or not self._dirty:
            return
        self._shutting_down = True
        try:
            if self._save():
                self._dirty = False
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

    def _mark_dirty(self) -> None:
        self._dirty = True

    # ------------------------------------------------------------------
    # Migration and creation
    # ------------------------------------------------------------------

    def _migrate_legacy_file(self, legacy_path: str, new_path: str) -> Optional[Dict[str, Any]]:
        if not os.path.exists(legacy_path):
            return None
        legacy_texts = self._load_json_safe(legacy_path)
        if legacy_texts is None:
            return None
        if self._save_texts(legacy_texts, new_path):
            logger.info("Migrated %s keys from '%s' to '%s'", len(legacy_texts), legacy_path, new_path)
            return legacy_texts
        return None

    def _load_or_create(self) -> Dict[str, Any]:
        if os.path.exists(self.lang_file):
            texts = self._load_json_safe(self.lang_file)
            if texts is not None:
                logger.debug("Loaded %s keys from file: %s", len(texts), self.lang_file)
                return texts

        legacy_file = os.path.join(self.folder, f"lang_{self.lang_code}.json")
        legacy_texts = self._migrate_legacy_file(legacy_file, self.lang_file)
        if legacy_texts is not None:
            return legacy_texts

        base_texts: Dict[str, Any] = {}

        if os.path.exists(self.base_file):
            loaded_base = self._load_json_safe(self.base_file)
            if loaded_base is not None:
                base_texts = loaded_base

        self._save_texts(base_texts, self.lang_file)
        return base_texts

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def L(self, key: str, default: str = "") -> str:
        validated_key = self._validate_key(key)
        if not validated_key:
            return default or ""

        if validated_key not in self.texts:
            value = default if default is not None else ""
            self.texts[validated_key] = value
            self._mark_dirty()
            self._invalidate_cache()
            self.save()

        return self.texts.get(validated_key, default) or ""

    def get(self, key: str, default: str = "") -> str:
        return self.L(key, default)

    def get_text(self, key: str, lang_code: Optional[str] = None, fallback: bool = True) -> Optional[str]:
        validated_key = self._validate_key(key)
        if not validated_key:
            return None

        target_lang = normalize_full_tag(lang_code or self.lang_code)
        text = self._get_text_from_lang(validated_key, target_lang)

        if text is not None:
            return text

        if fallback and target_lang != self.base_lang_tag:
            return self._get_text_from_lang(validated_key, self.base_lang_tag)

        return None

    def _get_text_from_lang(self, key: str, lang_code: str) -> Optional[str]:
        try:
            normalized_lang = normalize_full_tag(lang_code)

            if normalized_lang == self.lang_code:
                return self.texts.get(key)

            if normalized_lang in self._loaded_langs:
                return self._loaded_langs[normalized_lang].get(key)

            lang_file = os.path.join(self.folder, f"{normalized_lang}.json")

            if not os.path.exists(lang_file):
                self._loaded_langs[normalized_lang] = {}
                return None

            texts = self._load_json_safe(lang_file)
            if texts is None:
                self._loaded_langs[normalized_lang] = {}
                return None

            self._loaded_langs[normalized_lang] = texts
            return texts.get(key)

        except Exception as error:
            if not self._shutting_down:
                logger.error("Error fetching key '%s' from language '%s': %s", key, lang_code, error)
            return None

    def set_text(self, key: str, value: Optional[str]) -> bool:
        validated_key = self._validate_key(key)
        if not validated_key:
            return False

        normalized_value = value if value is not None else ""
        self.texts[validated_key] = normalized_value
        self._mark_dirty()
        self._invalidate_cache()

        saved = self.save()
        logger.debug("Set: '%s' = '%s'", validated_key, normalized_value)
        return saved

    def set_language(self, lang_code: str) -> bool:
        new_lang = normalize_full_tag(lang_code)
        if new_lang == self.lang_code:
            return True

        if not self.save():
            return False

        self.lang_code = new_lang
        self.lang_file = os.path.join(self.folder, f"{self.lang_code}.json")
        self.texts = self._load_or_create()
        self._invalidate_cache()
        self._dirty = False

        return True

    # ------------------------------------------------------------------
    # Mapping API
    # ------------------------------------------------------------------

    def has_key(self, key: str) -> bool:
        validated_key = self._validate_key(key)
        return bool(validated_key and validated_key in self.texts)

    def keys(self):
        return list(self.texts.keys())

    def values(self):
        return [value if value is not None else "" for value in self.texts.values()]

    def items(self):
        return [(key, value if value is not None else "") for key, value in self.texts.items()]

    def __contains__(self, key: str) -> bool:
        return self.has_key(key)

    def __getitem__(self, key: str) -> str:
        return self.L(key)

    def __setitem__(self, key: str, value: Optional[str]) -> None:
        self.set_text(key, value)

    def __len__(self) -> int:
        return len(self.texts)

    def __repr__(self) -> str:
        return f"Localizer(lang='{self.lang_code}', keys={len(self.texts)})"

