"""
Tests for Localizer class.

Tests:
- Initialization and language file creation
- Key validation and normalization
- Base language fallback
- None vs "" consistency
- Corrupted file handling
- Backup creation
- Dynamic language switching
- Legacy file migration
"""

import json
import os
import pytest
from shl.engine.localizer import Localizer


class TestLocalizerInitialization:
    """Tests for Localizer initialization."""

    def test_initialization_creates_folder(self, temp_locales_dir):
        """Test that initialization creates folder if it doesn't exist."""
        folder = os.path.join(temp_locales_dir, "new_locales")
        localizer = Localizer(lang_code="fi", base_lang="en", folder=folder)
        assert os.path.exists(folder)

    def test_initialization_creates_file(self, temp_locales_dir):
        """Test that initialization creates language file."""
        localizer = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
        expected_file = os.path.join(temp_locales_dir, "fi.json")
        assert os.path.exists(expected_file)

    def test_initialization_with_none_lang(self, temp_locales_dir):
        """Test initialization with lang_code=None."""
        localizer = Localizer(lang_code=None, base_lang="en", folder=temp_locales_dir)
        assert localizer.lang_code in ["en", "fi"]

    def test_initialization_loads_existing_file(self, temp_locales_dir, base_en_file):
        """Test that existing file is loaded."""
        localizer = Localizer(lang_code="en", base_lang="en", folder=temp_locales_dir)
        assert "greeting" in localizer.texts
        assert localizer.texts["greeting"] == "Hello"

    def test_initialization_migrates_legacy_file(self, temp_locales_dir):
        """Test that legacy lang_xx.json is migrated to xx.json."""
        # Create legacy format file
        legacy_file = os.path.join(temp_locales_dir, "lang_fi.json")
        legacy_data = {"greeting": "Moi", "farewell": "Näkemiin"}
        with open(legacy_file, "w", encoding="utf-8") as f:
            json.dump(legacy_data, f, ensure_ascii=False, indent=4)

        localizer = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)

        # New format should exist
        new_file = os.path.join(temp_locales_dir, "fi.json")
        assert os.path.exists(new_file)
        assert localizer.texts["greeting"] == "Moi"
        assert localizer.texts["farewell"] == "Näkemiin"


class TestKeyValidation:
    """Tests for key validation."""

    def test_normal_key(self, temp_locales_dir):
        """Test normal key."""
        localizer = Localizer(lang_code="fi", folder=temp_locales_dir)
        result = localizer._validate_key("normal_key")
        assert result == "normal_key"

    def test_key_with_whitespace(self, temp_locales_dir):
        """Test whitespace normalization."""
        localizer = Localizer(lang_code="fi", folder=temp_locales_dir)
        result = localizer._validate_key("  spaced_key  ")
        assert result == "spaced_key"

    def test_empty_key(self, temp_locales_dir):
        """Test empty key."""
        localizer = Localizer(lang_code="fi", folder=temp_locales_dir)
        result = localizer._validate_key("")
        assert result == ""

    def test_whitespace_only_key(self, temp_locales_dir):
        """Test whitespace-only key."""
        localizer = Localizer(lang_code="fi", folder=temp_locales_dir)
        result = localizer._validate_key("   ")
        assert result == ""

    def test_non_string_key(self, temp_locales_dir):
        """Test non-string key."""
        localizer = Localizer(lang_code="fi", folder=temp_locales_dir)
        result = localizer._validate_key(None)
        assert result == ""
        result = localizer._validate_key(123)
        assert result == ""


class TestNoneVsEmptyString:
    """Tests for None vs '' consistency."""

    def test_get_text_returns_empty_string_not_none(self, temp_locales_dir):
        """Test that get_text returns '' not None for empty values."""
        localizer = Localizer(lang_code="fi", folder=temp_locales_dir)
        localizer.texts["empty_value"] = ""
        result = localizer.get_text("empty_value")
        assert result == ""
        assert result is not None

    def test_set_text_converts_none_to_empty(self, temp_locales_dir):
        """Test that set_text converts None to empty string."""
        localizer = Localizer(lang_code="fi", folder=temp_locales_dir)
        localizer.set_text("test_key", None)
        assert localizer.texts["test_key"] == ""

    def test_L_returns_empty_not_none(self, temp_locales_dir):
        """Test that L() returns '' not None."""
        localizer = Localizer(lang_code="fi", folder=temp_locales_dir)
        result = localizer.L("nonexistent", default="")
        assert result == ""
        assert result is not None

    def test_missing_key_returns_none(self, temp_locales_dir):
        """Test that missing key returns None from get_text."""
        localizer = Localizer(lang_code="fi", folder=temp_locales_dir)
        result = localizer.get_text("missing_key")
        assert result is None


