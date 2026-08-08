"""
File: localizer.py
Author: Tuomas Lähteenmäki
Version: 0.2.0
License: MIT
Description:
    Self-Healing Localizer for UI text.

    - Creates missing language files automatically
    - Adds missing keys on the fly
    - Falls back to default language - controlled by caller
    - Handles corrupted JSON files gracefully
    - Validates and normalizes all keys
    - Migrates legacy file format (lang_xx.json -> xx.json)
    - Preserves region subtags in file names
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

from shl.utils.lang_utils import base_language, normalize_full_tag


logger = logging.getLogger(__name__)


class Localizer:
    """
    Self-Healing Localizer for UI text.

    Uses BCP-47 language tags with region subtag support.
    """

    def __init__(
        self,
        lang_code: Optional[str] = None,
        base_lang: str = "en",
        folder: str = "locales",
    ):
        self.folder = folder
        self._dirty = False
        self._alive = True

        if lang_code is None:
            lang_code = self._detect_language() or base_lang

        self.lang_code = normalize_full_tag(lang_code)

        # Säilytä sekä täydellinen että provider-kutsuissa mahdollisesti
        # tarvittava lyhyt peruskielen tunniste.
        self.base_lang_tag = normalize_full_tag(base_lang)
        self.base_lang = base_language(self.base_lang_tag)

        # Välimuisti muille ladatuille kielille.
        # Aktiivinen self.texts pidetään erillään tästä välimuistista.
        self._loaded_langs: Dict[str, Dict[str, Any]] = {}

        os.makedirs(self.folder, exist_ok=True)

        self.lang_file = os.path.join(
            self.folder,
            f"{self.lang_code}.json",
        )
        self.base_file = os.path.join(
            self.folder,
            f"{self.base_lang_tag}.json",
        )

        self.texts = self._load_or_create()

        # Viimeinen best-effort-varmistus ohjelman sulkeutuessa.
        atexit.register(self._atexit_save)

        logger.debug(
            "Localizer initialized: lang=%s, base=%s, base_tag=%s, keys=%s",
            self.lang_code,
            self.base_lang,
            self.base_lang_tag,
            len(self.texts),
        )

    # ------------------------------------------------------------------
    # Language detection
    # ------------------------------------------------------------------

    def _detect_language(self) -> Optional[str]:
        """
        Detect the language when lang_code was not explicitly provided.

        Priority:
            1. config.conf -> [SETTINGS] language
            2. SHL_LANGUAGE environment variable
            3. LANG environment variable
            4. None
        """
        try:
            import configparser

            if os.path.exists("config.conf"):
                config = configparser.ConfigParser()
                config.read("config.conf", encoding="utf-8")

                language = config.get(
                    "SETTINGS",
                    "language",
                    fallback=None,
                )

                if language:
                    return language.strip()

        except Exception as error:
            logger.debug(
                "Language detection from config.conf failed: %s",
                error,
            )

        environment_language = os.environ.get("SHL_LANGUAGE")
        if environment_language:
            return environment_language.strip()

        raw_language = os.environ.get("LANG", "")
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

        return None

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_key(self, key: str) -> str:
        """Validate and normalize a localization key."""
        if not isinstance(key, str):
            logger.warning("Invalid key type: %s", type(key))
            return ""

        normalized_key = key.strip()

        if not normalized_key:
            logger.debug("Empty key detected")
            return ""

        if normalized_key != key:
            logger.debug(
                "Key normalized: '%s' -> '%s'",
                key,
                normalized_key,
            )

        return normalized_key

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def _invalidate_cache(self) -> None:
        """
        Clear cached language files.

        The active language is stored in self.texts and is not stored in
        _loaded_langs. Clearing the complete cache avoids stale values after
        L() or set_text() changes.
        """
        if self._loaded_langs:
            self._loaded_langs.clear()
            logger.debug("Loaded language cache cleared")

    # ------------------------------------------------------------------
    # File loading
    # ------------------------------------------------------------------

    def _load_json_safe(
        self,
        filepath: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Safely load a JSON dictionary.

        Returns:
            A dictionary, including an empty dictionary for a valid empty
            JSON object.

            None if the file does not exist, is invalid, or cannot be read.
        """
        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as file:
                data = json.load(file)

            if not isinstance(data, dict):
                logger.error(
                    "JSON file does not contain a dictionary: %s",
                    filepath,
                )
                self._backup_corrupted_file(filepath)
                return None

            return data

        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            logger.error(
                "Corrupted JSON file: %s - %s",
                filepath,
                error,
            )
            self._backup_corrupted_file(filepath)
            return None

        except OSError as error:
            logger.error(
                "Could not read JSON file: %s - %s",
                filepath,
                error,
            )
            return None

        except Exception as error:
            logger.error(
                "Unexpected error loading file: %s - %s",
                filepath,
                error,
            )
            return None

    def _backup_corrupted_file(self, filepath: str) -> None:
        """Create a timestamped backup of a corrupted file."""
        try:
            if not os.path.exists(filepath):
                return

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{filepath}.{timestamp}.bak"

            shutil.copy2(filepath, backup_path)

            logger.info(
                "Backup created for corrupted file: %s",
                backup_path,
            )

        except Exception as error:
            logger.error(
                "Backup creation failed for %s: %s",
                filepath,
                error,
            )

    # ------------------------------------------------------------------
    # File saving
    # ------------------------------------------------------------------

    def _save_texts(
        self,
        texts: Dict[str, Any],
        filepath: Optional[str] = None,
    ) -> bool:
        """
        Save texts using an atomic temporary-file replacement.

        Returns:
            True if saving succeeded, otherwise False.
        """
        if filepath is None:
            filepath = self.lang_file

        tmp_path = f"{filepath}.tmp"

        try:
            directory = os.path.dirname(filepath)

            if directory:
                os.makedirs(directory, exist_ok=True)

            with open(tmp_path, "w", encoding="utf-8") as file:
                json.dump(
                    texts,
                    file,
                    indent=4,
                    ensure_ascii=False,
                )
                file.flush()
                os.fsync(file.fileno())

            os.replace(tmp_path, filepath)

            logger.debug(
                "Saved %s keys to %s",
                len(texts),
                filepath,
            )
            return True

        except Exception as error:
            logger.error(
                "Save failed for %s: %s",
                filepath,
                error,
            )

            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception as cleanup_error:
                logger.debug(
                    "Temporary file cleanup failed for %s: %s",
                    tmp_path,
                    cleanup_error,
                )

            return False

    def _save(self) -> bool:
        """Save the active language texts."""
        return self._save_texts(self.texts, self.lang_file)

    def _save_if_dirty(self) -> bool:
        """
        Save only when there are unsaved changes.

        Returns:
            True if there was nothing to save or saving succeeded.
        """
        if not self._dirty:
            return True

        saved = self._save()

        if saved:
            self._dirty = False

        return saved

    def save(self) -> bool:
        """
        Explicitly save pending changes.

        Returns:
            True if saving succeeded or there were no pending changes.
        """
        return self._save_if_dirty()

    def _atexit_save(self) -> None:
        """Final best-effort save when the interpreter exits."""
        if not self._alive or not self._dirty:
            return

        try:
            if self._save():
                self._dirty = False
            else:
                logger.error("Atexit save failed")

        except Exception as error:
            logger.error("Atexit save failed: %s", error)

    def close(self) -> bool:
        """
        Explicitly save and close the Localizer.

        Returns:
            True if closed successfully, otherwise False.
        """
        if not self._alive:
            return True

        if not self._save_if_dirty():
            logger.error(
                "Close failed because pending changes could not be saved"
            )
            return False

        self._alive = False
        return True

    def __del__(self):
        """
        Last-resort cleanup.

        This method is not reliable and must not be used as the primary
        save mechanism. Use save() or close() explicitly.
        """
        try:
            if (
                getattr(self, "_alive", False)
                and getattr(self, "_dirty", False)
                and self._save()
            ):
                self._dirty = False

        except Exception:
            # Destructors must not raise exceptions.
            pass

    def _mark_dirty(self) -> None:
        """Mark the active language data as changed."""
        self._dirty = True

    # ------------------------------------------------------------------
    # Migration
    # ------------------------------------------------------------------

    def _migrate_legacy_file(
        self,
        legacy_path: str,
        new_path: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Migrate lang_xx.json to xx.json.

        The legacy file is intentionally preserved as a backup.
        """
        if not os.path.exists(legacy_path):
            return None

        if legacy_path == new_path:
            return None

        logger.info("Found legacy file: %s", legacy_path)

        legacy_texts = self._load_json_safe(legacy_path)

        if legacy_texts is None:
            return None

        if self._save_texts(legacy_texts, new_path):
            logger.info(
                "Migrated %s keys from '%s' to '%s'",
                len(legacy_texts),
                legacy_path,
                new_path,
            )

            logger.info(
                "Legacy file preserved as a backup: %s",
                legacy_path,
            )

            return legacy_texts

        logger.error(
            "Migration failed from '%s' to '%s'",
            legacy_path,
            new_path,
        )
        return None

    # ------------------------------------------------------------------
    # Load / create
    # ------------------------------------------------------------------

    def _load_or_create(self) -> Dict[str, Any]:
        """
        Load the active language or create it from the base language.
        """
        # 1. Load the current language file.
        if os.path.exists(self.lang_file):
            texts = self._load_json_safe(self.lang_file)

            # {} is a valid result and must not be treated as corruption.
            if texts is not None:
                logger.debug(
                    "Loaded %s keys from file: %s",
                    len(texts),
                    self.lang_file,
                )
                return texts

            logger.warning(
                "Language file could not be loaded, using fallback: %s",
                self.lang_file,
            )

        # 2. Try the legacy language file.
        legacy_file = os.path.join(
            self.folder,
            f"lang_{self.lang_code}.json",
        )

        legacy_texts = self._migrate_legacy_file(
            legacy_file,
            self.lang_file,
        )

        if legacy_texts is not None:
            return legacy_texts

        # 3. Load the base language.
        base_texts: Dict[str, Any] = {}

        if os.path.exists(self.base_file):
            loaded_base_texts = self._load_json_safe(self.base_file)

            if loaded_base_texts is not None:
                base_texts = loaded_base_texts
                logger.info(
                    "Loading from base language: %s (%s keys)",
                    self.base_file,
                    len(base_texts),
                )
            else:
                logger.warning(
                    "Base file could not be loaded: %s",
                    self.base_file,
                )

        else:
            legacy_base = os.path.join(
                self.folder,
                f"lang_{self.base_lang_tag}.json",
            )

            migrated_base = self._migrate_legacy_file(
                legacy_base,
                self.base_file,
            )

            if migrated_base is not None:
                base_texts = migrated_base

        # 4. Always create the missing active language file, including {}.
        if self._save_texts(base_texts, self.lang_file):
            logger.info(
                "Created language file from base: %s",
                self.lang_file,
            )
        else:
            logger.error(
                "Failed to create language file: %s",
                self.lang_file,
            )

        return base_texts

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def L(
        self,
        key: str,
        default: str = "",
    ) -> str:
        """
        Look up a key and create it when missing.

        Changes are kept in memory until save(), close(), or atexit.
        """
        validated_key = self._validate_key(key)

        if not validated_key:
            return default if default else ""

        if validated_key not in self.texts:
            normalized_default = (
                default if default is not None else ""
            )

            self.texts[validated_key] = normalized_default
            self._mark_dirty()
            self._invalidate_cache()

            logger.debug(
                "Added missing key: '%s' = '%s'",
                validated_key,
                normalized_default,
            )

        text = self.texts.get(validated_key, default)

        return text if text is not None else ""

    def get(
        self,
        key: str,
        default: str = "",
    ) -> str:
        """Alias for L()."""
        return self.L(key, default)

    def get_text(
        self,
        key: str,
        lang_code: Optional[str] = None,
        fallback: bool = True,
    ) -> Optional[str]:
        """
        Return text from a selected language.

        The active language is checked first. If fallback is enabled,
        the base language is checked next.
        """
        validated_key = self._validate_key(key)

        if not validated_key:
            return None

        target_lang = normalize_full_tag(
            lang_code or self.lang_code
        )

        text = self._get_text_from_lang(
            validated_key,
            target_lang,
        )

        if text is not None:
            return text

        if fallback and target_lang != self.base_lang_tag:
            logger.debug(
                "UI key '%s' missing, fallback to base language",
                validated_key,
            )

            text = self._get_text_from_lang(
                validated_key,
                self.base_lang_tag,
            )

            if text is not None:
                return text

        return None

    def _get_text_from_lang(
        self,
        key: str,
        lang_code: str,
    ) -> Optional[str]:
        """Load text from a language file using the language cache."""
        try:
            normalized_lang = normalize_full_tag(lang_code)

            if normalized_lang in self._loaded_langs:
                texts = self._loaded_langs[normalized_lang]
                return texts.get(key)

            lang_file = os.path.join(
                self.folder,
                f"{normalized_lang}.json",
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
            logger.error(
                "Error fetching key '%s' from language '%s': %s",
                key,
                lang_code,
                error,
            )
            return None

    def set_text(
        self,
        key: str,
        value: Optional[str],
    ) -> bool:
        """
        Set a text value and mark the active language as dirty.

        Returns:
            True if the value was set, otherwise False.
        """
        validated_key = self._validate_key(key)

        if not validated_key:
            logger.warning("Attempted to set text for empty key")
            return False

        normalized_value = value if value is not None else ""

        self.texts[validated_key] = normalized_value
        self._mark_dirty()
        self._invalidate_cache()

        logger.debug(
            "Set: '%s' = '%s'",
            validated_key,
            normalized_value,
        )

        return True

    def set_language(self, lang_code: str) -> bool:
        """
        Switch active language.

        Pending changes are saved before switching.
        """
        new_lang = normalize_full_tag(lang_code)

        if new_lang == self.lang_code:
            logger.debug(
                "Language already set to: %s",
                new_lang,
            )
            return True

        if not self.save():
            logger.error(
                "Language switch cancelled because current texts "
                "could not be saved: %s",
                self.lang_code,
            )
            return False

        old_lang = self.lang_code

        self.lang_code = new_lang
        self.lang_file = os.path.join(
            self.folder,
            f"{self.lang_code}.json",
        )

        self.texts = self._load_or_create()
        self._invalidate_cache()
        self._dirty = False

        logger.info(
            "Language switched: %s -> %s (%s keys)",
            old_lang,
            new_lang,
            len(self.texts),
        )

        return True

    # ------------------------------------------------------------------
    # Mapping-like API
    # ------------------------------------------------------------------

    def has_key(self, key: str) -> bool:
        """Return True if the active language contains the key."""
        validated_key = self._validate_key(key)

        if not validated_key:
            return False

        return validated_key in self.texts

    def keys(self):
        """Return all localization keys."""
        return list(self.texts.keys())

    def values(self):
        """Return all values with None normalized to empty strings."""
        return [
            value if value is not None else ""
            for value in self.texts.values()
        ]

    def items(self):
        """Return all key-value pairs with None normalized."""
        return [
            (
                key,
                value if value is not None else "",
            )
            for key, value in self.texts.items()
        ]

    def __contains__(self, key: str) -> bool:
        return self.has_key(key)

    def __getitem__(self, key: str) -> str:
        return self.L(key)

    def __setitem__(self, key: str, value: Optional[str]) -> None:
        self.set_text(key, value)

    def __len__(self) -> int:
        return len(self.texts)

    def __repr__(self) -> str:
        return (
            f"Localizer("
            f"lang='{self.lang_code}', "
            f"keys={len(self.texts)}"
            f")"
        )
