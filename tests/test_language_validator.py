"""
Tests for LanguageValidator class using GLFM database.
"""

import json
import os
import tempfile
import pytest
from shl.language_validator import LanguageValidator


@pytest.fixture
def glfm_file():
    """Create a minimal GLFM JSON file for testing."""
    data = {
        "fin": {
            "id": "fin",
            "name": "Finnish",
            "iso639_1": "fi",
            "bcp47": "fi-Latn-FI",
            "fallback": "fin"
        },
        "eng": {
            "id": "eng",
            "name": "English",
            "iso639_1": "en",
            "bcp47": "en-Latn-US",
            "fallback": "eng"
        },
        "zho": {
            "id": "zho",
            "name": "Chinese",
            "iso639_1": "zh",
            "bcp47": "zh-Hans-CN",
            "fallback": "eng"
        }
    }

    tmpdir = tempfile.mkdtemp()
    filepath = os.path.join(tmpdir, "test_languages.json")
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f)
    yield filepath
    # Cleanup
    os.unlink(filepath)
    os.rmdir(tmpdir)


class TestLanguageValidator:

    def test_no_file_passthrough(self):
        """Test that validator works without GLFM file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            validator = LanguageValidator(
                os.path.join(tmpdir, "nonexistent.json")
            )
            assert not validator.is_loaded
            assert validator.is_valid("fi")

    def test_default_glfm_found(self):
        """Test that default GLFM file is found and loaded."""
        validator = LanguageValidator()
        assert validator.is_loaded
        assert len(validator.languages) > 7000
        assert validator.get_name("fi") == "Finnish"

    def test_loads_glfm(self, glfm_file):
        """Test loading a custom GLFM file."""
        validator = LanguageValidator(glfm_file)
        assert validator.is_loaded

    def test_valid_language(self, glfm_file):
        """Test that valid languages are recognized."""
        validator = LanguageValidator(glfm_file)
        assert validator.is_valid("fi")
        assert validator.is_valid("en")
        assert validator.is_valid("zh")

    def test_invalid_language(self, glfm_file):
        """Test that invalid languages are rejected."""
        validator = LanguageValidator(glfm_file)
        assert not validator.is_valid("xyz")

    def test_bcp47(self, glfm_file):
        """Test BCP-47 tag retrieval."""
        validator = LanguageValidator(glfm_file)
        assert validator.get_bcp47("fi") == "fi-Latn-FI"

    def test_fallback(self, glfm_file):
        """Test fallback chain retrieval."""
        validator = LanguageValidator(glfm_file)
        assert validator.get_fallback("zh") == "en"

    def test_name(self, glfm_file):
        """Test language name retrieval."""
        validator = LanguageValidator(glfm_file)
        assert validator.get_name("fi") == "Finnish"

    def test_language_info(self, glfm_file):
        """Test full language info retrieval."""
        validator = LanguageValidator(glfm_file)
        info = validator.get_language_info("fi")
        assert info is not None
        assert info["name"] == "Finnish"

    def test_is_valid_with_region_subtag(self, glfm_file):
        """Test that region subtags are handled correctly."""
        validator = LanguageValidator(glfm_file)
        assert validator.is_valid("zh-TW")
        assert validator.is_valid("zh-CN")
        assert validator.is_valid("fi-FI")

    def test_get_name_with_region(self, glfm_file):
        """Test name lookup with region subtag."""
        validator = LanguageValidator(glfm_file)
        assert validator.get_name("zh-TW") == "Chinese"
        assert validator.get_name("fi-FI") == "Finnish"
