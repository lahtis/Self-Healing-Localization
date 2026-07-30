# tests/test_lang_utils.py
"""
Tests for language utilities (BCP-47 parsing and normalization).
"""

import pytest
from shl.utils.lang_utils import (
    parse_bcp47,
    normalize_full_tag,
    base_language,
    has_region,
    get_parent,
    split_tag
)


# ---------------------------------------------------------------------------
# parse_bcp47 tests
# ---------------------------------------------------------------------------

def test_parse_bcp47_basic():
    """Test basic language code parsing."""
    assert parse_bcp47("fi") == ("fi", None, None)
    assert parse_bcp47("en") == ("en", None, None)
    assert parse_bcp47("fr") == ("fr", None, None)


def test_parse_bcp47_with_region():
    """Test parsing with region subtag."""
    assert parse_bcp47("zh-TW") == ("zh", None, "tw")
    assert parse_bcp47("pt-BR") == ("pt", None, "br")
    assert parse_bcp47("en-US") == ("en", None, "us")
    assert parse_bcp47("es-419") == ("es", None, "419")


def test_parse_bcp47_with_script():
    """Test parsing with script subtag."""
    assert parse_bcp47("zh-Hant") == ("zh", "hant", None)
    assert parse_bcp47("sr-Latn") == ("sr", "latn", None)
    assert parse_bcp47("zh-Hans") == ("zh", "hans", None)


def test_parse_bcp47_with_script_and_region():
    """Test parsing with both script and region subtags."""
    assert parse_bcp47("zh-Hant-TW") == ("zh", "hant", "tw")
    assert parse_bcp47("sr-Latn-RS") == ("sr", "latn", "rs")
    assert parse_bcp47("zh-Hans-CN") == ("zh", "hans", "cn")


def test_parse_bcp47_underscore_separator():
    """Test parsing with underscore separators."""
    assert parse_bcp47("pt_BR") == ("pt", None, "br")
    assert parse_bcp47("zh_Hant_TW") == ("zh", "hant", "tw")
    assert parse_bcp47("en_US") == ("en", None, "us")


def test_parse_bcp47_case_insensitive():
    """Test case insensitivity."""
    assert parse_bcp47("FI") == ("fi", None, None)
    assert parse_bcp47("Zh-Tw") == ("zh", None, "tw")
    assert parse_bcp47("ZH-HANT-TW") == ("zh", "hant", "tw")


def test_parse_bcp47_with_encoding():
    """Test parsing with encoding suffix - should strip .UTF-8."""
    assert parse_bcp47("en_US.UTF-8") == ("en", None, "us")
    assert parse_bcp47("zh_TW.UTF-8") == ("zh", None, "tw")


def test_parse_bcp47_empty():
    """Test parsing empty string."""
    assert parse_bcp47("") == (None, None, None)
    assert parse_bcp47(" ") == (None, None, None)
    assert parse_bcp47(None) == (None, None, None)


def test_parse_bcp47_invalid():
    """Test parsing invalid formats."""
    # "en-US-extra" has too many parts -> invalid
    assert parse_bcp47("en-US-extra") == (None, None, None)
    assert parse_bcp47("invalid") == (None, None, None)
    assert parse_bcp47("123") == (None, None, None)


def test_parse_bcp47_long_language():
    """Test parsing with 3-letter language code."""
    assert parse_bcp47("eng") == ("eng", None, None)
    assert parse_bcp47("fin") == ("fin", None, None)
    assert parse_bcp47("zho") == ("zho", None, None)


def test_parse_bcp47_with_numeric_region():
    """Test parsing with numeric region (UN M49)."""
    assert parse_bcp47("es-419") == ("es", None, "419")
    assert parse_bcp47("zh-001") == ("zh", None, "001")


# ---------------------------------------------------------------------------
# normalize_full_tag tests
# ---------------------------------------------------------------------------

