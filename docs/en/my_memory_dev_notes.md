# MyMemory.dev – API Findings and SHL Integration Notes

**Date:** 2026-10-04

## Overview

The MyMemory.dev API has evolved significantly since the initial SHL integration tests.

The current API supports spaces, memories, tags, semantic and hybrid search, and chat. The current API behavior described below is based on successful SHL regression tests performed with a new API key.

The tests were performed directly against:

```text
https://api.mymemory.dev/v1
```

SHL uses Python's standard-library `urllib` for API communication and does not require `requests` or another HTTP client dependency.

The current API behavior should be considered the authoritative result of the latest regression tests. Earlier observations from 2026-09-12 are retained near the end of this document as historical findings.

---

# Authentication and Basic Configuration

The current SHL integration uses:

```text
Base URL:
https://api.mymemory.dev/v1

Authentication:
Authorization: Bearer <API_KEY>

API key:
MYMEMORY_DEV_API_KEY

POST content type:
Content-Type: application/json
```

The API key is loaded through SHL's environment loader.

SHL uses Python's standard-library `urllib` implementation for HTTP requests.

The current regression test was successfully executed with a new API key.

All major endpoints used by the test returned HTTP 200.

---

# Verified API Endpoints

## Creating a Space

Endpoint:

```text
POST /v1/spaces/create
```

Request:

```json
{
  "spaceName": "SHL Regression Test",
  "isPublic": false
}
```

Result:

```text
HTTP 200 OK
```

The response contains information such as:

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

Important:

The correct endpoint is:

```text
/v1/spaces/create
```

not:

```text
/v1/spaces
```

The request field is:

```text
spaceName
```

not:

```text
name
```

---

## Listing Spaces

Endpoint:

```text
GET /v1/spaces
```

Result:

```text
HTTP 200 OK
```

The API returns a single `spaces` list containing both public and private spaces.

Example:

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

The `isPublic` field determines whether a space is public or private.

There are no separate public/private listing endpoints from the owner's perspective.

---

## Getting an Individual Space

Endpoint:

```text
GET /v1/spaces/{uuid}
```

Result:

```text
HTTP 200 OK
```

Example:

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

For an owned public space, the response similarly contains:

```json
{
  "permissions": {
    "canRead": true,
    "canEdit": true,
    "isOwner": true,
    "isPublic": true
  }
}
```

For the owner, the tests confirmed:

```text
canRead  = true
canEdit  = true
isOwner  = true
```

---

# Adding Memories

Endpoint:

```text
POST /v1/add
```

A working request is:

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

Result:

```text
HTTP 200 OK
```

Example response:

```json
{
  "message": "Content added successfully",
  "id": "add-...",
  "type": "note",
  "isFirstUserMemory": false
}
```

Important:

The space field is:

```text
spaces
```

and its value is a list.

It is not:

```text
spaceId
```

The correct endpoint is `/v1/add`, not `/v1/memories`.

---

## Memory Content Must Be a String

The `content` field must contain a string.

This works:

```json
{
  "content": "source text -> translated text",
  "type": "note",
  "spaces": [
    "<space_uuid>"
  ]
}
```

This does not work:

```json
{
  "content": {
    "source": "...",
    "target": "..."
  }
}
```

The latter produces HTTP 400 with an error similar to:

```text
Expected string, received object
```

For SHL, this means translation-memory information should be serialized into a single string before being sent to `/v1/add`.

SHL's current translation-memory representation can, for example, contain:

```text
Source language: en
Target language: fi
Source: Hello
Translation: Hei
```

---

# Tags

## Listing Tags

Endpoint:

```text
GET /v1/tags
```

Result:

```text
HTTP 200 OK
```

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

## Searching Memories by Tag

Endpoint:

```text
GET /v1/memories?tags=shl-regression
```

Result:

```text
HTTP 200 OK
```

The endpoint returns memories associated with the requested tag.

---

# Listing Memories

Endpoint:

```text
GET /v1/memories
```

Result:

```text
HTTP 200 OK
```

Response structure:

```json
{
  "items": [...],
  "total": 0
}
```

