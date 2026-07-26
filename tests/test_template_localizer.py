"""
Tests for TemplateLocalizer class.

Tests:
- Initialization and template file creation
- Key validation
- Base language fallback
- None vs "" consistency
- Corrupted file handling
- Template variable formatting
"""

import json
import os
import pytest
from shl.engine.template_localizer import TemplateLocalizer


class TestTemplateLocalizerInitialization:
    """Tests for TemplateLocalizer initialization."""

    def test_initialization_creates_folder(self, temp_prompts_dir):
        """Test that initialization creates folder."""
        folder = os.path.join(temp_prompts_dir, "new_prompts")
        localizer = TemplateLocalizer(lang_code="fi", base_lang="en", folder=folder)
        assert os.path.exists(folder)

    def test_initialization_creates_file(self, temp_prompts_dir):
        """Test that initialization creates template file."""
        localizer = TemplateLocalizer(lang_code="fi", base_lang="en", folder=temp_prompts_dir)
        expected_file = os.path.join(temp_prompts_dir, "fi.json")
        assert os.path.exists(expected_file)

    def test_initialization_loads_base_templates(self, temp_prompts_dir, base_en_prompts):
        """Test that base templates are loaded."""
        localizer = TemplateLocalizer(lang_code="fi", base_lang="en", folder=temp_prompts_dir)
        assert "greeting_prompt" in localizer.templates
        assert localizer.templates["greeting_prompt"] == "Say hello to {name}"


class TestTemplateKeyValidation:
    """Tests for template key validation."""

    def test_empty_key(self, temp_prompts_dir):
        """Test empty key."""
        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        result = localizer._validate_key("")
        assert result == ""

    def test_whitespace_key(self, temp_prompts_dir):
        """Test whitespace normalization."""
        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        result = localizer._validate_key("  template_key  ")
        assert result == "template_key"

    def test_none_key(self, temp_prompts_dir):
        """Test None key."""
        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        result = localizer._validate_key(None)
        assert result == ""


class TestTemplateNoneVsEmpty:
    """Tests for None vs '' consistency."""

    def test_set_template_none_converts_to_empty(self, temp_prompts_dir):
        """Test None → '' conversion."""
        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        result = localizer.set_template("test", None)
        assert result == ""
        assert localizer.templates["test"] == ""

    def test_get_template_missing_returns_none(self, temp_prompts_dir):
        """Test that missing template returns None."""
        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        result = localizer.get_template("missing")
        assert result is None


class TestTemplateBaseFallback:
    """Tests for base language fallback in templates."""

    def test_fallback_to_base(self, temp_prompts_dir, base_en_prompts):
        """Test fallback to base template."""
        # Create Finnish file without greeting_prompt
        fi_file = os.path.join(temp_prompts_dir, "fi.json")
        with open(fi_file, "w", encoding="utf-8") as f:
            json.dump({"other_prompt": "Muu prompti"}, f)

        localizer = TemplateLocalizer(lang_code="fi", base_lang="en", folder=temp_prompts_dir)
        result = localizer.get_template("greeting_prompt")
        assert result == "Say hello to {name}"


class TestTemplateFormatting:
    """Tests for template variable formatting."""

    def test_format_template(self, temp_prompts_dir):
        """Test format_template method."""
        localizer = TemplateLocalizer(lang_code="en", folder=temp_prompts_dir)
        localizer.templates["greeting"] = "Hello {name}!"

        result = localizer.format_template("greeting", name="World")
        assert result == "Hello World!"

    def test_format_template_missing_key(self, temp_prompts_dir):
        """Test formatting with missing key."""
        localizer = TemplateLocalizer(lang_code="en", folder=temp_prompts_dir)
        result = localizer.format_template("missing_template", name="World")
        assert result == "missing_template"  # Returns key name as fallback

    def test_format_template_missing_variable(self, temp_prompts_dir):
        """Test formatting with missing variable."""
        localizer = TemplateLocalizer(lang_code="en", folder=temp_prompts_dir)
        localizer.templates["greeting"] = "Hello {name}!"

        result = localizer.format_template("greeting")  # No name variable
        assert result == "Hello {name}!"  # Returns raw template


class TestTemplateCorruptedFile:
    """Tests for corrupted template file handling."""

    def test_corrupted_json_backup(self, temp_prompts_dir):
        """Test backup creation for corrupted file."""
        corrupted_file = os.path.join(temp_prompts_dir, "fi.json")
        with open(corrupted_file, "w", encoding="utf-8") as f:
            f.write("{invalid")

        bak_before = [f for f in os.listdir(temp_prompts_dir) if f.endswith('.bak')]
        TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        bak_after = [f for f in os.listdir(temp_prompts_dir) if f.endswith('.bak')]

        assert len(bak_after) > len(bak_before)


class TestTemplateDictionaryMethods:
    """Tests for dictionary-like methods."""

    def test_contains(self, temp_prompts_dir):
        """Test __contains__."""
        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        localizer.templates["test"] = "arvo"
        assert "test" in localizer
        assert "missing" not in localizer

    def test_getitem(self, temp_prompts_dir):
        """Test __getitem__."""
        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        localizer.templates["test"] = "arvo"
        assert localizer["test"] == "arvo"

    def test_setitem(self, temp_prompts_dir):
        """Test __setitem__."""
        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        localizer["test"] = "arvo"
        assert localizer.templates["test"] == "arvo"

    def test_len(self, temp_prompts_dir):
        """Test __len__."""
        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        localizer.templates["a"] = "1"
        localizer.templates["b"] = "2"
        assert len(localizer) == 2

    def test_keys_values_items(self, temp_prompts_dir):
        """Test keys(), values(), items()."""
        localizer = TemplateLocalizer(lang_code="fi", folder=temp_prompts_dir)
        localizer.templates["a"] = "1"
        localizer.templates["b"] = None

        assert set(localizer.keys()) == {"a", "b"}
        assert "" in localizer.values()
        assert ("b", "") in localizer.items()


class TestTemplateDynamicLanguageSwitching:
    """Tests for dynamic language switching."""

    def test_set_language_changes_lang(self, temp_prompts_dir, base_en_prompts):
        """Test language switching."""
        localizer = TemplateLocalizer(lang_code="en", folder=temp_prompts_dir)
        assert localizer.lang_code == "en"

        localizer.set_language("fi")
        assert localizer.lang_code == "fi"
        expected_file = os.path.join(temp_prompts_dir, "fi.json")
        assert os.path.exists(expected_file)

    def test_set_language_validates_input(self, temp_prompts_dir):
        """Test language switch validation."""
        localizer = TemplateLocalizer(lang_code="en", folder=temp_prompts_dir)
        localizer.set_language("  FI  ")
        assert localizer.lang_code == "fi"