def test_normalize_full_tag_basic():
    """Test basic tag normalization."""
    assert normalize_full_tag("fi") == "fi"
    assert normalize_full_tag("en") == "en"
    assert normalize_full_tag("fr") == "fr"


def test_normalize_full_tag_with_region():
    """Test normalization with region subtag."""
    assert normalize_full_tag("zh-TW") == "zh-tw"
    assert normalize_full_tag("pt-BR") == "pt-br"
    assert normalize_full_tag("en-US") == "en-us"
    assert normalize_full_tag("es-419") == "es-419"


def test_normalize_full_tag_with_script():
    """Test normalization with script subtag."""
    assert normalize_full_tag("zh-Hant") == "zh-hant"
    assert normalize_full_tag("sr-Latn") == "sr-latn"
    assert normalize_full_tag("zh-Hans") == "zh-hans"


def test_normalize_full_tag_with_script_and_region():
    """Test normalization with both script and region."""
    assert normalize_full_tag("zh-Hant-TW") == "zh-hant-tw"
    assert normalize_full_tag("sr-Latn-RS") == "sr-latn-rs"
    assert normalize_full_tag("zh-Hans-CN") == "zh-hans-cn"


def test_normalize_full_tag_underscore_separator():
    """Test normalization with underscore separators."""
    assert normalize_full_tag("pt_BR") == "pt-br"
    assert normalize_full_tag("zh_Hant_TW") == "zh-hant-tw"
    assert normalize_full_tag("en_US") == "en-us"


def test_normalize_full_tag_case_insensitive():
    """Test normalization case insensitivity."""
    assert normalize_full_tag("FI") == "fi"
    assert normalize_full_tag("Zh-Tw") == "zh-tw"
    assert normalize_full_tag("ZH-HANT-TW") == "zh-hant-tw"


def test_normalize_full_tag_empty():
    """Test normalization of empty values."""
    assert normalize_full_tag("") == "en"
    assert normalize_full_tag(None) == "en"
    assert normalize_full_tag(" ") == "en"


def test_normalize_full_tag_invalid():
    """Test normalization of invalid values."""
    # Invalid returns default "en"
    assert normalize_full_tag("invalid") == "en"
    assert normalize_full_tag("123") == "en"
    assert normalize_full_tag("en-US-extra") == "en"


def test_normalize_full_tag_custom_default():
    """Test normalization with custom default."""
    assert normalize_full_tag("", default="fi") == "fi"
    assert normalize_full_tag(None, default="sv") == "sv"


# ---------------------------------------------------------------------------
# base_language tests
# ---------------------------------------------------------------------------

def test_base_language_basic():
    """Test basic base language extraction."""
    assert base_language("fi") == "fi"
    assert base_language("en") == "en"
    assert base_language("fr") == "fr"


def test_base_language_with_region():
    """Test base language extraction with region."""
    assert base_language("zh-TW") == "zh"
    assert base_language("pt-BR") == "pt"
    assert base_language("en-US") == "en"
    assert base_language("es-419") == "es"


def test_base_language_with_script():
    """Test base language extraction with script."""
    assert base_language("zh-Hant") == "zh"
    assert base_language("sr-Latn") == "sr"


def test_base_language_with_script_and_region():
    """Test base language extraction with both."""
    assert base_language("zh-Hant-TW") == "zh"
    assert base_language("sr-Latn-RS") == "sr"


def test_base_language_empty():
    """Test base language extraction of empty values."""
    assert base_language("") == "en"
    assert base_language(None) == "en"


def test_base_language_custom_default():
    """Test base language extraction with custom default."""
    assert base_language("", default="fi") == "fi"
    assert base_language(None, default="sv") == "sv"


# ---------------------------------------------------------------------------
# has_region tests
# ---------------------------------------------------------------------------

def test_has_region_basic():
    """Test region detection."""
    assert has_region("zh-TW") is True
    assert has_region("pt-BR") is True
    assert has_region("en-US") is True
    assert has_region("es-419") is True


