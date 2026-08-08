"""
File: lang_utils.py
Shared BCP-47 language tag parsing and normalization for SHL.
Single source of truth for region/script subtag handling.
"""

import re
import logging
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)

# BCP-47 regex - strict match from start to end
_BCP47_RE = re.compile(
    r'^([a-z]{2,3})'                    # language: 2-3 letters
    r'(?:-([a-z]{4}))?'                 # optional script: 4 letters (e.g. Hant, Latn)
    r'(?:-([a-z]{2}|\d{3}))?'          # optional region: 2 letters or 3 digits (UN M49)
    r'$'                                 # Must match to end - no extra parts
)


def parse_bcp47(lang_code: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Parse a language code into (language, script, region).
    Accepts hyphens or underscores as separators, any case.
    Strips encoding suffixes (.UTF-8, etc.).
    Returns (None, None, None) if unparseable.

    Examples:
        >>> parse_bcp47("fi-FI")
        ('fi', None, 'FI')
        >>> parse_bcp47("zh-Hant-TW")
        ('zh', 'hant', 'tw')
        >>> parse_bcp47("en")
        ('en', None, None)
    """
    if not isinstance(lang_code, str) or not lang_code.strip():
        return None, None, None

    code = lang_code.strip().lower().replace('_', '-')
    
    # Remove encoding suffix if present
    if '.' in code:
        code = code.split('.')[0]
    
    match = _BCP47_RE.match(code)
    if not match:
        return None, None, None

    return match.groups()  # (lang, script, region)


def normalize_full_tag(lang_code: str, default: str = "en") -> str:
    """
    Full normalized tag for file naming / GLFM lookup.
    
    Examples:
        'zh-TW' -> 'zh-tw'
        'zh-Hant-TW' -> 'zh-hant-tw'
        'es-419' -> 'es-419'
        'FI' -> 'fi'
    """
    if not isinstance(lang_code, str) or not lang_code.strip():
        return default.lower()
    
    lang, script, region = parse_bcp47(lang_code)
    if not lang:
        logger.warning(f"Unparseable language code: {lang_code}, using '{default}'")
        return default.lower()
    
    parts = [lang]
    if script:
        parts.append(script)
    if region:
        parts.append(region)
    
    return '-'.join(parts)


def base_language(lang_code: str, default: str = "en") -> str:
    """
    Bare language subtag only, for services that don't support
    script/region (e.g. LibreTranslate).
    
    Examples:
        'zh-Hant-TW' -> 'zh'
        'fi-FI' -> 'fi'
        'en-US' -> 'en'
    """
    if not isinstance(lang_code, str) or not lang_code.strip():
        return default
    
    lang, _, _ = parse_bcp47(lang_code)
    return lang or default


def has_region(lang_code: str) -> bool:
    """Check if language code has a region subtag."""
    _, _, region = parse_bcp47(lang_code)
    return region is not None


def get_parent(lang_code: str, default: str = "en") -> str:
    """Get parent tag (language + script if present, without region)."""
    if not isinstance(lang_code, str) or not lang_code.strip():
        return default
    
    lang, script, _ = parse_bcp47(lang_code)
    if not lang:
        return default
    
    if script:
        return f"{lang}-{script}"
    return lang


def split_tag(lang_code: str) -> Dict[str, Any]:
    """
    Return structured dict from language tag.
    
    Returns:
        dict with keys: language, script, region, tag, valid
    
    Examples:
        >>> split_tag("fi-FI")
        {'language': 'fi', 'script': None, 'region': 'FI', 'tag': 'fi-fi', 'valid': True}
        >>> split_tag("invalid")
        {'language': None, 'script': None, 'region': None, 'tag': None, 'valid': False}
    """
    lang, script, region = parse_bcp47(lang_code)
    
    if lang:
        tag = normalize_full_tag(lang_code)
    else:
        tag = None
    
    return {
        "language": lang,
        "script": script,
        "region": region,
        "tag": tag,
        "valid": lang is not None,
    }


def is_valid(lang_code: str) -> bool:
    """
    Check if a language code is a valid BCP-47 tag.
    
    Examples:
        >>> is_valid("fi-FI")
        True
        >>> is_valid("zh-Hant-TW")
        True
        >>> is_valid("invalid")
        False
        >>> is_valid("")
        False
    """
    lang, _, _ = parse_bcp47(lang_code)
    return lang is not None


# --- Aliases for convenience ---

def normalize_language(lang_code: str, default: str = "en") -> str:
    """Alias for normalize_full_tag() for consistency."""
    return normalize_full_tag(lang_code, default)


# --- Test ---

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    print("=== lang_utils Tests ===\n")
    
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
        print(f"  parse_bcp47: {parse_bcp47(tag)!r}")
        print(f"  normalize_full_tag: {normalize_full_tag(tag)!r}")
        print(f"  base_language: {base_language(tag)!r}")
        print(f"  has_region: {has_region(tag)!r}")
        print(f"  get_parent: {get_parent(tag)!r}")
        print(f"  split_tag: {split_tag(tag)!r}")
        print(f"  is_valid: {is_valid(tag)!r}")
        print()
