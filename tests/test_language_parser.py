"""
Tests for provider-specific language code resolution in LanguageParser.

These tests verify that:
    - basic language codes resolve correctly
    - explicit BCP-47 regions are preserved
    - explicit script and region variants resolve to provider-native codes
    - provider-specific language codes are obtained from the provider cache
"""

from shl.language_parser import LanguageParser


def test_basic_provider_language_codes():
    parser = LanguageParser()

    assert parser.get_provider_code("en", "Papago") == "en"
    assert parser.get_provider_code("fi", "DeepL") == "fi"
    assert parser.get_provider_code("sv", "DeepL") == "sv"


def test_chinese_default_provider_codes():
    parser = LanguageParser()

    assert parser.get_provider_code("zh", "Papago") == "zh-cn"
    assert parser.get_provider_code("zh", "DeepL") == "zh"


def test_chinese_region_variants():
    parser = LanguageParser()

    assert parser.get_provider_code("zh-CN", "Papago") == "zh-cn"
    assert parser.get_provider_code("zh-TW", "Papago") == "zh-tw"


def test_chinese_script_variants():
    parser = LanguageParser()

    assert parser.get_provider_code(
        "zh-Hans-CN",
        "DeepL",
    ) == "zh-hans"

    assert parser.get_provider_code(
        "zh-Hant-TW",
        "DeepL",
    ) == "zh-hant"


def test_chinese_script_region_falls_back_to_provider_region():
    parser = LanguageParser()

    assert parser.get_provider_code(
        "zh-Hant-TW",
        "Papago",
    ) == "zh-tw"
