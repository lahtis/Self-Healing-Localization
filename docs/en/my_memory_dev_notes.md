# MyMemory.dev – Spaces and Memory Integration Test Results

## Purpose

This test investigated how MyMemory.dev `spaces` and `memories` work together from the SHL perspective.

The test created one private space and one public space. One memory was added to each space using the `/v1/add` endpoint. The test then waited for the memory to become visible in the space-specific memory list and finally tested searching within the space using `/v1/search`.

Run the test from the SHL project root:

```text
python3 -m tests.test_mymemory_dev_spaces_memory
```

## `/v1/add` – Correct Content Format

The test confirmed that the `/v1/add` endpoint expects the `content` field to be a string.

The working structure is:

```json
{
  "content": "SHL regression test memory with tags and space",
  "type": "note",
  "tags": [
    "shl-regression",
    "test"
  ],
  "spaces": [
    "SPACE_UUID"
  ]
}
```

The previously tested structure where `content` was an object:

```json
{
  "content": {
    "source": "...",
    "target": "..."
  }
}
```

does not work.

The API returns HTTP 400 with:

```text
Expected string, received object
```

For the spaces integration test, the source and target texts were therefore combined into a single `content` string.

## Private Space

The test created a private space:

```text
Name: SHL Private Memory Integration Test
UUID: s5L2X9G3Dk
ownerId: 124
isPublic: false
```

Adding the memory succeeded:

```text
POST /v1/add
HTTP 200
```

The API returned:

```json
{
  "message": "Content added successfully",
  "id": "add-124-8EdEjQ4ALh",
  "type": "note",
  "isFirstUserMemory": false
}
```

### Space-specific Memory List

Immediately after adding the memory, the space-specific request returned:

```text
GET /v1/memories?spaceId=s5L2X9G3Dk
HTTP 200
items=0
total=0
```

The memory was therefore not immediately visible.

The test polled the endpoint every two seconds. The memory eventually appeared:

```text
items=1
total=1
```

The resulting memory had:

```text
ID: add-124-8EdEjQ4ALh
type: note
tags: shl-spaces-test, en-fi
```

Content:

```text
SHL private space memory test 2026-10-04
->
SHL yksityisen spacen muistitesti 2026-10-04
```

At this point the memory still had:

```text
processingStage: embedding
isSuccessfullyProcessed: false
```

Despite this, it was already searchable.

### Space-restricted Search

The search was performed using:

```text
POST /v1/search
```

with:

```json
{
  "query": "SHL private space memory test 2026-10-04",
  "spaceId": "s5L2X9G3Dk"
}
```

The result was:

```text
HTTP 200
```

The search returned the expected memory:

```text
matchType: hybrid
similarity: 0.7962
```

The private-space test therefore succeeded end-to-end.

## Public Space

The test created a public space:

```text
Name: SHL Public Memory Integration Test
UUID: TAn2v789wN
ownerId: 124
isPublic: true
```

Adding the memory succeeded:

```text
POST /v1/add
HTTP 200
```

The API returned:

```json
{
  "message": "Content added successfully",
  "id": "add-124-tNAsZbSVhC",
  "type": "note",
  "isFirstUserMemory": false
}
```

### Space-specific Memory List

As with the private space, the memory did not appear immediately.

The initial requests returned:

```text
items=0
total=0
```

The test continued polling every two seconds until the memory appeared.

The final result was:

```text
items=1
total=1
```

The memory had:

```text
ID: add-124-tNAsZbSVhC
type: note
tags: shl-spaces-test, en-fi
processingStage: ready
isSuccessfullyProcessed: true
```

Content:

```text
SHL public space memory test 2026-10-04
->
SHL julkisen spacen muistitesti 2026-10-04
```

### Space-restricted Search

The search was performed using:

```text
POST /v1/search
```

with:

```json
{
  "query": "SHL public space memory test 2026-10-04",
  "spaceId": "TAn2v789wN"
}
```

The result was:

```text
HTTP 200
```

The expected memory was returned:

```text
matchType: hybrid
similarity: 0.8397
```

The public-space test therefore also succeeded end-to-end.

## Observation: Memory Processing Is Asynchronous

The test clearly demonstrated that `/v1/add` can return a successful response before the memory becomes visible through `GET /v1/memories?spaceId=...`.

The practical sequence is:

```text
POST /v1/add
      │
      ├── HTTP 200
      │
      ▼
Memory added
      │
      │  processing / embedding
      ▼
GET /v1/memories?spaceId=...
      │
      ├── items=0
      │
      │  ...wait...
      │
      ▼
Memory becomes visible
      │
      ▼
Memory can be found through /search
```

