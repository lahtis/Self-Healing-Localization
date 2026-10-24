"""
File: shl/engine/language_detection/provider_cache.py
Author: Tuomas Lähteenmäki
License: MIT
Version: 0.3.2
Description:
    Language detection provider support and cache.

    Checks the language support of language detection providers and
    saves it to a dedicated language detection cache.

    All outbound HTTP goes through safe_urlopen for SSRF prevention,
    redirect validation, and response size limits.

    The cache file is written atomically (tmp + fsync + replace).
    A crash mid-write cannot corrupt an existing cache. Corrupted
    caches are backed up with a timestamp and the most recent valid
    backup is restored before regenerating.
"""

import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

# CHANGED: import Request only; urlopen is replaced with the safe
# variant so every call gets HTTPS-only, is_global DNS checks,
# redirect validation, and a bounded response body.
from urllib.request import Request

from shl.utils.safe_http import safe_urlopen as urlopen
from shl.utils.safe_http_common import (
    MAX_RESPONSE_BYTES,
    SafeHTTPError,
    read_limited_response,
)

from shl.utils.env_loader import get_env_value
from shl.config import get_config_value


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------

SHL_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = SHL_DIR.parent
CACHE_FILE = Path.home() / ".cache" / "shl" / "language_detection_cache.json"


# ---------------------------------------------------------------------------
# CACHE & FETCHERS
# ---------------------------------------------------------------------------

def load_cache() -> dict:
    """Load the existing language detection cache or generate a new one.

    A cache written before a provider was added is completed with the
    missing providers only. Providers already in the file are kept.

    If the cache file is corrupted, it is backed up with a timestamp
    and the most recent valid backup is restored before falling back
    to a full regeneration.
    """

    if CACHE_FILE.exists():
        try:
            with CACHE_FILE.open("r", encoding="utf-8") as file:
                cache = json.load(file)

        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(
                "Detection cache %s is corrupted: %s",
                CACHE_FILE,
                exc,
            )

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup = CACHE_FILE.with_suffix(f".json.{timestamp}.bak")

            try:
                shutil.copy2(CACHE_FILE, backup)
                logger.info("Corrupted cache backed up to %s", backup)
            except OSError:
                pass

            # Try to restore from the most recent valid backup.
            for candidate in sorted(
                CACHE_FILE.parent.glob("language_detection_cache.json.*.bak"),
                reverse=True,
            ):
                try:
                    with candidate.open("r", encoding="utf-8") as file:
                        restored = json.load(file)
                    if isinstance(restored, dict):
                        logger.warning(
                            "Restored detection cache from backup %s",
                            candidate,
                        )
                        return _add_missing_providers(restored)
                except (json.JSONDecodeError, OSError):
                    continue

        else:
            return _add_missing_providers(cache)

    return generate_cache()


def _provider_fetchers() -> dict:
    """Return provider name -> (fetch function, empty value on failure).

    This is the single list of providers in the detection cache.
    """

    return {
        "detectlanguage": (fetch_detectlanguage, dict),
        "yandex": (fetch_yandex, dict),
        "deepl": (fetch_deepl, list),
    }


def _fetch_provider(name: str) -> object:
    """Fetch one provider's language data, or its empty value on failure."""

    fetcher, empty = _provider_fetchers()[name]

    # CHANGED: catch SafeHTTPError in addition to OSError so security
    # and transport failures do not crash startup.
    try:
        return fetcher()
    except (OSError, SafeHTTPError):
        return empty()


def _write_cache(cache: dict) -> None:
    """Write the cache file atomically.

    Writes to a temporary file first and replaces the target only
    after a successful flush and fsync. A crash mid-write cannot
    corrupt an existing cache.
    """

    CACHE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    tmp_path = CACHE_FILE.with_suffix(".json.tmp")

    try:
        with tmp_path.open("w", encoding="utf-8") as file:
            json.dump(
                cache,
                file,
                indent=4,
                ensure_ascii=False,
            )
            file.flush()
            os.fsync(file.fileno())

        os.replace(tmp_path, CACHE_FILE)

    except OSError as error:
        logger.error(
            "Failed to write detection cache %s: %s",
            CACHE_FILE,
            error,
        )
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise


def _add_missing_providers(cache: object) -> dict:
    """Fetch providers that are absent from an existing cache.

    Existing entries are never refetched or overwritten, so a cache
    that holds data from an earlier run keeps it.
    """

    if not isinstance(cache, dict) or not isinstance(
        cache.get("providers"), dict
    ):
        return generate_cache()

    providers = cache["providers"]

    missing = [
        name for name in _provider_fetchers() if name not in providers
    ]

    if not missing:
        return cache

    for name in missing:
        providers[name] = _fetch_provider(name)

    cache["last_updated"] = datetime.now(timezone.utc).isoformat()
    _write_cache(cache)

    return cache


