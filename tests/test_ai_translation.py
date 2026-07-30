# tests/test_ai_translation.py
"""
Tests for AI translation module.
"""

import pytest
from unittest.mock import patch, MagicMock
from shl.engine.ai_translation import (
    translate_text,
    AITranslator,
    TranslationCache,
    get_supported_languages,
    get_all_supported_languages,
    get_best_provider,
    is_language_supported_by_mymemory,
    RateLimitExceededError,
    ServiceUnavailableError,
    LanguageNotSupportedError,
    ProviderAccessError,
    InvalidRequestError,
    TranslationError,
    _translate_mymemory,
    _translate_libretranslate,
    _MYMEMORY_FALLBACK_LANGUAGES,
    _LIBRETRANSLATE_FALLBACK_LANGUAGES
)


# ---------------------------------------------------------------------------
# Basic translation tests
# ---------------------------------------------------------------------------

def test_translate_text_basic():
    """Test basic translation with smart routing."""
    result = translate_text("Hello", "fi", smart_routing=True)
    assert result is not None
    assert result != "Hello"
    assert isinstance(result, str)


def test_translate_text_same_language():
    """Test that same language returns original text."""
    result = translate_text("Hello", "en", "en")
    assert result == "Hello"


def test_translate_text_empty():
    """Test empty text handling."""
    result = translate_text("", "fi")
    assert result == ""


def test_translate_text_invalid():
    """Test invalid text handling - returns empty string."""
    result = translate_text(None, "fi")
    assert result == ""


def test_translate_text_cache():
    """Test translation cache functionality."""
    result1 = translate_text("Cache test", "fi")
    result2 = translate_text("Cache test", "fi")
    assert result1 == result2


def test_translate_text_no_cache():
    """Test translation without cache."""
    result1 = translate_text("No cache test", "fi", use_cache=False)
    result2 = translate_text("No cache test", "fi", use_cache=False)
    assert result1 is not None
    assert result2 is not None
    # Results should be the same even without cache
    assert result1 == result2


def test_translate_text_smart_routing_false():
    """Test translation with smart routing disabled."""
    result = translate_text("Hello", "fi", smart_routing=False)
    assert result is not None
    assert result != "Hello"


# ---------------------------------------------------------------------------
# Provider selection tests
# ---------------------------------------------------------------------------

def test_get_best_provider():
    """Test provider selection for language pairs."""
    provider = get_best_provider("fi", "en")
    assert provider in ["mymemory", "libretranslate", "none"]


def test_get_best_provider_with_supported_langs():
    """Test provider selection with pre-fetched language list."""
    supported = {
        "mymemory": {"en": "English", "fi": "Finnish"},
        "libretranslate": {"en": "English", "fi": "Finnish"}
    }
    provider = get_best_provider("fi", "en", supported)
    assert provider == "mymemory"


def test_get_best_provider_mymemory_only():
    """Test provider selection when only MyMemory supports."""
    supported = {
        "mymemory": {"en": "English", "fi": "Finnish"},
        "libretranslate": {"en": "English"}
    }
    provider = get_best_provider("fi", "en", supported)
    assert provider == "mymemory"


def test_get_best_provider_libretranslate_only():
    """Test provider selection when only LibreTranslate supports."""
    supported = {
        "mymemory": {"en": "English"},
        "libretranslate": {"en": "English", "fi": "Finnish"}
    }
    provider = get_best_provider("fi", "en", supported)
    # MyMemory may still support via fallback, so check accordingly
    assert provider in ["mymemory", "libretranslate"]


def test_get_best_provider_none():
    """Test provider selection when no service supports."""
    provider = get_best_provider("xx", "yy", {"mymemory": {}, "libretranslate": {}})
    assert provider in ["mymemory", "none"]


# ---------------------------------------------------------------------------
# Language list tests
# ---------------------------------------------------------------------------

def test_get_supported_languages():
    """Test fetching supported languages from LibreTranslate."""
    langs = get_supported_languages()
    assert isinstance(langs, dict)
    assert len(langs) > 0


def test_get_supported_languages_custom_url():
    """Test fetching languages from custom LibreTranslate URL."""
    langs = get_supported_languages("https://unreachable.example.com")
    assert isinstance(langs, dict)
    assert len(langs) > 0


