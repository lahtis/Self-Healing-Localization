"""
File: tests/test_memory_manager.py
Author: Tuomas Lähteenmäki
Version: 0.2.10
License: MIT
Description:
    Tests for the SHL translation memory manager.
"""

from unittest.mock import MagicMock

from shl.engine.translation.memory.memory_manager import MemoryManager
from shl.config.policy_manager import ConfigManager


def test_store_translation():
    """Test storing a successful translation."""

    config_manager = MagicMock()

    config_manager.get_memory_settings.return_value = {
        "enabled": True,
        "requires_env": "MYMEMORY_API_KEY",
        "space_name": "SHL Test Space",
        "space_uuid": "T5x1ovmY6m",
        "timeout": "12",
    }

    manager = MemoryManager(
        config_manager=config_manager,
    )

    backend = MagicMock()
    backend.add_memory.return_value = {
        "id": "test-memory-id",
        "content": "stored",
    }

    manager._private_mymemory = backend

    result = manager.store_translation(
        source_text="Guestbook",
        translated_text="Vieraskirja",
        source_lang="en",
        target_lang="fi",
    )

    assert result == {
        "id": "test-memory-id",
        "content": "stored",
    }

    backend.add_memory.assert_called_once()

    call = backend.add_memory.call_args

    assert call.kwargs["memory_type"] == "note"

    content = call.kwargs["content"]

    assert "Source language: en" in content
    assert "Target language: fi" in content
    assert "Source: Guestbook" in content
    assert "Translation: Vieraskirja" in content

def test_store_translation_when_memory_disabled():
    """Test that disabled memory does not store translations."""

    config_manager = MagicMock()

    config_manager.get_memory_settings.return_value = {
        "enabled": False,
        "space_uuid": "T5x1ovmY6m",
        "timeout": 12,
    }

    manager = MemoryManager(
        config_manager=config_manager,
    )

    backend = MagicMock()
    manager._private_mymemory = backend

    result = manager.store_translation(
        source_text="Guestbook",
        translated_text="Vieraskirja",
        source_lang="en",
        target_lang="fi",
    )

    assert result is None
    backend.add_memory.assert_not_called()


def test_store_translation_passes_correct_content():
    """Test that translation data is passed to the memory backend."""

    config_manager = MagicMock()

    config_manager.get_memory_settings.return_value = {
        "enabled": True,
        "space_uuid": "T5x1ovmY6m",
    }

    manager = MemoryManager(
        config_manager=config_manager,
    )

    backend = MagicMock()
    manager._private_mymemory = backend

    manager.store_translation(
        source_text="Hello world",
        translated_text="Hei maailma",
        source_lang="en",
        target_lang="fi",
    )

    backend.add_memory.assert_called_once_with(
        content=(
            "Source language: en\n"
            "Target language: fi\n"
            "Source: Hello world\n"
            "Translation: Hei maailma"
        ),
        memory_type="note",
    )


def test_store_translation_returns_backend_result():
    """Test that the backend result is returned unchanged."""

    config_manager = MagicMock()

    config_manager.get_memory_settings.return_value = {
        "enabled": True,
        "space_uuid": "T5x1ovmY6m",
        "timeout": "12",
    }

    manager = MemoryManager(
        config_manager=config_manager,
    )

    expected = {
        "id": "memory-123",
        "content": "stored",
    }

    backend = MagicMock()
    backend.add_memory.return_value = expected

    manager._private_mymemory = backend

    result = manager.store_translation(
        source_text="Saved: {}",
        translated_text="Tallennettu: {}",
        source_lang="en",
        target_lang="fi",
    )

    assert result is expected



def test_store_translation_with_real_mymemory():
    """Test storing a translation in the real MyMemory.dev test space."""

    import uuid

    config_manager = ConfigManager()

    settings = config_manager.get_memory_settings(
        "private_mymemory"
    )

    assert settings.get("enabled") is True
    assert settings.get("space_uuid")
    assert settings.get("timeout")

    manager = MemoryManager(
        config_manager=config_manager,
    )

    source_text = f"SHL memory integration test {uuid.uuid4()}"

    result = manager.store_translation(
        source_text=source_text,
        translated_text="SHL-muistin integraatiotesti",
        source_lang="en",
        target_lang="fi",
    )

    assert result is not None

def test_private_mymemory_uses_configured_timeout():
    """Test that the configured memory timeout is passed to the backend."""

    config_manager = MagicMock()

    config_manager.get_memory_settings.return_value = {
        "enabled": True,
        "space_uuid": "T5x1ovmY6m",
        "timeout": "12",
    }

    manager = MemoryManager(
        config_manager=config_manager,
    )

    backend = manager._get_private_mymemory()

    assert backend is not None
    assert backend.timeout == 12

