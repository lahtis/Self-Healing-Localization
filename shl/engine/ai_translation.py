"""
File: ai_translation.py — module for AI-powered translations.
Author: Tuomas Lähteenmäki
Version: 0.1.7
License: MIT
Description:
    Provides AI-powered translation capabilities with automatic fallback.
    - MyMemory as primary translation service (with optional email for higher limits)
    - LibreTranslate as fallback service (with automatic language code normalization)
    - Dynamic language list fetching with 24h cache
    - Translation caching to reduce API calls
    - API key support via .env file
    - Detailed error logging for common API errors (403, 429, etc.)
    - Graceful degradation on failures
"""

import json
import logging
import hashlib
import os
import time
from typing import Optional, Dict, Any
from urllib.request import Request, urlopen
from urllib.parse import quote
from urllib.error import URLError, HTTPError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# .env loading (no external dependencies)
# ---------------------------------------------------------------------------

def _load_env() -> None:
    """Load environment variables from .env file if it exists."""
    env_path = os.path.join(os.getcwd(), '.env')
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key not in os.environ:
                    os.environ[key] = value
    except Exception as e:
        logger.warning(f"Failed to load .env file: {e}")


_load_env()


# ---------------------------------------------------------------------------
# Configuration (can be overridden via environment variables)
# ---------------------------------------------------------------------------

MYMEMORY_EMAIL = os.environ.get('MYMEMORY_EMAIL', '')
LIBRETRANSLATE_API_KEY = os.environ.get('LIBRETRANSLATE_API_KEY', '')
LIBRETRANSLATE_URL = os.environ.get(
    'LIBRETRANSLATE_URL',
    'https://translate.argosopentech.com'
)
SHL_VERSION = "0.1.7"


# ---------------------------------------------------------------------------
# Translation Cache
# ---------------------------------------------------------------------------