The current API returns user memories through this endpoint.

A limit can also be specified:

```text
GET /v1/memories?limit=5
```

which also returns HTTP 200.

Space filtering is supported:

```text
GET /v1/memories?spaceId=<space_uuid>
```

which returns HTTP 200.

One important detail is that newly added memories may not appear immediately. This is caused by asynchronous processing rather than by the `spaceId` filter itself.

---

# Getting an Individual Memory

Endpoint:

```text
GET /v1/memories/{uuid}
```

Result:

```text
HTTP 200 OK
```

The response contains the full memory information.

Fields observed during testing include:

```text
id
uuid
url
content
raw
type
title
createdAt
updatedAt
userId
searchVector
processingLog
```

The exact response structure may contain additional fields.

---

# Semantic and Hybrid Search

Endpoint:

```text
POST /v1/search
```

Basic request:

```json
{
  "query": "search text"
}
```

Result:

```text
HTTP 200 OK
```

The current API returns fields such as:

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
      "matchingChunk": {}
    }
  ],
  "widenSuggestion": null
}
```

The current API therefore supports both semantic and hybrid retrieval.

The response can include:

```text
retrievalEventId
embeddingModel
results
similarity
matchType
matchingChunk
widenSuggestion
```

The current implementation uses embedding model:

```text
v2
```

---

## Short Queries

Short queries such as:

```text
SHL
```

work in the current API version.

For example:

```json
{
  "query": "SHL"
}
```

returned multiple memories related to SHL during the regression tests.

This is an important difference from the earlier September tests, where short queries such as `SHL` did not return useful results.

---

# Space-Restricted Search

The current `/v1/search` endpoint supports space restrictions.

For example:

```json
{
  "query": "SHL private space memory test 2026-10-04",
  "spaceId": "s5L2X9G3Dk"
}
```

The request returned:

```text
HTTP 200
```

and found the memory belonging to that space.

The result included:

```text
matchType: hybrid
similarity: 0.7962
```

A corresponding public-space test returned:

```text
matchType: hybrid
similarity: 0.8397
```

Another regression test produced:

```text
similarity: 0.7774
```

These tests confirm that space-restricted search works with the current `/v1/search` implementation.

The API can accept space restrictions using fields such as:

```text
spaceId
spaces
```

The exact request format should follow the current API schema used by the endpoint.

---

# Unknown Search Fields

The current API can report unknown search fields through an `ignoredFields` value instead of silently discarding them.

This is useful for API clients because an incorrectly supplied search parameter can be detected rather than disappearing without any indication.

---

# Chat

Endpoint:

```text
POST /v1/chat
```

Result:

```text
HTTP 200 OK
```

The regression test successfully received a response from the chat endpoint.

The returned information was based on MyMemory.dev's memory retrieval functionality.

---

# Asynchronous Memory Processing

One of the most important findings for SHL integration is that adding a memory is asynchronous.

`POST /v1/add` can return HTTP 200 before the memory has finished processing.

For example, a newly added memory may initially contain:

```json
{
  "isSuccessfullyProcessed": false,
  "processingStage": "extracting",
  "content": null
}
```

Later, the processing stage can become:

```text
embedding
```

and eventually:

```text
ready
```

with:

```text
isSuccessfullyProcessed: true
```

The important observation is that a memory can already be searchable before its processing status reaches `ready`.

---

# Space and Memory Integration Test

The SHL regression test also specifically tested the relationship between spaces and memories.

The test created:

1. one private space
2. one public space

A memory was then added to each space using `/v1/add`.

The test subsequently checked:

```text
GET /v1/memories?spaceId=...
```

and:

```text
POST /v1/search
```

with a space restriction.

---

## Private Space Test

A private space was created:

```text
Name: SHL Private Memory Integration Test
UUID: s5L2X9G3Dk
ownerId: 124
isPublic: false
```

A memory was added successfully:

```text
POST /v1/add
HTTP 200
```

Immediately after the addition:

```text
GET /v1/memories?spaceId=s5L2X9G3Dk
```

returned:

```text
items=0
total=0
```

The test then polled the endpoint every two seconds.

Eventually:

```text
items=1
total=1
```

The memory was:

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

At this point the memory was still:

```text
processingStage: embedding
isSuccessfullyProcessed: false
```

Nevertheless, it was already searchable.

A space-restricted search was performed:

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

The memory was found with:

```text
matchType: hybrid
similarity: 0.7962
```

The private-space test therefore succeeded.

---

## Public Space Test

A public space was created:

```text
Name: SHL Public Memory Integration Test
UUID: TAn2v789wN
ownerId: 124
isPublic: true
```

The memory was added successfully:

```text
POST /v1/add
HTTP 200
```

Immediately afterwards, the space-specific memory list was still empty:

```text
items=0
total=0
```

After polling:

```text
items=1
total=1
```

The memory had reached:

```text
processingStage: ready
isSuccessfullyProcessed: true
```

The content was:

```text
SHL public space memory test 2026-10-04
->
SHL julkisen spacen muistitesti 2026-10-04
```

A space-restricted search then returned the memory:

```text
matchType: hybrid
similarity: 0.8397
```

The public-space test therefore also succeeded.

---

# Asynchronous Processing Model

The observed processing sequence is approximately:

```text
POST /v1/add
      |
      | HTTP 200
      v
