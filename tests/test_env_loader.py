# tests/test_env_loader.py
"""
Tests for environment loader.
"""

import os
import tempfile
from pathlib import Path
from shl.utils.env_loader import (
    load_shl_env,
    mask_api_key,
    get_env_value,
    get_env_value_masked,
    is_env_loaded,
    reset_env_loader,
    get_env_file_path,
)


# tests/test_env_loader.py

def test_mask_api_key():
    """Test API key masking."""
    assert mask_api_key(None) == "(not set)"
    assert mask_api_key("") == "(not set)"
    assert mask_api_key("short") == "*****"
    
    # "my-secret-key-12345" pituus 19
    # 4 ekaa: "my-s", 4 vikaa: "2345", 11 tähteä
    assert mask_api_key("my-secret-key-12345") == "my-s***********2345"
    
    # "abcdefghijklmnopqrstuvwxyz" pituus 26
    # 4 ekaa: "abcd", 4 vikaa: "wxyz", 18 tähteä
    assert mask_api_key("abcdefghijklmnopqrstuvwxyz") == "abcd******************wxyz"


def test_mask_api_key_with_spaces():
    """Test API key masking with spaces."""
    # "  my-key  " -> strip -> "my-key" (pituus 6)
    assert mask_api_key("  my-key  ") == "******"

def test_get_env_file_path():
    """Test environment file path."""
    path = get_env_file_path()
    assert str(path).endswith(".env/shl/.env")


def test_load_shl_env():
    """Test loading environment."""
    reset_env_loader()
    loaded = load_shl_env()
    assert isinstance(loaded, bool)


def test_get_env_value():
    """Test getting environment value."""
    # Set test value
    os.environ["TEST_SHL_VAR"] = "test_value"
    
    value = get_env_value("TEST_SHL_VAR")
    assert value == "test_value"
    
    # Clean up
    del os.environ["TEST_SHL_VAR"]

def test_get_env_value_masked():
    """Test getting masked environment value."""
    os.environ["TEST_SHL_SECRET"] = "super-secret-key-12345"
    
    masked = get_env_value_masked("TEST_SHL_SECRET")
    
    # "super-secret-key-12345" pituus 22
    # 4 ekaa: "supe", 4 vikaa: "2345", 14 tähteä
    assert masked == "supe**************2345"
    
    # Clean up
    del os.environ["TEST_SHL_SECRET"]

def test_get_env_value_default():
    """Test getting environment value with default."""
    value = get_env_value("NON_EXISTENT_VAR", "default_value")
    assert value == "default_value"


def test_is_env_loaded():
    """Test checking if environment is loaded."""
    reset_env_loader()
    assert is_env_loaded() is False
    
    load_shl_env()
    assert is_env_loaded() is True
