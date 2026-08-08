"""
File: glfm_load_database.py
Author: Tuomas Lähteenmäki
Version: 0.2.0
License: MIT
Description:
    Load GLFM (Global Language Family Mapper) database from gzipped JSON.
    Uses only Python standard library (gzip + json).
    The database is loaded on demand and cached in memory.
    
    Two modes:
    - GLFM Lite: languages_top20.json.gz (~428 KB)
    - Full GLFM: unified_languages.json.gz (~800 MB)
"""

import gzip
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Polut SHL-paketin sisäisiin tiivistettyihin datatiedostoihin
DATA_DIR = Path(__file__).resolve().parent
LITE_DB_PATH = DATA_DIR / "languages_top20.json.gz"
FULL_DB_PATH = DATA_DIR / "unified_languages.json.gz"

# Välimuisti (kerran ladattu)
_glfm_cache: Optional[Dict[str, Any]] = None


def load_language_data(db_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load GLFM language database from gzipped JSON.
    
    The database is loaded once and cached in memory for subsequent calls.
    
    Args:
        db_path: Path to the gzipped JSON file
        
    Returns:
        Dictionary of language data
    
    Raises:
        FileNotFoundError: If the database file does not exist
        json.JSONDecodeError: If the file contains invalid JSON
    """
    global _glfm_cache
    
    if _glfm_cache is not None:
        return _glfm_cache
    
    if db_path is None:
        # Try Lite first, then Full
        if LITE_DB_PATH.exists():
            db_path = LITE_DB_PATH
        elif FULL_DB_PATH.exists():
            db_path = FULL_DB_PATH
        else:
            raise FileNotFoundError(
                f"GLFM language database not found.\n"
                f"Tried: {LITE_DB_PATH}\n"
                f"Tried: {FULL_DB_PATH}\n"
                "Please ensure at least one database file exists."
            )
    
    if not db_path.exists():
        raise FileNotFoundError(f"GLFM language database not found: {db_path}")
    
    try:
        with gzip.open(db_path, "rt", encoding="utf-8") as f:
            data = json.load(f)
        
        if not isinstance(data, dict):
            raise ValueError(f"Expected dictionary, got {type(data).__name__}")
        
        _glfm_cache = data
        logger.info(f"GLFM database loaded: {len(data)} languages from {db_path.name}")
        return data
        
    except gzip.BadGzipFile as e:
        logger.error(f"Invalid gzip file: {db_path} - {e}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in database: {db_path} - {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to load GLFM database: {e}")
        raise


def get_glfm_data() -> Optional[Dict[str, Any]]:
    """Get cached GLFM data if loaded, otherwise return None."""
    return _glfm_cache


def clear_glfm_cache() -> None:
    """Clear the GLFM cache."""
    global _glfm_cache
    _glfm_cache = None
    logger.debug("GLFM cache cleared")


def get_language_count() -> int:
    """Get the number of languages in the database. Returns 0 if not loaded."""
    if _glfm_cache:
        return len(_glfm_cache)
    return 0


def find_language(lang_code: str) -> Optional[Dict[str, Any]]:
    """
    Find a language by ISO 639-1, ISO 639-3, or BCP-47 tag.
    Uses cached data if available, otherwise loads it.
    """
    if not lang_code:
        return None
    
    data = load_language_data()
    
    # Normalize tag for lookup
    from shl.utils.lang_utils import base_language
    base = base_language(lang_code)
    
    # Try ISO 639-1
    for lang_id, info in data.items():
        if info.get("iso639_1", "").lower() == base:
            return info
    
    # Try direct lookup by code
    if base in data:
        return data[base]
    
    # Try full tag
    from shl.utils.lang_utils import normalize_full_tag
    full = normalize_full_tag(lang_code)
    if full in data:
        return data[full]
    
    return None


def is_lite_available() -> bool:
    """Check if GLFM Lite database is available."""
    return LITE_DB_PATH.exists()


def is_full_available() -> bool:
    """Check if full GLFM database is available."""
    return FULL_DB_PATH.exists()


# --- Test ---

if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    print("=== GLFM Load Test ===\n")
    print(f"Lite available: {is_lite_available()}")
    print(f"Full available: {is_full_available()}")
    
    try:
        data = load_language_data()
        print(f" Loaded {len(data)} languages")
        
        # Test find_language
        print("\n Testing find_language():")
        test_codes = ["fi", "en", "zh", "es", "de", "qxl"]
        for code in test_codes:
            info = find_language(code)
            if info:
                name = info.get('name', 'unknown')
                iso1 = info.get('iso639_1', '')
                print(f"  {code}: {name} (ISO: {iso1 or 'N/A'})")
            else:
                print(f"  {code}: NOT FOUND")
        
        print(f"\n📊 Cache loaded: {get_glfm_data() is not None}")
        print(f"📊 Language count: {get_language_count()}")
        
    except FileNotFoundError as e:
        print(f" {e}")
        sys.exit(1)
    except Exception as e:
        print(f" Error: {e}")
        sys.exit(1)