Therefore, an immediately empty space-specific memory list must not be interpreted as evidence that adding the memory failed.

The SHL test handles this by polling until the memory becomes visible or a timeout is reached.

## Confirmed Capabilities

The tests confirmed the following:

1. A space can be created through `/v1/spaces/create`.

2. Both private and public spaces can be created through the API.

3. The `/v1/add` endpoint accepts a `spaces` field containing a space UUID.

4. A memory can be assigned to a specific space when it is added.

5. `GET /v1/memories?spaceId=<uuid>` returns memories belonging to that space.

6. A newly added memory may take several seconds to appear in the space-specific memory list.

7. `/v1/search` accepts a `spaceId` restriction.

8. A space-restricted search can find a memory assigned to that space.

9. Both private and public spaces work with these operations.

10. `/v1/search` can find a memory before its processing status reaches `ready`.

## Relevance to SHL

Based on these tests, MyMemory.dev appears suitable for SHL's translation-memory use case.

SHL could, for example, store a translation as a single memory:

```text
source text -> translated text
```

and use a language-pair tag such as:

```text
en-fi
```

A space can then be used to separate memories according to their intended purpose.

For example:

```text
SHL Translation Memory
    │
    ├── en-fi
    ├── en-sv
    ├── en-de
    └── ...
```

Space-restricted search also allows SHL to avoid searching the entire memory collection for every lookup.

## Not Yet Tested

This test did not investigate visibility and permissions across different users.

The following questions remain open:

* Can another user see a public space?
* Can another user see memories stored in a public space?
* Can another user see a private space?
* Does a space-restricted search work for another user when the space is public?
* How exactly are public-space permissions enforced?

Testing these questions requires a second MyMemory.dev user or another working API key.

## Summary

The MyMemory.dev spaces and memory functionality works as required for the tested SHL use case.

In particular, it has been confirmed that a memory can be assigned directly to a specific space:

```text
POST /v1/add
    spaces: [space_uuid]
```

and subsequently retrieved through a space-specific memory listing:

```text
GET /v1/memories?spaceId=<space_uuid>
```

as well as through semantic search:

```text
POST /v1/search
    query: ...
    spaceId: <space_uuid>
```

The most important practical observation is the asynchronous processing behavior. `/v1/add` may return HTTP 200 even though the memory is not immediately visible through the space-specific memory list or has not yet finished embedding.

An SHL integration must therefore not interpret an immediately empty `GET /v1/memories?spaceId=...` response as a failed memory insertion.


# MyMemory.dev – Spaces API Testing and Findings

## Purpose

This test investigates the MyMemory.dev API `Spaces` functionality and its relationship with memories.

The goals of the test are to determine:

* how a user's spaces are listed
* how public and private spaces are distinguished
* what information is returned for an individual space
* whether a new space can be created as either private or public
* how memories belonging to a space are listed
* how public and private spaces appear to their owner.

The test accesses the MyMemory.dev API directly using Python's standard-library `urllib` module. No external HTTP dependency such as `requests` is used.

The API key is loaded through the SHL environment loader:

```python
from shl.utils.env_loader import get_env_value

API_KEY = get_env_value("MYMEMORY_API_KEY")
```

The test is run from the SHL project root as a module:

```bash
python3 -m tests.test_mymemory_dev_spaces
```

## Spaces Listing

Endpoint:

```text
GET /v1/spaces
```

The response contains a single `spaces` list. Public and private spaces are therefore not returned as separate lists.

For example:

```json
{
  "spaces": [
    {
      "id": 35,
      "uuid": "PT8od4asev",
      "name": "SHL Public Space Investigation",
      "ownerId": 124,
      "isPublic": true
    },
    {
      "id": 34,
      "uuid": "W6WEqizeba",
      "name": "SHL Private Space Investigation",
      "ownerId": 124,
      "isPublic": false
    }
  ]
}
```

A space is identified as public or private using:

```text
isPublic
```

The value:

```text
true
```

means that the space is public.

The value:

```text
false
```

means that the space is private.

This means that an SHL user interface could retrieve all spaces with a single API request and, if necessary, separate them into public and private sections locally.

## Initial Spaces Listing

At the beginning of the test, the user had six spaces.

All six were private:

```text
Total:   6
Public:  0
Private: 6
```

The list included, among others:

```text
SHL Regression Test
SHL Test Space
SHL Private Memory
```

All spaces owned by the user had the following permissions:

```json
{
  "canRead": true,
  "canEdit": true,
  "isOwner": true
}
```

The list response also contained the following fields:

```text
accessType
favorited
owner
permissions
```

