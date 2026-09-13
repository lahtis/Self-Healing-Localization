"""
File: shl/engine/translation/memory/memory_manager.py
Author: Tuomas Lähteenmäki
Version: 0.2.10
License: MIT
Description:
    Provider-independent translation memory management for SHL.
"""

import logging
from typing import Any, Dict, Optional

from shl.config.policy_manager import ConfigManager
from .private_mymemory import (
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

    def _get_private_mymemory(
        self,
    ) -> Optional[PrivateMyMemoryBackend]:
        """Return the configured private MyMemory backend."""
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

            self._private_mymemory = PrivateMyMemoryBackend(
                api_key_env=api_key_env,
                space_uuid=settings.get("space_uuid"),
                timeout=timeout,
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

        except MyMemoryError as error:
            logger.warning(
                "Translation memory storage failed: %s",
                error,
            )
            return None

