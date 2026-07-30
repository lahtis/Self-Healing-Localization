# tests/test_localizer.py
"""
Tests for the Localizer class (UI text localization).
"""

import pytest
import os
import json
import tempfile
from shl.engine.localizer import Localizer


# ---------------------------------------------------------------------------
# Basic initialization tests
# ---------------------------------------------------------------------------

def test_localizer_init(temp_locales_dir):
    """Test basic localizer initialization."""
    loc = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    assert loc.lang_code == "fi"
    assert loc.base_lang == "en"
    assert os.path.exists(os.path.join(temp_locales_dir, "fi.json"))


def test_localizer_init_without_lang(temp_locales_dir):
    """Test localizer initialization without language code."""
    loc = Localizer(base_lang="en", folder=temp_locales_dir)
    assert loc.lang_code == "en" or loc.lang_code is not None


def test_localizer_init_with_region(temp_locales_dir):
    """Test localizer initialization with region subtag."""
    loc = Localizer(lang_code="zh-TW", base_lang="en", folder=temp_locales_dir)
    assert loc.lang_code == "zh-tw"
    assert os.path.exists(os.path.join(temp_locales_dir, "zh-tw.json"))


def test_localizer_init_with_script(temp_locales_dir):
    """Test localizer initialization with script subtag."""
    loc = Localizer(lang_code="zh-Hant-TW", base_lang="en", folder=temp_locales_dir)
    assert loc.lang_code == "zh-hant-tw"


def test_localizer_init_with_base_region(temp_locales_dir):
    """Test localizer with base language region."""
    loc = Localizer(lang_code="fi", base_lang="en-US", folder=temp_locales_dir)
    assert loc.base_lang == "en"


def test_localizer_init_with_legacy_file(temp_locales_dir, legacy_file):
    """Test localizer with legacy file format (lang_xx.json)."""
    loc = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    
    # Check that key was migrated
    assert "greeting" in loc.texts
    assert loc.texts["greeting"] == "Terve"
    
    # Check that new file exists
    new_path = os.path.join(temp_locales_dir, "fi.json")
    assert os.path.exists(new_path)


def test_localizer_init_with_corrupted_file(temp_locales_dir, corrupted_file):
    """Test localizer with corrupted JSON file."""
    loc = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    
    # Should handle gracefully and create backup
    assert loc.texts is not None
    assert isinstance(loc.texts, dict)
    
    # Check that backup was created
    backup_files = [f for f in os.listdir(temp_locales_dir) if f.startswith("fi.json.") and f.endswith(".bak")]
    assert len(backup_files) > 0


def test_localizer_init_with_empty_file(temp_locales_dir, empty_file):
    """Test localizer with empty JSON file."""
    loc = Localizer(lang_code="sv", base_lang="en", folder=temp_locales_dir)
    
    # Should handle gracefully
    assert loc.texts is not None
    assert isinstance(loc.texts, dict)


def test_localizer_init_with_base_file(temp_locales_dir, base_en_file):
    """Test localizer using base language file."""
    loc = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    
    # Should copy base file
    assert os.path.exists(os.path.join(temp_locales_dir, "fi.json"))
    assert len(loc.texts) > 0


# ---------------------------------------------------------------------------
# Language switching tests
# ---------------------------------------------------------------------------

def test_localizer_set_language(temp_locales_dir, base_en_file):
    """Test dynamic language switching."""
    loc = Localizer(lang_code="en", base_lang="en", folder=temp_locales_dir)
    loc.set_language("fi")
    
    assert loc.lang_code == "fi"
    assert loc.lang_file == os.path.join(temp_locales_dir, "fi.json")


def test_localizer_set_language_with_region(temp_locales_dir):
    """Test language switching with region subtag."""
    loc = Localizer(lang_code="en", base_lang="en", folder=temp_locales_dir)
    loc.set_language("zh-TW")
    
    assert loc.lang_code == "zh-tw"


def test_localizer_set_language_same(temp_locales_dir):
    """Test switching to the same language."""
    loc = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    old_texts = loc.texts.copy()
    
    loc.set_language("fi")
    
    assert loc.lang_code == "fi"
    assert loc.texts == old_texts


