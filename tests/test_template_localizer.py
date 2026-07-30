# tests/test_template_localizer.py
"""
Tests for TemplateLocalizer class.

Tests:
- Initialization and template file creation
- Key validation
- Base language fallback
- None vs "" consistency
- Corrupted file handling
- Template variable formatting
- Region subtag preservation
- Dynamic language switching
- Dictionary-like methods
"""

import json
import os
import pytest
from shl.engine.template_localizer import TemplateLocalizer


# ---------------------------------------------------------------------------
# Initialization tests
# ---------------------------------------------------------------------------

class TestTemplateLocalizerInitialization:
    """Tests for TemplateLocalizer initialization."""

    def test_initialization_creates_folder(self, temp_prompts_dir):
        """Test that initialization creates folder."""
        folder = os.path.join(temp_prompts_dir, "new_prompts")
        localizer = TemplateLocalizer(lang_code="fi", base_lang="en", folder=folder)
        assert os.path.exists(folder)
        assert localizer.folder == folder

    def test_initialization_creates_file(self, temp_prompts_dir):
        """Test that initialization creates template file."""
        localizer = TemplateLocalizer(lang_code="fi", base_lang="en", folder=temp_prompts_dir)
        expected_file = os.path.join(temp_prompts_dir, "fi.json")
        assert os.path.exists(expected_file)
        assert localizer.lang_file == expected_file

    def test_initialization_loads_base_templates(self, temp_prompts_dir, base_en_prompts):
        """Test that base templates are loaded."""
        localizer = TemplateLocalizer(lang_code="fi", base_lang="en", folder=temp_prompts_dir)
        assert "greeting_prompt" in localizer.templates
        assert localizer.templates["greeting_prompt"] == "Say hello to {name}"
        assert "summary_prompt" in localizer.templates
        assert "test_template" in localizer.templates

    def test_initialization_without_lang(self, temp_prompts_dir):
        """Test initialization without language code."""
        localizer = TemplateLocalizer(base_lang="en", folder=temp_prompts_dir)
        assert localizer.lang_code is not None
        assert localizer.base_lang == "en"

    def test_initialization_with_region_subtag(self, temp_prompts_dir):
        """Test that region subtag is preserved in template file name."""
        localizer = TemplateLocalizer(lang_code="zh-TW", base_lang="en", folder=temp_prompts_dir)
        expected_file = os.path.join(temp_prompts_dir, "zh-tw.json")
        assert os.path.exists(expected_file)
        assert localizer.lang_code == "zh-tw"

    def test_initialization_with_script_subtag(self, temp_prompts_dir):
        """Test that script subtag is preserved in template file name."""
        localizer = TemplateLocalizer(lang_code="zh-Hant-TW", base_lang="en", folder=temp_prompts_dir)
        expected_file = os.path.join(temp_prompts_dir, "zh-hant-tw.json")
        assert os.path.exists(expected_file)
        assert localizer.lang_code == "zh-hant-tw"

    def test_initialization_with_pt_br(self, temp_prompts_dir):
        """Test Brazilian Portuguese gets its own template file."""
        localizer = TemplateLocalizer(lang_code="pt-BR", base_lang="en", folder=temp_prompts_dir)
        expected_file = os.path.join(temp_prompts_dir, "pt-br.json")
        assert os.path.exists(expected_file)

    def test_initialization_with_pt_pt(self, temp_prompts_dir):
        """Test European Portuguese gets its own template file."""
        localizer = TemplateLocalizer(lang_code="pt-PT", base_lang="en", folder=temp_prompts_dir)
        expected_file = os.path.join(temp_prompts_dir, "pt-pt.json")
        assert os.path.exists(expected_file)

    def test_initialization_base_lang_normalized(self, temp_prompts_dir):
        """Test that base language is normalized."""
        localizer = TemplateLocalizer(lang_code="fi", base_lang="en-US", folder=temp_prompts_dir)
        assert localizer.base_lang == "en"

    def test_initialization_detects_language_from_config(self, temp_prompts_dir, monkeypatch):
        """Test language detection from config.conf."""
        # Create config.conf
        with open("config.conf", "w", encoding="utf-8") as f:
            f.write("[SETTINGS]\nlanguage = sv\n")
        
        localizer = TemplateLocalizer(base_lang="en", folder=temp_prompts_dir)
        assert localizer.lang_code == "sv"
        
        # Clean up
        os.remove("config.conf")


