"""
File: shl/engine/translation/provider_cache.py
Author: Tuomas Lähteenmäki
Version: 0.3.0
License: MIT
Description:
    Provider language support and cache.

    Checks the language support of service providers and saves it to
    the cache. LibreTranslate Community endpoints are loaded from the
    shared endpoint resolver, which honours the user override file.

    All outbound HTTP goes through safe_urlopen for SSRF prevention,
    redirect validation, and response size limits.

    This module is imported during SHL startup and may run a network
    refresh when the cache file is missing.

    A single unreachable or misbehaving provider must not break the
    whole cache. Each provider fetch is isolated and returns a safe
    empty result on failure.
"""

import json
import logging
import shutil
from pathlib import Path
from urllib.request import Request

from shl.utils.safe_http import safe_urlopen as urlopen
from shl.utils.safe_http_common import (
    MAX_RESPONSE_BYTES,
    SafeHTTPError,
    read_limited_response,
)

from shl.utils.env_loader import get_env_value
from shl.config import get_config_value

from .providers.libretranslate_community.endpoints import (
    load_endpoints,
)


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------

SHL_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = SHL_DIR.parent
CACHE_FILE = PROJECT_DIR / ".languages_cache.json"
PM_FILE = SHL_DIR / "data" / "papago_mymemory.json"


# ---------------------------------------------------------------------------
# CACHE & FETCHERS
# ---------------------------------------------------------------------------

