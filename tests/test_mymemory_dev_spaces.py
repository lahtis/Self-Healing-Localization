"""
MyMemory.dev space API investigation test.

Tests:
- GET /v1/spaces
- public/private space visibility
- space metadata
- creation of private and public spaces
- GET /v1/spaces/{uuid}
- GET /v1/memories?spaceId={uuid}

Uses SHL's standard environment loader and Python's standard library.
"""

import json
import urllib.error
import urllib.parse
import urllib.request

from shl.utils.env_loader import get_env_value


BASE = "https://api.mymemory.dev/v1"
API_KEY = get_env_value("MYMEMORY_API_KEY")

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


def request(method, path, params=None, payload=None):
    """Send an HTTP request to MyMemory.dev and print the result."""

    url = f"{BASE}{path}"

    if params:
        url += "?" + urllib.parse.urlencode(params)

    data = None

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    request_obj = urllib.request.Request(
        url,
        data=data,
        headers=HEADERS,
        method=method,
    )

    print()
    print("=" * 70)
    print(f"{method} {path}")

    if params:
        print(f"Params: {params}")

    if payload:
        print(f"Payload: {payload}")

    print(f"URL: {url}")

    try:
        with urllib.request.urlopen(request_obj, timeout=30) as response:
            status = response.status
            body = response.read().decode("utf-8", errors="replace")

            print(f"Status: {status}")
            print(f"Body: {body}")

            try:
                return status, json.loads(body)
            except json.JSONDecodeError:
                return status, body

    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")

        print(f"Status: {exc.code}")
        print(f"Body: {body}")

        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, body

    except urllib.error.URLError as exc:
        print(f"Connection error: {exc}")
        return None, None


def print_space(space):
    """Print the relevant fields of one space."""

    print()
    print(f"Name:       {space.get('name')}")
    print(f"ID:         {space.get('id')}")
    print(f"UUID:       {space.get('uuid')}")
    print(f"Owner ID:   {space.get('ownerId')}")
    print(f"Public:     {space.get('isPublic')}")
    print(f"AccessType: {space.get('accessType')}")
    print(f"Favorited:  {space.get('favorited')}")
    print(f"Owner:      {space.get('owner')}")

    permissions = space.get("permissions")

    if permissions is not None:
        print(f"Permissions: {permissions}")


def create_space(name, is_public):
    """Create a MyMemory.dev space and return its UUID."""

    status, data = request(
        "POST",
        "/spaces/create",
        payload={
            "spaceName": name,
            "isPublic": is_public,
        },
    )

    if status != 200 or not isinstance(data, dict):
        return None

    space = data.get("space")

    if not isinstance(space, dict):
        return None

    print()
    print("Created space:")
    print_space(space)

    return space.get("uuid")


def get_space(uuid):
    """Retrieve one space by UUID."""

    return request(
        "GET",
        f"/spaces/{urllib.parse.quote(uuid, safe='')}",
    )


def get_space_memories(uuid):
    """List memories associated with one space."""

    return request(
        "GET",
        "/memories",
        params={"spaceId": uuid},
    )


print("=" * 70)
print("MyMemory.dev SPACE API INVESTIGATION")
print("=" * 70)

if not API_KEY:
    print("ERROR: MYMEMORY_API_KEY is not configured.")
    raise SystemExit(1)


# ----------------------------------------------------------------------
# TEST A: List all spaces
# ----------------------------------------------------------------------

print()
print("=" * 70)
print("TEST A: List all spaces")
print("=" * 70)

status, data = request("GET", "/spaces")

spaces = []

if status == 200 and isinstance(data, dict):
    spaces = data.get("spaces", [])

    if not isinstance(spaces, list):
        spaces = []

print()
print(f"Total spaces returned: {len(spaces)}")

public_spaces = []
private_spaces = []

for space in spaces:
    if space.get("isPublic") is True:
        public_spaces.append(space)
    elif space.get("isPublic") is False:
        private_spaces.append(space)

