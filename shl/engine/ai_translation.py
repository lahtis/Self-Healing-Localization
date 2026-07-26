"""
File: ai_translation.py — module for AI-powered translations.
Author: Tuomas Lähteenmäki
Version: 0.1.6
License: MIT
Description:
    Provides AI-powered translation capabilities with automatic fallback.
    - MyMemory as primary translation service
    - LibreTranslate as fallback service
    - Translation caching to reduce API calls
    - Response validation and error logging
    - Graceful degradation on failures
"""

import json
import logging
import hashlib
import time
from typing import Optional, Dict, Any
from urllib.request import Request, urlopen
from urllib.parse import quote
from urllib.error import URLError, HTTPError

logger = logging.getLogger(__name__)


class TranslationCache:
    """Translation cache to reduce API calls"""
    
    def __init__(self, ttl: int = 3600):
        """
        Initialize cache.
        
        Args:
            ttl: Time-to-live in seconds (default: 1 hour)
        """
        self.cache: Dict[str, tuple] = {}
        self.ttl = ttl
    
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
            else:
                # Expired, remove from cache
                del self.cache[key]
                logger.debug("Expired cache entry removed")
        
        return None
    
    def set(self, text: str, translated: str, source_lang: str, target_lang: str):
        """Store translation in cache"""
        key = self._generate_key(text, source_lang, target_lang)
        self.cache[key] = (translated, time.time())
        logger.debug(f"Cached: '{text[:50]}...' -> '{translated[:50]}...'")
    
    def clear(self):
        """Clear cache"""
        self.cache.clear()
        logger.debug("Cache cleared")
    
    def size(self) -> int:
        """Return cache size"""
        return len(self.cache)


# Global cache
_translation_cache = TranslationCache()


def translate_text(
    text: str,
    target_lang: str = "fi",
    source_lang: str = "en",
    use_cache: bool = True
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
    
    Returns:
        Translated text or original text if translation fails
    """
    # Validate input
    if not text or not isinstance(text, str):
        logger.warning("translate_text: empty or invalid text")
        return text if text else ""
    
    # Same language → no translation needed
    if target_lang == source_lang:
        return text
    
    # Check cache
    if use_cache:
        cached = _translation_cache.get(text, source_lang, target_lang)
        if cached is not None:
            return cached
    
    logger.debug(f"Translating: '{text[:100]}...' {source_lang}->{target_lang}")
    
    # Try primary translation service (MyMemory)
    translated = _translate_mymemory(text, target_lang, source_lang)
    
    # If MyMemory failed, try fallback (LibreTranslate)
    if translated is None:
        logger.info("MyMemory failed, trying LibreTranslate")
        translated = _translate_libretranslate(text, target_lang, source_lang)
    
    # If both failed, return original text
    if translated is None:
        logger.warning("Translation completely failed, returning original text")
        return text
    
    # Store in cache
    if use_cache:
        _translation_cache.set(text, translated, source_lang, target_lang)
    
    return translated


def _translate_mymemory(text: str, target_lang: str, source_lang: str) -> Optional[str]:
    """
    Translate text via MyMemory API.
    
    Args:
        text: Text to translate
        target_lang: Target language
        source_lang: Source language
    
    Returns:
        Translated text or None if translation fails
    """
    try:
        langpair = f"{source_lang}|{target_lang}"
        encoded_text = quote(text)
        url = f"https://api.mymemory.translated.net/get?q={encoded_text}&langpair={langpair}"
        
        logger.debug(f"MyMemory request: {url[:100]}...")
        
        req = Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (SHL-Client/0.1.6)',
            'Accept': 'application/json'
        })
        
        with urlopen(req, timeout=10) as response:
            response_data = json.loads(response.read().decode('utf-8'))
            
            # Check responseStatus
            response_status = response_data.get("responseStatus")
            if response_status != 200:
                logger.warning(f"MyMemory invalid responseStatus: {response_status}")
                logger.debug(f"MyMemory response: {response_data}")
                return None
            
            # Get translated text
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


def _translate_libretranslate(text: str, target_lang: str, source_lang: str) -> Optional[str]:
    """
    Translate text via LibreTranslate API (fallback).
    
    Uses a public free instance.
    Note: Public API may have limitations.
    
    Args:
        text: Text to translate
        target_lang: Target language
        source_lang: Source language
    
    Returns:
        Translated text or None if translation fails
    """
    # LibreTranslate uses different language codes than MyMemory
    # Map common language codes
    lang_map = {
        "fi": "fi",  # Finnish
        "sv": "sv",  # Swedish
        "en": "en",  # English
        "de": "de",  # German
        "fr": "fr",  # French
        "es": "es",  # Spanish
        "ru": "ru",  # Russian
        "zh": "zh",  # Chinese
        "ja": "ja",  # Japanese
    }
    
    lt_source = lang_map.get(source_lang, source_lang)
    lt_target = lang_map.get(target_lang, target_lang)
    
    try:
        # Public LibreTranslate instance
        url = "https://libretranslate.com/translate"
        
        # Alternative public instances:
        # url = "https://translate.argosopentech.com/translate"
        # url = "https://translate.fortytwo-it.com/translate"
        
        request_data = json.dumps({
            "q": text,
            "source": lt_source,
            "target": lt_target,
            "format": "text"
        }).encode('utf-8')
        
        logger.debug(f"LibreTranslate request: {lt_source}->{lt_target}")
        
        req = Request(url, data=request_data, headers={
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (SHL-Client/0.1.6)',
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


class AITranslator:
    """
    Extensible AI translator class for future needs.
    
    Supports multiple translation services and provides
    a unified interface for translations.
    """
    
    def __init__(self, provider: str = "auto"):
        """
        Initialize AI translator.
        
        Args:
            provider: Translation service ("auto", "mymemory", "libretranslate", "none")
        """
        self.provider = provider.lower() if provider else "none"
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
        
        # Check cache
        cached = self.cache.get(text, source_lang, target_lang)
        if cached:
            return cached
        
        # Translate with selected service
        if self.provider == "mymemory":
            translated = _translate_mymemory(text, target_lang, source_lang)
        elif self.provider == "libretranslate":
            translated = _translate_libretranslate(text, target_lang, source_lang)
        else:  # "auto" - use default order
            translated = translate_text(text, target_lang, source_lang, use_cache=False)
        
        if translated:
            self.cache.set(text, translated, source_lang, target_lang)
            return translated
        
        return text
    
    def batch_translate(self, texts: Dict[str, str], target_lang: str, source_lang: str = "en") -> Dict[str, str]:
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
    
    def clear_cache(self):
        """Clear cache"""
        self.cache.clear()


# Utility function for testing
def test_translation():
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
    
    # Test cache
    print(f"\nCache size: {_translation_cache.size()}")
    
    # Test AITranslator class
    translator = AITranslator(provider="auto")
    batch_result = translator.batch_translate(
        {"greeting": "Hello", "farewell": "Goodbye"},
        "fi"
    )
    print(f"Batch translation: {batch_result}")


if __name__ == "__main__":
    # Configure logging for testing
    logging.basicConfig(level=logging.DEBUG)
    test_translation()
