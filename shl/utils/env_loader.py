"""
File: env_loader.py
Author: Tuomas Lähteenmäki
Version: 0.2.4
License: MIT
Description:
    Environment loader for SHL.
    Loads .env files from ./.env/shl/ directory.
    Provides secure logging with API key masking.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Globaali flagi, jotta .env ladattaisiin vain kerran
_env_loaded = False
_env_load_attempted = False

logger = logging.getLogger(__name__)


# shl/utils/env_loader.py

def mask_api_key(key: Optional[str]) -> str:
    """
    Mask API key for safe logging.

    Args:
        key: API key string or None

    Returns:
        Masked string:
        - "(not set)" if key is None or empty
        - "*****" if key is 8 characters or less
        - "abcd***********wxyz" for longer keys (first 4 + last 4 visible)
        - Middle part is always at least 4 asterisks

    Examples:
        >>> mask_api_key("my-secret-key-12345")
        'my-s*****************12345'  # 4 + 17 + 4 = 25? Ei, 4 + 15 + 4 = 23
        >>> mask_api_key("short")
        '*****'
        >>> mask_api_key(None)
        '(not set)'
    """
    if not key:
        return "(not set)"

    key_str = str(key).strip()
    if not key_str:
        return "(not set)"

    if len(key_str) <= 8:
        return "*" * len(key_str)

    # Näytä ensimmäiset 4 ja viimeiset 4 merkkiä
    # Keskiosa korvataan tähdillä (vähintään 4 tähteä)
    prefix = key_str[:4]
    suffix = key_str[-4:]
    
    # Lasketaan tähtien määrä: koko pituus - 8 (4+4)
    star_count = len(key_str) - 8
    # Varmistetaan, että vähintään 4 tähteä
    if star_count < 4:
        star_count = 4
    
    return prefix + "*" * star_count + suffix

def get_env_file_path() -> Path:
    """
    Return the path to the SHL .env file.

    Returns:
        Path object pointing to ./.env/shl/.env

    Example:
        >>> env_path = get_env_file_path()
        >>> print(env_path)
        /path/to/project/.env/shl/.env
    """
    cwd = Path.cwd()
    return cwd / ".env" / "shl" / ".env"


def load_shl_env(force: bool = False) -> bool:
    """
    Load .env from ./.env/shl/ directory.

    Args:
        force: Force reload even if already loaded

    Returns:
        True if .env was loaded successfully, False otherwise.

    Example:
        >>> load_shl_env()
        True

        # With logging
        >>> import logging
        >>> logging.basicConfig(level=logging.DEBUG)
        >>> load_shl_env()
        DEBUG:shl.utils.env_loader:Loading .env from /path/to/project/.env/shl/.env
        DEBUG:shl.utils.env_loader:Loaded environment: NAVER_CLIENT_ID=abcd************1234
    """
    global _env_loaded, _env_load_attempted

    if _env_loaded and not force:
        logger.debug("SHL environment already loaded")
        return True

    if _env_load_attempted and not force:
        logger.debug("SHL environment load already attempted")
        return _env_loaded

    _env_load_attempted = True

    try:
        from dotenv import load_dotenv
    except ImportError:
        logger.warning("python-dotenv not installed - environment loading disabled")
        _env_loaded = True
        return False

    env_file = get_env_file_path()

    if env_file.exists():
        try:
            load_dotenv(env_file)
            _env_loaded = True

            # Log loaded variables (masked)
            loaded_vars = _get_loaded_env_vars()
            if loaded_vars:
                logger.debug(
                    f"Loaded environment from {env_file}: {loaded_vars}"
                )
            else:
                logger.debug(f"Loaded empty .env file from {env_file}")

            return True

        except Exception as e:
            logger.error(f"Failed to load .env from {env_file}: {e}")
            _env_loaded = False
            return False

    # Fallback: projektin juuren .env
    root_env = Path.cwd() / ".env"
    if root_env.exists():
        try:
            load_dotenv(root_env)
            _env_loaded = True

            loaded_vars = _get_loaded_env_vars()
            if loaded_vars:
                logger.debug(
                    f"Loaded environment from {root_env} (fallback): {loaded_vars}"
                )
            else:
                logger.debug(f"Loaded empty .env file from {root_env} (fallback)")

            return True

        except Exception as e:
            logger.error(f"Failed to load .env from {root_env}: {e}")
            _env_loaded = False
            return False

    logger.debug("No .env file found in ./.env/shl/ or ./.env")
    _env_loaded = True
    return False


def _get_loaded_env_vars() -> Dict[str, str]:
    """
    Get loaded environment variables with masked values.

    Returns:
        Dictionary of environment variable names and masked values.

    Example:
        >>> _get_loaded_env_vars()
        {
            'NAVER_CLIENT_ID': 'abcd************1234',
            'DEEPL_API_KEY': 'dee********5678',
        }
    """
    env_vars = {}

    # SHL-related environment variables
    shl_env_vars = [
        "NAVER_CLIENT_ID",
        "NAVER_CLIENT_SECRET",
        "DEEPL_API_KEY",
        "GOOGLE_API_KEY",
        "GOOGLE_BACKUP_API_KEY",
        "LIBRETRANSLATE_URL",
        "LIBRETRANSLATE_API_KEY",
    ]

    for var in shl_env_vars:
        value = os.getenv(var)
        if value is not None:
            env_vars[var] = mask_api_key(value)

    return env_vars


def get_env_value(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get environment variable value with optional default.

    Args:
        key: Environment variable name
        default: Default value if not found

    Returns:
        Environment variable value or default

    Example:
        >>> get_env_value("DEEPL_API_KEY")
        'my-deepl-key'
        >>> get_env_value("NON_EXISTENT", "default")
        'default'
    """
    # Ensure .env is loaded
    load_shl_env()

    value = os.getenv(key, default)
    return value


