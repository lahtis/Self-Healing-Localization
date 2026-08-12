"""
Translation providers package.
"""

from .base import TranslationProvider
from .mymemory import MyMemoryAdapter
from .libretranslate import LibreTranslateAdapter
from .deepl import DeepLAdapter
from .googlev2 import GoogleV2Adapter

__all__ = [
    "TranslationProvider",
    "MyMemoryAdapter",
    "LibreTranslateAdapter",
    "DeepLAdapter",
    "GoogleV2Adapter",
]