# ---------------------------------------------------------------------------
# Key validation tests
# ---------------------------------------------------------------------------

class TestTemplateKeyValidation:
    """Tests for template key validation."""

    def test_empty_key(self, temp_prompts_dir):
        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        result = localizer._validate_key("")
        assert result == ""

    def test_whitespace_key(self, temp_prompts_dir):
        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        result = localizer._validate_key("  template_key  ")
        assert result == "template_key"

    def test_none_key(self, temp_prompts_dir):
        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        result = localizer._validate_key(None)
        assert result == ""

    def test_invalid_key_type(self, temp_prompts_dir):
        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        result = localizer._validate_key(123)
        assert result == ""

    def test_key_with_newlines(self, temp_prompts_dir):
        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        result = localizer._validate_key("key\nwith\nnewlines")
        assert result == "key\nwith\nnewlines"


# ---------------------------------------------------------------------------
# None vs empty tests
# ---------------------------------------------------------------------------

class TestTemplateNoneVsEmpty:
    """Tests for None vs '' consistency."""

    def test_set_template_none_converts_to_empty(self, temp_prompts_dir):
        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        result = localizer.set_template("test", None)
        assert result == ""
        assert localizer.templates["test"] == ""

    def test_get_template_missing_returns_none(self, temp_prompts_dir):
        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        result = localizer.get_template("missing")
        assert result is None

    def test_ensure_key_none_default(self, temp_prompts_dir):
        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        result = localizer.ensure_key("test", None)
        assert result == ""
        assert localizer.templates["test"] == ""

    def test_get_none_default(self, temp_prompts_dir):
        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        result = localizer.get("test", None)
        assert result == ""


# ---------------------------------------------------------------------------
# Base fallback tests
# ---------------------------------------------------------------------------

class TestTemplateBaseFallback:
    """Tests for base language fallback in templates."""

    def test_fallback_to_base(self, temp_prompts_dir, base_en_prompts):
        fi_file = os.path.join(temp_prompts_dir, "fi.json")
        with open(fi_file, "w", encoding="utf-8") as f:
            json.dump({"other_prompt": "Muu prompti"}, f)

        localizer = TemplateLocalizer(lang_code="fi", base_lang="en", folder=temp_prompts_dir)
        result = localizer.get_template("greeting_prompt")
        assert result == "Say hello to {name}"

    def test_no_fallback_when_key_exists(self, temp_prompts_dir, base_en_prompts):
        fi_file = os.path.join(temp_prompts_dir, "fi.json")
        with open(fi_file, "w", encoding="utf-8") as f:
            json.dump({"greeting_prompt": "Terve {name}"}, f)

        localizer = TemplateLocalizer(lang_code="fi", base_lang="en", folder=temp_prompts_dir)
        result = localizer.get_template("greeting_prompt")
        assert result == "Terve {name}"

    def test_fallback_when_base_missing(self, temp_prompts_dir):
        localizer = TemplateLocalizer(lang_code="fi", base_lang="en", folder=temp_prompts_dir)
        result = localizer.get_template("nonexistent")
        assert result is None

    def test_ensure_key_self_healing(self, temp_prompts_dir):
        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        result = localizer.ensure_key("new_template", "Default template")
        assert result == "Default template"
        assert "new_template" in localizer.templates


# ---------------------------------------------------------------------------
# Formatting tests
# ---------------------------------------------------------------------------

