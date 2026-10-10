"""
MyMemory.dev Spaces and Memory Integration Test.

Tests:
  1. Create a private space.
  2. Create a public space.
  3. Add one memory to each space.
  4. Poll the space memory lists until the memory is visible.
  5. Poll until the memory has finished processing (embedding).
  6. Search each space using the search API.
  7. Delete the test memory from each space.
  8. Print the observed results.

Run from the SHL project root:

    python3 -m tools.test_mymemory_dev_spaces_memory

Not a pytest test — this is a manual integration script.
"""

import json
import time
import uuid
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


def make_test_text(prefix):
    """Return a unique test string for this run.

    MyMemory.dev deduplicates content globally per user account, so
    re-running the test with identical text fails with HTTP 409.
    The short UUID suffix makes every run unique without changing
    the semantics of the test.
    """
    return f"{prefix} [{uuid.uuid4().hex[:8]}]"


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
    """Add a memory to a specific space.

    Returns:
        tuple: (status, memory_uuid_or_None, raw_result)
    """

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

    memory_uuid = None
    if status == 200 and isinstance(result, dict):
        memory_uuid = result.get("id")

    return status, memory_uuid, result


def delete_memory(memory_uuid):
    """Delete a memory by UUID.

    Returns True on success (HTTP 200 or 204) or if the memory was
    already gone (HTTP 404). Returns False on any other failure.
    """

    print()
    print(f"Deleting memory: {memory_uuid}")

    status, result = request(
        "DELETE",
        f"/memories/{memory_uuid}",
    )

    if status in (200, 204, 404):
        print(f"  OK (HTTP {status}).")
        return True

    print_result(
        f"DELETE MEMORY FAILED: {memory_uuid}",
        status,
        result,
    )
    return False


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
    """Poll a space until the expected memory becomes visible.

    Returns:
        tuple: (found, last_response, elapsed_seconds)
    """

    print()
    print(
        f"Waiting for memory to appear in space "
        f"{space_uuid}..."
    )

    started = time.time()
    deadline = started + timeout
    last_status = None
    last_result = None

    while time.time() < deadline:
        status, result = get_space_memories(space_uuid)

        last_status = status
        last_result = result

        elapsed = time.time() - started

        print(
            f"  GET /memories?spaceId={space_uuid} "
            f"-> HTTP {status} "
            f"({elapsed:.1f}s)"
        )

        if status == 200:
            items = result.get("items", [])

            for item in items:
                serialized = json.dumps(
                    item,
                    ensure_ascii=False,
                )

                if expected_text in serialized:
                    elapsed = time.time() - started
                    print(
                        f"  Memory found after "
                        f"{elapsed:.1f}s."
                    )
                    return True, result, elapsed

            print(
                f"  Memory not visible yet "
                f"(items={len(items)}, "
                f"total={result.get('total')})."
            )

        time.sleep(interval)

    elapsed = time.time() - started
    print(
        f"  Timeout reached after {elapsed:.1f}s; "
        f"memory was not found."
    )

    return False, {
        "status": last_status,
        "result": last_result,
    }, elapsed


def wait_for_processed(
    space_uuid,
    timeout=60,
    interval=2,
):
    """Poll a space until every memory is fully processed.

    Search is unreliable until the embedding stage has completed,
    so callers should wait for this before running search queries.

    Returns:
        tuple: (processed, elapsed_seconds)
    """

    print()
    print(
        f"Waiting for memories in space {space_uuid} "
        f"to finish processing..."
    )

    started = time.time()
    deadline = started + timeout

    while time.time() < deadline:
        status, result = get_space_memories(space_uuid)

        elapsed = time.time() - started

        if status == 200:
            items = result.get("items", [])

            if not items:
                print(
                    f"  No items yet ({elapsed:.1f}s)."
                )
                time.sleep(interval)
                continue

            pending = [
                item for item in items
                if not item.get("isSuccessfullyProcessed")
            ]

            if not pending:
                print(
                    f"  All {len(items)} memories processed "
                    f"after {elapsed:.1f}s."
                )
                return True, elapsed

            stages = {
                item.get("processingStage")
                for item in pending
            }
            stages.discard(None)

            print(
                f"  {len(pending)}/{len(items)} still "
                f"processing ({elapsed:.1f}s), "
                f"stages: {', '.join(sorted(stages)) or 'unknown'}"
            )

        time.sleep(interval)

    elapsed = time.time() - started
    print(
        f"  Timeout reached after {elapsed:.1f}s; "
        f"memories were not fully processed."
    )

    return False, elapsed


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


def run_space_test(
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

    add_status, memory_uuid, add_result = add_memory(
        space_uuid,
        source_text,
        target_text,
    )

    if add_status != 200:
        print("Memory creation failed.")
        return

    found, memories, wait_elapsed = wait_for_memory(
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

    # Wait until processing completes before searching; otherwise
    # search may return an empty result even though the memory is
    # already visible in the space listing.
    processed, process_elapsed = wait_for_processed(space_uuid)

    search_space(
        space_uuid,
        source_text,
    )

    print()
    print("-" * 72)
    print("SUMMARY")
    print("-" * 72)
    print(
        f"Memory visible through spaceId: "
        f"{'YES' if found else 'NO'}"
    )
    print(
        f"Memory fully processed:         "
        f"{'YES' if processed else 'NO'}"
    )
    print(f"Time to become visible:         {wait_elapsed:.1f}s")
    print(f"Time to finish processing:      {process_elapsed:.1f}s")
    print(
        f"Total wait time:                "
        f"{wait_elapsed + process_elapsed:.1f}s"
    )

    # Clean up the memory so repeated runs do not accumulate test
    # content on the account. The space itself is left in place
    # because the API does not document a space-delete endpoint.
    if memory_uuid:
        delete_memory(memory_uuid)


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

    run_space_test(
        name=(
            "SHL Private Memory Integration Test "
            f"{uuid.uuid4().hex[:6]}"
        ),
        is_public=False,
        source_text=make_test_text(
            "SHL private space memory test"
        ),
        target_text=make_test_text(
            "SHL yksityisen spacen muistitesti"
        ),
    )

    run_space_test(
        name=(
            "SHL Public Memory Integration Test "
            f"{uuid.uuid4().hex[:6]}"
        ),
        is_public=True,
        source_text=make_test_text(
            "SHL public space memory test"
        ),
        target_text=make_test_text(
            "SHL julkisen spacen muistitesti"
        ),
    )

    print()
    print("=" * 72)
    print("TEST COMPLETE")
    print("=" * 72)
    print()
    print(
        "Test memories are deleted after each run. "
        "Test spaces are intentionally not deleted."
    )


if __name__ == "__main__":
    main()