For the user's own spaces, the following values were observed:

```text
accessType = null
favorited = false
owner = null
```

The actual access rights were provided through the `permissions` object.

## Creating a Private Space

Endpoint:

```text
POST /v1/spaces/create
```

Request:

```json
{
  "spaceName": "SHL Private Space Investigation",
  "isPublic": false
}
```

The API returned HTTP 200 and created the space successfully.

The UUID of the created space was:

```text
W6WEqizeba
```

The response included:

```json
{
  "uuid": "W6WEqizeba",
  "name": "SHL Private Space Investigation",
  "ownerId": 124,
  "isPublic": false
}
```

## Creating a Public Space

A public space can be created using the same endpoint.

Request:

```json
{
  "spaceName": "SHL Public Space Investigation",
  "isPublic": true
}
```

The API returned HTTP 200.

The UUID of the created space was:

```text
PT8od4asev
```

The response included:

```json
{
  "uuid": "PT8od4asev",
  "name": "SHL Public Space Investigation",
  "ownerId": 124,
  "isPublic": true
}
```

## Updated Spaces Listing

After the two new spaces were created, `/v1/spaces` returned a total of eight spaces.

The distribution was:

```text
Total:   8
Public:  1
Private: 7
```

The public space appeared in the same `spaces` list as the private spaces:

```text
SHL Public Space Investigation
isPublic = true
```

The private space appeared as:

```text
SHL Private Space Investigation
isPublic = false
```

This confirms that the API does not provide separate public/private lists from the owner's perspective. Instead, it returns the spaces as one combined collection.

## Retrieving an Individual Space

An individual space can be retrieved using its UUID:

```text
GET /v1/spaces/{uuid}
```

For example:

```text
GET /v1/spaces/W6WEqizeba
```

returned HTTP 200 with a structure similar to:

```json
{
  "id": 34,
  "uuid": "W6WEqizeba",
  "name": "SHL Private Space Investigation",
  "createdAt": "2026-10-04T09:36:38.828Z",
  "updatedAt": "2026-10-04T09:36:38.883Z",
  "ownerId": 124,
  "isPublic": false,
  "permissions": {
    "canRead": true,
    "canEdit": true,
    "isOwner": true,
    "isPublic": false
  }
}
```

The public space returned correspondingly:

```json
{
  "id": 35,
  "uuid": "PT8od4asev",
  "name": "SHL Public Space Investigation",
  "ownerId": 124,
  "isPublic": true,
  "permissions": {
    "canRead": true,
    "canEdit": true,
    "isOwner": true,
    "isPublic": true
  }
}
```

An important observation is that the `permissions` object in the individual-space response also contains an `isPublic` field.

## Listing Memories in a Space

Memories belonging to a space can be requested with:

```text
GET /v1/memories?spaceId={uuid}
```

For example:

```text
GET /v1/memories?spaceId=W6WEqizeba
```

and:

```text
GET /v1/memories?spaceId=PT8od4asev
```

both returned HTTP 200.

Because the spaces had just been created and no memories had yet been added to them, both responses were:

```json
{
  "items": [],
  "total": 0
}
```

This confirms that the `spaceId` filtering endpoint works at the HTTP/API level and returns an empty result when the specified space contains no memories.

The test therefore does not indicate that `spaceId` is broken.

An empty result observed in an earlier regression test immediately after adding a memory should instead be treated as a separate issue. Memory processing may still have been in progress at the time of the request.

## Confirmed Findings

The following findings can currently be considered confirmed by the test:

1. `GET /v1/spaces` works.
2. Public and private spaces are returned in the same `spaces` list.
3. `isPublic` identifies whether a space is public.
4. `POST /v1/spaces/create` is the endpoint used to create a new space.
5. `isPublic: false` creates a private space.
6. `isPublic: true` creates a public space.
7. Newly created spaces subsequently appear in `/v1/spaces`.
8. An individual space can be retrieved using `/v1/spaces/{uuid}`.
9. The individual-space response contains a `permissions` object.
10. Memories belonging to a space can be requested using `/v1/memories?spaceId={uuid}`.
11. An empty space returns HTTP 200 with `total: 0`.
12. The owner has `canRead`, `canEdit`, and `isOwner` permissions for their own spaces.

## What the Test Does Not Yet Establish

The test was performed using a single user's API key. It therefore does not establish how public and private spaces appear to another user.

The following questions remain untested:

* whether another user sees a public space in `/v1/spaces`
* whether another user sees a private space
* whether another user can read memories in a public space
* whether another user can edit a public space
* whether another user can add memories to a public space
* whether access to a private space is rejected at the API level for another user.

