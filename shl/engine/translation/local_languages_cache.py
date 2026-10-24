"""
File: shl/engine/translation/local_languages_cache.py
Author: Tuomas Lähteenmäki
License: MIT
Version: 0.1.0
Description:
    Cache of languages supported by the local translation service.

    The cache is written atomically (tmp + fsync + replace). A crash
    mid-write cannot corrupt an existing cache. A corrupted cache is
    backed up with a timestamp and the most recent valid backup is
    restored before regenerating.

    All outbound HTTP goes through safe_local_urlopen so local
    endpoints stay inside the allowlist defined in
    shl/utils/safe_local_http.py.
"""

import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request
from urllib.error import HTTPError, URLError

from shl.utils.safe_local_http import safe_local_urlopen as urlopen
from shl._version import __version__ as SHL_VERSION


logger = logging.getLogger(__name__)


CACHE_FILE = Path.home() / ".cache" / "shl" / "local_languages_cache.json"
CACHE_MAX_AGE_SECONDS = 7 * 24 * 3600   # 1 week
FETCH_TIMEOUT_SECONDS = 5


# ---------------------------------------------------------------------------
# LOAD / SAVE
# ---------------------------------------------------------------------------

def load_cache() -> dict:
    """Load the local languages cache or return an empty one.

    A corrupted cache is backed up with a timestamp and the most
    recent valid backup is restored before giving up.
    """

    if not CACHE_FILE.exists():
        return _empty_cache()

    try:
        with CACHE_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if _is_valid_shape(data):
            return data

        logger.warning(
            "Local languages cache %s has unexpected structure; ignoring.",
            CACHE_FILE,
        )

    except (json.JSONDecodeError, OSError) as exc:
        logger.warning(
            "Local languages cache %s is corrupted: %s",
            CACHE_FILE,
            exc,
        )

    # Backup with timestamp, then try to restore from a backup.
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = CACHE_FILE.with_suffix(f".json.{timestamp}.bak")

    try:
        shutil.copy2(CACHE_FILE, backup)
        logger.info("Corrupted local languages cache backed up to %s", backup)
    except OSError:
        pass

    for candidate in sorted(
        CACHE_FILE.parent.glob("local_languages_cache.json.*.bak"),
        reverse=True,
    ):
        try:
            with candidate.open("r", encoding="utf-8") as file:
                data = json.load(file)
            if _is_valid_shape(data):
                logger.warning(
                    "Restored local languages cache from backup %s",
                    candidate,
                )
                return data
        except (json.JSONDecodeError, OSError):
            continue

    return _empty_cache()


def save_cache(languages: list[str]) -> None:
    """Write the local languages cache atomically."""

    cache = {
        "languages": sorted(
            {
                code.strip().lower()
                for code in languages
                if isinstance(code, str) and code.strip()
            }
        ),
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }

    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = CACHE_FILE.with_suffix(".json.tmp")

    try:
        with tmp_path.open("w", encoding="utf-8") as file:
            json.dump(cache, file, indent=4, ensure_ascii=False)
            file.flush()
            os.fsync(file.fileno())

        os.replace(tmp_path, CACHE_FILE)

    except OSError as error:
        logger.error(
            "Failed to write local languages cache %s: %s",
            CACHE_FILE,
            error,
        )
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise


def is_stale(
    cache: dict,
    max_age_seconds: int = CACHE_MAX_AGE_SECONDS,
) -> bool:
    """Return True if the cache has no last_updated or is older than max_age."""

    last = cache.get("last_updated")
    if not isinstance(last, str) or not last:
        return True

    try:
        when = datetime.fromisoformat(last)
    except ValueError:
        return True

    if when.tzinfo is None:
        return True

    age = (datetime.now(timezone.utc) - when).total_seconds()
    return age > max_age_seconds


# ---------------------------------------------------------------------------
# FETCH
# ---------------------------------------------------------------------------

def fetch_local_languages(
    base_url: str,
    timeout: int = FETCH_TIMEOUT_SECONDS,
) -> list[str] | None:
    """Fetch supported languages from the local service.

    Returns a list of ISO 639-1 codes, or None if the service is
    unreachable or returns an unexpected shape.
    """

    url = f"{base_url.rstrip('/')}/languages"

    try:
        request = Request(
            url,
            headers={
                "User-Agent": f"SHL-Client/{SHL_VERSION}",
                "Accept": "application/json",
            },
            method="GET",
        )

        with urlopen(request, timeout=timeout) as response:
            raw = response.read(1024 * 1024)   # 1 MB cap

        data = json.loads(raw.decode("utf-8"))

    except (OSError, URLError, HTTPError, json.JSONDecodeError) as exc:
        logger.debug("Local language fetch failed (%s): %s", url, exc)
        return None

    if not isinstance(data, list):
        logger.debug(
            "Local language fetch returned %s, expected list",
            type(data).__name__,
        )
        return None

    codes = [
        item["code"].strip().lower()
        for item in data
        if isinstance(item, dict)
        and isinstance(item.get("code"), str)
    ]

    return sorted(set(codes))


def get_local_supported_languages(
    base_url: str,
    force_refresh: bool = False,
) -> list[str]:
    """Return the local service's supported languages.

    Uses the on-disk cache when fresh; fetches the service when the
    cache is stale or missing; falls back to the stale cache if the
    fetch fails.
    """

    cache = load_cache()

    if not force_refresh and not is_stale(cache):
        languages = cache.get("languages") or []
        if languages:
            return languages

    fetched = fetch_local_languages(base_url)

    if fetched:
        save_cache(fetched)
        return fetched

    # Fetch failed: use stale cache if any.
    languages = cache.get("languages") or []
    if languages:
        logger.info(
            "Using stale local languages cache (%d entries)",
            len(languages),
        )
        return languages

    logger.warning(
        "No local language data available; assuming all languages supported",
    )
    return []


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _empty_cache() -> dict:
    return {
        "languages": [],
        "last_updated": None,
    }


def _is_valid_shape(data: object) -> bool:
    if not isinstance(data, dict):
        return False
    languages = data.get("languages")
    return isinstance(languages, list)
