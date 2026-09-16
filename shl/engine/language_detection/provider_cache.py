"""
File: provider_cache.py - Language detection provider support and cache.
Author: Tuomas Lähteenmäki
License: MIT
Version: 0.2.10

Checks the language support of language detection providers and saves it
to a dedicated language detection cache.
"""

import json
import logging
import shutil
from pathlib import Path
from urllib.request import Request, urlopen

from shl.utils.env_loader import get_env_value
from shl.config import get_config_value


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------

SHL_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = SHL_DIR.parent
CACHE_FILE = PROJECT_DIR / ".language_detection_cache.json"


# ---------------------------------------------------------------------------
# CACHE & FETCHERS
# ---------------------------------------------------------------------------

def load_cache() -> dict:
    """Load the existing language detection cache or generate a new one."""

    if CACHE_FILE.exists():
        try:
            with CACHE_FILE.open("r", encoding="utf-8") as file:
                return json.load(file)

        except (json.JSONDecodeError, OSError):
            backup = CACHE_FILE.with_suffix(".json.bak")

            try:
                shutil.copy2(CACHE_FILE, backup)
            except OSError:
                pass

    return generate_cache()


def fetch_json(
    url: str,
    method: str = "GET",
    headers: dict | None = None,
    data: dict | None = None,
):
    """Fetch JSON data using the specified HTTP method."""

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
        return json.loads(
            response.read().decode("utf-8")
        )


def generate_cache() -> dict:
    """Generate the language detection provider cache."""

    try:
        detectlanguage = fetch_detectlanguage()
    except OSError:
        detectlanguage = {}

    try:
        yandex = fetch_yandex()
    except OSError:
        yandex = {}

    cache = {
        "providers": {
            "detectlanguage": detectlanguage,
            "yandex": yandex,
        }
    }

    CACHE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with CACHE_FILE.open("w", encoding="utf-8") as file:
        json.dump(
            cache,
            file,
            indent=4,
            ensure_ascii=False,
        )

    return cache


# ---------------------------------------------------------------------------
# DETECT LANGUAGE
# ---------------------------------------------------------------------------

def fetch_detectlanguage() -> dict:
    """Fetch supported languages from Detect Language."""

    api_key = get_env_value(
        "DETECTLANGUAGE_API_KEY"
    )

    if not api_key:
        logger.info(
            "Detect Language: API key not found"
        )
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

        with urlopen(
            request,
            timeout=10,
        ) as response:
            data = json.loads(
                response.read().decode("utf-8")
            )

        if not isinstance(data, list):
            logger.error(
                "Detect Language returned an invalid "
                "language list"
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

    except (OSError, json.JSONDecodeError) as exc:
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

    api_key = get_env_value(
        "YANDEX_API_KEY"
    )

    folder_id = get_config_value(
        "providers.yandex.folder_id"
    )

    if not api_key:
        logger.info(
            "Yandex: API key not found"
        )
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

        languages = response.get(
            "languages",
            [],
        )

        if not languages:
            logger.warning(
                "Yandex: no languages returned"
            )
            return {}

        return {
            language["code"].lower(): language.get(
                "name",
                language["code"],
            )
            for language in languages
            if language.get("code")
        }

    except (OSError, json.JSONDecodeError) as exc:
        logger.error(
            "Yandex language fetch failed: %s",
            exc,
        )
        return {}