class TestTemplateFormatting:
    """Tests for template variable formatting."""

    def test_format_template(self, temp_prompts_dir):
        localizer = TemplateLocalizer(lang_code="en", folder=temp_prompts_dir)
        # Add template before formatting
        localizer.templates["greeting"] = "Hello {name}!"

        result = localizer.format_template("greeting", name="World")
        assert result == "Hello World!"

    def test_format_template_multiple_vars(self, temp_prompts_dir):
        localizer = TemplateLocalizer(lang_code="en", folder=temp_prompts_dir)
        # Add template before formatting
        localizer.templates["greeting"] = "Hello {name}! Welcome to {place}."

        result = localizer.format_template("greeting", name="John", place="Finland")
        assert result == "Hello John! Welcome to Finland."

    def test_format_template_missing_key(self, temp_prompts_dir):
        localizer = TemplateLocalizer(lang_code="en", folder=temp_prompts_dir)
        # Template doesn't exist
        result = localizer.format_template("missing_template", name="World")
        assert result == "missing_template"

    def test_format_template_missing_variable(self, temp_prompts_dir):
        localizer = TemplateLocalizer(lang_code="en", folder=temp_prompts_dir)
        # Add template before formatting
        localizer.templates["greeting"] = "Hello {name}!"

        result = localizer.format_template("greeting")
        assert result == "Hello {name}!"

    def test_format_template_empty_key(self, temp_prompts_dir):
        localizer = TemplateLocalizer(lang_code="en", folder=temp_prompts_dir)
        result = localizer.format_template("", name="World")
        assert result == ""


# ---------------------------------------------------------------------------
# Corrupted file tests
# ---------------------------------------------------------------------------

class TestTemplateCorruptedFile:
    """Tests for corrupted template file handling."""

    def test_corrupted_json_backup(self, temp_prompts_dir):
        corrupted_file = os.path.join(temp_prompts_dir, "fi.json")
        with open(corrupted_file, "w", encoding="utf-8") as f:
            f.write("{invalid")

        bak_before = [f for f in os.listdir(temp_prompts_dir) if f.endswith('.bak')]
        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        bak_after = [f for f in os.listdir(temp_prompts_dir) if f.endswith('.bak')]

        assert len(bak_after) > len(bak_before)
        assert localizer.templates is not None

    def test_corrupted_json_fallback_to_base(self, temp_prompts_dir, base_en_prompts):
        corrupted_file = os.path.join(temp_prompts_dir, "fi.json")
        with open(corrupted_file, "w", encoding="utf-8") as f:
            f.write("{invalid")

        localizer = TemplateLocalizer(lang_code="fi", base_lang="en", folder=temp_prompts_dir)
        # Should fallback to base templates
        assert "greeting_prompt" in localizer.templates
        assert localizer.templates["greeting_prompt"] == "Say hello to {name}"

    def test_empty_json_file(self, temp_prompts_dir):
        empty_file = os.path.join(temp_prompts_dir, "fi.json")
        with open(empty_file, "w", encoding="utf-8") as f:
            f.write("")

        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        assert localizer.templates is not None
        assert isinstance(localizer.templates, dict)


# ---------------------------------------------------------------------------
# Dictionary-like methods tests
# ---------------------------------------------------------------------------