def test_get_all_supported_languages():
    """Test fetching all supported languages from both services."""
    langs = get_all_supported_languages()
    assert "mymemory" in langs
    assert "libretranslate" in langs
    assert isinstance(langs["mymemory"], dict)
    assert isinstance(langs["libretranslate"], dict)


def test_is_language_supported_by_mymemory():
    """Test MyMemory language support detection."""
    result = is_language_supported_by_mymemory("en")
    assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# Translation Cache tests
# ---------------------------------------------------------------------------

def test_translation_cache_set_get():
    """Test cache set and get operations."""
    cache = TranslationCache(ttl=60, max_size=10)
    cache.set("test", "translated", "en", "fi")
    result = cache.get("test", "en", "fi")
    assert result == "translated"


def test_translation_cache_miss():
    """Test cache miss behavior."""
    cache = TranslationCache(ttl=60, max_size=10)
    result = cache.get("missing", "en", "fi")
    assert result is None


def test_translation_cache_expiry():
    """Test cache entry expiry."""
    cache = TranslationCache(ttl=0, max_size=10)
    cache.set("test", "translated", "en", "fi")
    result = cache.get("test", "en", "fi")
    assert result is None


def test_translation_cache_size():
    """Test cache size limit."""
    cache = TranslationCache(ttl=60, max_size=3)
    for i in range(5):
        cache.set(f"key{i}", f"value{i}", "en", "fi")
    assert cache.size() == 3


def test_translation_cache_clear():
    """Test cache clearing."""
    cache = TranslationCache(ttl=60, max_size=10)
    cache.set("test", "translated", "en", "fi")
    assert cache.size() == 1
    cache.clear()
    assert cache.size() == 0


# ---------------------------------------------------------------------------
# AITranslator tests
# ---------------------------------------------------------------------------

def test_aitranslator_init():
    """Test AITranslator initialization."""
    translator = AITranslator(provider="auto")
    assert translator.provider == "auto"
    assert translator.cache is not None


def test_aitranslator_translate():
    """Test AITranslator translation."""
    translator = AITranslator(provider="auto")
    result = translator.translate("Hello", "fi")
    assert result is not None
    assert result != "Hello"


def test_aitranslator_translate_none_provider():
    """Test AITranslator with none provider."""
    translator = AITranslator(provider="none")
    result = translator.translate("Hello", "fi")
    assert result == "Hello"


def test_aitranslator_batch_translate():
    """Test AITranslator batch translation."""
    translator = AITranslator(provider="auto")
    texts = {"greeting": "Hello", "farewell": "Goodbye"}
    result = translator.batch_translate(texts, "fi")
    assert len(result) == 2
    assert "greeting" in result
    assert "farewell" in result
    assert result["greeting"] != "Hello"
    assert result["farewell"] != "Goodbye"


def test_aitranslator_batch_translate_none_provider():
    """Test AITranslator batch translation with none provider."""
    translator = AITranslator(provider="none")
    texts = {"greeting": "Hello", "farewell": "Goodbye"}
    result = translator.batch_translate(texts, "fi")
    assert result == texts


def test_aitranslator_get_supported_languages():
    """Test AITranslator.get_supported_languages()."""
    translator = AITranslator(provider="auto")
    langs = translator.get_supported_languages()
    assert "mymemory" in langs
    assert "libretranslate" in langs


def test_aitranslator_get_best_provider():
    """Test AITranslator.get_best_provider()."""
    translator = AITranslator(provider="auto")
    provider = translator.get_best_provider("fi", "en")
    assert provider in ["mymemory", "libretranslate", "none"]


def test_aitranslator_is_language_supported():
    """Test AITranslator.is_language_supported()."""
    translator = AITranslator(provider="auto")
    result = translator.is_language_supported("en")
    assert isinstance(result, bool)


def test_aitranslator_cache_stats():
    """Test AITranslator cache statistics."""
    translator = AITranslator(provider="auto")
    translator.translate("Hello", "fi")
    stats = translator.get_cache_stats()
    assert "cache_size" in stats
    assert "provider" in stats
    assert stats["provider"] == "auto"


