"""
File: localizer.py
Author: Tuomas Lähteenmäki
Version: 0.2.3
License: MIT
Description:
    Self-Healing Localizer for UI text.
    SETTINGS.language now overrides OS locale and GLFM completely.

    Locale file names use the canonical ISO 639-3 identity
    (e.g. "fin", "eng", "zho") so that the same file is used
    regardless of whether the caller provides ISO 639-1,
    ISO 639-3, or BCP-47 input.
"""

import atexit
import json
import logging
import os
import shutil
from datetime import datetime
from typing import Any, Dict, Optional

from shl.language_parser import LanguageParser
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

        self._parser = LanguageParser()

        # Kanoninen ISO 639-3 -identiteetti
        self.lang_code = self._parser.normalize(lang_code)      # fin
        self.base_lang = self._parser.normalize(base_lang)      # eng

        # Tiedostonimet – ISO 639-3
        self.lang_tag = self.lang_code                          # fin
        self.base_lang_tag = self.base_lang                     # eng

        self._loaded_langs: Dict[str, Dict[str, Any]] = {}

        os.makedirs(self.folder, exist_ok=True)

        self.lang_file = os.path.join(
            self.folder, f"{self.lang_tag}.json"
        )   # fin.json
        self.base_file = os.path.join(
            self.folder, f"{self.base_lang_tag}.json"
        )   # eng.json

        self.texts = self._load_or_create()

        atexit.register(self._atexit_save)

        logger.debug(
            "Localizer initialized: lang=%s, base=%s, "
            "lang_tag=%s, base_tag=%s, keys=%s",
            self.lang_code,
            self.base_lang,
            self.lang_tag,
            self.base_lang_tag,
            len(self.texts),
        )

    # ------------------------------------------------------------------
    # Language detection (SETTINGS overrides locale)
    # ------------------------------------------------------------------

    def _detect_language(self) -> Optional[str]:
        """Detect language from config.toml, config.conf, or environment.

        Priority (highest first):
            1. config.toml [general] language  (new, preferred)
            2. config.conf [SETTINGS] language (legacy, fallback)
            3. SHL_LANGUAGE environment variable
            4. LANG environment variable (locale)
            5. None (caller falls back to base_lang)
        """
        # 1. config.toml [general] language (new, preferred)
        try:
            from shl.config import get_config_value
            value = (
                get_config_value("general.language")
                or get_config_value("language")
            )
            if value and isinstance(value, str) and value.strip():
                logger.debug("Language from config.toml: %s", value)
                return value.strip()
        except Exception as error:
            logger.debug("config.toml read failed: %s", error)

        # 2. config.conf [SETTINGS] language (legacy, fallback)
        try:
            import configparser
            if os.path.exists("config.conf"):
                parser = configparser.ConfigParser()
                parser.read("config.conf", encoding="utf-8")
                if parser.has_option("SETTINGS", "language"):
                    value = parser.get("SETTINGS", "language")
                    if value and value.strip():
                        logger.debug("Language from config.conf: %s", value)
                        return value.strip()
        except Exception as error:
            logger.debug("config.conf read failed: %s", error)

        # 3. SHL_LANGUAGE environment variable
        value = os.environ.get("SHL_LANGUAGE")
        if value and value.strip():
            logger.debug("Language from SHL_LANGUAGE: %s", value)
            return value.strip()

        # 4. LANG environment variable (locale)
        raw = os.environ.get("LANG", "")
        if raw:
            language = raw.split(".")[0]
            if "_" in language:
                parts = language.split("_")
                if len(parts) == 2:
                    detected = f"{parts[0].lower()}-{parts[1].upper()}"
                    logger.debug("Language from locale: %s", detected)
                    return detected
            detected = language.lower()
            logger.debug("Language from locale: %s", detected)
            return detected

        # 5. None – caller falls back to base_lang
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
                logger.debug(
                    "Loaded %s keys from file: %s",
                    len(texts),
                    self.lang_file,
                )
                return texts

        legacy_file = os.path.join(
            self.folder, f"lang_{self.lang_tag}.json"
        )
        legacy_texts = self._migrate_legacy_file(
            legacy_file, self.lang_file
        )
        if legacy_texts is not None:
            return legacy_texts

        # Älä kopioi base_file → lang_file.
        # Luo tyhjä tiedosto, jotta engine.ui_text() voi kääntää
        # base_lang → lang_code.
        self._save_texts({}, self.lang_file)
        return {}

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

        target_lang = self._parser.normalize(
            lang_code or self.lang_code
        )
        text = self._get_text_from_lang(validated_key, target_lang)

        if text is not None:
            return text

        if fallback and target_lang != self.base_lang:
            return self._get_text_from_lang(
                validated_key, self.base_lang
            )

        return None

    def _get_text_from_lang(self, key: str, lang_code: str) -> Optional[str]:
        try:
            normalized_lang = self._parser.normalize(lang_code)

            if normalized_lang == self.lang_code:
                return self.texts.get(key)

            if normalized_lang in self._loaded_langs:
                return self._loaded_langs[normalized_lang].get(key)

            lang_file = os.path.join(
                self.folder, f"{normalized_lang}.json"
            )

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
                logger.error(
                    "Error fetching key '%s' from language '%s': %s",
                    key,
                    lang_code,
                    error,
                )
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
        new_lang = self._parser.normalize(lang_code)
        if new_lang == self.lang_code:
            return True

        if not self.save():
            return False

        self.lang_code = new_lang
        self.lang_tag = new_lang
        self.lang_file = os.path.join(
            self.folder, f"{self.lang_tag}.json"
        )
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