Memory accepted
      |
      | background processing / embedding
      v
GET /v1/memories?spaceId=...
      |
      +-- items=0
      |
      |   ...processing...
      |
      v
Memory becomes visible
      |
      v
Memory can be retrieved through /search
```

Therefore, an immediate empty response from:

```text
GET /v1/memories?spaceId=...
```

must not be interpreted as proof that the memory was not added.

This is especially important for automated integration tests.

---

# SHL Integration Implications

The current MyMemory.dev API is suitable for SHL's translation-memory use case.

SHL can store translation memories in a dedicated space and use `/v1/search` as the retrieval mechanism.

A memory can contain information such as:

```text
Source language: en
Target language: fi
Source: Hello
Translation: Hei
```

A language-pair tag can also be used:

```text
en-fi
```

A possible organization is:

```text
SHL Translation Memory
    |
    +-- en-fi
    +-- en-sv
    +-- en-de
    +-- ...
```

The important architectural point is that MyMemory.dev should be treated as a candidate-retrieval layer.

For SHL, `/v1/search` can find semantically or hybrid-matched memories, but SHL should still validate the returned memory before using it as an exact translation-memory hit.

For example, SHL can verify:

```text
source language
target language
source text
translation
```

before returning the stored translation.

This keeps the final translation-memory decision inside SHL rather than delegating it entirely to the remote search service.

---

# Current SHL Translation-Memory Flow

The intended SHL lookup flow is:

```text
TranslationCache
      |
      | cache miss
      v
Translation Memory
      |
      | no valid memory hit
      v