def test_aitranslator_clear_cache():
    """Test AITranslator cache clearing."""
    translator = AITranslator(provider="auto")
    translator.translate("Hello", "fi")
    translator.clear_cache()
    assert translator.cache.size() == 0


# ---------------------------------------------------------------------------
# Error handling tests (mocked)
# ---------------------------------------------------------------------------

@patch('shl.engine.ai_translation._translate_mymemory')
def test_translate_text_rate_limit(mock_mymemory):
    """Test rate limit error handling."""
    mock_mymemory.side_effect = RateLimitExceededError("Rate limit")
    result = translate_text("Hello", "fi", smart_routing=False)
    assert result is not None


@patch('shl.engine.ai_translation._translate_mymemory')
def test_translate_text_service_unavailable(mock_mymemory):
    """Test service unavailable error handling."""
    mock_mymemory.side_effect = ServiceUnavailableError("Service down")
    result = translate_text("Hello", "fi", smart_routing=False)
    assert result is not None


@patch('shl.engine.ai_translation._translate_mymemory')
def test_translate_text_language_not_supported(mock_mymemory):
    """Test language not supported error handling."""
    mock_mymemory.side_effect = LanguageNotSupportedError("Language not supported")
    result = translate_text("Hello", "fi", smart_routing=False)
    assert result is not None


@patch('shl.engine.ai_translation._translate_mymemory')
def test_translate_text_retry(mock_mymemory):
    """Test retry mechanism on transient errors."""
    mock_mymemory.side_effect = [
        ServiceUnavailableError("Timeout"),
        ServiceUnavailableError("Timeout"),
        "Hei"
    ]
    result = translate_text("Hello", "fi", smart_routing=False, max_retries=3)
    assert result == "Hei"


# ---------------------------------------------------------------------------
# MyMemory API tests (mocked)
# ---------------------------------------------------------------------------

@patch('shl.engine.ai_translation.urlopen')
def test_mymemory_translate_success(mock_urlopen, mock_mymemory_response, mock_response):
    """Test successful MyMemory translation."""
    mock_response_obj = mock_response(mock_mymemory_response)
    mock_urlopen.return_value = mock_response_obj
    
    result = _translate_mymemory("Hello world", "fi", "en")
    assert result == "Hei maailma"


@patch('shl.engine.ai_translation.urlopen')
def test_mymemory_translate_rate_limit(mock_urlopen, mock_mymemory_rate_limit_response, mock_response):
    """Test MyMemory rate limit handling."""
    mock_response_obj = mock_response(mock_mymemory_rate_limit_response, status=429)
    mock_urlopen.return_value = mock_response_obj
    
    with pytest.raises(RateLimitExceededError):
        _translate_mymemory("Hello", "fi", "en")


@patch('shl.engine.ai_translation.urlopen')
def test_mymemory_translate_server_error(mock_urlopen, mock_mymemory_error_response, mock_response):
    """Test MyMemory server error handling."""
    mock_response_obj = mock_response(mock_mymemory_error_response, status=500)
    mock_urlopen.return_value = mock_response_obj
    
    with pytest.raises(ServiceUnavailableError):
        _translate_mymemory("Hello", "fi", "en")


# ---------------------------------------------------------------------------
# Fallback language list tests
# ---------------------------------------------------------------------------

def test_mymemory_fallback_list():
    """Test that MyMemory fallback list is loaded."""
    assert isinstance(_MYMEMORY_FALLBACK_LANGUAGES, dict)
    assert "en" in _MYMEMORY_FALLBACK_LANGUAGES


def test_libretranslate_fallback_list():
    """Test that LibreTranslate fallback list is loaded."""
    assert isinstance(_LIBRETRANSLATE_FALLBACK_LANGUAGES, dict)
    assert "en" in _LIBRETRANSLATE_FALLBACK_LANGUAGES


# ---------------------------------------------------------------------------
# Integration tests (optional - slow)
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_integration_translate():
    """Integration test for real translation."""
    result = translate_text("Hello world", "fi")
    assert result is not None
    assert result != "Hello world"


@pytest.mark.slow
def test_integration_get_supported_languages():
    """Integration test for language list fetching."""
    langs = get_supported_languages()
    assert isinstance(langs, dict)
    assert len(langs) > 0


# ---------------------------------------------------------------------------
# Run tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main(["-v", __file__])