class TranslationCache:
    """Translation cache to reduce API calls"""

    def __init__(self, ttl: int = 3600, max_size: int = 10000):
        """
        Initialize cache.

        Args:
            ttl: Time-to-live in seconds (default: 1 hour)
            max_size: Maximum number of cache entries (default: 10000)
        """
        self.cache: Dict[str, tuple] = {}
        self.ttl = ttl
        self.max_size = max_size

    def _generate_key(self, text: str, source_lang: str, target_lang: str) -> str:
        """Generate cache key based on text and languages"""
        raw_key = f"{text}:{source_lang}:{target_lang}"
        return hashlib.md5(raw_key.encode('utf-8')).hexdigest()

    def get(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """Get translation from cache"""
        key = self._generate_key(text, source_lang, target_lang)

        if key in self.cache:
            cached_text, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                logger.debug(f"Cache hit: '{text[:50]}...'")
                return cached_text
            del self.cache[key]
            logger.debug("Expired cache entry removed")

        return None

    def set(self, text: str, translated: str, source_lang: str, target_lang: str) -> None:
        """Store translation in cache"""
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache, key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
            logger.debug("Cache full, oldest entry removed")

        key = self._generate_key(text, source_lang, target_lang)
        self.cache[key] = (translated, time.time())
        logger.debug(f"Cached: '{text[:50]}...' -> '{translated[:50]}...'")

    def clear(self) -> None:
        """Clear cache"""
        self.cache.clear()
        logger.debug("Cache cleared")

    def size(self) -> int:
        """Return cache size"""
        return len(self.cache)


_translation_cache = TranslationCache()


# ---------------------------------------------------------------------------
# Language list cache
# ---------------------------------------------------------------------------

_language_cache: Dict[str, tuple] = {}
_LANGUAGE_CACHE_TTL = 86400  # 24 hours


def get_supported_languages(base_url: str = None) -> Dict[str, str]:
    """
    Fetch supported languages from a LibreTranslate instance.
    Results are cached for 24 hours.

    Args:
        base_url: Base URL of the LibreTranslate instance

    Returns:
        Dictionary of {language_code: language_name}
    """
    if base_url is None:
        base_url = LIBRETRANSLATE_URL

    cache_key = base_url.rstrip('/')

    if cache_key in _language_cache:
        languages, timestamp = _language_cache[cache_key]
        if time.time() - timestamp < _LANGUAGE_CACHE_TTL:
            return languages

    try:
        url = f"{cache_key}/languages"
        req = Request(url, headers={
            'User-Agent': f'Mozilla/5.0 (SHL-Client/{SHL_VERSION})',
            'Accept': 'application/json'
        })

        logger.debug(f"Fetching supported languages from: {url}")

        with urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            languages = {
                lang["code"]: lang["name"]
                for lang in data
                if "code" in lang and "name" in lang
            }

            _language_cache[cache_key] = (languages, time.time())
            logger.info(f"Fetched {len(languages)} supported languages from LibreTranslate")
            return languages

    except Exception as e:
        logger.error(f"Failed to fetch language list: {e}")
        if cache_key in _language_cache:
            logger.info("Using cached language list")
            return _language_cache[cache_key][0]
        return {}


# ---------------------------------------------------------------------------
# Language code normalization
# ---------------------------------------------------------------------------

def _normalize_lang_code(lang_code: str) -> str:
    """
    Normalize a language code for LibreTranslate.
    Strips region subtags (e.g., 'en-US' → 'en').
    Handles special cases like Chinese.
    """
    code = lang_code.strip().lower()

    if code.startswith('zh'):
        return 'zh'

    if '-' in code:
        code = code.split('-')[0]

    return code


# ---------------------------------------------------------------------------
# API key masking for logging
# ---------------------------------------------------------------------------

def _mask_api_key(key: str) -> str:
    """Mask API key for safe logging."""
    if not key:
        return "(not set)"
    if len(key) <= 8:
        return '*' * len(key)
    return key[:4] + '*' * (len(key) - 8) + key[-4:]


# ---------------------------------------------------------------------------
# Main translation function
# ---------------------------------------------------------------------------

def translate_text(
    text: str,
    target_lang: str = "fi",
    source_lang: str = "en",
    use_cache: bool = True,
    libretranslate_url: Optional[str] = None,
    libretranslate_api_key: Optional[str] = None,
    mymemory_email: Optional[str] = None
) -> str:
    """
    Translate text automatically.

    Translation order:
    1. Check cache
    2. Try MyMemory API
    3. Fallback: LibreTranslate API
    4. Final fallback: return original text

    Args:
        text: Text to translate
        target_lang: Target language (default: "fi")
        source_lang: Source language (default: "en")
        use_cache: Use cache (default: True)
        libretranslate_url: Override LibreTranslate server URL
        libretranslate_api_key: Override LibreTranslate API key
        mymemory_email: Override MyMemory email for higher daily limits

    Returns:
        Translated text or original text if translation fails
    """
    if not text or not isinstance(text, str):
        logger.warning("translate_text: empty or invalid text")
        return text if text else ""

    if target_lang == source_lang:
        return text

    if use_cache:
        cached = _translation_cache.get(text, source_lang, target_lang)
        if cached is not None:
            return cached

    logger.debug(f"Translating: '{text[:100]}...' {source_lang}->{target_lang}")

    translated = _translate_mymemory(text, target_lang, source_lang, mymemory_email)

    if translated is None:
        logger.info("MyMemory failed, trying LibreTranslate")
        translated = _translate_libretranslate(
            text, target_lang, source_lang,
            libretranslate_url, libretranslate_api_key
        )

    if translated is None:
        logger.warning("Translation completely failed, returning original text")
        return text

    if use_cache:
        _translation_cache.set(text, translated, source_lang, target_lang)

    return translated


# ---------------------------------------------------------------------------
# MyMemory API
# ---------------------------------------------------------------------------

def _translate_mymemory(
    text: str,
    target_lang: str,
    source_lang: str,
    email: Optional[str] = None
) -> Optional[str]:
    """
    Translate text via MyMemory API.

    Args:
        text: Text to translate
        target_lang: Target language
        source_lang: Source language
        email: Optional email for higher daily limit (30k words instead of 1k)

    Returns:
        Translated text or None if translation fails
    """
    try:
        langpair = f"{source_lang}|{target_lang}"
        encoded_text = quote(text)
        url = f"https://api.mymemory.translated.net/get?q={encoded_text}&langpair={langpair}"

        email_to_use = email or MYMEMORY_EMAIL
        if email_to_use:
            url += f"&de={quote(email_to_use)}"

        logger.debug(f"MyMemory request: {url[:120]}...")

        req = Request(url, headers={
            'User-Agent': f'Mozilla/5.0 (SHL-Client/{SHL_VERSION})',
            'Accept': 'application/json'
        })

        with urlopen(req, timeout=10) as response:
            response_data = json.loads(response.read().decode('utf-8'))

            response_status = response_data.get("responseStatus")
            if response_status != 200:
                logger.warning(f"MyMemory invalid responseStatus: {response_status}")
                logger.debug(f"MyMemory response: {response_data}")
                return None

            response_details = response_data.get("responseData", {})
            translated = response_details.get("translatedText")

            if translated and translated != text:
                logger.debug(f"MyMemory success: '{translated[:100]}...'")
                return translated
            else:
                logger.warning("MyMemory returned empty or same text")
                return None

    except HTTPError as e:
        logger.error(f"MyMemory HTTP error: {e.code} - {e.reason}")
        return None
    except URLError as e:
        logger.error(f"MyMemory URL error: {e.reason}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"MyMemory JSON parse error: {e}")
        return None
    except Exception as e:
        logger.error(f"MyMemory unexpected error: {type(e).__name__}: {e}")
        return None


# ---------------------------------------------------------------------------
# LibreTranslate API (fallback)
# ---------------------------------------------------------------------------

def _translate_libretranslate(
    text: str,
    target_lang: str,
    source_lang: str,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None
) -> Optional[str]:
    """
    Translate text via LibreTranslate API (fallback).

    Uses a public free instance by default, or a custom instance
    configured via parameters or environment variables.

    Args:
        text: Text to translate
        target_lang: Target language
        source_lang: Source language
        base_url: Override LibreTranslate server URL
        api_key: Override LibreTranslate API key

    Returns:
        Translated text or None if translation fails
    """
    _base_url = (base_url or LIBRETRANSLATE_URL).rstrip('/')
    _api_key = api_key or LIBRETRANSLATE_API_KEY

    lt_source = _normalize_lang_code(source_lang)
    lt_target = _normalize_lang_code(target_lang)

    try:
        url = f"{_base_url}/translate"

        request_body = {
            "q": text,
            "source": lt_source,
            "target": lt_target,
            "format": "text"
        }

        if _api_key:
            request_body["api_key"] = _api_key

        request_data = json.dumps(request_body).encode('utf-8')

        logger.debug(
            f"LibreTranslate request: {lt_source}->{lt_target} "
            f"(api_key={_mask_api_key(_api_key)})"
        )

        req = Request(url, data=request_data, headers={
            'Content-Type': 'application/json',
            'User-Agent': f'Mozilla/5.0 (SHL-Client/{SHL_VERSION})',
            'Accept': 'application/json'
        })

        with urlopen(req, timeout=15) as response:
            response_data = json.loads(response.read().decode('utf-8'))

            translated = response_data.get("translatedText")

            if translated and translated != text:
                logger.debug(f"LibreTranslate success: '{translated[:100]}...'")
                return translated
            else:
                logger.warning("LibreTranslate returned empty or same text")
                return None

    except HTTPError as e:
        try:
            error_body = e.read().decode('utf-8')
            logger.debug(f"LibreTranslate error details: {error_body}")
        except Exception:
            pass

        if e.code == 403:
            logger.error(
                f"LibreTranslate HTTP 403 Forbidden. "
                f"This instance requires an API key. "
                f"Set LIBRETRANSLATE_API_KEY in .env or pass api_key parameter."
            )
        elif e.code == 429:
            logger.error(
                f"LibreTranslate HTTP 429 Too Many Requests. "
                f"Rate limit exceeded. Consider using an API key for higher limits."
            )
        else:
            logger.error(f"LibreTranslate HTTP error: {e.code} - {e.reason}")
        return None

    except URLError as e:
        logger.error(f"LibreTranslate URL error: {e.reason}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"LibreTranslate JSON parse error: {e}")
        return None
    except Exception as e:
        logger.error(f"LibreTranslate unexpected error: {type(e).__name__}: {e}")
        return None


# ---------------------------------------------------------------------------
# AITranslator class
# ---------------------------------------------------------------------------

class AITranslator:
    """
    Extensible AI translator class for future needs.

    Supports multiple translation services and provides
    a unified interface for translations.
    """

    def __init__(
        self,
        provider: str = "auto",
        libretranslate_url: Optional[str] = None,
        libretranslate_api_key: Optional[str] = None,
        mymemory_email: Optional[str] = None
    ):
        """
        Initialize AI translator.

        Args:
            provider: Translation service ("auto", "mymemory", "libretranslate", "none")
            libretranslate_url: Override LibreTranslate server URL
            libretranslate_api_key: Override LibreTranslate API key
            mymemory_email: Override MyMemory email for higher limits
        """
        self.provider = provider.lower() if provider else "none"
        self.libretranslate_url = libretranslate_url
        self.libretranslate_api_key = libretranslate_api_key
        self.mymemory_email = mymemory_email
        self.cache = TranslationCache()
        logger.info(f"AITranslator initialized: provider={self.provider}")

    def translate(self, text: str, target_lang: str = "fi", source_lang: str = "en") -> str:
        """
        Translate a single text.

        Args:
            text: Text to translate
            target_lang: Target language
            source_lang: Source language

        Returns:
            Translated text
        """
        if self.provider == "none":
            return text

        cached = self.cache.get(text, source_lang, target_lang)
        if cached:
            return cached

        if self.provider == "mymemory":
            translated = _translate_mymemory(
                text, target_lang, source_lang, self.mymemory_email
            )
        elif self.provider == "libretranslate":
            translated = _translate_libretranslate(
                text, target_lang, source_lang,
                self.libretranslate_url, self.libretranslate_api_key
            )
        else:
            translated = translate_text(
                text, target_lang, source_lang,
                use_cache=False,
                libretranslate_url=self.libretranslate_url,
                libretranslate_api_key=self.libretranslate_api_key,
                mymemory_email=self.mymemory_email
            )

        if translated:
            self.cache.set(text, translated, source_lang, target_lang)
            return translated

        return text

    def batch_translate(
        self,
        texts: Dict[str, str],
        target_lang: str,
        source_lang: str = "en"
    ) -> Dict[str, str]:
        """
        Translate multiple texts at once.

        Args:
            texts: Dictionary {key: text} of texts to translate
            target_lang: Target language
            source_lang: Source language

        Returns:
            Dictionary {key: translated_text}
        """
        if self.provider == "none":
            return texts

        translated_texts = {}
        for key, text in texts.items():
            translated_texts[key] = self.translate(text, target_lang, source_lang)

        logger.info(f"Batch translated {len(translated_texts)} texts")
        return translated_texts

    def get_cache_stats(self) -> Dict[str, Any]:
        """Return cache statistics"""
        return {
            "cache_size": self.cache.size(),
            "provider": self.provider
        }

    def clear_cache(self) -> None:
        """Clear cache"""
        self.cache.clear()


# ---------------------------------------------------------------------------
# Utility function for testing
# ---------------------------------------------------------------------------

def test_translation() -> None:
    """Test translation functionality"""
    test_texts = [
        ("Hello world", "fi"),
        ("Good morning", "sv"),
        ("Thank you very much", "de"),
    ]

    print("=== AI Translation Test ===")
    for text, target in test_texts:
        result = translate_text(text, target)
        print(f"EN -> {target.upper()}: '{text}' -> '{result}'")

    print(f"\nCache size: {_translation_cache.size()}")

    print("\nFetching supported languages...")
    langs = get_supported_languages()
    if langs:
        print(f"Supported languages: {len(langs)}")
        sample = list(langs.items())[:5]
        for code, name in sample:
            print(f"  {code}: {name}")

    translator = AITranslator(provider="auto")
    batch_result = translator.batch_translate(
        {"greeting": "Hello", "farewell": "Goodbye"},
        "fi"
    )
    print(f"\nBatch translation: {batch_result}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    test_translation()
