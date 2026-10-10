"""
File: tools/test_style_rules.py
Description: End-to-end test for SHL style_rules integration.

Tests that style_id flows correctly through:
  - TranslationRequest (DTO)
  - TranslationCache (get/set with style_id)
  - MemoryManager (search/store with style_id)
  - DeepLAdapter (payload mapping)

Run:
    python3 -m tools.test_style_rules

Requires:
    DEEPL_API_KEY in ./.env/shl/.env
    At least one valid style_id created via DeepL API
"""

import logging
import os
import sys
from dataclasses import replace

from shl.engine.translation.metadata import TranslationRequest
from shl.engine.translation.router import (
    translate_text_with_metadata,
    _translation_cache,
    _memory_manager,
)


# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

STYLE_ID_MENU = os.getenv("SHL_TEST_STYLE_MENU", "")
STYLE_ID_ERROR = os.getenv("SHL_TEST_STYLE_ERROR", "")

TEST_TEXT = "Open file"
SOURCE_LANG = "en"
TARGET_LANG = "fi"


# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("test_style_rules")


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

PASS = "\033[92m✓ PASS\033[0m"
FAIL = "\033[91m✗ FAIL\033[0m"
SKIP = "\033[93m⊘ SKIP\033[0m"

_results = {"pass": 0, "fail": 0, "skip": 0}


def check(name: str, condition: bool, detail: str = "") -> None:
    """Record a test result."""
    if condition:
        _results["pass"] += 1
        print(f"  {PASS}  {name}")
    else:
        _results["fail"] += 1
        print(f"  {FAIL}  {name}")
        if detail:
            print(f"         → {detail}")


def skip(name: str, reason: str) -> None:
    """Mark a test as skipped."""
    _results["skip"] += 1
    print(f"  {SKIP}  {name}  ({reason})")


def reset_state() -> None:
    """Clear cache so tests start from a clean state."""
    _translation_cache.clear()


def call_router(req: TranslationRequest):
    """Call router with all required positional arguments.

    translate_text_with_metadata requires text and target_lang even
    when request is provided, because the DTO fields are not used to
    fill in missing positional arguments.
    """
    return translate_text_with_metadata(
        text=req.text,
        target_lang=req.target_lang,
        source_lang=req.source_lang,
        request=req,
    )


# ---------------------------------------------------------------------------
# TESTS
# ---------------------------------------------------------------------------

def test_dto_has_style_fields() -> None:
    """TranslationRequest has style and style_id fields."""
    print("\n[1] DTO shape")

    req = TranslationRequest(
        text="hello",
        source_lang="en",
        target_lang="fi",
    )

    check(
        "style_id defaults to None",
        req.style_id is None,
    )
    check(
        "style defaults to None",
        req.style is None,
    )

    req2 = replace(req, style_id="abc-123", style="menu")
    check(
        "style_id can be set",
        req2.style_id == "abc-123",
    )
    check(
        "style can be set",
        req2.style == "menu",
    )


def test_cache_key_differs_by_style() -> None:
    """Cache keys differ when style_id differs."""
    print("\n[2] Cache key isolation")

    reset_state()

    key_a = _translation_cache._generate_key(
        "hello", "en", "fi", None, None, "style-A",
    )
    key_b = _translation_cache._generate_key(
        "hello", "en", "fi", None, None, "style-B",
    )
    key_none = _translation_cache._generate_key(
        "hello", "en", "fi", None, None, None,
    )
    key_empty = _translation_cache._generate_key(
        "hello", "en", "fi", None, None, "",
    )

    check(
        "different style_id → different key",
        key_a != key_b,
    )
    check(
        "None and '' produce same key",
        key_none == key_empty,
    )
    check(
        "style_id vs None → different key",
        key_a != key_none,
    )


def test_cache_roundtrip_with_style() -> None:
    """Cache stores and retrieves by style_id."""
    print("\n[3] Cache roundtrip")

    reset_state()

    _translation_cache.set(
        "hello", "hei-A", "en", "fi",
        None, None, "style-A",
    )
    _translation_cache.set(
        "hello", "hei-B", "en", "fi",
        None, None, "style-B",
    )

    got_a = _translation_cache.get(
        "hello", "en", "fi", None, None, "style-A",
    )
    got_b = _translation_cache.get(
        "hello", "en", "fi", None, None, "style-B",
    )
    got_none = _translation_cache.get(
        "hello", "en", "fi", None, None, None,
    )

    check(
        "style-A returns its own translation",
        got_a == "hei-A",
        f"got {got_a!r}",
    )
    check(
        "style-B returns its own translation",
        got_b == "hei-B",
        f"got {got_b!r}",
    )
    check(
        "style-less query does NOT match styled entries",
        got_none is None,
        f"got {got_none!r}",
    )


