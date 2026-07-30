"""
File: lang_utils.py
Shared BCP-47 language tag parsing and normalization for SHL.
Single source of truth for region/script subtag handling.
"""

import re
import logging
from typing import Optional, Tuple

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
    'zh-TW' -> 'zh-tw', 'zh-Hant-TW' -> 'zh-hant-tw', 'es-419' -> 'es-419'
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
    script/region (e.g. LibreTranslate). 'zh-Hant-TW' -> 'zh'
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


def split_tag(lang_code: str) -> dict:
    """Return structured dict from language tag."""
    lang, script, region = parse_bcp47(lang_code)
    return {
        "language": lang,
        "script": script,
        "region": region,
        "tag": normalize_full_tag(lang_code) if lang else None
    }
