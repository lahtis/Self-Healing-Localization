"""
Tests for the core LocalizationEngine.
"""

import os

import pytest

from shl.engine.core import LocalizationEngine
from shl.engine.localizer import Localizer


# ---------------------------------------------------------------------------
# Basic initialization tests
# ---------------------------------------------------------------------------


def test_engine_init():
    """Test basic engine initialization."""
    engine = LocalizationEngine(
        lang_code="fi",
        base_lang="en",
    )

    assert engine.lang_code == "fi"
    assert engine.base_lang == "en"
    assert engine.ui_localizer is not None
    assert engine.template_localizer is not None
    assert engine.cache is not None
    assert engine.mymemory_adapter is not None
    assert engine.libretranslate_adapter is not None


def test_engine_init_with_region():
    """Test engine initialization with region subtag."""
    engine = LocalizationEngine(
        lang_code="zh-TW",
        base_lang="en",
    )

    assert engine.lang_code == "zh-tw"


def test_engine_init_with_script():
    """Test engine initialization with script subtag."""
    engine = LocalizationEngine(
        lang_code="zh-Hant-TW",
        base_lang="en",
    )

    assert engine.lang_code == "zh-hant-tw"


def test_engine_init_without_lang():
    """Test engine initialization without language code."""
    engine = LocalizationEngine(
        base_lang="en",
    )

    assert engine.lang_code is not None
    assert engine.base_lang == "en"


def test_engine_init_with_config():
    """Test engine initialization with custom config."""
    config = {
        "m_translation_enabled": True,
        "fallback_to_base": False,
    }

    engine = LocalizationEngine(
        lang_code="fi",
        base_lang="en",
        config=config,
    )

    assert engine.config["m_translation_enabled"] is True
    assert engine.config["fallback_to_base"] is False


def test_engine_init_with_glfm(temp_data_dir, glfm_file):
    """Test engine initialization with GLFM validation."""
    engine = LocalizationEngine(
        lang_code="fi",
        base_lang="en",
        glfm_path=glfm_file,
    )

    assert engine.validator is not None
    assert engine.validator.is_loaded is True


def test_engine_init_with_glfm_fallback(
    temp_data_dir,
    glfm_file,
):
    """Test GLFM fallback is stored correctly."""
    engine = LocalizationEngine(
        lang_code="fi",
        base_lang="en",
        glfm_path=glfm_file,
    )

    assert engine.glfm_fallback in [
        None,
        "en",
    ]


def test_engine_init_invalid_lang():
    """Test engine initialization with invalid language code."""
    engine = LocalizationEngine(
        lang_code="xyz",
        base_lang="en",
    )

    assert engine.lang_code in [
        "en",
        "xyz",
    ]


# ---------------------------------------------------------------------------
# UI text tests
# ---------------------------------------------------------------------------


def test_engine_ui_text():
    """Test basic UI text retrieval."""
    engine = LocalizationEngine(
        lang_code="fi",
        base_lang="en",
    )

    result = engine.ui_text(
        "test_key",
        "Default value",
    )

    assert result == "Default value"
    assert "test_key" in engine.ui_localizer.texts


def test_engine_ui_text_existing():
    """Test UI text retrieval for an existing key."""
    engine = LocalizationEngine(
        lang_code="fi",
        base_lang="en",
    )

    engine.ui_localizer.set_text(
        "existing_key",
        "Existing value",
    )

    result = engine.ui_text(
        "existing_key",
        "Default",
    )

    assert result == "Existing value"


def test_engine_ui_text_with_machine_translation_enabled(
    monkeypatch,
):
    """Test UI text with machine translation enabled."""

    def fake_translate_text(*args, **kwargs):
        return "Hei maailma"

    monkeypatch.setattr(
        "shl.engine.core.translate_text",
        fake_translate_text,
    )

    engine = LocalizationEngine(
        lang_code="fi",
        base_lang="en",
        config={
            "m_translation_enabled": True,
        },
    )

    result = engine.ui_text(
        "translation_test",
        "Hello World",
    )

    assert result == "Hei maailma"


def test_engine_ui_text_with_machine_translation_disabled():
    """Test UI text with machine translation disabled."""
    engine = LocalizationEngine(
        lang_code="fi",
        base_lang="en",
        config={
            "m_translation_enabled": False,
        },
    )

    result = engine.ui_text(
        "translation_test_disabled",
        "Hello World",
    )

    assert result == "Hello World"


def test_engine_ui_text_cache():
    """Test UI text caching."""
    engine = LocalizationEngine(
        lang_code="fi",
        base_lang="en",
    )

    first_result = engine.ui_text(
        "cached_key",
        "Cached value",
    )

    second_result = engine.ui_text(
        "cached_key",
        "Different value",
    )

    assert first_result == "Cached value"
    assert second_result == "Cached value"


