"""
File: shl/engine/translation/providers/yandex_languages.py
Author: Tuomas Lähteenmäki
Version: 0.3.0
License: MIT
Description:
    Single source of truth for Yandex supported language codes.

    All codes are already lowercase and use the two-letter ISO 639-1
    form (plus a few Yandex-specific variants like "mhr", "mrj",
    "sah", "udm"), so no normalization step is required.

    This module performs no HTTP calls. It only defines a constant.
"""

YANDEX_SUPPORTED_LANGUAGES_RAW = frozenset({
    "af", "am", "ar", "az", "ba", "be", "bg", "bn", "bs", "ca",
    "ceb", "cs", "cy", "da", "de", "el", "en", "eo", "es", "et",
    "eu", "fa", "fi", "fr", "ga", "gd", "gl", "gu", "he", "hi",
    "hr", "ht", "hu", "hy", "id", "is", "it", "ja", "jv", "ka",
    "kk", "km", "kn", "ko", "ky", "la", "lb", "lo", "lt", "lv",
    "mg", "mhr", "mi", "mk", "ml", "mn", "mr", "mrj", "ms", "mt",
    "my", "ne", "nl", "no", "pa", "pap", "pl", "pt", "ro", "ru",
    "sah", "si", "sk", "sl", "sq", "sr", "su", "sv", "sw", "ta",
    "te", "tg", "th", "tl", "tr", "tt", "udm", "uk", "ur", "uz",
    "vi", "xh", "yi", "zh",
})
