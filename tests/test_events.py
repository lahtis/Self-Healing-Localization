"""
File: tests/test_events.py
Author: Tuomas Lähteenmäki
License: MIT
Description:
    Unit tests for PreloadEvent and LocalizationEngine.preload().

    These tests do not call any translation provider. They use a
    fake translate_text and a temporary directory for locales.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from shl.engine.preload import (
    PreloadEvent,
    KIND_GLFM,
    KIND_LANGUAGE,
    KIND_TRANSLATE,
    KIND_READY,
)


class TestPreloadEvent:
    """Test the PreloadEvent dataclass."""

    def test_phase_fraction_at_start(self):
        event = PreloadEvent(
            kind=KIND_GLFM,
            done=0,
            total=3,
            message="Loading...",
        )
        assert event.phase_fraction == 0.0

    def test_phase_fraction_at_end(self):
        event = PreloadEvent(
            kind=KIND_READY,
            done=3,
            total=3,
            message="Ready.",
        )
        assert event.phase_fraction == 1.0

    def test_phase_fraction_zero_total(self):
        event = PreloadEvent(
            kind=KIND_GLFM,
            done=0,
            total=0,
            message="...",
        )
        assert event.phase_fraction == 1.0

    def test_key_total(self):
        event = PreloadEvent(
            kind=KIND_TRANSLATE,
            done=1,
            total=3,
            message="...",
            translated=12,
            missing=4,
        )
        assert event.key_total == 16

    def test_key_fraction(self):
        event = PreloadEvent(
            kind=KIND_TRANSLATE,
            done=1,
            total=3,
            message="...",
            translated=12,
            missing=4,
        )
        assert event.key_fraction == 12 / 16

    def test_key_fraction_no_keys(self):
        event = PreloadEvent(
            kind=KIND_LANGUAGE,
            done=1,
            total=2,
            message="...",
        )
        assert event.key_fraction == 1.0

    def test_frozen(self):
        event = PreloadEvent(
            kind=KIND_GLFM,
            done=0,
            total=3,
            message="...",
        )
        with pytest.raises(Exception):
            event.kind = "changed"


class TestPreloadGenerator:
    """Test LocalizationEngine.preload() with a fake translator."""

    def test_preload_without_translation(self, tmp_path):
        """Without include_translation, no translate events."""
        from shl.engine.core import LocalizationEngine

        engine = LocalizationEngine(
            lang_code="fi",
            base_lang="en",
            ui_folder=str(tmp_path / "locales"),
            template_folder=str(tmp_path / "prompts"),
        )

        events = list(engine.preload(include_translation=False))
        kinds = [e.kind for e in events]

        assert KIND_GLFM in kinds
        assert KIND_LANGUAGE in kinds
        assert KIND_READY in kinds
        assert KIND_TRANSLATE not in kinds

        # Ready is always last
        assert events[-1].kind == KIND_READY
        assert events[-1].phase_fraction == 1.0

    def test_preload_with_translation(self, tmp_path):
        """With include_translation, translate events are emitted."""
        from shl.engine.core import LocalizationEngine

        engine = LocalizationEngine(
            lang_code="fi",
            base_lang="en",
            ui_folder=str(tmp_path / "locales"),
            template_folder=str(tmp_path / "prompts"),
        )

        # Seed some keys that need translation
        engine.ui_localizer.texts = {
            "Save": "",
            "Cancel": "",
            "Open": "",
        }

        def fake_translate(text, target_lang, source_lang, **kwargs):
            return f"[{target_lang}]{text}"

        with patch(
            "shl.engine.core.translate_text",
            side_effect=fake_translate,
        ):
            events = list(engine.preload(include_translation=True))

        translate_events = [
            e for e in events if e.kind == KIND_TRANSLATE
        ]

        # One initial "Translating N keys" + one per key
        assert len(translate_events) >= 3

        # Keys that were translated are now filled in
        assert engine.ui_localizer.texts["Save"] == "[fi]Save"
        assert engine.ui_localizer.texts["Cancel"] == "[fi]Cancel"
        assert engine.ui_localizer.texts["Open"] == "[fi]Open"

    def test_preload_language_not_supported(self, tmp_path):
        """LanguageNotSupportedError stops translation cleanly."""
        from shl.engine.core import LocalizationEngine
        from shl.engine.translation.exceptions import (
            LanguageNotSupportedError,
        )

        engine = LocalizationEngine(
            lang_code="xx",
            base_lang="en",
            ui_folder=str(tmp_path / "locales"),
            template_folder=str(tmp_path / "prompts"),
        )

        engine.ui_localizer.texts = {"Save": ""}

        with patch(
            "shl.engine.core.translate_text",
            side_effect=LanguageNotSupportedError("pair not supported"),
        ):
            events = list(engine.preload(include_translation=True))

        # No exception leaked out
        assert any(e.kind == KIND_READY for e in events)

        # The failure was reported in a translate event
        messages = [e.message for e in events if e.kind == KIND_TRANSLATE]
        assert any("not supported" in m.lower() for m in messages)

        # The key was left empty
        assert engine.ui_localizer.texts["Save"] == ""

    def test_ready_has_correct_counts(self, tmp_path):
        """The ready event carries final translated/missing counts."""
        from shl.engine.core import LocalizationEngine

        engine = LocalizationEngine(
            lang_code="fi",
            base_lang="en",
            ui_folder=str(tmp_path / "locales"),
            template_folder=str(tmp_path / "prompts"),
        )

        engine.ui_localizer.texts = {
            "Save": "Tallenna",
            "Cancel": "",
        }

        def fake_translate(text, target_lang, source_lang, **kwargs):
            return f"[{target_lang}]{text}"

        with patch(
            "shl.engine.core.translate_text",
            side_effect=fake_translate,
        ):
            events = list(engine.preload(include_translation=True))

        ready = events[-1]
        assert ready.kind == KIND_READY
        assert ready.translated == 2
        assert ready.missing == 0


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