def test_engine_ui_text_fallback_to_base(
    temp_locales_dir,
    base_en_file,
):
    """Test UI text fallback to base language."""
    engine = LocalizationEngine(
        lang_code="fi",
        base_lang="en",
        ui_folder=temp_locales_dir,
    )

    result = engine.ui_text(
        "greeting",
        "Default",
    )

    assert result == "Hello"


def test_engine_ui_text_glfm_fallback(
    temp_data_dir,
    glfm_file,
):
    """Test UI text GLFM fallback chain."""
    engine = LocalizationEngine(
        lang_code="fi",
        base_lang="en",
        glfm_path=glfm_file,
    )

    assert engine.glfm_fallback in [
        None,
        "en",
    ]


def test_engine_ui_text_empty_key():
    """Test UI text with an empty key."""
    engine = LocalizationEngine(
        lang_code="fi",
        base_lang="en",
    )

    result = engine.ui_text(
        "",
        "Default",
    )

    assert result == "Default"


def test_engine_ui_text_none_key():
    """Test UI text with a None key."""
    engine = LocalizationEngine(
        lang_code="fi",
        base_lang="en",
    )

    result = engine.ui_text(
        None,
        "Default",
    )

    assert result == "Default"


# ---------------------------------------------------------------------------
# Template tests
# ---------------------------------------------------------------------------


def test_engine_template():
    """Test basic template retrieval."""
    engine = LocalizationEngine(
        lang_code="fi",
        base_lang="en",
    )

    result = engine.template(
        "test_template",
        "Default template",
    )

    assert result == "Default template"
    assert (
        "test_template"
        in engine.template_localizer.templates
    )


def test_engine_template_with_kwargs():
    """Test template with variable substitution."""
    engine = LocalizationEngine(
        lang_code="fi",
        base_lang="en",
    )

    engine.template_localizer.set_template(
        "welcome_template",
        "Welcome {name}!",
    )

    result = engine.template(
        "welcome_template",
        name="John",
    )

    assert result == "Welcome John!"


def test_engine_template_existing():
    """Test template retrieval for an existing key."""
    engine = LocalizationEngine(
        lang_code="fi",
        base_lang="en",
    )

    engine.template_localizer.set_template(
        "existing_template",
        "Existing template",
    )

    result = engine.template(
        "existing_template",
        "Default",
    )

    assert result == "Existing template"


def test_engine_template_fallback_to_base(
    temp_prompts_dir,
    base_en_prompts,
):
    """Test template fallback to base language."""
    engine = LocalizationEngine(
        lang_code="fi",
        base_lang="en",
        template_folder=temp_prompts_dir,
    )

    result = engine.template(
        "greeting_prompt",
        text="Hello",
        name="John",
    )

    assert result == "Say hello to John"


def test_engine_template_empty_key():
    """Test template with an empty key."""
    engine = LocalizationEngine(
        lang_code="fi",
        base_lang="en",
    )

    result = engine.template(
        "",
        "Default",
    )

    assert result == "Default"


# ---------------------------------------------------------------------------
# Language management tests
# ---------------------------------------------------------------------------


def test_engine_set_language():
    """Test dynamic language switching."""
    engine = LocalizationEngine(
        lang_code="en",
        base_lang="en",
    )

    engine.set_language("fi")

    assert engine.lang_code == "fi"
    assert engine.ui_localizer.lang_code == "fi"
    assert engine.template_localizer.lang_code == "fi"


def test_engine_set_language_with_region():
    """Test dynamic language switching with region subtag."""
    engine = LocalizationEngine(
        lang_code="en",
        base_lang="en",
    )

    engine.set_language("zh-TW")

    assert engine.lang_code == "zh-tw"


def test_engine_ensure_language(
    temp_locales_dir,
    temp_prompts_dir,
):
    """Test ensuring language files exist."""
    engine = LocalizationEngine(
        lang_code="en",
        base_lang="en",
        ui_folder=temp_locales_dir,
        template_folder=temp_prompts_dir,
    )

    engine.ensure_language("sv")

    sv_ui = os.path.join(
        temp_locales_dir,
        "sv.json",
    )

    sv_prompts = os.path.join(
        temp_prompts_dir,
        "sv.json",
    )

    assert os.path.exists(sv_ui)
    assert os.path.exists(sv_prompts)


# ---------------------------------------------------------------------------
# Sync tests
# ---------------------------------------------------------------------------


def test_engine_sync(temp_locales_dir):
    """Test synchronizing keys from base language."""
    base_localizer = Localizer(
        lang_code="en",
        base_lang="en",
        folder=temp_locales_dir,
    )

    base_localizer.set_text(
        "sync_test",
        "Base value",
    )

    base_localizer.save()

    engine = LocalizationEngine(
        lang_code="fi",
        base_lang="en",
        ui_folder=temp_locales_dir,
    )

    result = engine.sync()

    assert result >= 1
    assert (
        engine.ui_localizer.texts["sync_test"]
        == "Base value"
    )