class TestTemplateDictionaryMethods:
    """Tests for dictionary-like methods."""

    def test_contains(self, temp_prompts_dir):
        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        localizer.templates["test"] = "arvo"
        assert "test" in localizer
        assert "missing" not in localizer

    def test_getitem(self, temp_prompts_dir):
        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        localizer.templates["test"] = "arvo"
        assert localizer["test"] == "arvo"

    def test_setitem(self, temp_prompts_dir):
        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        localizer["test"] = "arvo"
        assert localizer.templates["test"] == "arvo"

    def test_len(self, temp_prompts_dir):
        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        localizer.templates["a"] = "1"
        localizer.templates["b"] = "2"
        assert len(localizer) == 2

    def test_keys(self, temp_prompts_dir):
        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        localizer.templates["a"] = "1"
        localizer.templates["b"] = "2"
        assert set(localizer.keys()) == {"a", "b"}

    def test_values(self, temp_prompts_dir):
        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        localizer.templates["a"] = "1"
        localizer.templates["b"] = None
        assert "1" in localizer.values()
        assert "" in localizer.values()

    def test_items(self, temp_prompts_dir):
        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        localizer.templates["a"] = "1"
        localizer.templates["b"] = None
        assert ("a", "1") in localizer.items()
        assert ("b", "") in localizer.items()

    def test_repr(self, temp_prompts_dir):
        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        repr_str = repr(localizer)
        assert "TemplateLocalizer" in repr_str
        assert "fi" in repr_str


# ---------------------------------------------------------------------------
# Dynamic language switching tests
# ---------------------------------------------------------------------------

class TestTemplateDynamicLanguageSwitching:
    """Tests for dynamic language switching."""

    def test_set_language_changes_lang(self, temp_prompts_dir, base_en_prompts):
        localizer = TemplateLocalizer(lang_code="en", folder=temp_prompts_dir)
        assert localizer.lang_code == "en"

        localizer.set_language("fi")
        assert localizer.lang_code == "fi"
        expected_file = os.path.join(temp_prompts_dir, "fi.json")
        assert os.path.exists(expected_file)

    def test_set_language_validates_input(self, temp_prompts_dir):
        localizer = TemplateLocalizer(lang_code="en", folder=temp_prompts_dir)
        localizer.set_language("  FI  ")
        assert localizer.lang_code == "fi"

    def test_set_language_with_region(self, temp_prompts_dir):
        localizer = TemplateLocalizer(lang_code="en", folder=temp_prompts_dir)
        localizer.set_language("zh-TW")
        assert localizer.lang_code == "zh-tw"

    def test_set_language_same_lang(self, temp_prompts_dir):
        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        old_templates = localizer.templates.copy()
        localizer.set_language("fi")
        assert localizer.lang_code == "fi"
        assert localizer.templates == old_templates


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------

class TestTemplateErrorHandling:
    """Tests for error handling in TemplateLocalizer."""

    def test_get_nonexistent_key_returns_none(self, temp_prompts_dir):
        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        result = localizer.get_template("nonexistent")
        assert result is None

    def test_ensure_key_invalid_key(self, temp_prompts_dir):
        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        result = localizer.ensure_key("", "Default")
        assert result == "Default"

    def test_set_template_invalid_key(self, temp_prompts_dir):
        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        result = localizer.set_template("", "Value")
        assert result == ""


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

class TestTemplateIntegration:
    """Integration tests for TemplateLocalizer."""

    def test_full_workflow(self, temp_prompts_dir):
        localizer = TemplateLocalizer(lang_code="fi", base_lang="en", folder=temp_prompts_dir)
        
        # 1. Set template
        localizer.set_template("greeting", "Terve {name}!")
        
        # 2. Get template
        result = localizer.get_template("greeting")
        assert result == "Terve {name}!"
        
        # 3. Format template
        result = localizer.format_template("greeting", name="Maailma")
        assert result == "Terve Maailma!"
        
        # 4. Check key exists
        assert "greeting" in localizer
        
        # 5. Save and reload
        localizer2 = TemplateLocalizer(lang_code="fi", base_lang="en", folder=temp_prompts_dir)
        assert localizer2.get_template("greeting") == "Terve {name}!"

    def test_self_healing(self, temp_prompts_dir):
        localizer = TemplateLocalizer(lang_code="fi", base_lang="en", folder=temp_prompts_dir)
        
        # Missing key should be added
        result = localizer.get("new_template", "Default template")
        assert result == "Default template"
        assert "new_template" in localizer.templates


# ---------------------------------------------------------------------------
# Run tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main(["-v", __file__])
