import json
import urllib.parse
import urllib.request

from shl.utils.env_loader import get_env_value


API_URL = "https://api.mymemory.translated.net/get"

SOURCE_LANG = "en"
TARGET_LANG = "es"

TEST_TEXTS = [
    "Saved: {702826718258_0_50212006055}",
    "Clear the {629167323872_0_43558167237} database",
]


def translate(text: str) -> str | None:
    email = get_env_value("MYMEMORY_EMAIL", "")
    api_key = get_env_value("MYMEMORY_API_KEY", "")

    if not email or not api_key:
        raise RuntimeError(
            "MyMemory credentials were not found."
        )

    params = urllib.parse.urlencode(
        {
            "q": text,
            "langpair": f"{SOURCE_LANG}|{TARGET_LANG}",
            "de": email,
        }
    )

    request = urllib.request.Request(
        f"{API_URL}?{params}",
        headers={
            "User-Agent": "SHL-Placeholder-Test/1.0",
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="GET",
    )

    with urllib.request.urlopen(
        request,
        timeout=15,
    ) as response:
        data = json.loads(
            response.read().decode("utf-8")
        )

    print("HTTP:", response.status)
    print(
        "responseStatus:",
        data.get("responseStatus"),
    )

    response_data = data.get(
        "responseData",
        {},
    )

    translated = response_data.get(
        "translatedText"
    )

    return translated


def main() -> None:
    for text in TEST_TEXTS:
        print()
        print("=" * 70)
        print("INPUT:")
        print(repr(text))

        try:
            result = translate(text)

            print("OUTPUT:")
            print(repr(result))

            if result is None:
                print("RESULT: No translation returned.")
                continue

            start = text.find("{")
            end = text.find("}", start)

            if start != -1 and end != -1:
                original_token = text[start:end + 1]

                print("ORIGINAL TOKEN:")
                print(repr(original_token))

                print("TOKEN PRESERVED:")
                print(
                    "YES"
                    if original_token in result
                    else "NO"
                )

        except Exception as exc:
            print(
                "ERROR:",
                type(exc).__name__,
                str(exc),
            )


if __name__ == "__main__":
    main()
