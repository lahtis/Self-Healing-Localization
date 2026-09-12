"""
MyMemory.dev – haku POST /v1/search -päätepisteellä.

Zod-virhe paljasti, että API odottaa kenttää "query" (ei "q").
Tämä testi kokeilee oikeaa muotoa ja sen variaatioita.
"""

import requests
from shl.utils.env_loader import get_env_value

BASE_URL = "https://api.mymemory.dev/v1"
api_key = get_env_value("MYMEMORY_API_KEY")
space_uuid = "4G9yjBCS1m"
translations_uuid = "NiEqzkKVRs"

if not api_key:
    raise RuntimeError("MYMEMORY_API_KEY is not configured.")

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}


def try_post(label, path, payload):
    url = f"{BASE_URL}{path}"
    print(f"\n=== POST {label} ===")
    print(f"URL: {url}")
    print(f"Payload: {payload}")
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"Status: {r.status_code}")
        body = r.text
        if not body.strip():
            print("Body: <TYHJÄ>")
        elif len(body) > 800:
            print(f"Body (ensimmäiset 800): {body[:800]}...")
        else:
            print(f"Body: {body}")
    except requests.exceptions.RequestException as e:
        print("HTTP request failed:", e)


# ----------------------------------------------------------------------
# Perusmuoto Zod-virheen perusteella
# ----------------------------------------------------------------------

print("=" * 70)
print("HAKU: perusmuoto ja variaatiot")
print("=" * 70)

try_post("Perus query", "/search", {
    "query": "dokumentaatio",
})

try_post("Query + spaceId", "/search", {
    "query": "dokumentaatio",
    "spaceId": space_uuid,
})

try_post("Query + spaces-lista", "/search", {
    "query": "dokumentaatio",
    "spaces": [space_uuid],
})


# ----------------------------------------------------------------------
# Kokeile löytää omat muistot laajemmilla hakusanoilla
# ----------------------------------------------------------------------

print("\n" + "=" * 70)
print("HAKU: laajemmat hakusanat")
print("=" * 70)

for termi in ["mymemory", "api", "note", "surkea", "SHL", "test"]:
    try_post(f"Query: {termi}", "/search", {
        "query": termi,
        "spaceId": space_uuid,
    })


# ----------------------------------------------------------------------
# Kokeile lisäparametreja, joita API saattaa tukea
# ----------------------------------------------------------------------

print("\n" + "=" * 70)
print("HAKU: lisäparametrit")
print("=" * 70)

try_post("Limit + query", "/search", {
    "query": "mymemory",
    "limit": 50,
})

try_post("Type + query", "/search", {
    "query": "mymemory",
    "type": "note",
})

try_post("Scope + query", "/search", {
    "query": "mymemory",
    "scope": "all",
})

try_post("Ilman spaceId, laaja haku", "/search", {
    "query": "mymemory",
})
