import requests
from shl.utils.env_loader import get_env_value

BASE_URL = "https://api.mymemory.dev/v1"
api_key = get_env_value("MYMEMORY_API_KEY")
space_uuid = "4G9yjBCS1m"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "application/json",
}

try:
    response = requests.get(
        f"{BASE_URL}/memories/search",
        headers=headers,
        params={"q": "dokumentaatio", "spaceId": space_uuid},
        timeout=30,
    )
    print("HTTP status:", response.status_code)
    print("Content-Type:", response.headers.get("Content-Type"))
    print("Content-Length:", response.headers.get("Content-Length"))
    print("Raw body (repr):", repr(response.text))   # ← tärkein debug

    if response.status_code == 200:
        if not response.text.strip():
            print("Vastaus on tyhjä – todennäköisesti ei hakutuloksia.")
        else:
            try:
                data = response.json()
                print("Hakutulokset:")
                print(data)
            except ValueError as e:
                print("Ei JSONia:", e)
                print("Raaka vastaus:", response.text)

except requests.exceptions.RequestException as error:
    print("HTTP request failed:", error)
