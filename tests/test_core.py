"""
Tests for LocalizationEngine class.

Tests:
- sync() runs without errors
- template() self-healing with default parameter
- Base language fallback in all lookup paths
- None vs "" consistency
- config.conf handling
- Dynamic language switching
- Region subtag support in engine
"""

import os
import json
import pytest
from shl.engine.core import LocalizationEngine


class TestSyncMethod:
    """Tests for sync() method."""

    def test_sync_runs_without_errors(self, temp_locales_dir, temp_prompts_dir):
        base_file = os.path.join(temp_locales_dir, "en.json")
        with open(base_file, "w", encoding="utf-8") as f:
            json.dump({"greeting": "Hello", "farewell": "Goodbye"}, f)

        base_prompt = os.path.join(temp_prompts_dir, "en.json")
        with open(base_prompt, "w", encoding="utf-8") as f:
            json.dump({"prompt1": "Say {text}"}, f)

        engine = LocalizationEngine(
            lang_code="fi",
            base_lang="en",
            ui_folder=temp_locales_dir,
            template_folder=temp_prompts_dir
        )

        synced = engine.sync()
        assert synced >= 0

        result = engine.ui_text("greeting", "Hello")
        assert result is not None


class TestTemplateMethod:
    """Tests for template() method."""

    def test_template_self_healing_with_default(self, temp_locales_dir, temp_prompts_dir):
        engine = LocalizationEngine(
            lang_code="fi",
            base_lang="en",
            ui_folder=temp_locales_dir,
            template_folder=temp_prompts_dir
        )

        result = engine.template("missing_template", default="Default template")
        assert result == "Default template"

    def test_template_with_kwargs(self, temp_locales_dir, temp_prompts_dir):
        base_prompt = os.path.join(temp_prompts_dir, "en.json")
        with open(base_prompt, "w", encoding="utf-8") as f:
            json.dump({"greeting": "Hello {name}!"}, f)

        engine = LocalizationEngine(
            lang_code="en",
            base_lang="en",
            ui_folder=temp_locales_dir,
            template_folder=temp_prompts_dir
        )

        result = engine.template("greeting", default="Hi!", name="World")
        assert result == "Hello World!"

    def test_template_empty_key(self, temp_locales_dir, temp_prompts_dir):
        engine = LocalizationEngine(
            lang_code="fi",
            ui_folder=temp_locales_dir,
            template_folder=temp_prompts_dir
        )

        result = engine.template("", default="default")
        assert result == "default"


class TestBaseFallbackAllPaths:
    """Tests for base language fallback in all lookup paths."""

    def test_ui_text_fallback(self, temp_locales_dir, temp_prompts_dir):
        base_file = os.path.join(temp_locales_dir, "en.json")
        with open(base_file, "w", encoding="utf-8") as f:
            json.dump({"greeting": "Hello"}, f)

        engine = LocalizationEngine(
            lang_code="fi",
            base_lang="en",
            ui_folder=temp_locales_dir,
            template_folder=temp_prompts_dir
        )

        result = engine.ui_text("greeting", default_value="Default")
        assert result == "Hello"

    def test_template_fallback(self, temp_locales_dir, temp_prompts_dir):
        base_prompt = os.path.join(temp_prompts_dir, "en.json")
        with open(base_prompt, "w", encoding="utf-8") as f:
            json.dump({"test_prompt": "Base template"}, f)

        engine = LocalizationEngine(
            lang_code="fi",
            base_lang="en",
            ui_folder=temp_locales_dir,
            template_folder=temp_prompts_dir
        )

        result = engine.template("test_prompt", default="Default")
        assert result == "Base template"


class TestNoneVsEmpty:
    """Tests for None vs '' consistency."""

    def test_ui_text_with_empty_default(self, temp_locales_dir, temp_prompts_dir):
        engine = LocalizationEngine(
            lang_code="fi",
            ui_folder=temp_locales_dir,
            template_folder=temp_prompts_dir
        )

        result = engine.ui_text("missing", default_value="")
        assert result == ""
        assert result is not None

    def test_ensure_ui_key_empty_key(self, temp_locales_dir, temp_prompts_dir):
        engine = LocalizationEngine(
            lang_code="fi",
            ui_folder=temp_locales_dir,
            template_folder=temp_prompts_dir
        )

        result = engine.ensure_ui_key("", default="test")
        assert result == ""


class TestConfigHandling:
    """Tests for config.conf handling."""

    def test_init_with_config(self, temp_locales_dir, temp_prompts_dir):
        config = {"default_language": "fi", "ai_translation_enabled": True}

        engine = LocalizationEngine(
            config=config,
            ui_folder=temp_locales_dir,
            template_folder=temp_prompts_dir
        )

        assert engine.config == config
        assert engine.lang_code == "fi"

    def test_init_without_lang_code(self, temp_locales_dir, temp_prompts_dir):
        engine = LocalizationEngine(
            lang_code=None,
            ui_folder=temp_locales_dir,
            template_folder=temp_prompts_dir
        )

        assert engine.lang_code is not None
        assert len(engine.lang_code) >= 2


class TestDynamicLanguageSwitching:
    """Tests for dynamic language switching."""

    def test_set_language_updates_engine(self, temp_locales_dir, temp_prompts_dir):
        engine = LocalizationEngine(
            lang_code="en",
            ui_folder=temp_locales_dir,
            template_folder=temp_prompts_dir
        )

        assert engine.lang_code == "en"
        engine.set_language("fi")
        assert engine.lang_code == "fi"

    def test_set_language_with_region(self, temp_locales_dir, temp_prompts_dir):
        engine = LocalizationEngine(
            lang_code="en",
            ui_folder=temp_locales_dir,
            template_folder=temp_prompts_dir
        )

        engine.set_language("zh-TW")
        assert engine.lang_code == "zh-tw"


class TestGetStats:
    """Tests for get_stats() method."""

    def test_get_stats_returns_dict(self, temp_locales_dir, temp_prompts_dir):
        engine = LocalizationEngine(
            lang_code="fi",
            ui_folder=temp_locales_dir,
            template_folder=temp_prompts_dir
        )

        stats = engine.get_stats()
        assert isinstance(stats, dict)
        assert "lang_code" in stats
        assert "base_lang" in stats
        assert "ui_keys_count" in stats
        assert "template_keys_count" in stats
        assert "glfm_loaded" in stats
        assert stats["lang_code"] == "fi"
        assert stats["base_lang"] == "en"
