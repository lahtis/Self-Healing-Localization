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

