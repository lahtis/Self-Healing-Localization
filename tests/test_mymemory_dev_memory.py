import requests
from shl.utils.env_loader import get_env_value

BASE_URL = "https://api.mymemory.dev/v1"
api_key = get_env_value("MYMEMORY_API_KEY")
space_uuid = "4G9yjBCS1m"

if not api_key:
    raise RuntimeError("MYMEMORY_API_KEY is not configured.")

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# Vaihtoehto 1: /v1/add + spaces-lista (Spaces-sivun mukaan)
payload = {
    "content": (
        "MyMemory.dev API:n dokumentaatio on surkea – sitä ei käytännössä ole. "
        "Päätepisteet ja payload-kentät on selvitetty yrityksen ja erehdyksen kautta. "
        "Esimerkiksi /v1/spaces/create vaatii spaceName-kentän, ei name-kenttää. "
        "Muistojen luonti: POST /v1/add, kentät content, type, spaces."
    ),
    "type": "note",
    "spaces": [space_uuid],   # ← lista, ei spaceId
}

try:
    response = requests.post(
        f"{BASE_URL}/add",     # ← Vaihdettu /memories → /add
        headers=headers,
        json=payload,
        timeout=30,
    )

    print("HTTP status:", response.status_code)
    print("Content-Type:", response.headers.get("Content-Type"))
    print("Raw body (repr):", repr(response.text))
    print()

    if response.status_code in (200, 201):
        if not response.text.strip():
            print("Vastaus on tyhjä – mutta status oli OK. Muisto tallennettiin todennäköisesti.")
        else:
            try:
                print("Muisto luotu:", response.json())
            except ValueError:
                print("Vastaus ei ole JSONia:", response.text)
    else:
        print("Virhe:", response.status_code)
        try:
            print("Virheen tiedot:", response.json())
        except ValueError:
            print("Virheen teksti:", response.text)

except requests.exceptions.RequestException as error:
    print("HTTP request failed:", error)