def get_env_value_masked(key: str, default: Optional[str] = None) -> str:
    """
    Get environment variable value masked for logging.

    Args:
        key: Environment variable name
        default: Default value if not found

    Returns:
        Masked environment variable value

    Example:
        >>> get_env_value_masked("DEEPL_API_KEY")
        'dee********5678'
        >>> get_env_value_masked("NON_EXISTENT")
        '(not set)'
    """
    value = get_env_value(key, default)
    return mask_api_key(value)


def is_env_loaded() -> bool:
    """
    Check if SHL environment has been loaded.

    Returns:
        True if .env has been loaded, False otherwise.

    Example:
        >>> is_env_loaded()
        True
    """
    return _env_loaded


def reset_env_loader() -> None:
    """
    Reset environment loader state.

    Useful for testing or forcing reload.

    Example:
        >>> reset_env_loader()
        >>> load_shl_env(force=True)
    """
    global _env_loaded, _env_load_attempted
    _env_loaded = False
    _env_load_attempted = False
    logger.debug("Environment loader reset")


# --- Test and example ---

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(levelname)-8s [%(name)s] %(message)s'
    )

    print("=== SHL Environment Loader Test ===\n")

    # Test 1: Load .env
    print("1. Loading .env...")
    loaded = load_shl_env()
    print(f"   Loaded: {loaded}")

    # Test 2: Get loaded variables
    print("\n2. Loaded environment variables:")
    loaded_vars = _get_loaded_env_vars()
    if loaded_vars:
        for key, value in loaded_vars.items():
            print(f"   {key}: {value}")
    else:
        print("   No SHL environment variables found")

    # Test 3: Get specific value
    print("\n3. Getting specific values:")
    deepl_key = get_env_value("DEEPL_API_KEY")
    print(f"   DEEPL_API_KEY: {mask_api_key(deepl_key)}")

    google_key = get_env_value("GOOGLE_API_KEY")
    print(f"   GOOGLE_API_KEY: {mask_api_key(google_key)}")

    # Test 4: Get value masked
    print("\n4. Masked values:")
    print(f"   DEEPL_API_KEY (masked): {get_env_value_masked('DEEPL_API_KEY')}")
    print(f"   NON_EXISTENT (masked): {get_env_value_masked('NON_EXISTENT')}")

    # Test 5: Check load state
    print(f"\n5. Environment loaded: {is_env_loaded()}")

    # Test 6: Reset
    print("\n6. Resetting...")
    reset_env_loader()
    print(f"   Environment loaded after reset: {is_env_loaded()}")
