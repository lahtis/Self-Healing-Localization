"""
File: shl/engine/translation/providers/libretranslate_community/endpoints.py
Author: Tuomas Lähteenmäki
Version: 0.3.0
License: MIT
Description:
    Loads the LibreTranslate Community endpoint list.

    Lookup order:
      1. <current working directory>/libretranslate_endpoints.json
      2. Built-in defaults below

    If the user file does not exist, it is created with the built-in
    defaults on first call. This gives users a visible, editable
    starting point instead of an invisible fallback. If the file
    cannot be written (read-only filesystem), the built-in defaults
    are used silently.

    The user file must be JSON with this structure:

        {
            "endpoints": [
                "https://libretranslate.example",
                "https://other.example"
            ]
        }

    All URLs must be HTTPS and resolve to public IPs so they pass
    validation in shl/utils/safe_http.py.

    The user file path is resolved at call time, not at import time,
    so changing the working directory after import is honoured.

    This module performs no HTTP calls. It only reads and writes a
    local file.
"""

import json
import logging
from pathlib import Path


logger = logging.getLogger(__name__)


# Name of the user override file, looked up in the current working
# directory at call time.
_USER_ENDPOINTS_FILENAME = "libretranslate_endpoints.json"


# Built-in defaults. Used to seed the user file on first run, and as
# fallback when the file cannot be read or written.
#
# These are public LibreTranslate instances known to be reachable
# without authentication at the time of writing. Public instances
# come and go — users who need a specific set should create their
# own libretranslate_endpoints.json.
_DEFAULT_ENDPOINTS: list[str] = [
    "https://libretranslate.com",
    "https://libretranslate.de",
]


def _user_endpoints_path() -> Path:
    """Return the path to the user override file.

    Resolved on each call so a change of working directory after
    import is honoured.
    """
    return Path.cwd() / _USER_ENDPOINTS_FILENAME


def _normalize(urls: list) -> list[str]:
    """Strip whitespace, drop empties, and remove trailing slashes."""
    return [
        str(url).strip().rstrip("/")
        for url in urls
        if isinstance(url, str) and url.strip()
    ]


def _create_user_file_if_missing() -> None:
    """Create the user endpoints file with defaults if it does not exist.

    This gives the user a visible, editable starting point. Failures
    are logged at DEBUG level so read-only filesystems do not produce
    noise — the adapter continues with the built-in defaults.
    """
    path = _user_endpoints_path()

    if path.exists():
        return

    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(
                {"endpoints": list(_DEFAULT_ENDPOINTS)},
                f,
                indent=4,
                ensure_ascii=False,
            )
            f.write("\n")

        logger.info("Created default %s", path.name)

    except OSError as exc:
        logger.debug(
            "Could not create %s: %s (using built-in defaults).",
            path.name,
            exc,
        )


def _load_user_endpoints() -> list[str]:
    """Load endpoints from the user override file if it exists.

    Returns an empty list when the file is missing or malformed; the
    caller falls back to the built-in defaults in that case.
    """
    path = _user_endpoints_path()

    if not path.exists():
        return []

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        logger.warning(
            "Invalid JSON in %s; using built-in defaults.",
            path,
        )
        return []
    except OSError as exc:
        logger.warning(
            "Unable to read %s: %s; using built-in defaults.",
            path,
            exc,
        )
        return []

    if not isinstance(data, dict):
        logger.warning(
            "Top-level value in %s must be a JSON object; "
            "using built-in defaults.",
            path,
        )
        return []

    endpoints = data.get("endpoints")

    if not isinstance(endpoints, list):
        logger.warning(
            "Missing or invalid 'endpoints' key in %s; "
            "using built-in defaults.",
            path,
        )
        return []

    normalized = _normalize(endpoints)

    if not normalized:
        logger.warning(
            "'endpoints' list in %s is empty; "
            "using built-in defaults.",
            path,
        )
        return []

    return normalized


def load_endpoints() -> list[str]:
    """Return the active LibreTranslate Community endpoint list.

    Lookup order:
      1. <current working directory>/libretranslate_endpoints.json
      2. Built-in defaults

    If the user file does not exist, it is created with the built-in
    defaults on first call so the user has a visible template to
    edit. If creation fails (read-only filesystem), the built-in
    defaults are used silently.

    The user override takes precedence when present and valid.
    Otherwise the library defaults are returned, so the adapter
    works out of the box without any configuration.
    """
    # Create the user file with defaults on first run so the user
    # has a visible, editable template.
    _create_user_file_if_missing()

    user = _load_user_endpoints()

    if user:
        logger.debug(
            "Loaded %d community endpoints from %s.",
            len(user),
            _user_endpoints_path(),
        )
        return user

    logger.debug(
        "Using %d built-in community endpoints.",
        len(_DEFAULT_ENDPOINTS),
    )
    return list(_DEFAULT_ENDPOINTS)
