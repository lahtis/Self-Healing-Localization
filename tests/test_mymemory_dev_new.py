import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from shl.utils.env_loader import get_env_value


API_KEY = get_env_value("MYMEMORY_API_KEY")

if not API_KEY:
    raise RuntimeError("MYMEMORY_API_KEY is not configured.")

BASE = "https://api.mymemory.dev/v1"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}


def call(method, path, payload=None):
    url = f"{BASE}{path}"

    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    request = Request(
        url,
        data=data,
        headers=HEADERS,
        method=method,
    )

    try:
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")

            print(f"\n{'=' * 60}")
            print(f"{method} {path} → {response.status}")

            try:
                result = json.loads(body)
                print(json.dumps(result, indent=2, ensure_ascii=False)[:2000])
                return result
            except json.JSONDecodeError:
                print(body[:1000])
                return None

    except HTTPError as error:
        print(f"\n{'=' * 60}")
        print(f"{method} {path} → HTTP {error.code}")

        try:
            body = error.read().decode("utf-8")
            print(body[:2000])
        except Exception:
            print(error)

        return None

    except URLError as error:
        print(f"\nHTTP request failed: {error}")
        return None


# 1. Create test space
space = call(
    "POST",
    "/spaces/create",
    {
        "spaceName": "SHL Regression Test",
        "isPublic": False,
    },
)

space_uuid = space.get("space", {}).get("uuid") if space else None

if not space_uuid:
    raise RuntimeError("Could not create test space.")

print(f"\nSpace UUID: {space_uuid}")


# 2. Add memory with tags and space
call(
    "POST",
    "/add",
    {
        "content": "SHL regression test memory with tags and space",
        "type": "note",
        "tags": ["shl-regression", "test"],
        "spaces": [space_uuid],
    },
)


# 3. List tags
call("GET", "/tags")


# 4. Get memories by tag
call("GET", "/memories?tags=shl-regression")


# 5. Get memories from the test space
call("GET", f"/memories?spaceId={space_uuid}")


# 6. Basic memory listing
call("GET", "/memories?limit=5")


# 7. Search without space restriction
call(
    "POST",
    "/search",
    {
        "query": "SHL regression test memory",
    },
)


# 8. Search using spaces
call(
    "POST",
    "/search",
    {
        "query": "SHL regression test memory",
        "spaces": [space_uuid],
    },
)


# 9. Search using spaceId
call(
    "POST",
    "/search",
    {
        "query": "SHL regression test memory",
        "spaceId": space_uuid,
    },
)


# 10. Short keyword search
call(
    "POST",
    "/search",
    {
        "query": "SHL",
    },
)


# 11. Semantic search
call(
    "POST",
    "/search",
    {
        "query": "What have I learned about testing?",
    },
)


# 12. Unknown field / ignoredFields
call(
    "POST",
    "/search",
    {
        "query": "SHL regression test memory",
        "spaceID": space_uuid,
    },
)


# 13. Chat
call(
    "POST",
    "/chat",
    {
        "messages": [
            {
                "role": "user",
                "content": "What do I remember about testing?",
            }
        ]
    },
)
