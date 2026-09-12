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


payload = {
    "spaceName": "SHL Test Space",
    "isPublic": False,
}


try:
    response = requests.post(
        f"{BASE_URL}/spaces/create",
        headers=headers,
        json=payload,
        timeout=30,
    )

    print("HTTP status:", response.status_code)
    print("Response:")

    try:
        print(response.json())
    except ValueError:
        print(response.text)

except requests.exceptions.RequestException as error:
    print("HTTP request failed:", error)
