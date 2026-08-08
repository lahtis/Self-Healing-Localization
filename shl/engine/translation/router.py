"""
Translation router with smart routing and automatic fallback.
"""

import logging
import time
import json
import os
from typing import Optional, Dict, Any

from shl.utils.lang_utils import base_language

from .cache import TranslationCache
from .exceptions import (
    TranslationError,
    ServiceUnavailableError,
    RateLimitExceededError,
    LanguageNotSupportedError,
    ProviderAccessError,
    InvalidRequestError,
)
from .metadata import TranslationRequest
from .providers.mymemory import MyMemoryAdapter
from .providers.libretranslate import LibreTranslateAdapter, get_supported_languages

logger = logging.getLogger(__name__)

# Cache TTLs
LANGUAGE_CACHE_TTL = 86400  # 24 hours
TRANSLATION_CACHE_TTL = 3600  # 1 hour
UNAVAILABLE_CACHE_TTL = 86400  # 24 hours

# Default configuration
MYMEMORY_DEFAULT_EMAIL = ""
LIBRETRANSLATE_DEFAULT_URL = "https://libretranslate.com"
LIBRETRANSLATE_DEFAULT_API_KEY = ""

# Global caches
_translation_cache = TranslationCache()
_unavailable_cache: dict[str, float] = {}  # Kielikoodi -> aikaleima


# ---------------------------------------------------------------------------
# MyMemory fallback language list (static)
# ---------------------------------------------------------------------------

def _get_mymemory_fallback_languages() -> Dict[str, str]:
    """Load fallback language list for MyMemory from JSON."""
    try:
        # Etsitään data-hakemistoa suhteessa tähän tiedostoon
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        json_path = os.path.join(base_dir, "data", "languages", "mymemory_fallback.json")

        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"MyMemory fallback file not found: {json_path}")
        return {}
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON in MyMemory fallback file: {e}")
        return {}
    except Exception as e:
        logger.warning(f"Failed to load MyMemory fallback languages: {e}")
        return {}


# ---------------------------------------------------------------------------
# MyMemory language support (static list + learning from errors)
# ---------------------------------------------------------------------------

def is_language_supported_by_mymemory(lang_code: str) -> bool:
    """
    Check if MyMemory supports a language.

    Strategy (no API calls):
    1. Check static fallback list first
    2. Check if language was previously marked as unsupported
    3. Return True only if in static list AND not marked unsupported

    This never makes API calls for language detection.
    """
    lang = base_language(lang_code)

    # 1. Check static list first
    fallback_langs = _get_mymemory_fallback_languages()
    if lang not in fallback_langs:
        logger.debug(f"MyMemory: {lang} not in static list")
        return False

    # 2. Check if language was marked unavailable
    if lang in _unavailable_cache:
        if time.time() - _unavailable_cache[lang] < UNAVAILABLE_CACHE_TTL:
            logger.debug(f"MyMemory: {lang} marked unavailable (cached)")
            return False
        else:
            # Cache expired, remove it
            del _unavailable_cache[lang]

    # 3. Static list says yes and not marked unavailable
    return True


def mark_mymemory_unavailable(lang_code: str) -> None:
    """
    Mark a language as unsupported by MyMemory.
    Called when a translation fails with LanguageNotSupportedError.
    """
    lang = base_language(lang_code)
    _unavailable_cache[lang] = time.time()
    logger.info(f"MyMemory marked unsupported: {lang} (cached 24h)")


def get_all_supported_languages() -> Dict[str, Dict[str, str]]:
    """
    Get supported languages from both services.
    MyMemory uses static list, LibreTranslate uses API.
    """
    mymemory_langs = _get_mymemory_fallback_languages()
    libretranslate_langs = get_supported_languages()

    return {
        "mymemory": mymemory_langs,
        "libretranslate": libretranslate_langs,
    }


def get_best_provider(
    target_lang: str,
    source_lang: str = "en",
    supported_languages: Optional[Dict[str, Dict[str, str]]] = None,
) -> str:
    """
    Choose the best translation provider for a language pair.

    Uses static list for MyMemory (no API calls) and language list for LibreTranslate.
    """
    target = base_language(target_lang)
    source = base_language(source_lang)

    # 1. Check MyMemory support (static list, no API calls)
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
# Main translation function
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
    mymemory_email: Optional[str] = None,
) -> str:
    """
    Translate text with smart routing and automatic fallback.

    Translation flow:
    1. Check cache
    2. Choose best provider based on language support (static list, no API calls)
    3. Try primary provider
    4. If fails with LanguageNotSupportedError, mark language unsupported
    5. Fallback to secondary provider
    6. If all fail, return original text

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
        logger.warning(f"No translation service supports {source}->{target}")
        return text
    else:
        order = ["mymemory", "libretranslate"]

    # Create adapters
    mymemory_adapter = MyMemoryAdapter(email=mymemory_email)
    libretranslate_adapter = LibreTranslateAdapter(
        base_url=libretranslate_url,
        api_key=libretranslate_api_key,
    )

    # Build request
    request = TranslationRequest(
        text=text,
        source_lang=source,
        target_lang=target,
    )

    # Try providers in order
    translated = None
    errors = []

    for service in order:
        for attempt in range(max_retries):
            try:
                if service == "mymemory":
                    translated = mymemory_adapter.translate(request)
                else:  # libretranslate
                    translated = libretranslate_adapter.translate(request)

                if translated:
                    if use_cache:
                        _translation_cache.set(text, translated, source, target)
                    return translated

            except LanguageNotSupportedError as e:
                logger.warning(f"{service} doesn't support language: {e}")
                # Mark language unsupported for MyMemory
                if service == "mymemory":
                    mark_mymemory_unavailable(target)
                    mark_mymemory_unavailable(source)
                errors.append(f"{service}: language not supported")
                break  # Move to next service

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
# Utility functions
# ---------------------------------------------------------------------------

def clear_unavailable_cache() -> None:
    """Clear the MyMemory unavailable language cache."""
    _unavailable_cache.clear()
    logger.info("MyMemory unavailable cache cleared")


def get_unavailable_cache_stats() -> Dict[str, Any]:
    """Get statistics about the unavailable language cache."""
    return {
        "size": len(_unavailable_cache),
        "languages": list(_unavailable_cache.keys()),
        "ttl": UNAVAILABLE_CACHE_TTL,
    }