# ---------------------------------------------------------------------------
# Text retrieval tests
# ---------------------------------------------------------------------------

def test_localizer_L(temp_locales_dir):
    """Test L() method (self-healing key lookup)."""
    loc = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    result = loc.L("test_key", "Default")
    
    assert result == "Default"
    assert "test_key" in loc.texts


def test_localizer_L_existing(temp_locales_dir):
    """Test L() with existing key."""
    loc = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    loc.set_text("existing_key", "Existing value")
    
    result = loc.L("existing_key", "Default")
    assert result == "Existing value"


def test_localizer_L_empty_key(temp_locales_dir):
    """Test L() with empty key."""
    loc = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    result = loc.L("", "Default")
    assert result == "Default"


def test_localizer_L_none_value(temp_locales_dir):
    """Test L() with None default value."""
    loc = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    result = loc.L("test_key", None)
    assert result == ""


def test_localizer_get(temp_locales_dir):
    """Test get() method (alias for L)."""
    loc = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    result = loc.get("test_key", "Default")
    
    assert result == "Default"
    assert "test_key" in loc.texts


def test_localizer_get_text(temp_locales_dir):
    """Test get_text() method."""
    loc = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    loc.set_text("test_key", "Test value")
    
    result = loc.get_text("test_key")
    assert result == "Test value"


def test_localizer_get_text_missing(temp_locales_dir):
    """Test get_text() with missing key."""
    loc = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    result = loc.get_text("missing_key")
    assert result is None


def test_localizer_get_text_with_lang(temp_locales_dir, base_en_file):
    """Test get_text() with specific language."""
    loc = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    
    # Add key to base language
    base_loc = Localizer(lang_code="en", base_lang="en", folder=temp_locales_dir)
    base_loc.set_text("base_key", "Base value")
    
    # Get from specific language
    result = loc.get_text("base_key", lang_code="en")
    assert result == "Base value"


def test_localizer_get_text_fallback(temp_locales_dir, base_en_file):
    """Test get_text() fallback to base language."""
    loc = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    
    # Base language has "greeting": "Hello"
    result = loc.get_text("greeting")
    assert result == "Hello"


def test_localizer_get_text_no_fallback(temp_locales_dir):
    """Test get_text() with no fallback."""
    loc = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    
    # Key doesn't exist anywhere
    result = loc.get_text("nonexistent_key")
    assert result is None


# ---------------------------------------------------------------------------
# Text setting tests
# ---------------------------------------------------------------------------

def test_localizer_set_text(temp_locales_dir):
    """Test set_text() method."""
    loc = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    loc.set_text("test_key", "Test value")
    
    assert "test_key" in loc.texts
    assert loc.texts["test_key"] == "Test value"


def test_localizer_set_text_empty_key(temp_locales_dir):
    """Test set_text() with empty key."""
    loc = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    loc.set_text("", "Value")
    
    assert "" not in loc.texts


def test_localizer_set_text_none_value(temp_locales_dir):
    """Test set_text() with None value."""
    loc = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    loc.set_text("test_key", None)
    
    assert "test_key" in loc.texts
    assert loc.texts["test_key"] == ""


# ---------------------------------------------------------------------------
# Key existence tests
# ---------------------------------------------------------------------------

def test_localizer_has_key(temp_locales_dir):
    """Test has_key() method."""
    loc = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    loc.set_text("existing_key", "Value")
    
    assert loc.has_key("existing_key") is True
    assert loc.has_key("missing_key") is False


def test_localizer_has_key_empty(temp_locales_dir):
    """Test has_key() with empty key."""
    loc = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    assert loc.has_key("") is False


def test_localizer_contains(temp_locales_dir):
    """Test __contains__ magic method."""
    loc = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    loc.set_text("existing_key", "Value")
    
    assert "existing_key" in loc
    assert "missing_key" not in loc


# ---------------------------------------------------------------------------
# Collection tests
# ---------------------------------------------------------------------------

def test_localizer_keys(temp_locales_dir):
    """Test keys() method."""
    loc = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    loc.set_text("key1", "value1")
    loc.set_text("key2", "value2")
    
    keys = loc.keys()
    assert "key1" in keys
    assert "key2" in keys
    assert len(keys) >= 2


