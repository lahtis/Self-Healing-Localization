"""
Shared pytest fixtures for all SHL tests.
"""

import pytest
import os
import json
import tempfile
import logging
import shutil
from pathlib import Path

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("shl.tests")


@pytest.fixture
def temp_locales_dir():
    """Create a temporary locales directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_prompts_dir():
    """Create a temporary prompts directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory for GLFM and fallback files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def base_en_file(temp_locales_dir):
    """Create an English base language file."""
    filepath = os.path.join(temp_locales_dir, "en.json")
    base_data = {
        "greeting": "Hello",
        "farewell": "Goodbye",
        "welcome": "Welcome {name}!",
        "test": "Working"
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(base_data, f, ensure_ascii=False, indent=4)
    return filepath


@pytest.fixture
def base_en_prompts(temp_prompts_dir):
    """Create an English base prompt template file."""
    filepath = os.path.join(temp_prompts_dir, "en.json")
    base_data = {
        "greeting_prompt": "Say hello to {name}",
        "summary_prompt": "Summarize the following: {text}",
        "test_template": "Test template"
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(base_data, f, ensure_ascii=False, indent=4)
    return filepath


@pytest.fixture
def glfm_file(temp_data_dir):
    """Create a minimal GLFM database file for testing."""
    filepath = os.path.join(temp_data_dir, "unified_languages.json")
    glfm_data = {
        "en": {
            "iso639_1": "en",
            "iso639_3": "eng",
            "bcp47": "en",
            "name": "English",
            "fallback": ""
        },
        "fi": {
            "iso639_1": "fi",
            "iso639_3": "fin",
            "bcp47": "fi",
            "name": "Finnish",
            "fallback": "en"
        },
        "sv": {
            "iso639_1": "sv",
            "iso639_3": "swe",
            "bcp47": "sv",
            "name": "Swedish",
            "fallback": "en"
        },
        "zh": {
            "iso639_1": "zh",
            "iso639_3": "zho",
            "bcp47": "zh-CN",
            "name": "Chinese",
            "fallback": "en"
        }
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(glfm_data, f, ensure_ascii=False, indent=4)
    return filepath


@pytest.fixture
def mymemory_fallback_file(temp_data_dir):
    """Create a fallback language list for MyMemory testing."""
    filepath = os.path.join(temp_data_dir, "mymemory_fallback.json")
    data = {
        "en": "English",
        "fi": "Finnish",
        "sv": "Swedish",
        "de": "German"
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return filepath


@pytest.fixture
def libretranslate_fallback_file(temp_data_dir):
    """Create a fallback language list for LibreTranslate testing."""
    filepath = os.path.join(temp_data_dir, "libretranslate_fallback.json")
    data = {
        "en": "English",
        "fi": "Finnish",
        "sv": "Swedish",
        "de": "German"
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return filepath


@pytest.fixture
def corrupted_file(temp_locales_dir):
    """Create a corrupted JSON file."""
    filepath = os.path.join(temp_locales_dir, "fi.json")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("{invalid json content [}")
    return filepath


@pytest.fixture
def empty_file(temp_locales_dir):
    """Create an empty language file."""
    filepath = os.path.join(temp_locales_dir, "sv.json")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("")
    return filepath


@pytest.fixture
def legacy_file(temp_locales_dir):
    """Create a legacy format language file (lang_xx.json)."""
    filepath = os.path.join(temp_locales_dir, "lang_fi.json")
    legacy_data = {
        "greeting": "Terve",
        "farewell": "Näkemiin"
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(legacy_data, f, ensure_ascii=False, indent=4)
    return filepath


@pytest.fixture
def temp_env_file():
    """Create a temporary .env file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write("""
MYMEMORY_EMAIL=test@example.com
LIBRETRANSLATE_API_KEY=test-api-key
LIBRETRANSLATE_URL=https://test.libretranslate.com
SHL_LANGUAGE=fi
""")
        env_path = f.name
    yield env_path
    os.unlink(env_path)


@pytest.fixture
def mock_response():
    """Mock HTTP response for testing API calls."""
    class MockResponse:
        def __init__(self, data, status=200):
            self.data = data
            self.status = status
        
        def read(self):
            return json.dumps(self.data).encode('utf-8')
        
        def getcode(self):
            return self.status
        
        def getheader(self, name):
            return None
        
        # Context manager protocol support
        def __enter__(self):
            return self
        
        def __exit__(self, *args):
            pass
    
    return MockResponse


@pytest.fixture
def mock_libretranslate_languages():
    """Mock response from LibreTranslate /languages endpoint."""
    return [
        {"code": "en", "name": "English"},
        {"code": "fi", "name": "Finnish"},
        {"code": "sv", "name": "Swedish"},
        {"code": "de", "name": "German"},
        {"code": "fr", "name": "French"},
        {"code": "es", "name": "Spanish"},
        {"code": "zh", "name": "Chinese"},
        {"code": "ja", "name": "Japanese"},
        {"code": "ko", "name": "Korean"},
        {"code": "ru", "name": "Russian"},
    ]


@pytest.fixture
def mock_mymemory_response():
    """Mock response from MyMemory API."""
    return {
        "responseStatus": 200,
        "responseData": {
            "translatedText": "Hei maailma"
        },
        "quotaReached": False,
        "responseDetails": "",
        "mtLangSupported": True
    }


@pytest.fixture
def mock_mymemory_rate_limit_response():
    """Mock rate limit response from MyMemory API."""
    return {
        "responseStatus": 429,
        "responseData": {
            "translatedText": ""
        },
        "quotaReached": True,
        "responseDetails": "Daily limit exceeded"
    }


@pytest.fixture
def mock_mymemory_error_response():
    """Mock error response from MyMemory API."""
    return {
        "responseStatus": 500,
        "responseData": {
            "translatedText": ""
        },
        "responseDetails": "Server error"
    }


@pytest.fixture
def mock_libretranslate_response():
    """Mock response from LibreTranslate API."""
    return {
        "translatedText": "Hei maailma"
    }


@pytest.fixture
def mock_libretranslate_rate_limit_response():
    """Mock rate limit response from LibreTranslate API."""
    return {
        "error": "Rate limit exceeded",
        "code": 429
    }


@pytest.fixture
def mock_libretranslate_error_response():
    """Mock error response from LibreTranslate API."""
    return {
        "error": "Server error",
        "code": 500
    }
