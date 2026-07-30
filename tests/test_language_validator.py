# tests/test_language_validator.py
"""
Tests for the LanguageValidator class with GLFM integration.
"""

import pytest
import os
import json
import tempfile
from shl.language_validator import LanguageValidator


# ---------------------------------------------------------------------------
# Basic initialization tests
# ---------------------------------------------------------------------------

def test_validator_init():
    """Test validator initialization."""
    validator = LanguageValidator()
    assert validator is not None
    assert hasattr(validator, 'languages')
    assert hasattr(validator, '_loaded')


def test_validator_init_with_glfm_path(temp_data_dir, glfm_file):
    """Test validator initialization with custom GLFM path."""
    validator = LanguageValidator(glfm_path=glfm_file)
    assert validator is not None
    assert validator.is_loaded is True


def test_validator_init_with_invalid_path():
    """Test validator initialization with invalid path."""
    validator = LanguageValidator(glfm_path="/nonexistent/path.json")
    assert validator is not None
    assert validator.is_loaded is False


def test_validator_is_loaded():
    """Test is_loaded property."""
    validator = LanguageValidator()
    assert isinstance(validator.is_loaded, bool)


def test_validator_is_loaded_with_glfm(temp_data_dir, glfm_file):
    """Test is_loaded property when GLFM is loaded."""
    validator = LanguageValidator(glfm_path=glfm_file)
    assert validator.is_loaded is True


# ---------------------------------------------------------------------------
# Language validation tests
# ---------------------------------------------------------------------------

def test_validator_is_valid(temp_data_dir, glfm_file):
    """Test language validation with GLFM loaded."""
    validator = LanguageValidator(glfm_path=glfm_file)
    
    # Valid languages
    assert validator.is_valid("en") is True
    assert validator.is_valid("fi") is True
    assert validator.is_valid("sv") is True
    assert validator.is_valid("zh") is True
    
    # Invalid languages
    assert validator.is_valid("xyz") is False
    assert validator.is_valid("foo") is False
    # Empty string should be False
    assert validator.is_valid("") is False


def test_validator_is_valid_without_glfm():
    """Test language validation without GLFM (should return True)."""
    validator = LanguageValidator()
    # If GLFM is loaded (which it usually is in tests), "en" is valid
    # "xyz" is not valid if GLFM is loaded
    if validator.is_loaded:
        assert validator.is_valid("en") is True
        assert validator.is_valid("xyz") is False
    else:
        assert validator.is_valid("xyz") is True


def test_validator_is_valid_with_region(temp_data_dir, glfm_file):
    """Test language validation with region subtags."""
    validator = LanguageValidator(glfm_path=glfm_file)
    
    # Should validate base language
    assert validator.is_valid("en-US") is True
    assert validator.is_valid("zh-TW") is True
    # pt-BR is not in our test GLFM, so should be False
    assert validator.is_valid("pt-BR") is False


def test_validator_is_valid_with_script(temp_data_dir, glfm_file):
    """Test language validation with script subtags."""
    validator = LanguageValidator(glfm_path=glfm_file)
    
    # Should validate base language
    assert validator.is_valid("zh-Hant-TW") is True


# ---------------------------------------------------------------------------
# Language info tests
# ---------------------------------------------------------------------------

def test_validator_get_name(temp_data_dir, glfm_file):
    """Test getting language name."""
    validator = LanguageValidator(glfm_path=glfm_file)
    
    assert validator.get_name("en") == "English"
    assert validator.get_name("fi") == "Finnish"
    assert validator.get_name("sv") == "Swedish"


def test_validator_get_name_without_glfm():
    """Test getting language name without GLFM."""
    validator = LanguageValidator()
    # If GLFM is loaded, returns the actual name
    # If not loaded, returns "Language: en"
    name = validator.get_name("en")
    assert name is not None
    # Accept either case
    assert name == "English" or "Language:" in name


def test_validator_get_name_invalid(temp_data_dir, glfm_file):
    """Test getting name for invalid language."""
    validator = LanguageValidator(glfm_path=glfm_file)
    
    name = validator.get_name("xyz")
    assert name is None


def test_validator_get_bcp47(temp_data_dir, glfm_file):
    """Test getting BCP-47 tag."""
    validator = LanguageValidator(glfm_path=glfm_file)
    
    assert validator.get_bcp47("en") is not None
    assert validator.get_bcp47("fi") is not None


def test_validator_get_bcp47_without_glfm():
    """Test getting BCP-47 tag without GLFM."""
    validator = LanguageValidator()
    
    # Should generate from lang_utils
    bcp47 = validator.get_bcp47("en")
    assert bcp47 == "en" or bcp47 is not None


def test_validator_get_bcp47_invalid(temp_data_dir, glfm_file):
    """Test getting BCP-47 for invalid language."""
    validator = LanguageValidator(glfm_path=glfm_file)
    
    bcp47 = validator.get_bcp47("xyz")
    # Should return generated tag
    assert bcp47 == "xyz" or bcp47 is None


def test_validator_get_fallback(temp_data_dir, glfm_file):
    """Test getting fallback language."""
    validator = LanguageValidator(glfm_path=glfm_file)
    
    # In test GLFM, fi → en
    fallback = validator.get_fallback("fi")
    assert fallback == "en"


def test_validator_get_fallback_no_fallback(temp_data_dir, glfm_file):
    """Test getting fallback for language without fallback."""
    validator = LanguageValidator(glfm_path=glfm_file)
    
    # In test GLFM, en has no fallback
    fallback = validator.get_fallback("en")
    assert fallback is None


