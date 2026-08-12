"""
File: glfm_load_database.py
Author: Tuomas Lähteenmäki
Version: 0.2.0
License: MIT
Description:
    Load GLFM (Global Language Family Mapper) database from JSON or
    gzipped JSON.

    Uses only Python standard library.

    Supported modes:
    - GLFM Lite: languages_top20.json.gz
    - Full GLFM: unified_languages.json.gz
    - Test/custom databases: ordinary .json files
"""

import gzip
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)


# glfm_load_database.py sijaitsee shl/utils-kansiossa.
# Varsinaiset tietokannat sijaitsevat shl/data-kansiossa.
DATA_DIR = (
    Path(__file__).resolve().parent.parent
    / "data"
)

LITE_DB_PATH = (
    DATA_DIR / "languages_top20.json.gz"
)

FULL_DB_PATH = (
    DATA_DIR / "unified_languages.json.gz"
)


# Cache avaimella, jotta eri tietokannat eivät sekoitu keskenään.
# Tämä on tärkeää testien custom-tietokantojen kanssa.
_glfm_cache: Dict[
    str,
    Dict[str, Any],
] = {}


def _cache_key(db_path: Path) -> str:
    """Return a stable cache key for a database path."""
    try:
        return str(db_path.resolve())
    except OSError:
        return str(db_path.absolute())


def _is_gzip_file(db_path: Path) -> bool:
    """
    Detect gzip format from file header.

    Gzip magic bytes are:
        0x1f 0x8b
    """
    with open(db_path, "rb") as file:
        header = file.read(2)

    return header == b"\x1f\x8b"