print(f"Public spaces:  {len(public_spaces)}")
print(f"Private spaces: {len(private_spaces)}")


# ----------------------------------------------------------------------
# TEST B: Show public spaces
# ----------------------------------------------------------------------

print()
print("=" * 70)
print("TEST B: Public spaces")
print("=" * 70)

if not public_spaces:
    print("No public spaces returned.")

for index, space in enumerate(public_spaces, 1):
    print()
    print(f"--- Public space #{index} ---")
    print_space(space)


# ----------------------------------------------------------------------
# TEST C: Show private spaces
# ----------------------------------------------------------------------

print()
print("=" * 70)
print("TEST C: Private spaces")
print("=" * 70)

if not private_spaces:
    print("No private spaces returned.")

for index, space in enumerate(private_spaces, 1):
    print()
    print(f"--- Private space #{index} ---")
    print_space(space)


# ----------------------------------------------------------------------
# TEST D: Create a private test space
# ----------------------------------------------------------------------

print()
print("=" * 70)
print("TEST D: Create private test space")
print("=" * 70)

private_uuid = create_space(
    "SHL Private Space Investigation",
    False,
)


# ----------------------------------------------------------------------
# TEST E: Create a public test space
# ----------------------------------------------------------------------

print()
print("=" * 70)
print("TEST E: Create public test space")
print("=" * 70)

public_uuid = create_space(
    "SHL Public Space Investigation",
    True,
)


# ----------------------------------------------------------------------
# TEST F: List spaces again
# ----------------------------------------------------------------------

print()
print("=" * 70)
print("TEST F: List spaces after creating test spaces")
print("=" * 70)

status, data = request("GET", "/spaces")

if status == 200 and isinstance(data, dict):
    spaces_after = data.get("spaces", [])

    if isinstance(spaces_after, list):
        print()
        print(f"Total spaces returned: {len(spaces_after)}")

        public_after = [
            space
            for space in spaces_after
            if space.get("isPublic") is True
        ]

        private_after = [
            space
            for space in spaces_after
            if space.get("isPublic") is False
        ]

        print(f"Public spaces:  {len(public_after)}")
        print(f"Private spaces: {len(private_after)}")


# ----------------------------------------------------------------------
# TEST G: Retrieve private space directly
# ----------------------------------------------------------------------

if private_uuid:
    print()
    print("=" * 70)
    print("TEST G: Retrieve private space by UUID")
    print("=" * 70)

    get_space(private_uuid)


# ----------------------------------------------------------------------
# TEST H: Retrieve public space directly
# ----------------------------------------------------------------------

if public_uuid:
    print()
    print("=" * 70)
    print("TEST H: Retrieve public space by UUID")
    print("=" * 70)

    get_space(public_uuid)


# ----------------------------------------------------------------------
# TEST I: List memories in private space
# ----------------------------------------------------------------------

if private_uuid:
    print()
    print("=" * 70)
    print("TEST I: Memories in private space")
    print("=" * 70)

    get_space_memories(private_uuid)


# ----------------------------------------------------------------------
# TEST J: List memories in public space
# ----------------------------------------------------------------------

if public_uuid:
    print()
    print("=" * 70)
    print("TEST J: Memories in public space")
    print("=" * 70)

    get_space_memories(public_uuid)


# ----------------------------------------------------------------------
# SUMMARY
# ----------------------------------------------------------------------

print()
print("=" * 70)
print("INVESTIGATION COMPLETE")
print("=" * 70)

print()
print("Created private space UUID:")
print(private_uuid)

print()
print("Created public space UUID:")
print(public_uuid)

print()
print("The test specifically checks:")
print("  - /v1/spaces response structure")
print("  - isPublic values")
print("  - public/private space counts")
print("  - accessType")
print("  - permissions")
print("  - owner information")
print("  - private space creation")
print("  - public space creation")
print("  - direct space lookup")
print("  - memory listing by spaceId")