Testing these cases would require a second MyMemory.dev user or another API key.

## Relevance to SHL

The MyMemory.dev Spaces structure appears well suited to a possible SHL translation-memory model.

SHL could, for example, use a private space for translation memory and identify language pairs with tags such as:

```text
en-fi
fi-en
en-swe
```

Spaces could also be used to separate different purposes, for example:

```text
SHL Translation Memory
SHL Project Memory
SHL Shared Memory
```

A private space could contain a user's own translation memory, while a public space could potentially be used for shared memory.

However, this functionality should not yet be implemented in SHL based solely on this test. The actual cross-user access rules for public and private spaces should first be verified.

## Remaining Test Questions

The next useful test would be to add at least one memory to both a public and a private space and then verify:

```text
POST /v1/add
GET /v1/memories?spaceId=...
POST /v1/search
```

This would show how space contents behave in practice and how quickly a newly added memory becomes visible through the `spaceId` listing.

The next step after that would be to repeat the test using a second user account. Only then can the exact cross-user visibility and editing behavior of public and private spaces be established.

## Summary

The MyMemory.dev Spaces API uses a single combined spaces list. Public and private spaces are distinguished using the `isPublic` field.

A new space is created with:

```text
POST /v1/spaces/create
```

and its visibility is specified with:

```json
{
  "isPublic": false
}
```

or:

```json
{
  "isPublic": true
}
```

An individual space can be retrieved with:

```text
GET /v1/spaces/{uuid}
```

and the memories belonging to a space can be requested with:

```text
GET /v1/memories?spaceId={uuid}
```

The current tests confirm the basic structure and operation of the Spaces API. The visibility and permissions of public versus private spaces between different users still need to be verified separately.


# MyMemory.dev – Findings (2026-10-04)

## Overview

The MyMemory.dev API has evolved significantly since the initial tests. The current API documentation is available through the MyMemory.dev API Reference and OpenAPI documentation.

The SHL regression test was successfully run with the new API key. All major endpoints used by the test returned HTTP 200.

## Verified Working Endpoints

### Create a Space

POST /v1/spaces/create

```json
{
  "spaceName": "SHL Regression Test",
  "isPublic": false
}
```

→ 200 OK

Returns, among other fields:

```json
{
  "message": "Space created successfully",
  "space": {
    "uuid": "...",
    "name": "SHL Regression Test",
    "ownerId": 124,
    "isPublic": false,
    "createdAt": "..."
  }
}
```

NOTE: The correct endpoint is `/spaces/create`, not `/spaces`.

### Add a Memory

POST /v1/add

```json
{
  "content": "SHL regression test memory with tags and space",
  "type": "note",
  "tags": [
    "shl-regression",
    "test"
  ],
  "spaces": [
    "<space_uuid>"
  ]
}
```

→ 200 OK

Returns, among other fields:

```json
{
  "message": "Content added successfully",
  "id": "add-...",
  "type": "note",
  "isFirstUserMemory": false
}
```

NOTE: The space field is `spaces`, and its value is a list.

## Tags

### List Tags

GET /v1/tags

→ 200 OK

Example:

```json
{
  "tags": [
    {
      "tag": "shl-regression",
      "count": 1
    },
    {
      "tag": "test",
      "count": 1
    }
  ]
}
```

### Find Memories by Tag

GET /v1/memories?tags=shl-regression

→ 200 OK

Returns memories associated with the specified tag.

## Memory Listing

GET /v1/memories

→ 200 OK

Returns:

```json
{
  "items": [...],
  "total": N
}
```

User-created `note` memories added through the API are also visible in the listing.

### Limited Listing

GET /v1/memories?limit=5

→ 200 OK

Returns the user's memories within the specified limit.

### Space Filtering

GET /v1/memories?spaceId=<space_uuid>

→ 200 OK

In the regression test, the newly created space did not immediately return the newly added memory:

```json
{
  "items": [],
  "total": 0
}
```

At the same time, `/search` successfully found the same memory when restricted to the same space.

This has been reported to the MyMemory.dev developer for clarification. One possible explanation is background processing of newly added memories.

## Get an Individual Memory

GET /v1/memories/{uuid}

→ 200 OK

Returns the complete details of an individual memory.

Previous tests have shown fields including:

* `id`
* `uuid`
* `url`
* `content`
* `raw`
* `type`
* `title`
* `createdAt`
* `updatedAt`
* `userId`
* `searchVector`
* `processingLog`

## Semantic and Hybrid Search

POST /v1/search

```json
{
  "query": "search term"
}
```

→ 200 OK

Returns, among other fields:

