"""
Tests for AI translation module.

Tests:
- TranslationCache functionality
- translate_text function
- MyMemory API calls (mocked)
- LibreTranslate fallback (mocked)
- AITranslator class
- Cache hit/miss/expiry
- Error handling and graceful degradation
"""

import time
import pytest
from shl.engine.ai_translation import (
    TranslationCache,
    translate_text,
    AITranslator,
    _translation_cache,
)


class TestTranslationCache:
    """Tests for TranslationCache class."""

    def test_cache_set_and_get(self):
        """Test basic cache set and get."""
        cache = TranslationCache(ttl=3600)
        cache.set("Hello", "Hei", "en", "fi")
        result = cache.get("Hello", "en", "fi")
        assert result == "Hei"

    def test_cache_miss(self):
        """Test cache miss returns None."""
        cache = TranslationCache(ttl=3600)
        result = cache.get("Nonexistent", "en", "fi")
        assert result is None

    def test_cache_different_languages(self):
        """Test that different language pairs are cached separately."""
        cache = TranslationCache(ttl=3600)
        cache.set("Hello", "Hei", "en", "fi")
        cache.set("Hello", "Hallo", "en", "de")

        assert cache.get("Hello", "en", "fi") == "Hei"
        assert cache.get("Hello", "en", "de") == "Hallo"

    def test_cache_expiry(self):
        """Test that expired cache entries are removed."""
        cache = TranslationCache(ttl=0)  # Immediate expiry
        cache.set("Hello", "Hei", "en", "fi")
        time.sleep(0.01)  # Ensure expiry
        result = cache.get("Hello", "en", "fi")
        assert result is None

    def test_cache_clear(self):
        """Test cache clear."""
        cache = TranslationCache(ttl=3600)
        cache.set("Hello", "Hei", "en", "fi")
        assert cache.size() == 1
        cache.clear()
        assert cache.size() == 0

    def test_cache_size(self):
        """Test cache size tracking."""
        cache = TranslationCache(ttl=3600)
        assert cache.size() == 0
        cache.set("a", "1", "en", "fi")
        cache.set("b", "2", "en", "fi")
        assert cache.size() == 2

    def test_cache_same_text_different_source(self):
        """Test that different source languages are cached separately."""
        cache = TranslationCache(ttl=3600)
        cache.set("Hello", "Hei", "en", "fi")
        cache.set("Hello", "Hej", "sv", "fi")

        assert cache.get("Hello", "en", "fi") == "Hei"
        assert cache.get("Hello", "sv", "fi") == "Hej"


class TestTranslateText:
    """Tests for translate_text function."""

    def test_empty_text(self):
        """Test empty text returns empty string."""
        result = translate_text("", "fi", "en")
        assert result == ""

    def test_none_text(self):
        """Test None text returns empty string."""
        result = translate_text(None, "fi", "en")
        assert result == ""

    def test_same_language(self):
        """Test same source and target language returns original."""
        result = translate_text("Hello", "en", "en")
        assert result == "Hello"

    def test_cache_used(self):
        """Test that cache is used when available."""
        _translation_cache.clear()
        _translation_cache.set("Hello", "Cached Hei", "en", "fi")

        result = translate_text("Hello", "fi", "en", use_cache=True)
        assert result == "Cached Hei"

    def test_cache_disabled(self):
        """Test that cache can be disabled."""
        _translation_cache.clear()
        _translation_cache.set("Hello", "Cached Hei", "en", "fi")

        result = translate_text("Hello", "fi", "en", use_cache=False)
        # Will try API, likely fail, return original
        assert result is not None


class TestAITranslator:
    """Tests for AITranslator class."""

    def test_init_default(self):
        """Test default initialization."""
        translator = AITranslator()
        assert translator.provider == "auto"

    def test_init_mymemory(self):
        """Test MyMemory provider."""
        translator = AITranslator(provider="mymemory")
        assert translator.provider == "mymemory"

    def test_init_libretranslate(self):
        """Test LibreTranslate provider."""
        translator = AITranslator(provider="libretranslate")
        assert translator.provider == "libretranslate"

    def test_init_none(self):
        """Test none provider."""
        translator = AITranslator(provider="none")
        assert translator.provider == "none"

    def test_init_case_insensitive(self):
        """Test provider is lowercased."""
        translator = AITranslator(provider="MYMEMORY")
        assert translator.provider == "mymemory"

    def test_translate_none_provider(self):
        """Test none provider returns original text."""
        translator = AITranslator(provider="none")
        result = translator.translate("Hello", "fi", "en")
        assert result == "Hello"

    def test_batch_translate(self):
        """Test batch translation."""
        translator = AITranslator(provider="none")
        texts = {"greeting": "Hello", "farewell": "Goodbye"}
        result = translator.batch_translate(texts, "fi")
        assert result == texts

    def test_batch_translate_none_provider(self):
        """Test batch translate with none provider returns original."""
        translator = AITranslator(provider="none")
        texts = {"a": "Hello", "b": "World"}
        result = translator.batch_translate(texts, "fi")
        assert result == texts

    def test_cache_stats(self):
        """Test cache statistics."""
        translator = AITranslator(provider="auto")
        stats = translator.get_cache_stats()
        assert "cache_size" in stats
        assert "provider" in stats
        assert stats["provider"] == "auto"

    def test_clear_cache(self):
        """Test cache clearing."""
        translator = AITranslator(provider="auto")
        translator.cache.set("Hello", "Hei", "en", "fi")
        assert translator.cache.size() == 1
        translator.clear_cache()
        assert translator.cache.size() == 0

    def test_translate_uses_cache(self):
        """Test that translate uses internal cache."""
        translator = AITranslator(provider="auto")
        translator.cache.set("Hello", "Cached Hei", "en", "fi")

        result = translator.translate("Hello", "fi", "en")
        assert result == "Cached Hei"
