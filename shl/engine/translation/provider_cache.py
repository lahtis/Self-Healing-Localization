"""
File: provider_cache.py - Provider language support and cache.
Author: Tuomas Lähteenmäki
License: MIT
Version: 0.2.6

Checks the language support of service providers and saves it to the cache.
puuttuu google ja DeepL
"""

import json
import shutil
from pathlib import Path
from urllib.request import urlopen, Request

from shl.utils.env_loader import get_env_value
from shl.config import get_config_value


# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------

SHL_DIR = Path(__file__).resolve().parents[2]
CACHE_FILE = SHL_DIR / "languages_cache.json"
PM_FILE = SHL_DIR / "data" / "papago_mymemory.json"


# ---------------------------------------------------------------------------
# CACHE & FETCHERS
# ---------------------------------------------------------------------------

def load_cache() -> dict:
    """Load the existing cache or generate a new one."""
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
) -> dict:
    """Fetch JSON data using the specified HTTP method."""

    request_headers = dict(headers) if headers else {
        "User-Agent": "SHL-Client"
    }

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
        return json.loads(response.read().decode("utf-8"))


def generate_cache() -> dict:
    """Generate the provider language cache with current data."""

    try:
        microsoft = fetch_microsoft_translator()
    except OSError:
        microsoft = {}

    try:
        libretranslate = fetch_libretranslate()
    except OSError:
        libretranslate = {}

    yandex = fetch_yandex_translator()

    papago_mymemory = load_papago_mymemory()

    cache = {
        "providers": {
            "microsoft_translator": microsoft,
            "libretranslate": libretranslate,
            "yandex": yandex,
            "papago": sorted(
                code.lower()
                for code in papago_mymemory.get("papago", [])
            ),
            "mymemory_iso_639_1": sorted(
                code.lower()
                for code in papago_mymemory.get("mymemory_iso_639_1", [])
            ),
        }
    }

    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

    with CACHE_FILE.open("w", encoding="utf-8") as file:
        json.dump(cache, file, indent=4, ensure_ascii=False)

    return cache


def fetch_microsoft_translator() -> dict:
    """Fetch supported languages from Microsoft Translator."""
    data = fetch_json(
        "https://api.cognitive.microsofttranslator.com/languages"
        "?api-version=3.0"
    )

    return {
        code.lower(): info["name"]
        for code, info in data.get("translation", {}).items()
    }


def fetch_libretranslate() -> dict:
    """Fetch supported languages from LibreTranslate."""
    languages = fetch_json("https://libretranslate.com/languages")

    return {
        lang["code"].lower(): lang["name"]
        for lang in languages
    }


def fetch_yandex_translator() -> dict:
    """Fetch supported Yandex languages or use the static fallback."""

    api_key = get_env_value("YANDEX_API_KEY")
    folder_id = get_config_value("providers.yandex.folder_id")

    if not api_key:
        return get_fallback_yandex_languages()

    data = {}

    if folder_id:
        data["folderId"] = folder_id

    try:
        response = fetch_json(
            "https://translate.api.cloud.yandex.net/translate/v2/languages",
            method="POST",
            headers={
                "Authorization": f"Api-Key {api_key}",
            },
            data=data,
        )

        languages = response.get("languages", [])

        if languages:
            return {
                lang["code"].lower(): lang.get("name", lang["code"])
                for lang in languages
                if lang.get("code")
            }

    except (OSError, json.JSONDecodeError):
        pass

    return get_fallback_yandex_languages()


def get_fallback_yandex_languages() -> dict:
    """Return the fallback list of supported Yandex languages."""
    codes = [
        "af", "am", "ar", "az", "ba", "be", "bg", "bn", "bs", "ca",
        "ceb", "cs", "cy", "da", "de", "el", "en", "eo", "es", "et",
        "eu", "fa", "fi", "fr", "ga", "gd", "gl", "gu", "he", "hi",
        "hr", "ht", "hu", "hy", "id", "is", "it", "ja", "jv", "ka",
        "kk", "km", "kn", "ko", "ky", "la", "lb", "lo", "lt", "lv",
        "mg", "mhr", "mi", "mk", "ml", "mn", "mr", "mrj", "ms", "mt",
        "my", "ne", "nl", "no", "pa", "pap", "pl", "pt", "ro", "ru",
        "sah", "si", "sk", "sl", "sq", "sr", "su", "sv", "sw", "ta",
        "te", "tg", "th", "tl", "tr", "tt", "udm", "uk", "ur", "uz",
        "vi", "xh", "yi", "zh",
    ]

    return {code: code for code in codes}


def load_papago_mymemory(path: Path = PM_FILE) -> dict:
    """Load Papago and MyMemory language data from the JSON file."""
    if not path.exists():
        return {
            "papago": [],
            "mymemory_iso_639_1": [],
        }

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)
