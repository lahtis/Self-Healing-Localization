# MyMemory.dev – havainnot (2026-09-12)

## Toimivat päätepisteet
- POST /v1/spaces/create  → luo spacen
  payload: {"spaceName": "...", "isPublic": bool}

## Ei toimi (404)
- POST /v1/spaces         → 404
- GET  /v1/memories/private → 404

## Dokumentaatio
Käytännössä olematon. Päätepisteet ja kenttänimet on selvitetty
yrityksen ja erehdyksen kautta.

# MyMemory.dev – todistetusti toimivat kutsut 

## Space-luonti
POST /v1/spaces/create
{"spaceName": "...", "isPublic": false}
→ 200 OK, palauttaa {"space": {"uuid": "...", ...}}

## Muiston lisäys
POST /v1/add
{"content": "...", "type": "note", "spaces": ["<space_uuid>"]}
→ 200 OK, palauttaa {"id": "add-...", ...}

## HUOM
Quickstart-oppaan esimerkki `/v1/memories` + `spaceId` EI toimi (404).
Oikea päätepiste on `/v1/add` ja kenttä on `spaces` (lista).

# MyMemory.dev – todistetusti toimivat kutsut 

## Space-luonti
POST /v1/spaces/create
{"spaceName": "...", "isPublic": false}
→ 200 OK

## Muiston lisäys
POST /v1/add
{"content": "...", "type": "note", "spaces": ["<space_uuid>"]}
→ 200 OK, palauttaa {"id": "add-...", ...}

## Yksittäisen muiston haku
GET /v1/memories/{uuid}
→ 200 OK, palauttaa täydet tiedot (mukaan lukien searchVector)

## Muistojen listaus
GET /v1/memories
→ 200 OK, palauttaa {"items": [...], "total": N}
HUOM: ei näytä äsken lisättyä note-tyypin muistoa.

## EI toimi (404 tai tyhjä)
- GET /v1/memories/search?q=...&spaceId=...  → 200 tyhjä runko
- GET /v1/spaces/{uuid}/memories              → 404
- GET /v1/get                                  → 404

# MyMemory.dev – API-resepti (2026-09-12)

Dokumentaatio on käytännössä olematon. Tämä tiedosto sisältää
todistetusti toimivat kutsut, jotka on selvitetty yrityksen ja
erehdyksen kautta.

## Perusta
- Base URL: https://api.mymemory.dev/v1
- Todennus: Authorization: Bearer <API_KEY>
- Content-Type: application/json (POST-pyynnöissä)
- API-avain: MYMEMORY_API_KEY ympäristömuuttujassa

## Space-luonti
POST /v1/spaces/create
{"spaceName": "...", "isPublic": false}
→ 200, {"space": {"uuid": "...", "name": "...", ...}}
HUOM: /create-pääte pakollinen. Kentät spaceName + isPublic (ei name).

## Spacen haku
GET /v1/spaces                    → 200, {"spaces": [...]}
GET /v1/spaces/{uuid}             → 200, {"uuid": "...", "name": "...", ...}
GET /v1/spaces/{uuid}/memories    → 404 (ei ole olemassa)

## Muiston lisäys
POST /v1/add
{"content": "...", "type": "note", "spaces": ["<space_uuid>"]}
→ 200, {"id": "add-...", "type": "note", "isFirstUserMemory": bool}
HUOM: kenttä on "spaces" (lista), ei "spaceId". Päätepiste on /add,
      ei /memories.

## Muiston haku ID:llä
GET /v1/memories/{uuid}
→ 200, täydet tiedot: id, uuid, url, content, raw, type, title,
       createdAt, updatedAt, userId, searchVector, processingLog, ...
HUOM: searchVector sisältää sisäisen hakemiston (A/B-painot).

## Semanttinen haku
POST /v1/search
{"query": "hakusana"}
→ 200, {
    "retrievalEventId": "...",
    "results": [
      {"uuid": "...", "content": "...", "type": "...", "title": "...",
       "similarity": 0.68, "matchingChunk": {...}}
    ],
    "widenSuggestion": null
  }
HUOM 1: kenttä on "query", ei "q", "text" tai "query".
HUOM 2: haku on semanttinen (vektori), ei avainsanapohjainen.
        Lyhyet sanat kuten "test" tai "SHL" eivät löydä mitään,
        vaikka ne olisivat sisällössä.
HUOM 3: spaceId/spaces hyväksytään, mutta ne EIVÄT rajaa tuloksia.
        Haku kohdistuu kaikkiin muistoihin.
HUOM 4: tyhjä tulos → {"results": [], "widenSuggestion": null}
        (ei 404, ei virhettä).

## Muistojen listaus
GET /v1/memories
→ 200, {"items": [...], "total": N}
HUOM: palauttaa vain demo-seedit (type=page), ei omia note-muistoja.
      Parametrit type, limit, jne. näytetään ohittavan.

## Toimimattomat päätepisteet (404 tai tyhjä)
- GET  /v1/memories/search?q=...    → 200 tyhjä runko (tynkä)
- POST /v1/memories/search          → 404
- GET  /v1/get                      → 404
- GET  /v1/spaces/{uuid}/memories   → 404
- GET  /v1/spaces/{uuid}/content    → 404
- GET  /v1/spaces/{uuid}/items      → 404
- GET  /v1/memories/{uuid}/content  → 404

## Virheiden tulkinta
- 404 → päätepistettä ei ole
- 400 ZodError → päätepiste on, mutta kenttä puuttuu tai on väärää tyyppiä
  Esim: {"issues":[{"path":["query"],"message":"Required"}]}
- 200 + tyhjä runko → päätepiste on tynkä, ei toimi
- 200 + results:[] → haku toimi, mutta ei osumia
