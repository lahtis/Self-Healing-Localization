"""
File: ai_translation.py — module for AI-powered translations.
Author: Tuomas Lähteenmäki
Version: 0.2.0
License: MIT
Description:
    Provides AI-powered translation capabilities with automatic fallback.
    - MyMemory as primary translation service (with optional email for higher limits)
    - LibreTranslate as fallback service
    - Smart routing: chooses best service based on language support
    - Automatic fallback if primary service fails (rate limit, downtime, etc.)
    - Error classification: rate limit, service unavailable, language not supported
    - Dynamic language list fetching from LibreTranslate with 24h cache
    - Fallback static language list from JSON file if API unavailable
    - MyMemory language support detection via test translation (cached 24h)
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

from shl.utils.lang_utils import base_language

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exceptions for translation errors
# ---------------------------------------------------------------------------

class TranslationError(Exception):
    """Base exception for translation errors."""
    pass


class ServiceUnavailableError(TranslationError):
    """Translation service is down or unreachable."""
    pass


class RateLimitExceededError(TranslationError):
    """Rate limit or quota exceeded."""
    pass


class LanguageNotSupportedError(TranslationError):
    """Language not supported by the service."""
    pass


class ProviderAccessError(TranslationError):
    """Access denied (banned, invalid API key, etc.)."""
    pass


class InvalidRequestError(TranslationError):
    """Invalid request (bad parameters, etc.)."""
    pass


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
    'https://libretranslate.com'
)
SHL_VERSION = "0.2.0"

# Timeouts
MYMEMORY_TIMEOUT = 10
LIBRETRANSLATE_TIMEOUT = 15

# Cache TTLs
TRANSLATION_CACHE_TTL = 3600  # 1 hour
LANGUAGE_CACHE_TTL = 86400    # 24 hours


# ---------------------------------------------------------------------------
# Static fallback language lists from JSON files
# ---------------------------------------------------------------------------

def _load_fallback_languages(filename: str) -> Dict[str, str]:
    """Load fallback language list from JSON file."""
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        json_path = os.path.join(base_dir, 'data', 'languages', filename)
        
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load fallback languages from {filename}: {e}")
        return {}


# Load fallback lists
_MYMEMORY_FALLBACK_LANGUAGES = _load_fallback_languages('mymemory_fallback.json')
_LIBRETRANSLATE_FALLBACK_LANGUAGES = _load_fallback_languages('libretranslate_fallback.json')


# ---------------------------------------------------------------------------
# Translation Cache
# ---------------------------------------------------------------------------

class TranslationCache:
    """Translation cache to reduce API calls"""

    def __init__(self, ttl: int = TRANSLATION_CACHE_TTL, max_size: int = 10000):
        self.cache: Dict[str, tuple] = {}
        self.ttl = ttl
        self.max_size = max_size

    def _generate_key(self, text: str, source_lang: str, target_lang: str) -> str:
        raw_key = f"{text}:{source_lang}:{target_lang}"
        return hashlib.md5(raw_key.encode('utf-8')).hexdigest()

    def get(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        key = self._generate_key(text, source_lang, target_lang)

        if key in self.cache:
            cached_text, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                logger.debug(f"Cache hit: '{text[:50]}...'")
                return cached_text
            del self.cache[key]

        return None

    def set(self, text: str, translated: str, source_lang: str, target_lang: str) -> None:
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache, key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]

        key = self._generate_key(text, source_lang, target_lang)
        self.cache[key] = (translated, time.time())

    def clear(self) -> None:
        self.cache.clear()

    def size(self) -> int:
        return len(self.cache)


_translation_cache = TranslationCache()


# ---------------------------------------------------------------------------
# Language list cache (24 hours) for LibreTranslate
# ---------------------------------------------------------------------------

_language_cache: Dict[str, tuple] = {}


def get_supported_languages(base_url: str = None) -> Dict[str, str]:
    """
    Fetch supported languages from a LibreTranslate instance.
    Results are cached for 24 hours.
    Falls back to static list from JSON file if API unavailable.
    """
    if base_url is None:
        base_url = LIBRETRANSLATE_URL

    cache_key = base_url.rstrip('/')

    if cache_key in _language_cache:
        languages, timestamp = _language_cache[cache_key]
        if time.time() - timestamp < LANGUAGE_CACHE_TTL:
            return languages

    try:
        url = f"{cache_key}/languages"
        req = Request(url, headers={
            'User-Agent': f'SHL-Client/{SHL_VERSION}',
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
        logger.warning(f"Failed to fetch language list from LibreTranslate: {e}")
        logger.info("Using static fallback language list from JSON")
        _language_cache[cache_key] = (_LIBRETRANSLATE_FALLBACK_LANGUAGES, time.time())
        return _LIBRETRANSLATE_FALLBACK_LANGUAGES


# ---------------------------------------------------------------------------
# MyMemory language support detection (test translation with cache)
# ---------------------------------------------------------------------------

_mymemory_support_cache: Dict[str, tuple] = {}


def is_language_supported_by_mymemory(lang_code: str) -> bool:
    """
    Test whether MyMemory supports a language.
    Results are cached for 24 hours.
    Falls back to static list from JSON if test fails.
    """
    lang = base_language(lang_code)
    
    if lang in _mymemory_support_cache:
        supported, timestamp = _mymemory_support_cache[lang]
        if time.time() - timestamp < LANGUAGE_CACHE_TTL:
            return supported

    try:
        # Test with a tiny translation
        result = _translate_mymemory("test", lang, "en", email=MYMEMORY_EMAIL)
        supported = result is not None and result != "test"
    except LanguageNotSupportedError:
        supported = False
    except Exception:
        # If test fails, check fallback list
        supported = lang in _MYMEMORY_FALLBACK_LANGUAGES

    _mymemory_support_cache[lang] = (supported, time.time())
    logger.debug(f"MyMemory language support for '{lang}': {supported}")
    return supported


def get_all_supported_languages() -> Dict[str, Dict[str, str]]:
    """
    Get supported languages from both services.
    MyMemory uses test-based detection, LibreTranslate uses API.
    """
    return {
        "mymemory": _MYMEMORY_FALLBACK_LANGUAGES,
        "libretranslate": get_supported_languages()
    }


def get_best_provider(
    target_lang: str,
    source_lang: str = "en",
    supported_languages: Dict[str, Dict[str, str]] = None
) -> str:
    """
    Choose the best translation provider for a language pair.
    
    Uses cached test translations for MyMemory and language list for LibreTranslate.
    """
    target = base_language(target_lang)
    source = base_language(source_lang)

    # 1. Check MyMemory support (using cached test results)
    if is_language_supported_by_mymemory(target):
        if is_language_supported_by_mymemory(source):
            return "mymemory"

    # 2. Check LibreTranslate support (from language list)
    if supported_languages is None:
        supported_languages = get_all_supported_languages()

    libretranslate_langs = supported_languages.get("libretranslate", {})
    if target in libretranslate_langs and source in libretranslate_langs:
        return "libretranslate"

    return "none"


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
# MyMemory API
# ---------------------------------------------------------------------------

def _translate_mymemory(
    text: str,
    target_lang: str,
    source_lang: str,
    email: Optional[str] = None
) -> Optional[str]:
    """
    Translate text via MyMemory API with error classification.
    
    Raises:
        RateLimitExceededError: 429 or quota message
        ServiceUnavailableError: 5xx, network errors, timeout
        LanguageNotSupportedError: 404 or 400 with unsupported message
        ProviderAccessError: 403
        InvalidRequestError: 400 (other)
        TranslationError: Other errors
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
            'User-Agent': f'SHL-Client/{SHL_VERSION}',
            'Accept': 'application/json'
        })

        with urlopen(req, timeout=MYMEMORY_TIMEOUT) as response:
            response_data = json.loads(response.read().decode('utf-8'))

            response_status = response_data.get("responseStatus")
            response_details = response_data.get("responseData", {})
            
            # Check for quota/rate limit messages
            quota_reached = response_data.get("quotaReached", False)
            response_warning = response_details.get("warning", "")
            
            # Check if it looks like a rate limit or quota message
            if quota_reached or "quota" in response_warning.lower():
                raise RateLimitExceededError(f"MyMemory: quota reached: {response_warning}")

            # HTTP status code classification
            if response_status == 403:
                raise ProviderAccessError("MyMemory: Access denied")
            if response_status == 429:
                raise RateLimitExceededError("MyMemory: Rate limit exceeded")
            if response_status >= 500:
                raise ServiceUnavailableError(f"MyMemory: Server error {response_status}")
            if response_status == 404:
                raise LanguageNotSupportedError(f"MyMemory: Language not supported")
            if response_status == 400:
                # Could be unsupported language or bad request
                if "language" in str(response_data).lower():
                    raise LanguageNotSupportedError("MyMemory: Language not supported")
                raise InvalidRequestError(f"MyMemory: Bad request {response_status}")
            if response_status != 200:
                raise TranslationError(f"MyMemory: Unexpected status {response_status}")

            translated = response_details.get("translatedText")

            if translated and translated != text:
                logger.debug(f"MyMemory success: '{translated[:100]}...'")
                return translated
            
            logger.warning("MyMemory returned empty or same text")
            return None

    except HTTPError as e:
        if e.code == 403:
            raise ProviderAccessError(f"MyMemory HTTP 403")
        elif e.code == 429:
            raise RateLimitExceededError(f"MyMemory HTTP 429")
        elif e.code >= 500:
            raise ServiceUnavailableError(f"MyMemory HTTP {e.code}")
        elif e.code == 404:
            raise LanguageNotSupportedError("MyMemory language not supported")
        elif e.code == 400:
            try:
                error_body = e.read().decode('utf-8')
                if "language" in error_body.lower():
                    raise LanguageNotSupportedError("MyMemory language not supported")
            except Exception:
                pass
            raise InvalidRequestError(f"MyMemory HTTP 400")
        else:
            raise TranslationError(f"MyMemory HTTP {e.code}")

    except URLError as e:
        raise ServiceUnavailableError(f"MyMemory network error: {e.reason}")
    except TimeoutError:
        raise ServiceUnavailableError("MyMemory timeout")
    except Exception as e:
        # If it's already one of our exceptions, re-raise it
        if isinstance(e, (RateLimitExceededError, ServiceUnavailableError, 
                         LanguageNotSupportedError, ProviderAccessError, 
                         InvalidRequestError, TranslationError)):
            raise
        raise TranslationError(f"MyMemory unexpected error: {type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# LibreTranslate API
# ---------------------------------------------------------------------------

def _translate_libretranslate(
    text: str,
    target_lang: str,
    source_lang: str,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None
) -> Optional[str]:
    """
    Translate text via LibreTranslate API with error classification.
    
    Raises:
        RateLimitExceededError: 429
        ServiceUnavailableError: 5xx, network errors, timeout
        LanguageNotSupportedError: 404 or language not supported
        ProviderAccessError: 403 (banned, invalid API key, etc.)
        InvalidRequestError: 400
        TranslationError: Other errors
    """
    _base_url = (base_url or LIBRETRANSLATE_URL).rstrip('/')
    _api_key = api_key or LIBRETRANSLATE_API_KEY

    try:
        url = f"{_base_url}/translate"

        request_body = {
            "q": text,
            "source": source_lang,
            "target": target_lang,
            "format": "text"
        }

        if _api_key:
            request_body["api_key"] = _api_key

        request_data = json.dumps(request_body).encode('utf-8')

        logger.debug(
            f"LibreTranslate request: {source_lang}->{target_lang} "
            f"(api_key={_mask_api_key(_api_key)})"
        )

        req = Request(url, data=request_data, headers={
            'Content-Type': 'application/json',
            'User-Agent': f'SHL-Client/{SHL_VERSION}',
            'Accept': 'application/json'
        })

        with urlopen(req, timeout=LIBRETRANSLATE_TIMEOUT) as response:
            response_data = json.loads(response.read().decode('utf-8'))

            translated = response_data.get("translatedText")

            if translated and translated != text:
                logger.debug(f"LibreTranslate success: '{translated[:100]}...'")
                return translated
            
            logger.warning("LibreTranslate returned empty or same text")
            return None

    except HTTPError as e:
        try:
            error_body = e.read().decode('utf-8')
            logger.debug(f"LibreTranslate error details: {error_body}")
        except Exception:
            error_body = ""

        if e.code == 403:
            raise ProviderAccessError(f"LibreTranslate: Access denied (banned/invalid API key)")
        elif e.code == 429:
            raise RateLimitExceededError("LibreTranslate: Rate limit exceeded")
        elif e.code >= 500:
            raise ServiceUnavailableError(f"LibreTranslate: Server error {e.code}")
        elif e.code == 404:
            raise LanguageNotSupportedError("LibreTranslate: Language not supported")
        elif e.code == 400:
            if "language" in error_body.lower():
                raise LanguageNotSupportedError("LibreTranslate: Language not supported")
            raise InvalidRequestError(f"LibreTranslate: Bad request {e.code}")
        else:
            raise TranslationError(f"LibreTranslate HTTP {e.code}")

    except URLError as e:
        raise ServiceUnavailableError(f"LibreTranslate network error: {e.reason}")
    except TimeoutError:
        raise ServiceUnavailableError("LibreTranslate timeout")
    except Exception as e:
        # If it's already one of our exceptions, re-raise it
        if isinstance(e, (RateLimitExceededError, ServiceUnavailableError, 
                         LanguageNotSupportedError, ProviderAccessError, 
                         InvalidRequestError, TranslationError)):
            raise
        raise TranslationError(f"LibreTranslate unexpected error: {type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# Main translation function with smart routing
# ---------------------------------------------------------------------------

def translate_text(
    text: str,
    target_lang: str = "fi",
    source_lang: str = "en",
    use_cache: bool = True,
    smart_routing: bool = True,
    max_retries: int = 2,
    retry_delay: int = 1,
    libretranslate_url: Optional[str] = None,
    libretranslate_api_key: Optional[str] = None,
    mymemory_email: Optional[str] = None
) -> str:
    """
    Translate text with smart routing and automatic fallback.
    
    Translation flow:
    1. Check cache
    2. Choose best provider based on language support
    3. Try primary provider
    4. If fails (rate limit, downtime, etc.), fallback to secondary
    5. If all fail, return original text
    
    Args:
        text: Text to translate
        target_lang: Target language
        source_lang: Source language (default: "en")
        use_cache: Use cache (default: True)
        smart_routing: Choose best provider (default: True)
        max_retries: Maximum retries per provider (default: 2)
        retry_delay: Delay between retries in seconds (default: 1)
        libretranslate_url: Override LibreTranslate server URL
        libretranslate_api_key: Override LibreTranslate API key
        mymemory_email: Override MyMemory email for higher daily limits
    
    Returns:
        Translated text or original text if translation fails
    """
    if not text or not isinstance(text, str):
        logger.warning("translate_text: empty or invalid text")
        return ""

    # Normalize language codes
    target = base_language(target_lang)
    source = base_language(source_lang)

    if target == source:
        return text

    # Check cache
    if use_cache:
        cached = _translation_cache.get(text, source, target)
        if cached is not None:
            return cached

    # Get supported languages
    supported_languages = get_all_supported_languages()
    
    # Choose provider
    if smart_routing:
        provider = get_best_provider(target, source, supported_languages)
    else:
        provider = "mymemory"

    # Define provider order with fallback
    if provider == "mymemory":
        order = ["mymemory", "libretranslate"]
    elif provider == "libretranslate":
        order = ["libretranslate", "mymemory"]
    elif provider == "none":
        logger.warning(f"No translation service supports {source}→{target}")
        return text
    else:
        order = ["mymemory", "libretranslate"]

    # Try providers in order
    translated = None
    errors = []

    for service in order:
        for attempt in range(max_retries):
            try:
                if service == "mymemory":
                    translated = _translate_mymemory(text, target, source, mymemory_email)
                else:  # libretranslate
                    translated = _translate_libretranslate(
                        text, target, source,
                        libretranslate_url, libretranslate_api_key
                    )

                if translated:
                    if use_cache:
                        _translation_cache.set(text, translated, source, target)
                    return translated

            except RateLimitExceededError as e:
                logger.warning(f"{service} rate limit exceeded: {e}")
                errors.append(f"{service}: rate limit")
                break  # Move to next service
            
            except ProviderAccessError as e:
                logger.warning(f"{service} access denied: {e}")
                errors.append(f"{service}: access denied")
                break  # Move to next service
            
            except ServiceUnavailableError as e:
                logger.warning(f"{service} unavailable: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                errors.append(f"{service}: unavailable")
                break  # Move to next service
            
            except LanguageNotSupportedError as e:
                logger.warning(f"{service} doesn't support language: {e}")
                errors.append(f"{service}: language not supported")
                break  # Move to next service
            
            except InvalidRequestError as e:
                logger.warning(f"{service} invalid request: {e}")
                errors.append(f"{service}: invalid request")
                break  # Move to next service
            
            except TranslationError as e:
                logger.warning(f"{service} error: {e}")
                errors.append(f"{service}: {e}")
                break  # Move to next service
            
            except Exception as e:
                logger.error(f"{service} unexpected error: {e}")
                errors.append(f"{service}: unexpected")
                break

    # All providers failed
    logger.error(f"All translation services failed: {', '.join(errors)}")
    return text


# ---------------------------------------------------------------------------
# AITranslator class
# ---------------------------------------------------------------------------

class AITranslator:
    """
    Extensible AI translator class for future needs.

    Supports multiple translation services and provides
    a unified interface for translations with smart routing.
    """

    def __init__(
        self,
        provider: str = "auto",
        libretranslate_url: Optional[str] = None,
        libretranslate_api_key: Optional[str] = None,
        mymemory_email: Optional[str] = None
    ):
        self.provider = provider.lower() if provider else "none"
        self.libretranslate_url = libretranslate_url
        self.libretranslate_api_key = libretranslate_api_key
        self.mymemory_email = mymemory_email
        self.cache = TranslationCache()
        self._supported_languages = None
        self._last_fetch = 0
        
        logger.info(f"AITranslator initialized: provider={self.provider}")

    def get_supported_languages(self, force_refresh: bool = False) -> Dict[str, Dict[str, str]]:
        """Get supported languages from both services with 24h cache."""
        if not force_refresh and self._supported_languages is not None:
            if time.time() - self._last_fetch < LANGUAGE_CACHE_TTL:
                return self._supported_languages
        
        self._supported_languages = get_all_supported_languages()
        self._last_fetch = time.time()
        return self._supported_languages

    def get_best_provider(self, target_lang: str, source_lang: str = "en") -> str:
        """Get best provider for language pair."""
        supported = self.get_supported_languages()
        return get_best_provider(target_lang, source_lang, supported)

    def is_language_supported(self, lang_code: str) -> bool:
        """Check if language is supported by any service."""
        supported = self.get_supported_languages()
        base = base_language(lang_code)
        return (base in supported.get("mymemory", {}) or 
                base in supported.get("libretranslate", {}))

    def translate(self, text: str, target_lang: str = "fi", source_lang: str = "en") -> str:
        """Translate a single text with smart routing."""
        if self.provider == "none":
            return text

        result = translate_text(
            text,
            target_lang,
            source_lang,
            use_cache=True,
            smart_routing=(self.provider == "auto"),
            max_retries=2,
            retry_delay=1,
            libretranslate_url=self.libretranslate_url,
            libretranslate_api_key=self.libretranslate_api_key,
            mymemory_email=self.mymemory_email
        )
        
        if result and result != text:
            target = base_language(target_lang)
            source = base_language(source_lang)
            self.cache.set(text, result, source, target)
        
        return result

    def batch_translate(
        self,
        texts: Dict[str, str],
        target_lang: str,
        source_lang: str = "en"
    ) -> Dict[str, str]:
        """Translate multiple texts at once."""
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
    langs = get_all_supported_languages()
    print(f"MyMemory: {len(langs.get('mymemory', {}))} languages (static fallback)")
    print(f"LibreTranslate: {len(langs.get('libretranslate', {}))} languages")

    translator = AITranslator(provider="auto")
    batch_result = translator.batch_translate(
        {"greeting": "Hello", "farewell": "Goodbye"},
        "fi"
    )
    print(f"\nBatch translation: {batch_result}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    test_translation()