class TestBaseFallback:
    """Tests for base language fallback."""

    def test_fallback_to_base_when_missing(self, temp_locales_dir, base_en_file):
        """Test fallback to base language when translation is missing."""
        # Create Finnish file without greeting key
        fi_file = os.path.join(temp_locales_dir, "fi.json")
        with open(fi_file, "w", encoding="utf-8") as f:
            json.dump({"farewell": "Näkemiin"}, f)

        localizer = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)

        # greeting missing in Finnish → fallback to English
        result = localizer.get_text("greeting")
        assert result == "Hello"

    def test_no_fallback_when_same_lang(self, temp_locales_dir, base_en_file):
        """Test no fallback when language is the same."""
        localizer = Localizer(lang_code="en", base_lang="en", folder=temp_locales_dir)
        result = localizer.get_text("nonexistent_key")
        assert result is None

    def test_fallback_returns_none_when_base_missing(self, temp_locales_dir):
        """Test fallback returns None when base is also missing."""
        localizer = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
        result = localizer.get_text("completely_missing")
        assert result is None


class TestCorruptedFileHandling:
    """Tests for corrupted file handling."""

    def test_corrupted_json_returns_empty_dict(self, corrupted_file):
        """Test that corrupted JSON returns empty dict."""
        folder = os.path.dirname(corrupted_file)
        localizer = Localizer(lang_code="fi", base_lang="en", folder=folder)
        assert localizer.texts == {}

    def test_corrupted_json_creates_backup(self, corrupted_file):
        """Test that corrupted file creates backup."""
        folder = os.path.dirname(corrupted_file)

        bak_files_before = [f for f in os.listdir(folder) if f.endswith('.bak')]

        Localizer(lang_code="fi", base_lang="en", folder=folder)

        bak_files_after = [f for f in os.listdir(folder) if f.endswith('.bak')]
        assert len(bak_files_after) > len(bak_files_before)

    def test_empty_file_handled(self, empty_file):
        """Test empty file handling."""
        folder = os.path.dirname(empty_file)
        localizer = Localizer(lang_code="sv", base_lang="en", folder=folder)
        assert isinstance(localizer.texts, dict)

    def test_load_json_safe_with_missing_file(self, temp_locales_dir):
        """Test _load_json_safe with missing file."""
        localizer = Localizer(lang_code="fi", folder=temp_locales_dir)
        result = localizer._load_json_safe("nonexistent.json")
        assert result == {}


class TestSelfHealing:
    """Tests for self-healing behavior."""

    def test_missing_key_added_automatically(self, temp_locales_dir):
        """Test that missing key is added automatically."""
        localizer = Localizer(lang_code="fi", folder=temp_locales_dir)
        result = localizer.L("new_key", default="Uusi arvo")
        assert result == "Uusi arvo"
        assert "new_key" in localizer.texts

    def test_set_text_saves(self, temp_locales_dir):
        """Test that set_text saves to file."""
        localizer = Localizer(lang_code="fi", folder=temp_locales_dir)
        localizer.set_text("test_key", "test_value")

        # Load file and verify
        with open(localizer.lang_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["test_key"] == "test_value"


class TestDynamicLanguageSwitching:
    """Tests for dynamic language switching."""

    def test_set_language_changes_lang(self, temp_locales_dir, base_en_file):
        """Test language switching."""
        localizer = Localizer(lang_code="en", folder=temp_locales_dir)
        assert localizer.lang_code == "en"

        localizer.set_language("fi")
        assert localizer.lang_code == "fi"
        expected_file = os.path.join(temp_locales_dir, "fi.json")
        assert os.path.exists(expected_file)

    def test_set_language_validates_input(self, temp_locales_dir):
        """Test language switch validation."""
        localizer = Localizer(lang_code="en", folder=temp_locales_dir)
        localizer.set_language("  FI  ")
        assert localizer.lang_code == "fi"


class TestDictionaryMethods:
    """Tests for dictionary-like methods."""

    def test_contains(self, temp_locales_dir):
        """Test __contains__."""
        localizer = Localizer(lang_code="fi", folder=temp_locales_dir)
        localizer.texts["test"] = "arvo"
        assert "test" in localizer
        assert "missing" not in localizer

    def test_getitem(self, temp_locales_dir):
        """Test __getitem__."""
        localizer = Localizer(lang_code="fi", folder=temp_locales_dir)
        localizer.texts["test"] = "arvo"
        assert localizer["test"] == "arvo"

    def test_setitem(self, temp_locales_dir):
        """Test __setitem__."""
        localizer = Localizer(lang_code="fi", folder=temp_locales_dir)
        localizer["test"] = "arvo"
        assert localizer.texts["test"] == "arvo"

    def test_len(self, temp_locales_dir):
        """Test __len__."""
        localizer = Localizer(lang_code="fi", folder=temp_locales_dir)
        localizer.texts["a"] = "1"
        localizer.texts["b"] = "2"
        assert len(localizer) == 2

    def test_keys_values_items(self, temp_locales_dir):
        """Test keys(), values(), items()."""
        localizer = Localizer(lang_code="fi", folder=temp_locales_dir)
        localizer.texts["a"] = "1"
        localizer.texts["b"] = None

        assert set(localizer.keys()) == {"a", "b"}
        assert "" in localizer.values()
        assert ("b", "") in localizer.items()
