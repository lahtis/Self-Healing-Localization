# MyMemory.dev – havainnot (2026-10-04)

## Yleistä

MyMemory.dev:n API on kehittynyt merkittävästi alkuperäisten testien jälkeen. API:n nykyinen dokumentaatio löytyy MyMemory.dev:n API Reference- ja OpenAPI-dokumenteista.

SHL:n regression-testi on ajettu onnistuneesti uudella API-avaimella. Kaikki testissä käytetyt keskeiset päätepisteet palauttivat HTTP 200 -vastauksen.

## Todistetusti toimivat päätepisteet

### Space-luonti

POST /v1/spaces/create

```json
{
  "spaceName": "SHL Regression Test",
  "isPublic": false
}
```

→ 200 OK

Palauttaa muun muassa:

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

HUOM: oikea päätepiste on `/spaces/create`, ei `/spaces`.

### Muiston lisäys

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

Palauttaa muun muassa:

```json
{
  "message": "Content added successfully",
  "id": "add-...",
  "type": "note",
  "isFirstUserMemory": false
}
```

HUOM: spacen kenttä on `spaces` ja sen arvo on lista.

## Tagit

### Tagien listaus

GET /v1/tags

→ 200 OK

Esimerkiksi:

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

### Muistojen haku tagilla

GET /v1/memories?tags=shl-regression

→ 200 OK

Palauttaa tagiin liittyvät muistit.

## Muistojen listaus

GET /v1/memories

→ 200 OK

Palauttaa:

```json
{
  "items": [...],
  "total": N
}
```

Myös omat API:n kautta lisätyt `note`-tyyppiset muistit näkyvät listauksessa.

### Rajoitettu listaus

GET /v1/memories?limit=5

→ 200 OK

Palauttaa käyttäjän muisteja annetun rajan puitteissa.

### Space-suodatus

GET /v1/memories?spaceId=<space_uuid>

→ 200 OK

Regression-testissä juuri luotu space ei kuitenkaan vielä palauttanut lisättyä muistia tällä tavalla:

```json
{
  "items": [],
  "total": 0
}
```

Samaan aikaan `/search` löysi saman muistin space-rajoituksella.

Tämä on lähetetty MyMemory.dev:n kehittäjälle tarkistettavaksi. Mahdollinen syy voi olla muistin taustalla tapahtuva prosessointi.

## Yksittäisen muiston haku

GET /v1/memories/{uuid}

→ 200 OK

Palauttaa yksittäisen muiston täydet tiedot.

Aiemmissa testeissä vastauksessa on ollut muun muassa:

* id
* uuid
* url
* content
* raw
* type
* title
* createdAt
* updatedAt
* userId
* searchVector
* processingLog

## Semanttinen ja hybridihaku

POST /v1/search

```json
{
  "query": "hakusana"
}
```

→ 200 OK

Palauttaa muun muassa:

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

Haku tukee nykyisin sekä semanttista että hybridihakua.

Lyhyet haut, kuten `SHL`, toimivat nykyisessä API-versiossa.

### Space-rajoitettu haku

POST /v1/search

Haku voi käyttää space-rajoitusta esimerkiksi `spaces`- tai `spaceId`-kentällä.

Regression-testissä space-rajoitettu haku löysi juuri kyseiseen spaceen lisätyn muistin:

```text
matchType: hybrid
similarity: 0.7774
```

Tämä vahvistaa, että space-rajoitus toimii `/search`-endpointissa.

### Lyhyt hakusana

POST /v1/search

```json
{
  "query": "SHL"
}
```

→ 200 OK

Haku palautti useita SHL:ään liittyviä muisteja.

### Tuntemattomat kentät

API käsittelee nykyisin myös tuntemattomia hakukenttiä siten, että ne voidaan ilmoittaa `ignoredFields`-tiedossa sen sijaan, että ne vain katoaisivat hiljaisesti.

## Chat

POST /v1/chat

→ 200 OK

Regression-testissä chat-endpoint vastasi onnistuneesti.

Chat palautti MyMemory.dev:n omia muistihakuun perustuvia tuloksia.

