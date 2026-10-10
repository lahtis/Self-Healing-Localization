"""
File: shl/engine/translation/providers/libretranslate_community/__init__.py
Author: Tuomas Lähteenmäki
Version: 0.3.0
License: MIT
Description: LibreTranslate Community translation provider package.
Exposes the community adapter, its runtime language support registry,
and the endpoint loader under a single namespace.
"""

from .endpoints import load_endpoints
from .libretranslate_community import LibreTranslateCommunityAdapter
from .libretranslate_community_registry import (
    LibreTranslateCommunityRegistry,
)

__all__ = [
    "LibreTranslateCommunityAdapter",
    "LibreTranslateCommunityRegistry",
    "load_endpoints",
]