def test_validator_get_fallback_without_glfm():
    """Test getting fallback without GLFM."""
    validator = LanguageValidator()
    # If GLFM is loaded and "fi" has no fallback, returns "fi"
    # If GLFM not loaded, returns None
    fallback = validator.get_fallback("fi")
    # Accept either case
    assert fallback is None or fallback == "fi"


def test_validator_get_language_info(temp_data_dir, glfm_file):
    """Test getting full language info."""
    validator = LanguageValidator(glfm_path=glfm_file)
    
    info = validator.get_language_info("fi")
    assert info is not None
    assert "iso639_1" in info
    assert info["iso639_1"] == "fi"
    assert "name" in info
    assert info["name"] == "Finnish"


def test_validator_get_language_info_invalid(temp_data_dir, glfm_file):
    """Test getting info for invalid language."""
    validator = LanguageValidator(glfm_path=glfm_file)
    
    info = validator.get_language_info("xyz")
    assert info is None


def test_validator_get_region():
    """Test getting region from language code."""
    validator = LanguageValidator()
    
    assert validator.get_region("zh-TW") == "tw"
    assert validator.get_region("pt-BR") == "br"
    assert validator.get_region("en-US") == "us"
    assert validator.get_region("fi") is None
    assert validator.get_region("") is None


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------

def test_validator_empty_lang_code(temp_data_dir, glfm_file):
    """Test validator with empty language code - should return False."""
    validator = LanguageValidator(glfm_path=glfm_file)
    
    assert validator.is_valid("") is False
    assert validator.get_name("") is None
    assert validator.get_fallback("") is None
    assert validator.get_bcp47("") is None


def test_validator_none_lang_code(temp_data_dir, glfm_file):
    """Test validator with None language code - should return False."""
    validator = LanguageValidator(glfm_path=glfm_file)
    
    assert validator.is_valid(None) is False
    assert validator.get_name(None) is None
    assert validator.get_fallback(None) is None


def test_validator_case_insensitive(temp_data_dir, glfm_file):
    """Test validator is case insensitive."""
    validator = LanguageValidator(glfm_path=glfm_file)
    
    assert validator.is_valid("FI") is True
    assert validator.is_valid("En") is True
    assert validator.is_valid("Zh-Tw") is True


def test_validator_underscore_lang_code(temp_data_dir, glfm_file):
    """Test validator with underscore in language code."""
    validator = LanguageValidator(glfm_path=glfm_file)
    
    # Should handle underscores
    assert validator.is_valid("zh_TW") is True


# ---------------------------------------------------------------------------
# GLFM file loading tests
# ---------------------------------------------------------------------------

def test_validator_glfm_file_not_found():
    """Test validator when GLFM file not found."""
    validator = LanguageValidator(glfm_path="/nonexistent/path/unified_languages.json")
    assert validator.is_loaded is False
    assert len(validator.languages) == 0


def test_validator_glfm_file_corrupted(temp_data_dir):
    """Test validator with corrupted GLFM file."""
    # Create corrupted JSON file
    filepath = os.path.join(temp_data_dir, "corrupted.json")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("{invalid json content [")
    
    validator = LanguageValidator(glfm_path=filepath)
    assert validator.is_loaded is False
    assert len(validator.languages) == 0


def test_validator_glfm_file_empty(temp_data_dir):
    """Test validator with empty GLFM file."""
    filepath = os.path.join(temp_data_dir, "empty.json")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("{}")
    
    validator = LanguageValidator(glfm_path=filepath)
    # Empty dict is valid JSON, but is_loaded checks len(languages) > 0
    # So is_loaded is False
    assert validator.is_loaded is False
    assert len(validator.languages) == 0


def test_validator_glfm_file_not_dict(temp_data_dir):
    """Test validator with GLFM file that's not a dict."""
    filepath = os.path.join(temp_data_dir, "not_dict.json")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write('["not", "a", "dict"]')
    
    validator = LanguageValidator(glfm_path=filepath)
    # Should handle gracefully - not loaded because data is not a dict
    assert validator.is_loaded is False
    assert len(validator.languages) == 0


# ---------------------------------------------------------------------------
# Language code normalization with lang_utils tests
# ---------------------------------------------------------------------------

def test_validator_normalizes_full_tag(temp_data_dir, glfm_file):
    """Test validator normalizes full tags properly."""
    validator = LanguageValidator(glfm_path=glfm_file)
    
    # Should find the language regardless of format
    assert validator.is_valid("zh-hant-tw") is True
    assert validator.is_valid("zh_Hant_TW") is True


def test_validator_normalizes_base_language(temp_data_dir, glfm_file):
    """Test validator uses base_language() for lookup."""
    validator = LanguageValidator(glfm_path=glfm_file)
    
    # Should strip script/region for lookup
    assert validator.is_valid("zh-Hant-TW") is True
    assert validator.get_name("zh-Hant-TW") == "Chinese"


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_validator_integration_real_glfm():
    """Integration test with real GLFM file."""
    # Try to load the actual GLFM file if it exists
    validator = LanguageValidator()
    if validator.is_loaded:
        assert len(validator.languages) > 0
        assert validator.is_valid("en") is True
        assert validator.is_valid("fi") is True


# ---------------------------------------------------------------------------
# Run tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main(["-v", __file__])
