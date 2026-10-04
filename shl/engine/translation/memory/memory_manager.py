"""
File: shl/engine/translation/memory/memory_manager.py
Author: Tuomas Lähteenmäki
Version: 0.2.16
License: MIT
Description:
    Provider-independent translation memory management for SHL.
"""

import logging
from typing import Any, Dict, Optional

from shl.config.policy_manager import ConfigManager
from shl.language_parser import LanguageParser

from .private_mymemory import (
    MyMemoryAlreadyExistsError,
    MyMemoryError,
    PrivateMyMemoryBackend,
)


logger = logging.getLogger(__name__)


class MemoryManager:
    """Manage SHL translation memory backends."""

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
    ) -> None:
        self.config_manager = (
            config_manager
            or ConfigManager()
        )

        self.language_parser = LanguageParser()

        self._private_mymemory: Optional[
            PrivateMyMemoryBackend
        ] = None

        self._private_mymemory_disabled = False

    def _get_private_mymemory(
        self,
    ) -> Optional[PrivateMyMemoryBackend]:
        """Return the configured private MyMemory backend."""
        if self._private_mymemory_disabled:
            return None

        settings = self.config_manager.get_memory_settings(
            "private_mymemory"
        )

        if not settings.get("enabled", False):
            return None

        if self._private_mymemory is None:
            timeout = int(settings.get("timeout", 30))

            api_key_env = settings.get(
                "requires_env",
                "MYMEMORY_API_KEY",
            )

            configured_uuid = settings.get("space_uuid")
            space_name = settings.get(
                "space_name",
                "SHL Private Memory",
            )

            self._private_mymemory = PrivateMyMemoryBackend(
                api_key_env=api_key_env,
                space_uuid=configured_uuid,
                timeout=timeout,
            )

            resolved_uuid = self._private_mymemory.ensure_space(
                name=space_name,
            )

            if resolved_uuid != configured_uuid:
                self.config_manager.set_memory_setting(
                    "private_mymemory",
                    "space_uuid",
                    resolved_uuid,
                )

        return self._private_mymemory

    def search_translation(
        self,
        source_text: str,
        source_lang: str,
        target_lang: str,
    ) -> Optional[str]:
        """
        Search the private translation memory for an exact source
        text and matching language pair.

        MyMemory.dev performs the semantic search. SHL then validates
        the returned memory entries against the canonical language
        pair and stored source text before accepting a translation.

        Returns:
            The stored translation if a suitable memory entry exists.
            None if no suitable entry is found or memory is disabled.
        """
        try:
            backend = self._get_private_mymemory()

            if backend is None:
                return None

            language_pair = self.language_parser.normalize_pair(
                source_lang,
                target_lang,
            )

            results = backend.search(
                query=source_text,
                space_uuid=backend.space_uuid,
            )

            for result in results:
                content = self._extract_memory_content(result)

                if not content:
                    continue

                memory = self._parse_memory_content(content)

                if memory is None:
                    continue

                stored_source_lang = memory["source_language"]
                stored_target_lang = memory["target_language"]
                stored_source = memory["source"]
                translation = memory["translation"]

                try:
                    stored_pair = self.language_parser.normalize_pair(
                        stored_source_lang,
                        stored_target_lang,
                    )
                except (TypeError, ValueError):
                    logger.debug(
                        "Ignoring memory entry with unknown "
                        "language pair: %s -> %s",
                        stored_source_lang,
                        stored_target_lang,
                    )
                    continue

                if stored_pair != language_pair:
                    continue

                if stored_source.strip() != source_text.strip():
                    continue

                if not translation:
                    continue

                logger.debug(
                    "Translation memory hit: %s",
                    language_pair,
                )

                return translation

            logger.debug(
                "No translation memory hit for language pair '%s'.",
                language_pair,
            )

            return None

        except MyMemoryError as error:
            error_text = str(error)

            if "Space limit reached" in error_text:
                self._private_mymemory_disabled = True

                logger.warning(
                    "MyMemory.dev memory disabled for this session: "
                    "space limit reached."
                )

                return None

            logger.warning(
                "MyMemory.dev translation memory search failed: %s",
                error,
            )

            return None

        except (TypeError, ValueError) as error:
            logger.warning(
                "Translation memory search validation failed: %s",
                error,
            )

            return None

    @staticmethod
    def _extract_memory_content(
        result: Any,
    ) -> Optional[str]:
        """
        Extract memory content from a MyMemory.dev search result.
        """
        if isinstance(result, str):
            return result

        if not isinstance(result, dict):
            return None

        content = result.get("content")

        if isinstance(content, str):
            return content

        memory = result.get("memory")

        if isinstance(memory, dict):
            content = memory.get("content")

            if isinstance(content, str):
                return content

        return None

    @staticmethod
    def _parse_memory_content(
        content: str,
    ) -> Optional[Dict[str, str]]:
        """
        Parse SHL translation memory content.

        Expected format:

            Source language: ...
            Target language: ...
            Source: ...
            Translation: ...
        """
        values: Dict[str, str] = {}

        prefixes = {
            "source_language": "Source language:",
            "target_language": "Target language:",
            "source": "Source:",
            "translation": "Translation:",
        }

        lines = content.splitlines()

        for line in lines:
            for key, prefix in prefixes.items():
                if line.startswith(prefix):
                    values[key] = line[len(prefix):].strip()
                    break

        required = (
            "source_language",
            "target_language",
            "source",
            "translation",
        )

        if not all(values.get(key) for key in required):
            return None

        return values

    def store_translation(
        self,
        source_text: str,
        translated_text: str,
        source_lang: str,
        target_lang: str,
    ) -> Optional[Dict[str, Any]]:
        """Store a successful translation in the enabled memory backend."""
        try:
            backend = self._get_private_mymemory()

            if backend is None:
                return None

            content = (
                f"Source language: {source_lang}\n"
                f"Target language: {target_lang}\n"
                f"Source: {source_text}\n"
                f"Translation: {translated_text}"
            )

            return backend.add_memory(
                content=content,
                memory_type="note",
            )

        except MyMemoryAlreadyExistsError:
            # The translation was already stored.
            # This is normal when the same text is translated again.
            logger.debug(
                "Translation already exists in MyMemory.dev, skipping"
            )

            return None

        except MyMemoryError as error:
            error_text = str(error)

            if "Space limit reached" in error_text:
                self._private_mymemory_disabled = True

                logger.warning(
                    "MyMemory.dev memory disabled for this session: "
                    "space limit reached."
                )

                return None

            logger.warning(
                "MyMemory.dev Translation memory storage failed: %s",
                error,
            )

            return None


