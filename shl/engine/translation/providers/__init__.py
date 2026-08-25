"""
File: __init__.py — Translation providers package.
Author: Tuomas Lähteenmäki
Version: 0.2.6
License: MIT
Description: Central export manifest for the SHL translation providers package.
             Exposes routing interfaces, provider adapters, caching mechanics,
             and exception taxonomy under a unified public API namespace.
"""

from .base import TranslationProvider
from .mymemory import MyMemoryAdapter
from .libretranslate import LibreTranslateAdapter
from .deepl import DeepLAdapter
from .googlev2 import GoogleV2Adapter
from .papago import PapagoAdapter
from .microsoft import MicrosoftTranslatorAdapter
from .yandex import YandexAdapter
from .local_translalator import LocalTranslatorAdapter


__all__ = [
    "TranslationProvider",
    "MyMemoryAdapter",
    "LibreTranslateAdapter",
    "DeepLAdapter",
    "GoogleV2Adapter",
    "PapagoAdapter",
    "MicrosoftTranslatorAdapter",
    "YandexAdapter",
    "LocalTranslatorAdapter",
]
