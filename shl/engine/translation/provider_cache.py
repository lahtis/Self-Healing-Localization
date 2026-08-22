"""
file: provider_cache.py - Providers language support and cache.
Author: Tuomas Lähteenmäki
License: MIT
Version: 0.2.5-fix

Checks the language support of service providers and saves it to the cache.
"""

import json
import shutil
from pathlib import Path
from urllib.request import urlopen


# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------

# __file__:
# shl/engine/translation/provider_cache.py
#
# parents[0] = shl/engine/translation
# parents[1] = shl/engine
# parents[2] = shl

SHL_DIR = Path(__file__).resolve().parents[2]

CACHE_FILE = SHL_DIR / "languages_cache.json"
PM_FILE = SHL_DIR / "data" / "papago_mymemory.json"


# ---------------------------------------------------------------------------
# CACHE
# ---------------------------------------------------------------------------

def load_cache() -> dict:
    """
    Lataa olemassa olevan cachen.

    Jos cachea ei löydy, se generoidaan automaattisesti.
    Jos cache on rikkinäinen, varmuuskopioidaan rikkinäinen tiedosto
    ja generoidaan uusi.
    """

    if CACHE_FILE.exists():
        try:
            with CACHE_FILE.open(
                "r",
                encoding="utf-8",
            ) as file:
                return json.load(file)

        except (
            json.JSONDecodeError,
            OSError,
        ):
            # Varmuuskopioi rikkinäinen cache, jotta se ei häviä
            backup = CACHE_FILE.with_suffix(".json.bak")
            try:
                shutil.copy2(CACHE_FILE, backup)
            except OSError:
                pass
            pass

    return generate_cache()


def fetch_json(url: str) -> object:
    """
    Hakee JSON-datan URL-osoitteesta Pythonin standardikirjastolla.
    """

    with urlopen(
        url,
        timeout=10,
    ) as response:
        return json.loads(
            response.read().decode("utf-8")
        )


# ---------------------------------------------------------------------------
# GENERATE CACHE
# ---------------------------------------------------------------------------

def generate_cache() -> dict:
    """
    Generoi providerien kielicachen.
    """

    try:
        microsoft = fetch_microsoft_translator()
    except Exception:
        microsoft = {}

    try:
        libretranslate = fetch_libretranslate()
    except Exception:
        libretranslate = {}

    papago_mymemory = load_papago_mymemory()

    cache = {
        "providers": {
            "microsoft_translator": microsoft,
            "libretranslate": libretranslate,
            "papago": sorted(
                code.lower()
                for code in papago_mymemory.get(
                    "papago",
                    [],
                )
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

    with CACHE_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            cache,
            file,
            indent=4,
            ensure_ascii=False,
        )

    return cache


# ---------------------------------------------------------------------------
# PROVIDER FETCHERS
# ---------------------------------------------------------------------------

def fetch_microsoft_translator() -> dict:
    """
    Hakee Microsoft Translatorin kielitiedot.
    """

    data = fetch_json(
        "https://api.cognitive.microsofttranslator.com/"
        "languages?api-version=3.0"
    )

    translations = data.get(
        "translation",
        {},
    )

    return {
        code.lower(): info["name"]
        for code, info in translations.items()
    }


def fetch_libretranslate() -> dict:
    """
    Hakee LibreTranslaten kielitiedot.

    Ei API-avainta.
    Ei localhostia.
    """

    languages = fetch_json(
        "https://libretranslate.com/languages"
    )

    return {
        language["code"].lower(): language["name"]
        for language in languages
    }


def load_papago_mymemory(
    path: Path = PM_FILE,
) -> dict:
    """
    Lataa Papago- ja MyMemory-kielitiedot.
    """

    if not path.exists():
        return {
            "papago": [],
            "mymemory_iso_639_1": [],
        }

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)