def test_localizer_values(temp_locales_dir):
    """Test values() method."""
    loc = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    loc.set_text("key1", "value1")
    loc.set_text("key2", "value2")
    
    values = loc.values()
    assert "value1" in values
    assert "value2" in values


def test_localizer_values_with_none(temp_locales_dir):
    """Test values() with None values (should be normalized to '')."""
    loc = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    loc.set_text("key1", None)
    loc.set_text("key2", "value2")
    
    values = loc.values()
    assert "" in values  # None normalized to ''
    assert "value2" in values


def test_localizer_items(temp_locales_dir):
    """Test items() method."""
    loc = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    loc.set_text("key1", "value1")
    loc.set_text("key2", "value2")
    
    items = loc.items()
    assert ("key1", "value1") in items
    assert ("key2", "value2") in items


def test_localizer_len(temp_locales_dir):
    """Test __len__ magic method."""
    loc = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    loc.set_text("key1", "value1")
    loc.set_text("key2", "value2")
    
    assert len(loc) >= 2


# ---------------------------------------------------------------------------
# Magic method tests
# ---------------------------------------------------------------------------

def test_localizer_getitem(temp_locales_dir):
    """Test __getitem__ magic method."""
    loc = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    loc.set_text("test_key", "Test value")
    
    result = loc["test_key"]
    assert result == "Test value"


def test_localizer_setitem(temp_locales_dir):
    """Test __setitem__ magic method."""
    loc = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    loc["test_key"] = "Test value"
    
    assert "test_key" in loc.texts
    assert loc.texts["test_key"] == "Test value"


def test_localizer_repr(temp_locales_dir):
    """Test __repr__ magic method."""
    loc = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    repr_str = repr(loc)
    
    assert "Localizer" in repr_str
    assert "fi" in repr_str


# ---------------------------------------------------------------------------
# File operation tests
# ----------------------------------------------------------------------------

def test_localizer_save(temp_locales_dir):
    """Test saving texts to file."""
    loc = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    loc.set_text("test_key", "Test value")
    
    # Check file was saved
    filepath = os.path.join(temp_locales_dir, "fi.json")
    assert os.path.exists(filepath)
    
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert "test_key" in data
        assert data["test_key"] == "Test value"


def test_localizer_load_after_save(temp_locales_dir):
    """Test loading saved texts."""
    loc1 = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    loc1.set_text("test_key", "Test value")
    
    # New instance should load saved data
    loc2 = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    assert "test_key" in loc2.texts
    assert loc2.texts["test_key"] == "Test value"


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------

def test_localizer_invalid_lang_code(temp_locales_dir):
    """Test localizer with invalid language code."""
    loc = Localizer(lang_code="", base_lang="en", folder=temp_locales_dir)
    assert loc.lang_code == "en"


def test_localizer_none_lang_code(temp_locales_dir):
    """Test localizer with None language code."""
    loc = Localizer(lang_code=None, base_lang="en", folder=temp_locales_dir)
    assert loc.lang_code is not None


def test_localizer_invalid_key_type(temp_locales_dir):
    """Test localizer with invalid key type."""
    loc = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    result = loc.L(123, "Default")
    assert result == "Default"


def test_localizer_whitespace_key(temp_locales_dir):
    """Test localizer with whitespace key."""
    loc = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    result = loc.L("  test_key  ", "Default")
    assert result == "Default"
    assert "test_key" in loc.texts


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

def test_localizer_integration_full_workflow(temp_locales_dir):
    """Test complete workflow with localizer."""
    loc = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    
    # 1. Add text
    loc.set_text("greeting", "Terve")
    
    # 2. Retrieve text
    result = loc.get_text("greeting")
    assert result == "Terve"
    
    # 3. Add missing key with L()
    result = loc.L("farewell", "Näkemiin")
    assert result == "Näkemiin"
    
    # 4. Check keys
    assert "greeting" in loc
    assert "farewell" in loc
    
    # 5. Save and reload
    loc2 = Localizer(lang_code="fi", base_lang="en", folder=temp_locales_dir)
    assert loc2.get_text("greeting") == "Terve"
    assert loc2.get_text("farewell") == "Näkemiin"


# ---------------------------------------------------------------------------
# Run tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main(["-v", __file__])