def fetch_json(
    url: str,
    method: str = "GET",
    headers: dict | None = None,
    data: dict | None = None,
) -> object:
    """Fetch JSON data using the specified HTTP method.

    Uses safe_urlopen for SSRF prevention, redirect validation, and
    response size limits. Raises SafeHTTPError on security or
    transport failures.
    """

    request_headers = (
        dict(headers)
        if headers
        else {
            "User-Agent": "SHL-Client",
        }
    )

    request_data = None

    if data is not None:
        request_data = json.dumps(data).encode("utf-8")

        request_headers.setdefault(
            "Content-Type",
            "application/json",
        )

    request = Request(
        url,
        data=request_data,
        headers=request_headers,
        method=method.upper(),
    )

    with urlopen(request, timeout=10) as response:
        # CHANGED: bounded read so a misbehaving endpoint cannot
        # return an unbounded body.
        raw = read_limited_response(response, MAX_RESPONSE_BYTES)

    return json.loads(raw.decode("utf-8"))


def generate_cache() -> dict:
    """Generate the language detection provider cache."""

    cache = {
        "providers": {
            name: _fetch_provider(name)
            for name in _provider_fetchers()
        },
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }

    try:
        _write_cache(cache)
    except OSError as exc:
        logger.error(
            "Detection cache generation failed (%s); returning in-memory cache",
            exc,
        )
        return cache

    return cache


# ---------------------------------------------------------------------------
# DETECT LANGUAGE
# ---------------------------------------------------------------------------

def fetch_detectlanguage() -> dict:
    """Fetch supported languages from Detect Language."""

    api_key = get_env_value("DETECTLANGUAGE_API_KEY")

    if not api_key:
        logger.info("Detect Language: API key not found")
        return {}

    api_key = api_key.strip()

    try:
        request = Request(
            "https://ws.detectlanguage.com/v3/languages",
            headers={
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "SHL-Client",
                "Accept": "application/json",
            },
            method="GET",
        )

        with urlopen(request, timeout=10) as response:
            # CHANGED: bounded read via the shared helper.
            raw = read_limited_response(response, MAX_RESPONSE_BYTES)

        data = json.loads(raw.decode("utf-8"))

        if not isinstance(data, list):
            logger.error(
                "Detect Language returned an invalid language list"
            )
            return {}

        languages = {
            item["code"].lower(): item["name"]
            for item in data
            if isinstance(item, dict)
            and item.get("code")
            and item.get("name")
        }

        logger.info(
            "Detect Language: received %d languages",
            len(languages),
        )

        return languages

    # CHANGED: include SafeHTTPError so security and transport
    # failures are handled the same way as network errors.
    except (OSError, json.JSONDecodeError, SafeHTTPError) as exc:
        logger.error(
            "Detect Language language fetch failed: %s",
            exc,
        )
        return {}


# ---------------------------------------------------------------------------
# YANDEX
# ---------------------------------------------------------------------------

def fetch_yandex() -> dict:
    """Fetch supported languages from Yandex Translate."""

    api_key = get_env_value("YANDEX_API_KEY")

    folder_id = get_config_value("providers.yandex.folder_id")

    if not api_key:
        logger.info("Yandex: API key not found")
        return {}

    data = {}

    if folder_id:
        data["folderId"] = folder_id

    try:
        response = fetch_json(
            "https://translate.api.cloud.yandex.net/"
            "translate/v2/languages",
            method="POST",
            headers={
                "Authorization": f"Api-Key {api_key}",
            },
            data=data,
        )

        # CHANGED: verify the shape before calling .get() so a wrong
        # response type does not raise AttributeError.
        if not isinstance(response, dict):
            logger.warning("Yandex: unexpected response shape")
            return {}

        languages = response.get("languages", [])

        if not languages:
            logger.warning("Yandex: no languages returned")
            return {}

        return {
            language["code"].lower(): language.get(
                "name",
                language["code"],
            )
            for language in languages
            if language.get("code")
        }

    # CHANGED: include SafeHTTPError for the same reason as above.
    except (OSError, json.JSONDecodeError, SafeHTTPError) as exc:
        logger.error(
            "Yandex language fetch failed: %s",
            exc,
        )
        return {}


# ---------------------------------------------------------------------------
# DEEPL
# ---------------------------------------------------------------------------

def fetch_deepl() -> list:
    """Fetch supported language codes from DeepL."""

    api_key = get_env_value("DEEPL_API_KEY")

    if not api_key:
        logger.info("DeepL: API key not found")
        return []

    api_key = api_key.strip()

    if api_key.endswith(":fx"):
        base_url = "https://api-free.deepl.com"
    else:
        base_url = "https://api.deepl.com"

    try:
        request = Request(
            f"{base_url}/v3/languages?resource=translate_text",
            headers={
                "Authorization": f"DeepL-Auth-Key {api_key}",
                "User-Agent": "SHL-Client",
                "Accept": "application/json",
            },
            method="GET",
        )

        with urlopen(request, timeout=10) as response:
            raw = read_limited_response(
                response,
                MAX_RESPONSE_BYTES,
            )

        try:
            data = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.error(
                "DeepL language fetch failed: response is not JSON"
            )
            return []

        if not isinstance(data, list):
            logger.error(
                "DeepL language fetch failed: unexpected response shape"
            )
            return []

        languages = sorted(
            lang["lang"].lower()
            for lang in data
            if isinstance(lang, dict) and lang.get("lang")
        )

        logger.info(
            "DeepL: received %d languages",
            len(languages),
        )

        return languages

    except (OSError, SafeHTTPError) as exc:
        logger.error(
            "DeepL language fetch failed: %s",
            exc,
        )
        return []
