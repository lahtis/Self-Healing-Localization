"""
File: lang_utils.py
Shared BCP-47 language tag parsing and normalization for SHL.
Single source of truth for region/script subtag handling.
"""

import logging
import re
from typing import Any, Dict, Optional, Tuple


logger = logging.getLogger(__name__)


_BCP47_RE = re.compile(
    r"^([a-z]{2,3})"
    r"(?:-([a-z]{4}))?"
    r"(?:-([a-z]{2}|\d{3}))?"
    r"$"
)


def parse_bcp47(
    lang_code: str,
) -> Tuple[
    Optional[str],
    Optional[str],
    Optional[str],
]:
    """
    Parse a language code into language, script, and region.

    Accepts hyphens or underscores as separators and any case.
    Encoding suffixes such as .UTF-8 are removed.

    Examples:
        parse_bcp47("fi-FI")
        -> ("fi", None, "fi")

        parse_bcp47("zh-Hant-TW")
        -> ("zh", "hant", "tw")

        parse_bcp47("en")
        -> ("en", None, None)
    """
    if (
        not isinstance(lang_code, str)
        or not lang_code.strip()
    ):
        return None, None, None

    code = (
        lang_code
        .strip()
        .lower()
        .replace("_", "-")
    )

    if "." in code:
        code = code.split(".", 1)[0]

    match = _BCP47_RE.match(code)

    if not match:
        return None, None, None

    return match.groups()


def normalize_full_tag(
    lang_code: str,
    default: str = "en",
) -> str:
    """
    Normalize a full language tag for file names and GLFM lookup.

    Examples:
        zh-TW -> zh-tw
        zh-Hant-TW -> zh-hant-tw
        es-419 -> es-419
        FI -> fi
    """
    if (
        not isinstance(lang_code, str)
        or not lang_code.strip()
    ):
        return default.lower()

    language, script, region = parse_bcp47(
        lang_code
    )

    if not language:
        logger.warning(
            "Unparseable language code: %s, "
            "using '%s'",
            lang_code,
            default,
        )

        return default.lower()

    parts = [language]

    if script:
        parts.append(script)

    if region:
        parts.append(region)

    return "-".join(parts)


def base_language(
    lang_code: str,
    default: str = "en",
) -> str:
    """
    Return only the base language subtag.

    Examples:
        zh-Hant-TW -> zh
        fi-FI -> fi
        en-US -> en
    """
    if (
        not isinstance(lang_code, str)
        or not lang_code.strip()
    ):
        return default

    language, _, _ = parse_bcp47(
        lang_code
    )

    return language or default


def has_region(
    lang_code: str,
) -> bool:
    """Return True if the language code has a region."""
    _, _, region = parse_bcp47(
        lang_code
    )

    return region is not None


def get_parent(
    lang_code: str,
    default: str = "en",
) -> str:
    """
    Return the parent tag without its region.

    Examples:
        zh-Hant-TW -> zh-hant
        fi-FI -> fi
        en -> en
    """
    if (
        not isinstance(lang_code, str)
        or not lang_code.strip()
    ):
        return default

    language, script, _ = parse_bcp47(
        lang_code
    )

    if not language:
        return default

    if script:
        return f"{language}-{script}"

    return language


def split_tag(
    lang_code: str,
) -> Dict[str, Any]:
    """
    Return a structured language-tag dictionary.

    The return value intentionally contains only these keys:

        language
        script
        region
        tag

    Examples:
        split_tag("fi-FI")
        -> {
            "language": "fi",
            "script": None,
            "region": "fi",
            "tag": "fi-fi",
        }

        split_tag("invalid")
        -> {
            "language": None,
            "script": None,
            "region": None,
            "tag": None,
        }
    """
    language, script, region = parse_bcp47(
        lang_code
    )

    if language:
        tag = normalize_full_tag(
            lang_code
        )
    else:
        tag = None

    return {
        "language": language,
        "script": script,
        "region": region,
        "tag": tag,
    }


def is_valid(
    lang_code: str,
) -> bool:
    """
    Return True if the language code is valid.

    Examples:
        is_valid("fi-FI") -> True
        is_valid("zh-Hant-TW") -> True
        is_valid("invalid") -> False
        is_valid("") -> False
    """
    language, _, _ = parse_bcp47(
        lang_code
    )

    return language is not None


def normalize_language(
    lang_code: str,
    default: str = "en",
) -> str:
    """Alias for normalize_full_tag()."""
    return normalize_full_tag(
        lang_code,
        default,
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG
    )

    print("=== lang_utils Tests ===")
    print()

    test_tags = [
        "fi",
        "fi-FI",
        "zh-Hant-TW",
        "zh_TW",
        "EN-US",
        "sr-Latn-RS",
        "es-419",
        "invalid",
        "",
        None,
    ]

    for tag in test_tags:
        print(f"Input: {tag!r}")
        print(
            "  parse_bcp47: "
            f"{parse_bcp47(tag)!r}"
        )
        print(
            "  normalize_full_tag: "
            f"{normalize_full_tag(tag)!r}"
        )
        print(
            "  base_language: "
            f"{base_language(tag)!r}"
        )
        print(
            "  has_region: "
            f"{has_region(tag)!r}"
        )
        print(
            "  get_parent: "
            f"{get_parent(tag)!r}"
        )
        print(
            "  split_tag: "
            f"{split_tag(tag)!r}"
        )
        print(
            "  is_valid: "
            f"{is_valid(tag)!r}"
        )
        print()
