"""
Tests for provider-specific language code resolution in LanguageParser.

These tests use the provider language data stored in the local
.languages_cache.json cache.
"""

import json
from pathlib import Path

from shl.language_parser import LanguageParser


CACHE_FILE = Path(".languages_cache.json")


def load_provider_codes(provider):
    with CACHE_FILE.open("r", encoding="utf-8") as file:
        cache = json.load(file)

    return cache["providers"][provider]


def test_basic_provider_language_codes():
    parser = LanguageParser()
    provider_codes = load_provider_codes("libretranslate")

    assert parser.get_provider_code("eng", "LibreTranslate") in provider_codes
    assert parser.get_provider_code("fin", "LibreTranslate") in provider_codes
    assert parser.get_provider_code("swe", "LibreTranslate") in provider_codes


def test_chinese_default_provider_code():
    parser = LanguageParser()
    provider_codes = load_provider_codes("libretranslate")

    result = parser.get_provider_code("zho", "LibreTranslate")

    assert result in provider_codes


def test_chinese_region_variant():
    parser = LanguageParser()
    provider_codes = load_provider_codes("libretranslate")

    result = parser.get_provider_code("zh-CN", "LibreTranslate")

    assert result in provider_codes


def test_chinese_script_region_variant():
    parser = LanguageParser()
    provider_codes = load_provider_codes("libretranslate")

    result = parser.get_provider_code(
        "zh-Hans-CN",
        "LibreTranslate",
    )

    assert result in provider_codes


def test_norwegian_provider_language_code():
    parser = LanguageParser()
    provider_codes = load_provider_codes("libretranslate")

    result = parser.get_provider_code("nor", "LibreTranslate")

    assert result in provider_codes


def test_norwegian_bcp47_variants():
    parser = LanguageParser()
    provider_codes = load_provider_codes("libretranslate")

    assert parser.get_provider_code(
        "no",
        "LibreTranslate",
    ) in provider_codes

    assert parser.get_provider_code(
        "no-NO",
        "LibreTranslate",
    ) in provider_codes


def test_norwegian_resolves_to_provider_language_name():
    parser = LanguageParser()
    provider_codes = load_provider_codes("libretranslate")

    result = parser.get_provider_code(
        "nor",
        "LibreTranslate",
    )

    assert result in provider_codes
    assert provider_codes[result] == "Norwegian"