## Muistin taustaprosessointi

`POST /add` palauttaa muistin ennen kuin sen prosessointi välttämättä on valmis.

Esimerkiksi uusi memory saattoi aluksi sisältää:

```json
{
  "isSuccessfullyProcessed": false,
  "processingStage": "extracting",
  "content": null
}
```

Samaan aikaan `/search` pystyi jo löytämään saman muistin myöhemmin prosessoinnin edettyä.

SHL:n integraatiossa on siis hyvä huomioida, että muistin lisääminen ja sen lopullinen prosessointi eivät välttämättä tapahdu synkronisesti.

# MyMemory.dev – API-resepti

## Perusta

* Base URL: `https://api.mymemory.dev/v1`
* Todennus: `Authorization: Bearer <API_KEY>`
* POST-pyynnöissä: `Content-Type: application/json`
* API-avain: `MYMEMORY_API_KEY`
* SHL käyttää API-kutsuissa Pythonin standardikirjaston `urllib`-toteutusta.

## Space-luonti

POST /v1/spaces/create

```json
{
  "spaceName": "...",
  "isPublic": false
}
```

→ 200

HUOM: `/create`-pääte on pakollinen. Kenttä on `spaceName`, ei `name`.

## Spacen haku

GET /v1/spaces

→ 200

GET /v1/spaces/{uuid}

→ 200

GET /v1/spaces/{uuid}/memories

→ 404

## Muiston lisäys

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

HUOM: oikea kenttä on `spaces` (lista), ei `spaceId`.

## Muistojen listaus

GET /v1/memories

→ 200

GET /v1/memories?limit=5

→ 200

GET /v1/memories?tags=<tag>

→ 200

GET /v1/memories?spaceId=<space_uuid>

→ 200

HUOM: `spaceId`-listauksen käyttäytyminen juuri lisätyille, vielä prosessoitaville muisteille on lähetetty MyMemory.dev:n kehittäjälle tarkistettavaksi.

## Yksittäisen muiston haku

GET /v1/memories/{uuid}

→ 200

## Tagit

GET /v1/tags

→ 200

## Semanttinen/hybridihaku

POST /v1/search

```json
{
  "query": "..."
}
```

→ 200

Tuettuja hakurajoituksia ovat muun muassa `spaceId` ja `spaces`.

Haku palauttaa muun muassa:

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

# Aiemmin toimimattomiksi todetut päätepisteet

Seuraavat ovat edelleen dokumentoituna vanhoina havaintoina, mutta niiden nykyistä tilaa ei ole tässä regression-testissä uudelleen varmennettu:

* GET /v1/memories/search
* POST /v1/memories/search
* GET /v1/get
* GET /v1/spaces/{uuid}/memories
* GET /v1/spaces/{uuid}/content
* GET /v1/spaces/{uuid}/items
* GET /v1/memories/{uuid}/content

## Virheiden tulkinta

Aiemmissa testeissä havaittu yleinen tulkinta:

* 404 → päätepistettä ei ole
* 400 ZodError → päätepiste on olemassa, mutta kenttä puuttuu tai on väärää tyyppiä
* 200 + tyhjä runko → päätepiste voi olla tynkä
* 200 + `results: []` → haku suoritettiin, mutta osumia ei löytynyt
* 401 → API-avain ei ole kelvollinen tai sitä ei ole yhdistetty käyttäjätiliin

## Nykyinen tila

SHL:n MyMemory.dev-regression testi toimii uudella API-avaimella.

Todistetusti toimivat kokonaisuudet:

* autentikointi
* spacen luonti
* muistin lisäys
* tagit
* muistojen listaus
* yksittäisten muistojen käsittely
* semanttinen/hybridihaku
* space-rajoitettu haku
* lyhyet hakusanat
* chat

Ainoa tällä hetkellä avoimeksi jäänyt havainto on `GET /memories?spaceId=...` -listauksen käyttäytyminen juuri lisätyn muistin kanssa. Asia on raportoitu MyMemory.dev:n kehittäjälle.


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
