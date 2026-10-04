"""
MyMemory.dev Spaces and Memory Integration Test.

Tests:
  1. Create a private space.
  2. Create a public space.
  3. Add one memory to each space.
  4. Poll the space memory lists until processing completes.
  5. Search each space using the search API.
  6. Print the observed results.

Run from the SHL project root:

    python3 -m tests.test_mymemory_dev_spaces_memory
"""

import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from shl.utils.env_loader import get_env_value


BASE = "https://api.mymemory.dev/v1"

API_KEY = get_env_value("MYMEMORY_DEV_API_KEY")

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "SHL-MyMemory-Spaces-Test",
}


def request(
    method,
    path,
    data=None,
    params=None,
):
    """Send an HTTP request to MyMemory.dev."""

    url = f"{BASE}{path}"

    if params:
        url = f"{url}?{urlencode(params)}"

    body = None

    if data is not None:
        body = json.dumps(data).encode("utf-8")

    req = Request(
        url,
        data=body,
        headers=HEADERS,
        method=method,
    )

    try:
        with urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")

            try:
                result = json.loads(raw)
            except json.JSONDecodeError:
                result = raw

            return response.status, result

    except HTTPError as exc:
        raw = exc.read().decode("utf-8")

        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            result = raw

        return exc.code, result

    except URLError as exc:
        return None, {
            "error": str(exc),
        }


def print_result(label, status, result):
    """Print a formatted test result."""

    print()
    print("=" * 72)
    print(label)
    print("=" * 72)
    print(f"Status: {status}")
    print(json.dumps(result, indent=2, ensure_ascii=False))


def create_space(name, is_public):
    """Create a MyMemory.dev space."""

    status, result = request(
        "POST",
        "/spaces/create",
        data={
            "spaceName": name,
            "isPublic": is_public,
        },
    )

    print_result(
        f"CREATE SPACE: {name}",
        status,
        result,
    )

    if status != 200:
        return None

    space = result.get("space", {})

    return space.get("uuid")


def add_memory(
    space_uuid,
    source_text,
    target_text,
):
    """Add a memory to a specific space."""

    payload = {
        "content": f"{source_text} -> {target_text}",
        "type": "note",
        "spaces": [space_uuid],
        "tags": [
            "shl-spaces-test",
            "en-fi",
        ],
    }

    status, result = request(
        "POST",
        "/add",
        data=payload,
    )

    print_result(
        f"ADD MEMORY TO SPACE: {space_uuid}",
        status,
        result,
    )

    return status, result


def get_space_memories(space_uuid):
    """Get memories belonging to a space."""

    return request(
        "GET",
        "/memories",
        params={
            "spaceId": space_uuid,
        },
    )


def wait_for_memory(
    space_uuid,
    expected_text,
    timeout=30,
    interval=2,
):
    """
    Poll a space until the expected memory becomes visible.

    Returns:
        tuple: (found, last_response)
    """

    print()
    print(
        f"Waiting for memory to appear in space "
        f"{space_uuid}..."
    )

    deadline = time.time() + timeout
    last_status = None
    last_result = None

    while time.time() < deadline:
        status, result = get_space_memories(space_uuid)

        last_status = status
        last_result = result

        print(
            f"  GET /memories?spaceId={space_uuid} "
            f"-> HTTP {status}"
        )

        if status == 200:
            items = result.get("items", [])

            for item in items:
                serialized = json.dumps(
                    item,
                    ensure_ascii=False,
                )

                if expected_text in serialized:
                    print("  Memory found.")
                    return True, result

            print(
                f"  Memory not visible yet "
                f"(items={len(items)}, "
                f"total={result.get('total')})."
            )

        time.sleep(interval)

    print("  Timeout reached; memory was not found.")

    return False, {
        "status": last_status,
        "result": last_result,
    }


def search_space(
    space_uuid,
    query,
):
    """Search for a memory restricted to one space."""

    payload = {
        "query": query,
        "spaceId": space_uuid,
    }

    status, result = request(
        "POST",
        "/search",
        data=payload,
    )

    print_result(
        f"SEARCH SPACE: {space_uuid} / {query}",
        status,
        result,
    )

    return status, result


def test_space(
    name,
    is_public,
    source_text,
    target_text,
):
    """Create a space and test memory storage and search."""

    print()
    print("#" * 72)
    print(
        f"TESTING {'PUBLIC' if is_public else 'PRIVATE'} SPACE"
    )
    print("#" * 72)

    space_uuid = create_space(
        name,
        is_public,
    )

    if not space_uuid:
        print("Space creation failed.")
        return

    print()
    print(f"Created space UUID: {space_uuid}")

    add_status, add_result = add_memory(
        space_uuid,
        source_text,
        target_text,
    )

    if add_status != 200:
        print("Memory creation failed.")
        return

    found, memories = wait_for_memory(
        space_uuid,
        source_text,
    )

    print_result(
        "FINAL SPACE MEMORY LIST",
        memories.get("status")
        if isinstance(memories, dict)
        and "status" in memories
        else 200,
        memories.get("result")
        if isinstance(memories, dict)
        and "result" in memories
        else memories,
    )

    search_space(
        space_uuid,
        source_text,
    )

    print()
    print(
        f"Memory visible through spaceId: "
        f"{'YES' if found else 'NO'}"
    )


def main():
    """Run the MyMemory.dev Spaces and Memory test."""

    if not API_KEY:
        print(
            "ERROR: MYMEMORY_DEV_API_KEY is not configured."
        )
        return

    print("=" * 72)
    print("MyMemory.dev Spaces + Memory Integration Test")
    print("=" * 72)

    test_space(
        name="SHL Private Memory Integration Test",
        is_public=False,
        source_text=(
            "SHL private space memory test "
            "2026-10-04"
        ),
        target_text=(
            "SHL yksityisen spacen muistitesti "
            "2026-10-04"
        ),
    )

    test_space(
        name="SHL Public Memory Integration Test",
        is_public=True,
        source_text=(
            "SHL public space memory test "
            "2026-10-04"
        ),
        target_text=(
            "SHL julkisen spacen muistitesti "
            "2026-10-04"
        ),
    )

    print()
    print("=" * 72)
    print("TEST COMPLETE")
    print("=" * 72)
    print()
    print(
        "Created test spaces are intentionally not deleted."
    )


if __name__ == "__main__":
    main()