def _load_json_file(
    db_path: Path,
) -> Dict[str, Any]:
    """Load an ordinary uncompressed JSON file."""
    with open(
        db_path,
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    return data


def _load_gzip_json_file(
    db_path: Path,
) -> Dict[str, Any]:
    """Load a gzip-compressed JSON file."""
    with gzip.open(
        db_path,
        "rt",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    return data


def load_language_data(
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Load GLFM language data from JSON or gzip JSON.

    The database is cached by its resolved path.

    Args:
        db_path:
            Path to an ordinary JSON file or gzip JSON file.
            If omitted, Lite is tried first and Full second.

    Returns:
        Dictionary containing language data.

    Raises:
        FileNotFoundError:
            If the database does not exist.

        json.JSONDecodeError:
            If the file contains invalid JSON.

        ValueError:
            If the JSON root is not a dictionary.
    """
    if db_path is None:
        if LITE_DB_PATH.exists():
            db_path = LITE_DB_PATH

        elif FULL_DB_PATH.exists():
            db_path = FULL_DB_PATH

        else:
            raise FileNotFoundError(
                "GLFM language database not found.\n"
                f"Tried: {LITE_DB_PATH}\n"
                f"Tried: {FULL_DB_PATH}\n"
                "Please ensure at least one database file exists."
            )

    db_path = Path(db_path)

    if not db_path.exists():
        raise FileNotFoundError(
            f"GLFM language database not found: {db_path}"
        )

    key = _cache_key(db_path)

    if key in _glfm_cache:
        return _glfm_cache[key]

    try:
        if _is_gzip_file(db_path):
            data = _load_gzip_json_file(db_path)
        else:
            data = _load_json_file(db_path)

        if not isinstance(data, dict):
            raise ValueError(
                "Expected dictionary, "
                f"got {type(data).__name__}"
            )

        _glfm_cache[key] = data

        logger.info(
            "GLFM database loaded: %s languages from %s",
            len(data),
            db_path.name,
        )

        return data

    except gzip.BadGzipFile as error:
        logger.error(
            "Invalid gzip file: %s - %s",
            db_path,
            error,
        )
        raise

    except json.JSONDecodeError as error:
        logger.error(
            "Invalid JSON in database: %s - %s",
            db_path,
            error,
        )
        raise

    except OSError as error:
        logger.error(
            "Could not read GLFM database: %s - %s",
            db_path,
            error,
        )
        raise

    except Exception as error:
        logger.error(
            "Failed to load GLFM database: %s",
            error,
        )
        raise


def get_glfm_data(
    db_path: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """
    Get cached GLFM data.

    If db_path is omitted, returns the first cached database.
    """
    if db_path is not None:
        key = _cache_key(Path(db_path))
        return _glfm_cache.get(key)

    if not _glfm_cache:
        return None

    return next(iter(_glfm_cache.values()))


def clear_glfm_cache(
    db_path: Optional[Path] = None,
) -> None:
    """
    Clear GLFM cache.

    If db_path is provided, only that database is removed.
    Otherwise, all cached databases are removed.
    """
    if db_path is not None:
        key = _cache_key(Path(db_path))
        _glfm_cache.pop(key, None)

        logger.debug(
            "GLFM cache cleared for: %s",
            db_path,
        )

        return

    _glfm_cache.clear()
    logger.debug("All GLFM cache entries cleared")


def get_language_count(
    db_path: Optional[Path] = None,
) -> int:
    """
    Get number of languages in the cache.

    Returns 0 if the requested database is not loaded.
    """
    data = get_glfm_data(db_path)

    if data:
        return len(data)

    return 0


def find_language(
    lang_code: str,
    db_path: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """
    Find a language by ISO 639-1, ISO 639-3, or BCP-47 tag.

    Uses cached data if available, otherwise loads the default database.
    """
    if not lang_code:
        return None

    data = load_language_data(db_path)

    from shl.utils.lang_utils import (
        base_language,
        normalize_full_tag,
    )

    base = base_language(lang_code)

    # Try ISO 639-1.
    for lang_id, info in data.items():
        if not isinstance(info, dict):
            continue

        iso1 = info.get(
            "iso639_1",
            "",
        )

        if (
            isinstance(iso1, str)
            and iso1.lower() == base.lower()
        ):
            return info

    # Try direct lookup by base code.
    if base in data:
        value = data[base]

        if isinstance(value, dict):
            return value

    # Try normalized full BCP-47 tag.
    full = normalize_full_tag(lang_code)

    if full in data:
        value = data[full]

        if isinstance(value, dict):
            return value

    # Try case-insensitive direct lookup.
    for lang_id, info in data.items():
        if (
            isinstance(lang_id, str)
            and lang_id.lower() == full.lower()
            and isinstance(info, dict)
        ):
            return info

    return None


def is_lite_available() -> bool:
    """Return True if the Lite database exists."""
    return LITE_DB_PATH.exists()


def is_full_available() -> bool:
    """Return True if the Full database exists."""
    return FULL_DB_PATH.exists()


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
    )

    print("=== GLFM Load Test ===")
    print()

    print(
        f"Lite available: {is_lite_available()}"
    )

    print(
        f"Full available: {is_full_available()}"
    )

    try:
        data = load_language_data()

        print(
            f"Loaded {len(data)} languages"
        )

        print()
        print("Testing find_language():")

        test_codes = [
            "fi",
            "en",
            "zh",
            "es",
            "de",
            "qxl",
        ]

        for code in test_codes:
            info = find_language(code)

            if info:
                name = info.get(
                    "name",
                    "unknown",
                )

                iso1 = info.get(
                    "iso639_1",
                    "",
                )

                print(
                    f"  {code}: {name} "
                    f"(ISO: {iso1 or 'N/A'})"
                )

            else:
                print(
                    f"  {code}: NOT FOUND"
                )

        print()
        print(
            "Cache loaded: "
            f"{get_glfm_data() is not None}"
        )

        print(
            "Language count: "
            f"{get_language_count()}"
        )

    except FileNotFoundError as error:
        print(error)
        sys.exit(1)

    except Exception as error:
        print(f"Error: {error}")
        sys.exit(1)