def test_has_region_no_region():
    """Test region detection for codes without region."""
    assert has_region("fi") is False
    assert has_region("en") is False
    assert has_region("zh-Hant") is False
    assert has_region("sr-Latn") is False


def test_has_region_empty():
    """Test region detection for empty values."""
    assert has_region("") is False
    assert has_region(None) is False


# ---------------------------------------------------------------------------
# get_parent tests
# ---------------------------------------------------------------------------

def test_get_parent_basic():
    """Test parent language extraction."""
    assert get_parent("fi") == "fi"
    assert get_parent("en") == "en"


def test_get_parent_with_region():
    """Test parent extraction with region."""
    assert get_parent("pt-BR") == "pt"
    assert get_parent("zh-TW") == "zh"
    assert get_parent("en-US") == "en"


def test_get_parent_with_script():
    """Test parent extraction with script."""
    assert get_parent("zh-Hant") == "zh-hant"
    assert get_parent("sr-Latn") == "sr-latn"


def test_get_parent_with_script_and_region():
    """Test parent extraction with both."""
    assert get_parent("zh-Hant-TW") == "zh-hant"
    assert get_parent("sr-Latn-RS") == "sr-latn"


def test_get_parent_empty():
    """Test parent extraction of empty values."""
    assert get_parent("") == "en"
    assert get_parent(None) == "en"


def test_get_parent_custom_default():
    """Test parent extraction with custom default."""
    assert get_parent("", default="fi") == "fi"
    assert get_parent(None, default="sv") == "sv"


# ---------------------------------------------------------------------------
# split_tag tests
# ---------------------------------------------------------------------------

def test_split_tag_basic():
    """Test tag splitting."""
    assert split_tag("fi") == {
        "language": "fi",
        "script": None,
        "region": None,
        "tag": "fi"
    }


def test_split_tag_with_region():
    """Test splitting with region."""
    assert split_tag("zh-TW") == {
        "language": "zh",
        "script": None,
        "region": "tw",
        "tag": "zh-tw"
    }


def test_split_tag_with_script():
    """Test splitting with script."""
    assert split_tag("zh-Hant") == {
        "language": "zh",
        "script": "hant",
        "region": None,
        "tag": "zh-hant"
    }


def test_split_tag_with_script_and_region():
    """Test splitting with both."""
    assert split_tag("zh-Hant-TW") == {
        "language": "zh",
        "script": "hant",
        "region": "tw",
        "tag": "zh-hant-tw"
    }


def test_split_tag_underscore_separator():
    """Test splitting with underscore separators."""
    assert split_tag("pt_BR") == {
        "language": "pt",
        "script": None,
        "region": "br",
        "tag": "pt-br"
    }


def test_split_tag_empty():
    """Test splitting empty values."""
    assert split_tag("") == {
        "language": None,
        "script": None,
        "region": None,
        "tag": None
    }
    assert split_tag(None) == {
        "language": None,
        "script": None,
        "region": None,
        "tag": None
    }


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------

def test_edge_case_three_letter_language():
    """Test 3-letter language codes."""
    assert parse_bcp47("eng") == ("eng", None, None)
    assert normalize_full_tag("eng") == "eng"
    assert base_language("eng") == "eng"


def test_edge_case_unusual_script():
    """Test unusual script codes."""
    assert parse_bcp47("ru-Cyrl") == ("ru", "cyrl", None)
    assert parse_bcp47("ja-Jpan") == ("ja", "jpan", None)


def test_edge_case_region_only():
    """Test cases that are only region codes."""
    # "US" is parsed as a language code because it's 2 letters
    assert parse_bcp47("US") == ("us", None, None)
    assert parse_bcp47("TW") == ("tw", None, None)


def test_edge_case_whitespace_handling():
    """Test whitespace handling - should strip whitespace."""
    assert parse_bcp47(" en ") == ("en", None, None)


# ---------------------------------------------------------------------------
# Run tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main(["-v", __file__])
