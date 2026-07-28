"""
Shared pytest fixtures for all SHL tests.
"""

import pytest
import os
import json
import tempfile
import logging

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
def base_en_file(temp_locales_dir):
    """Create an English base language file."""
    filepath = os.path.join(temp_locales_dir, "en.json")
    base_data = {
        "greeting": "Hello",
        "farewell": "Goodbye",
        "welcome": "Welcome {name}!"
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
        "summary_prompt": "Summarize the following: {text}"
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(base_data, f, ensure_ascii=False, indent=4)
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
