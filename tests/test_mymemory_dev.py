import requests
from shl.utils.env_loader import get_env_value

BASE_URL = "https://api.mymemory.dev/v1"
api_key = get_env_value("MYMEMORY_API_KEY")

if not api_key:
    raise RuntimeError("MYMEMORY_API_KEY is not configured.")

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# Dokumentaation mukaiset kenttänimet
payload = {
    "spaceName": "SHL Test Space",
    "isPublic": False,
}

# MyMemory.dev – todistetusti toimiva space-luonti (2026-09-12)
# HUOM: /create-pääte on pakollinen, muuten 404.
# HUOM: kentät ovat spaceName ja isPublic, ei name/description.
# HUOM: API-avain Authorization-otsikossa, ei URL-parametrina.


try:
    response = requests.post(
        f"{BASE_URL}/spaces/create",   # ← Oikea päätepiste
        headers=headers,
        json=payload,
        timeout=30,
    )
    print("HTTP status:", response.status_code)

    if response.status_code in (200, 201):
        print("Space luotu:")
        print(response.json())
    else:
        print("Virhe:", response.status_code)
        try:
            print("Virheen tiedot:", response.json())
        except ValueError:
            print("Virheen teksti:", response.text)

except requests.exceptions.RequestException as error:
    print("HTTP request failed:", error)
