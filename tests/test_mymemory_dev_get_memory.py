"""
Testi: MyMemory.dev – muiston hakeminen.

Yrittää hakea aiemmin tallennetun muiston (id: add-124-oanTc7pWNB)
usealla eri päätepisteellä, koska dokumentaatio ei kerro oikeaa tapaa.

Tulostaa jokaisen yrityksen tuloksen, jotta näet mikä toimii.
"""

import requests
from shl.utils.env_loader import get_env_value

BASE_URL = "https://api.mymemory.dev/v1"
api_key = get_env_value("MYMEMORY_API_KEY")
space_uuid = "4G9yjBCS1m"
memory_id = "add-124-oanTc7pWNB"   # äsken tallennettu muisto

if not api_key:
    raise RuntimeError("MYMEMORY_API_KEY is not configured.")

headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "application/json",
}


def try_get(label, url, params=None):
    """Apufunktio: tekee GET-kutsun ja tulostaa tuloksen."""
    print(f"\n--- {label} ---")
    print(f"URL: {url}")
    if params:
        print(f"Params: {params}")
    try:
        r = requests.get(url, headers=headers, params=params, timeout=30)
        print("Status:", r.status_code)
        print("Content-Type:", r.headers.get("Content-Type"))
        print("Body (repr):", repr(r.text))
        if r.status_code == 200 and r.text.strip():
            try:
                print("JSON:", r.json())
            except ValueError:
                pass
    except requests.exceptions.RequestException as e:
        print("HTTP request failed:", e)


# ----------------------------------------------------------------------
# Yritys 1: Hae muisto suoraan ID:llä
# ----------------------------------------------------------------------
try_get(
    "Hae muisto ID:llä",
    f"{BASE_URL}/memories/{memory_id}",
)


# ----------------------------------------------------------------------
# Yritys 2: Hae tekstihaulla
# ----------------------------------------------------------------------
try_get(
    "Hae tekstihaulla",
    f"{BASE_URL}/memories/search",
    params={"q": "dokumentaatio", "spaceId": space_uuid},
)


# ----------------------------------------------------------------------
# Yritys 3: Listaa kaikki muistot spacesta
# ----------------------------------------------------------------------
try_get(
    "Listaa spacen muistot",
    f"{BASE_URL}/spaces/{space_uuid}/memories",
)


# ----------------------------------------------------------------------
# Yritys 4: Listaa kaikki muistot (ilman space-rajausta)
# ----------------------------------------------------------------------
try_get(
    "Listaa kaikki muistot",
    f"{BASE_URL}/memories",
)


# ----------------------------------------------------------------------
# Yritys 5: /v1/get (sama tyyli kuin /v1/add)
# ----------------------------------------------------------------------
try_get(
    "Hae /get-päätepisteellä",
    f"{BASE_URL}/get",
    params={"spaces": [space_uuid]},
)