def load_cache() -> dict:
    """Load the existing cache or generate a new one."""

    # Ensure the user endpoints file exists even when the language
    # cache is already present. This gives users a visible, editable
    # template without forcing a full cache regeneration.
    load_endpoints()

    if CACHE_FILE.exists():
        try:
            with CACHE_FILE.open("r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, dict):
                return data

            logger.warning(
                "Cache file %s has unexpected structure; regenerating.",
                CACHE_FILE,
            )

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
) -> dict | list | None:
    """Fetch JSON data using the specified HTTP method.

    Uses safe_urlopen so every fetch goes through the safe HTTP layer.

    Returns:
        The parsed JSON payload (dict or list) on success.
        None if the response body is not valid JSON or is a scalar.

    Raises:
        SafeHTTPError on security or transport failures.
        OSError on low-level socket failures.

    Community LibreTranslate instances sometimes return HTML error
    pages (Cloudflare, rate limit, 404) instead of JSON. Treating
    those as "no data" is friendlier than crashing the entire cache
    generation.
    """

    request_headers = (
        dict(headers)
        if headers
        else {"User-Agent": "SHL-Client"}
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
        raw = read_limited_response(response, MAX_RESPONSE_BYTES)

    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.debug(
            "Response from %s is not valid JSON: %s",
            url,
            exc,
        )
        return None

    if not isinstance(parsed, (dict, list)):
        logger.debug(
            "Response from %s is not a JSON object or array (got %s).",
            url,
            type(parsed).__name__,
        )
        return None

    return parsed


def generate_cache() -> dict:
    """Generate the provider language cache with current data.

    Every provider is fetched in isolation; a failure in one does
    not affect the others.
    """

    try:
        microsoft = fetch_microsoft_translator()
    except (OSError, SafeHTTPError):
        microsoft = {}

    try:
        libretranslate = fetch_libretranslate()
    except (OSError, SafeHTTPError):
        libretranslate = {}

    # -----------------------------------------------------------------------
    # LibreTranslate Community
    #
    # Endpoint URLs are resolved by load_endpoints(), which honours the
    # user override file (<cwd>/libretranslate_endpoints.json) and
    # creates it from built-in defaults on first call.
    #
    # Each endpoint is queried separately and its /languages response
    # is merged into one provider-specific language mapping.
    #
    # Endpoint URLs themselves are NOT stored in the language cache.
    # -----------------------------------------------------------------------

    community_endpoints = load_endpoints()

    libretranslate_community: dict[str, str] = {}

    for endpoint in community_endpoints:
        try:
            languages = fetch_libretranslate_community(endpoint)

            for code, name in languages.items():
                libretranslate_community[code] = name

        except (OSError, SafeHTTPError) as exc:
            logger.warning(
                "LibreTranslate Community language fetch failed "
                "for endpoint %s: %s",
                endpoint,
                exc,
            )

    # Registry-compatible provider language list.
    libretranslate_community_languages = sorted(
        code.lower()
        for code in libretranslate_community
        if isinstance(code, str) and code.strip()
    )

    logger.info(
        "LibreTranslate Community: collected %d languages "
        "from %d endpoints",
        len(libretranslate_community_languages),
        len(community_endpoints),
    )

    try:
        yandex = fetch_yandex_translator()
    except (OSError, SafeHTTPError):
        yandex = {}

    try:
        deepl = fetch_deepl()
    except (OSError, SafeHTTPError):
        deepl = []

    papago_mymemory = load_papago_mymemory()

    cache = {
        "providers": {
            "microsoft_translator": microsoft,
            "libretranslate": libretranslate,

            # Provider-specific language list.
            # Endpoint URLs are intentionally not stored here.
            "libretranslate_community": (
                libretranslate_community_languages
            ),

            "deepl": deepl,
            "yandex": yandex,

            "papago": sorted(
                code.lower()
                for code in papago_mymemory.get("papago", [])
            ),

            "mymemory_iso_639_1": sorted(
                code.lower()
                for code in papago_mymemory.get(
                    "mymemory_iso_639_1",
                    [],
                )
            ),
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

    logger.info(
        "Provider language cache generated: %s",
        CACHE_FILE,
    )

    return cache


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


# ---------------------------------------------------------------------------
# MICROSOFT
# ---------------------------------------------------------------------------

def fetch_microsoft_translator() -> dict:
    """Fetch supported languages from Microsoft Translator."""

    data = fetch_json(
        "https://api.cognitive.microsofttranslator.com/languages"
        "?api-version=3.0"
    )

    if not isinstance(data, dict):
        return {}

    translation = data.get("translation", {})

    if not isinstance(translation, dict):
        return {}

    return {
        code.lower(): info["name"]
        for code, info in translation.items()
        if isinstance(info, dict) and info.get("name")
    }


# ---------------------------------------------------------------------------
# LIBRETRANSLATE
# ---------------------------------------------------------------------------

def fetch_libretranslate() -> dict:
    """Fetch supported languages from LibreTranslate."""

    languages = fetch_json(
        "https://libretranslate.com/languages"
    )

    if not isinstance(languages, list):
        return {}

    return {
        lang["code"].lower(): lang["name"]
        for lang in languages
        if isinstance(lang, dict)
        and lang.get("code")
        and lang.get("name")
    }


# ---------------------------------------------------------------------------
# LIBRETRANSLATE COMMUNITY
# ---------------------------------------------------------------------------

def fetch_libretranslate_community(
    endpoint: str,
) -> dict:
    """Fetch supported languages from one LibreTranslate Community
    endpoint.

    Returns an empty dict when the endpoint is unreachable or does
    not return a JSON language list.
    """

    url = f"{endpoint.rstrip('/')}/languages"

    data = fetch_json(url)

    if not isinstance(data, list):
        logger.debug(
            "LibreTranslate Community endpoint %s did not return a "
            "language list (got %s).",
            endpoint,
            type(data).__name__,
        )
        return {}

    languages: dict[str, str] = {}

    for lang in data:
        if not isinstance(lang, dict):
            continue

        code = lang.get("code")
        name = lang.get("name")

        if not isinstance(code, str):
            continue

        if not isinstance(name, str):
            continue

        code = code.strip().lower()

        if not code:
            continue

        languages[code] = name

    logger.debug(
        "LibreTranslate Community endpoint %s: received %d languages",
        endpoint,
        len(languages),
    )

    return languages


# ---------------------------------------------------------------------------
# YANDEX
# ---------------------------------------------------------------------------

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

        if isinstance(response, dict):
            languages = response.get("languages", [])

            if languages:
                return {
                    lang["code"].lower(): lang.get(
                        "name",
                        lang["code"],
                    )
                    for lang in languages
                    if isinstance(lang, dict) and lang.get("code")
                }

    except (OSError, SafeHTTPError):
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


# ---------------------------------------------------------------------------
# PAPAGO / MYMEMORY
# ---------------------------------------------------------------------------

def load_papago_mymemory(
    path: Path = PM_FILE,
) -> dict:
    """Load Papago and MyMemory language data from the JSON file."""

    if not path.exists():
        return {
            "papago": [],
            "mymemory_iso_639_1": [],
        }

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, dict):
            return data

        logger.warning(
            "%s does not contain a JSON object; using empty defaults.",
            path,
        )

    except (json.JSONDecodeError, OSError) as exc:
        logger.warning(
            "Unable to read %s: %s",
            path,
            exc,
        )

    return {
        "papago": [],
        "mymemory_iso_639_1": [],
    }
