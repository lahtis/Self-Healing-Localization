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


