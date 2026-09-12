import requests

from shl.utils.env_loader import get_env_value


BASE_URL = "https://api.mymemory.translated.net/set"


api_key = get_env_value("MYMEMORY_API_KEY")

if not api_key:
    raise RuntimeError("MYMEMORY_API_KEY is not configured.")


params = {
    "seg": "SHL raw private memory test",
    "tra": "SHL raaka yksityisen muistin testi",
    "langpair": "en|fi",
    "key": api_key,
}


try:
    response = requests.get(
        BASE_URL,
        params=params,
        timeout=30,
    )

    print("HTTP status:", response.status_code)
    print("Request URL:", response.url.replace(api_key, "***"))

    data = response.json()

    print("MyMemory response status:", data.get("responseStatus"))
    print("MyMemory response details:", data.get("responseDetails"))
    print("Full response:")
    print(data)

except requests.exceptions.RequestException as error:
    print("HTTP request failed:", error)

except ValueError:
    print("Response is not in JSON format.")
    print(response.text)
