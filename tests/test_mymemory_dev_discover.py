"""
MyMemory.dev – dokumentaation puutteen selvitystyökalu.

Kokeilee järjestelmällisesti eri päätepisteitä, parametreja ja
HTTP-metodeja selvittääkseen, miten API todella toimii.

Jokainen testi on itsenäinen – yhden epäonnistuminen ei kaada muita.
Tulokset tulostetaan selkeästi, jotta nähdään mikä toimii ja mikä ei.
"""

import requests
from shl.utils.env_loader import get_env_value

BASE_URL = "https://api.mymemory.dev/v1"
api_key = get_env_value("MYMEMORY_API_KEY")
space_uuid = "4G9yjBCS1m"
memory_id = "add-124-oanTc7pWNB"

if not api_key:
    raise RuntimeError("MYMEMORY_API_KEY is not configured.")

headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "application/json",
}

json_headers = {
    **headers,
    "Content-Type": "application/json",
}


# ----------------------------------------------------------------------
# Apufunktiot
# ----------------------------------------------------------------------

def try_get(label, path, params=None):
    """GET-kutsu ja tulostus."""
    url = f"{BASE_URL}{path}"
    print(f"\n=== GET {label} ===")
    print(f"URL: {url}")
    if params:
        print(f"Params: {params}")
    try:
        r = requests.get(url, headers=headers, params=params, timeout=30)
        _print_result(r)
    except requests.exceptions.RequestException as e:
        print("HTTP request failed:", e)


def try_post(label, path, payload):
    """POST-kutsu ja tulostus."""
    url = f"{BASE_URL}{path}"
    print(f"\n=== POST {label} ===")
    print(f"URL: {url}")
    print(f"Payload: {payload}")
    try:
        r = requests.post(url, headers=json_headers, json=payload, timeout=30)
        _print_result(r)
    except requests.exceptions.RequestException as e:
        print("HTTP request failed:", e)


def _print_result(r):
    """Tulostaa tuloksen yhdenmukaisesti."""
    print(f"Status: {r.status_code}")
    body = r.text
    if not body.strip():
        print("Body: <TYHJÄ>")
        return
    # Lyhennä pitkät vastaukset
    if len(body) > 500:
        print(f"Body (ensimmäiset 500 merkkiä): {body[:500]}...")
    else:
        print(f"Body: {body}")


# ----------------------------------------------------------------------
# TESTI A: Listan suodatus ja paginointi
# ----------------------------------------------------------------------

print("\n" + "=" * 70)
print("TESTI A: Listan suodatus ja paginointi")
print("=" * 70)

try_get("Listaa kaikki (oletus)", "/memories")
try_get("Listaa vain note-tyyppi", "/memories", {"type": "note"})
try_get("Listaa vain page-tyyppi", "/memories", {"type": "page"})
try_get("Listaa suuremmalla rajalla", "/memories", {"limit": 100})
try_get("Listaa type=note&limit=100", "/memories", {"type": "note", "limit": 100})


# ----------------------------------------------------------------------
# TESTI B: Haku POST-metodilla
# ----------------------------------------------------------------------

print("\n" + "=" * 70)
print("TESTI B: Haku POST-metodilla")
print("=" * 70)

try_post("Haku POST /memories/search", "/memories/search", {
    "q": "dokumentaatio",
    "spaceId": space_uuid,
})

try_post("Haku POST /search", "/search", {
    "q": "dokumentaatio",
    "spaceId": space_uuid,
})

try_post("Haku POST /memories/search ilman spaceId", "/memories/search", {
    "q": "dokumentaatio",
})


# ----------------------------------------------------------------------
# TESTI C: Hakuparametrien variaatiot GET-metodilla
# ----------------------------------------------------------------------

print("\n" + "=" * 70)
print("TESTI C: Hakuparametrien variaatiot")
print("=" * 70)

try_get("Haku q + space", "/memories/search", {"q": "dokumentaatio", "spaceId": space_uuid})
try_get("Haku query-parametrilla", "/memories/search", {"query": "dokumentaatio", "spaceId": space_uuid})
try_get("Haku text-parametrilla", "/memories/search", {"text": "dokumentaatio", "spaceId": space_uuid})
try_get("Haku spaces-listana", "/memories/search", {"q": "dokumentaatio", "spaces": space_uuid})
try_get("Haku vain q", "/memories/search", {"q": "dokumentaatio"})
try_get("Haku spaceId yksin", "/memories/search", {"spaceId": space_uuid})


# ----------------------------------------------------------------------
# TESTI D: Space-kohtaiset haut
# ----------------------------------------------------------------------

print("\n" + "=" * 70)
print("TESTI D: Space-kohtaiset haut")
print("=" * 70)

try_get("Space + /content", f"/spaces/{space_uuid}/content")
try_get("Space + /items", f"/spaces/{space_uuid}/items")
try_get("Space sellaisenaan", f"/spaces/{space_uuid}")
try_get("Listaa kaikki spacet", "/spaces")


# ----------------------------------------------------------------------
# TESTI E: Muiston päivitys ja metadata
# ----------------------------------------------------------------------

print("\n" + "=" * 70)
print("TESTI E: Muiston haku ja metadata")
print("=" * 70)

try_get("Hae muisto ID:llä", f"/memories/{memory_id}")
try_get("Hae muisto /content-polulla", f"/memories/{memory_id}/content")


# ----------------------------------------------------------------------
# Yhteenveto
# ----------------------------------------------------------------------

print("\n" + "=" * 70)
print("SELVITYS VALMIS")
print("=" * 70)
print(
    "\nTulkitse tulokset yllä olevista testeistä:\n"
    "  - Status 200 + runko  → päätepiste toimii\n"
    "  - Status 200 + tyhjä  → päätepiste on olemassa, mutta parametrit ovat väärät\n"
    "  - Status 404          → päätepistettä ei ole olemassa\n"
    "  - Status 401          → API-avain ei kelpaa\n"
    "  - Status 400          → parametrit ovat väärät\n"
)