```json
{
  "retrievalEventId": "...",
  "embeddingModel": "v2",
  "results": [
    {
      "uuid": "...",
      "content": "...",
      "type": "note",
      "similarity": 0.77,
      "matchType": "hybrid",
      "matchingChunk": {...}
    }
  ],
  "widenSuggestion": null
}
```

The search API currently supports both semantic and hybrid search.

Short queries such as `SHL` work in the current API version.

### Space-Restricted Search

POST /v1/search

Search can use a space restriction through fields such as `spaces` or `spaceId`.

The regression test successfully found the memory added to the test space:

```text
matchType: hybrid
similarity: 0.7774
```

This confirms that space filtering works with the `/search` endpoint.

### Short Keyword Search

POST /v1/search

```json
{
  "query": "SHL"
}
```

→ 200 OK

The search returned multiple SHL-related memories.

### Unknown Fields

The API now handles unknown search fields by reporting them through `ignoredFields` instead of silently discarding them.

## Chat

POST /v1/chat

→ 200 OK

The regression test successfully received a response from the chat endpoint.

The chat endpoint returned results based on MyMemory.dev's stored memories.

## Background Memory Processing

`POST /add` returns the memory before processing is necessarily complete.

For example, a newly added memory may initially contain:

```json
{
  "isSuccessfullyProcessed": false,
  "processingStage": "extracting",
  "content": null
}
```

The same memory can subsequently become searchable as processing progresses.

SHL integration should therefore account for the fact that adding a memory and completing its processing are not necessarily synchronous operations.

# MyMemory.dev – API Reference

## Base Configuration

* Base URL: `https://api.mymemory.dev/v1`
* Authentication: `Authorization: Bearer <API_KEY>`
* POST requests: `Content-Type: application/json`
* API key: `MYMEMORY_API_KEY`
* SHL uses Python's standard-library `urllib` implementation for API requests.

## Create a Space

POST /v1/spaces/create

```json
{
  "spaceName": "...",
  "isPublic": false
}
```

→ 200

NOTE: The `/create` suffix is required. The field is `spaceName`, not `name`.

## Get Spaces

GET /v1/spaces

→ 200

GET /v1/spaces/{uuid}

→ 200

GET /v1/spaces/{uuid}/memories

→ 404

## Add a Memory

POST /v1/add

```json
{
  "content": "...",
  "type": "note",
  "spaces": [
    "<space_uuid>"
  ]
}
```

→ 200

NOTE: The correct field is `spaces` (a list), not `spaceId`.

## List Memories

GET /v1/memories

→ 200

GET /v1/memories?limit=5

→ 200

GET /v1/memories?tags=<tag>

→ 200

GET /v1/memories?spaceId=<space_uuid>

→ 200

NOTE: The behavior of `spaceId` listing for newly added, still-processing memories has been reported to the MyMemory.dev developer for clarification.

## Get an Individual Memory

GET /v1/memories/{uuid}

→ 200

## Tags

GET /v1/tags

→ 200

## Semantic / Hybrid Search

POST /v1/search

```json
{
  "query": "..."
}
```

→ 200

Supported search restrictions include `spaceId` and `spaces`.

The response includes fields such as:

* `retrievalEventId`
* `embeddingModel`
* `results`
* `similarity`
* `matchType`
* `matchingChunk`
* `widenSuggestion`

## Chat

POST /v1/chat

→ 200

# Previously Unavailable or Unverified Endpoints

The following endpoints were identified as unavailable or empty during earlier testing. Their current status has not been re-verified by the latest regression test:

* GET /v1/memories/search
* POST /v1/memories/search
* GET /v1/get
* GET /v1/spaces/{uuid}/memories
* GET /v1/spaces/{uuid}/content
* GET /v1/spaces/{uuid}/items
* GET /v1/memories/{uuid}/content

## Error Interpretation

General behavior observed during testing:

* `404` → endpoint does not exist
* `400 ZodError` → endpoint exists, but a field is missing or has an invalid type
* `200` + empty response body → endpoint may be a stub
* `200` + `results: []` → search was executed successfully, but no matches were found
* `401` → API key is invalid, expired, or no longer associated with the user account

## Current Status

The SHL MyMemory.dev regression test now works successfully with the new API key.

The following functionality has been verified:

* authentication
* space creation
* memory creation
* tags
* memory listing
* individual memory retrieval
* semantic / hybrid search
* space-restricted search
* short keyword searches
* chat

The only currently unresolved observation is the behavior of `GET /memories?spaceId=...` immediately after adding a new memory. This has been reported to the MyMemory.dev developer for clarification.