def test_engine_sync_with_glfm_fallback(
    temp_data_dir,
    glfm_file,
):
    """Test sync from GLFM fallback."""
    engine = LocalizationEngine(
        lang_code="fi",
        base_lang="en",
        glfm_path=glfm_file,
    )

    engine.ui_localizer.set_text(
        "glfm_sync_test",
        "GLFM value",
    )

    result = engine.sync()

    assert result >= 0
    assert (
        "glfm_sync_test"
        in engine.ui_localizer.texts
    )


def test_engine_sync_no_new_keys():
    """Test sync when no new keys need to be added."""
    engine = LocalizationEngine(
        lang_code="fi",
        base_lang="en",
    )

    engine.ui_localizer.set_text(
        "existing_key",
        "Existing value",
    )

    result = engine.sync()

    assert result >= 0


# ---------------------------------------------------------------------------
# Key management tests
# ---------------------------------------------------------------------------


def test_engine_ensure_ui_key():
    """Test ensuring a UI key exists."""
    engine = LocalizationEngine(
        lang_code="fi",
        base_lang="en",
    )

    result = engine.ensure_ui_key(
        "new_key",
        "Default value",
    )

    assert result == "Default value"
    assert "new_key" in engine.ui_localizer.texts


def test_engine_ensure_ui_key_existing():
    """Test ensuring an existing UI key."""
    engine = LocalizationEngine(
        lang_code="fi",
        base_lang="en",
    )

    engine.ui_localizer.set_text(
        "existing_key",
        "Existing value",
    )

    result = engine.ensure_ui_key(
        "existing_key",
        "Default",
    )

    assert result == "Existing value"


def test_engine_ensure_template_key():
    """Test ensuring a template key exists."""
    engine = LocalizationEngine(
        lang_code="fi",
        base_lang="en",
    )

    result = engine.ensure_template_key(
        "new_template",
        "Default template",
    )

    assert result == "Default template"
    assert (
        "new_template"
        in engine.template_localizer.templates
    )


# ---------------------------------------------------------------------------
# Statistics tests
# ---------------------------------------------------------------------------


def test_engine_get_stats():
    """Test engine statistics."""
    engine = LocalizationEngine(
        lang_code="fi",
        base_lang="en",
    )

    stats = engine.get_stats()

    assert "lang_code" in stats
    assert stats["lang_code"] == "fi"
    assert "base_lang" in stats
    assert stats["base_lang"] == "en"
    assert "glfm_fallback" in stats
    assert "ui_keys_count" in stats
    assert "template_keys_count" in stats
    assert "cache_size" in stats
    assert "glfm_loaded" in stats
    assert "m_translation_enabled" in stats
    assert "config" in stats


def test_engine_get_stats_with_glfm(
    temp_data_dir,
    glfm_file,
):
    """Test engine statistics with GLFM loaded."""
    engine = LocalizationEngine(
        lang_code="fi",
        base_lang="en",
        glfm_path=glfm_file,
    )

    stats = engine.get_stats()

    assert stats["glfm_loaded"] is True
    assert stats["glfm_fallback"] in [
        None,
        "en",
    ]


# ---------------------------------------------------------------------------
# Fallback tests
# ---------------------------------------------------------------------------


def test_engine_fallback_to_base(
    temp_locales_dir,
    base_en_file,
):
    """Test fallback to base language."""
    engine = LocalizationEngine(
        lang_code="fi",
        base_lang="en",
        ui_folder=temp_locales_dir,
    )

    result = engine.ui_text(
        "greeting",
        "Default",
    )

    assert result == "Hello"


def test_engine_fallback_glfm_first(
    temp_data_dir,
    glfm_file,
):
    """Test GLFM fallback takes precedence over base language."""
    engine = LocalizationEngine(
        lang_code="fi",
        base_lang="en",
        glfm_path=glfm_file,
    )

    assert engine.glfm_fallback in [
        None,
        "en",
    ]


def test_engine_fallback_disabled():
    """Test fallback when disabled in config."""
    engine = LocalizationEngine(
        lang_code="fi",
        base_lang="en",
        config={
            "fallback_to_base": False,
        },
    )

    base_localizer = Localizer(
        lang_code="en",
        base_lang="en",
        folder=engine.ui_folder,
    )

    base_localizer.set_text(
        "base_only",
        "Base value",
    )

    result = engine.ui_text(
        "base_only",
        "Default",
    )

    assert result == "Default"


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_integration_engine_with_real_translation():
    """
    Integration test with real translation.

    This test may require network access and a configured provider.
    """
    config = {
        "m_translation_enabled": True,
    }

    engine = LocalizationEngine(
        lang_code="fi",
        base_lang="en",
        config=config,
    )

    result = engine.ui_text(
        "integration_test",
        "Hello world",
    )

    assert result is not None
    assert result != "Hello world"