Translation Providers
```

When MyMemory.dev is used as the translation-memory backend, its semantic/hybrid `/v1/search` endpoint provides the candidate memories.

SHL then validates the candidate before accepting it.

This allows MyMemory.dev to provide semantic retrieval while SHL retains control over the final translation-memory decision.

---

# Confirmed Capabilities

The current regression tests have confirmed the following:

1. Authentication works with the current API key.

2. Private spaces can be created.

3. Public spaces can be created.

4. Spaces can be listed through `/v1/spaces`.

5. Public and private spaces are returned in the same `spaces` list.

6. `isPublic` identifies whether a space is public.

7. Individual spaces can be retrieved through `/v1/spaces/{uuid}`.

8. Space permissions are returned in the `permissions` object.

9. Memories can be added through `/v1/add`.

10. A memory can be associated with a space using the `spaces` list.

11. Tags can be attached to memories.

12. Tags can be listed through `/v1/tags`.

13. Memories can be filtered by tags.

14. Memories can be listed through `/v1/memories`.

15. Memories can be filtered by `spaceId`.

16. Individual memories can be retrieved through `/v1/memories/{uuid}`.

17. Semantic and hybrid search work through `/v1/search`.

18. Short queries such as `SHL` work in the current API version.

19. Space-restricted search works.

20. Both private and public spaces worked in the space-restricted search tests.

21. `/v1/chat` works.

22. Memory processing is asynchronous.

23. A memory can become searchable before its processing status reaches `ready`.

---

# Not Yet Tested

The current tests were performed using a single MyMemory.dev user/API key.

Therefore, the following cross-user behavior has not yet been verified:

* Whether another user can see a public space in `/v1/spaces`.
* Whether another user can read memories from a public space.
* Whether another user can modify a public space.
* Whether another user can add memories to a public space.
* Whether another user can perform space-restricted searches against a public space.
* Whether another user is completely prevented from accessing a private space.
* How public-space permissions are represented for a non-owner.

A second MyMemory.dev user or a second working API key is required to test these cases properly.

Until that test is performed, SHL should not assume a specific cross-user permission model merely from the `isPublic` field.

---

# Historical Findings from 2026-09-12

The following observations are retained for historical reference only.

They describe the API state observed during the earlier September tests and should not be treated as the current API behavior where newer regression tests contradict them.

At that time, the documentation was sparse, and several endpoint behaviors had to be discovered experimentally.

## Endpoints observed as unavailable

The following endpoints returned 404 or otherwise did not provide a usable API:

```text
POST /v1/spaces
GET  /v1/memories/private
GET  /v1/spaces/{uuid}/memories
GET  /v1/spaces/{uuid}/content
GET  /v1/spaces/{uuid}/items
GET  /v1/memories/{uuid}/content
GET  /v1/get
POST /v1/memories/search
```

The endpoint:

```text
GET /v1/memories/search?q=...
```

could return a successful HTTP response with an empty body, but it was not a usable search interface.

These historical results do not affect the current `/v1/search` implementation, which has since been verified independently.

---

# Historical Search Behavior

During the 2026-09-12 testing, the following behavior was observed:

* `/v1/search` accepted a `query` field.
* The search appeared to use vector/semantic retrieval.
* Short queries such as `test` or `SHL` did not produce useful results.
* Space restrictions did not appear to restrict results at that time.

These observations have been superseded by the 2026-10-04 regression tests.

The current API has demonstrated:

```text
matchType: hybrid
embeddingModel: v2
```

and successful space-restricted searches.

---

# Historical Error Interpretation

The earlier tests also established some useful general API behavior:

```text
404
```

usually indicated that an endpoint did not exist.

```text
400 ZodError
```

generally indicated that the endpoint existed but a required field was missing or had the wrong type.

For example:

```json
{
  "issues": [
    {
      "path": ["query"],
      "message": "Required"
    }
  ]
}
```

A response such as:

```text
HTTP 200 + empty body
```

could indicate a stub or non-functional endpoint.

A response such as:

```json
{
  "results": []
}
```

indicates that the search itself executed successfully but did not find any matching results.

A response of:

```text
401
```

indicates that the API key is invalid or is not associated with an authorized user account.

---

# Current Status

The current MyMemory.dev regression test succeeds with a new API key.

The following major capabilities have been verified:

```text
Authentication
Space creation
Private spaces
Public spaces
Space listing
Individual space retrieval
Memory creation
Memory listing
Individual memory retrieval
Tags
Semantic search
Hybrid search
Space-restricted search
Short search queries
Chat
Asynchronous memory processing
```

The only significant open area in the current SHL investigation is cross-user access control for public and private spaces.

That requires a second MyMemory.dev user or API key.

The earlier issue where a newly added memory did not immediately appear in:

```text
GET /v1/memories?spaceId=...
```

has now been reproduced and explained by the observed asynchronous processing behavior. The memory eventually appeared after polling, and it could already be found through `/v1/search` while processing was still underway.

Therefore, SHL should not interpret an immediate empty space-specific memory list as an insertion failure.

For the current SHL integration, the most important verified capability is the combination of:

```text
POST /v1/add
    spaces: [space_uuid]

        +

POST /v1/search
    query: ...
    spaceId: <space_uuid>
```

This provides SHL with a working space-aware semantic/hybrid retrieval mechanism for translation memory.

