"""
file: provider_cache.py - Providers language support and cache. 
Author: Tuomas Lähteenmäki
License: MIT
Version: 0.2.5
Checks the language support of service providers and saves it to the cache. 
"""

import json
import os
import requests

CACHE_FILE = "languages_cache.json"
PM_FILE = "data/papago_mymemory.json"


# ---------------------------------------------------------
# 1) Lataa olemassa oleva cache (EI verkkoa)
# ---------------------------------------------------------

def load_cache() -> dict:
    """Load existing provider language cache without generating anything."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}  # router päättää mitä tehdä jos tyhjä


# ---------------------------------------------------------
# 2) Generoi cache (KÄYTTÄÄ VERKKOA, mutta vain kun kutsutaan)
# ---------------------------------------------------------

def generate_cache() -> dict:
    """Generate provider language cache using network calls."""
    ms = fetch_microsoft_translator()     # POST
    lt = fetch_libretranslate()           # POST
    pm = load_pagago_mymemory()           # JSON

    cache = {
        "providers": {
            "microsoft_translator": ms,
            "libretranslate": lt,
            "papago": sorted(code.lower() for code in pm.get("papago", [])),
            "mymemory": sorted(code.lower() for code in pm.get("mymemory_iso_639_1", [])),
        }
    }

    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=4, ensure_ascii=False)

    return cache


# ---------------------------------------------------------
# 3) Provider-kohtaiset hakijat (VERKKOA)
# ---------------------------------------------------------

def fetch_microsoft_translator() -> dict:
    url = "https://api.cognitive.microsofttranslator.com/languages?api-version=3.0"
    resp = requests.post(url, timeout=10)
    resp.raise_for_status()
    data = resp.json().get("translation", {})
    return {code.lower(): info["name"] for code, info in data.items()}


def fetch_libretranslate() -> dict:
    url = "https://libretranslate.com/languages"
    resp = requests.post(url, timeout=10)
    resp.raise_for_status()
    langs = resp.json()
    return {lang["code"].lower(): lang["name"] for lang in langs}


def load_papago_mymemory(path: str = PM_FILE) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

