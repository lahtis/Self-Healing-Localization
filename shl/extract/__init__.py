"""
File: shl/extract/__init__.py
Author: Tuomas Lähteenmäki
Version: 0.1.0
License: MIT
Description:
    Static translation key extraction for SHL.

    Scans Python source files for ui_text() / L() / get_text() /
    template() calls and extracts the literal key and default value.
    Keys are written in Localizer format (key -> default) so the
    output can be used directly as a base locale file.

    The extractor is dependency-free: only the Python standard
    library is used. It relies on ast.parse() which is the same
    parser Python itself uses. Code is never imported or executed.
"""

from .scanner import (
    DEFAULT_FUNCTION_NAMES,
    ExtractedKey,
    ScanResult,
    scan_file,
    scan_tree,
)
from .reporter import collect_keys
from .checker import check_locales, CheckReport

__all__ = [
    "DEFAULT_FUNCTION_NAMES",
    "ExtractedKey",
    "ScanResult",
    "scan_file",
    "scan_tree",
    "collect_keys",
    "check_locales",
    "CheckReport",
]

__version__ = "0.1.0"