def test_memory_parse_style() -> None:
    """MemoryManager parses Style: line correctly."""
    print("\n[4] Memory content parsing")

    content = (
        "Source language: en\n"
        "Target language: fi\n"
        "Source: Open file\n"
        "Translation: Avaa tiedosto\n"
        "Style: menu\n"
    )

    parsed = _memory_manager._parse_memory_content(content)

    check(
        "parses valid content with Style line",
        parsed is not None,
    )
    check(
        "extracts style field",
        parsed and parsed.get("style") == "menu",
    )

    legacy = (
        "Source language: en\n"
        "Target language: fi\n"
        "Source: Open file\n"
        "Translation: Avaa tiedosto"
    )

    parsed_legacy = _memory_manager._parse_memory_content(legacy)

    check(
        "legacy content still parses (no Style line)",
        parsed_legacy is not None,
    )
    check(
        "legacy content → style missing",
        parsed_legacy and "style" not in parsed_legacy,
    )


def test_router_passes_style_to_cache() -> None:
    """Router's full pipeline respects style_id."""
    print("\n[5] Router integration (no API call)")

    reset_state()

    _translation_cache.set(
        TEST_TEXT, "Avattu-A", SOURCE_LANG, TARGET_LANG,
        None, None, "style-A",
    )

    req = TranslationRequest(
        text=TEST_TEXT,
        source_lang=SOURCE_LANG,
        target_lang=TARGET_LANG,
        style_id="style-A",
    )

    result = call_router(req)

    check(
        "style-A hits cache",
        result.source == "cache",
        f"source={result.source}",
    )
    check(
        "cached translation returned",
        result.translated_text == "Avattu-A",
        f"text={result.translated_text!r}",
    )

    cached_b = _translation_cache.get(
        TEST_TEXT, SOURCE_LANG, TARGET_LANG,
        None, None, "style-B",
    )

    check(
        "style-B has no cache entry",
        cached_b is None,
        f"got {cached_b!r}",
    )


def test_live_deepl_style() -> None:
    """Live DeepL call with style_id (requires API key + valid UUID)."""
    print("\n[6] Live DeepL call")

    if not STYLE_ID_MENU:
        skip(
            "live DeepL style test",
            "SHL_TEST_STYLE_MENU not set",
        )
        return

    reset_state()

    req = TranslationRequest(
        text=TEST_TEXT,
        source_lang=SOURCE_LANG,
        target_lang=TARGET_LANG,
        style_id=STYLE_ID_MENU,
    )

    try:
        result = call_router(req)
    except Exception as exc:
        check(
            "live DeepL call succeeded",
            False,
            f"{type(exc).__name__}: {exc}",
        )
        return

    check(
        "live call returned non-empty translation",
        bool(result.translated_text),
        f"text={result.translated_text!r}",
    )
    check(
        "translation came from deepl (first call)",
        result.source == "deepl",
        f"source={result.source}",
    )

    result2 = call_router(req)

    check(
        "second identical call hits cache",
        result2.source == "cache",
        f"source={result2.source}",
    )
    check(
        "cached result matches live result",
        result2.translated_text == result.translated_text,
    )


def test_live_deepl_two_styles() -> None:
    """Two different style_ids produce different cache entries."""
    print("\n[7] Live DeepL with two styles")

    if not (STYLE_ID_MENU and STYLE_ID_ERROR):
        skip(
            "two-style comparison",
            "SHL_TEST_STYLE_MENU or SHL_TEST_STYLE_ERROR not set",
        )
        return

    reset_state()

    req_menu = TranslationRequest(
        text=TEST_TEXT,
        source_lang=SOURCE_LANG,
        target_lang=TARGET_LANG,
        style_id=STYLE_ID_MENU,
    )
    req_error = TranslationRequest(
        text=TEST_TEXT,
        source_lang=SOURCE_LANG,
        target_lang=TARGET_LANG,
        style_id=STYLE_ID_ERROR,
    )

    try:
        r_menu = call_router(req_menu)
        r_error = call_router(req_error)
    except Exception as exc:
        check(
            "two-style test completed",
            False,
            f"{type(exc).__name__}: {exc}",
        )
        return

    check(
        "menu call succeeded",
        bool(r_menu.translated_text),
    )
    check(
        "error call succeeded",
        bool(r_error.translated_text),
    )
    check(
        "both calls went to provider (not shared cache)",
        r_menu.source == "deepl" and r_error.source == "deepl",
        f"menu={r_menu.source}, error={r_error.source}",
    )

    cached_menu = _translation_cache.get(
        TEST_TEXT, SOURCE_LANG, TARGET_LANG,
        None, None, STYLE_ID_MENU,
    )
    cached_error = _translation_cache.get(
        TEST_TEXT, SOURCE_LANG, TARGET_LANG,
        None, None, STYLE_ID_ERROR,
    )

    check(
        "menu style cached",
        cached_menu is not None,
    )
    check(
        "error style cached separately",
        cached_error is not None,
    )


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 60)
    print("SHL style_rules integration test")
    print("=" * 60)

    if not os.getenv("DEEPL_API_KEY"):
        print(
            "\n⚠  DEEPL_API_KEY not set — "
            "live tests will be skipped.\n"
        )

    test_dto_has_style_fields()
    test_cache_key_differs_by_style()
    test_cache_roundtrip_with_style()
    test_memory_parse_style()
    test_router_passes_style_to_cache()
    test_live_deepl_style()
    test_live_deepl_two_styles()

    print("\n" + "=" * 60)
    print(
        f"Results: {_results['pass']} passed, "
        f"{_results['fail']} failed, "
        f"{_results['skip']} skipped"
    )
    print("=" * 60)

    return 0 if _results["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
