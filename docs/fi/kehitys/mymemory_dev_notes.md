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
* API-avain: `MYMEMORY_DEV_API_KEY`
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

# MyMemory.dev – Spaces- ja Memory-integraation testitulokset

## Tarkoitus

Tällä testillä selvitettiin, miten MyMemory.dev:n `spaces` ja `memories` toimivat yhdessä SHL:n näkökulmasta.

Testissä luotiin yksi yksityinen ja yksi julkinen space. Kumpaankin lisättiin yksi memory käyttäen `/v1/add`-päätepistettä. Tämän jälkeen odotettiin, että memory ilmestyy space-kohtaiseen muistilistaan, ja testattiin vielä haku `/v1/search`-päätepisteellä käyttäen space-rajausta.

Testi suoritetaan SHL-projektin juuresta:

```text
python3 -m tests.test_mymemory_dev_spaces_memory
```

## `/v1/add` – oikea sisältömuoto

Testin aikana varmistui, että `/v1/add`-päätepisteen `content`-kentän täytyy olla merkkijono.

Toimiva rakenne on:

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

Aiemmin kokeiltu rakenne, jossa `content` oli objekti:

```json
{
  "content": {
    "source": "...",
    "target": "..."
  }
}
```

ei toimi. API palauttaa HTTP 400 -virheen:

```text
Expected string, received object
```

SHL:n spaces-testissä source- ja target-tekstit yhdistettiin tämän vuoksi yhdeksi `content`-merkkijonoksi.

## Yksityinen space

Testi loi yksityisen spacen:

```text
Name: SHL Private Memory Integration Test
UUID: s5L2X9G3Dk
ownerId: 124
isPublic: false
```

Muistin lisääminen onnistui:

```text
POST /v1/add
HTTP 200
```

API palautti:

```json
{
  "message": "Content added successfully",
  "id": "add-124-8EdEjQ4ALh",
  "type": "note",
  "isFirstUserMemory": false
}
```

### Space-kohtainen muistilista

Välittömästi lisäämisen jälkeen:

```text
GET /v1/memories?spaceId=s5L2X9G3Dk
HTTP 200
items=0
total=0
```

Muisti ei siis tullut listalle välittömästi.

Testi suoritti kyselyn uudelleen kahden sekunnin välein. Lopulta memory tuli näkyviin:

```text
items=1
total=1
```

Muisti:

```text
ID: add-124-8EdEjQ4ALh
type: note
tags: shl-spaces-test, en-fi
```

Sisältö:

```text
SHL private space memory test 2026-10-04
->
SHL yksityisen spacen muistitesti 2026-10-04
```

Memoryn `processingStage` oli tässä vaiheessa vielä `embedding` ja `isSuccessfullyProcessed` oli `false`.

Tästä huolimatta memory oli jo löydettävissä haulla.

### Space-rajoitettu haku

Haku suoritettiin:

```text
POST /v1/search
```

payloadilla:

```json
{
  "query": "SHL private space memory test 2026-10-04",
  "spaceId": "s5L2X9G3Dk"
}
```

Tulos:

```text
HTTP 200
```

Haku palautti juuri kyseisen memoryn:

```text
matchType: hybrid
similarity: 0.7962
```

Yksityisen spacen testi siis onnistui kokonaisuudessaan.

## Julkinen space

Testi loi julkisen spacen:

```text
Name: SHL Public Memory Integration Test
UUID: TAn2v789wN
ownerId: 124
isPublic: true
```

Muistin lisääminen onnistui:

```text
POST /v1/add
HTTP 200
```

API palautti:

```json
{
  "message": "Content added successfully",
  "id": "add-124-tNAsZbSVhC",
  "type": "note",
  "isFirstUserMemory": false
}
```

### Space-kohtainen muistilista

Myös tässä tapauksessa memory ei tullut listalle välittömästi.

Ensimmäiset haut palauttivat:

```text
items=0
total=0
```

Polling jatkui kahden sekunnin välein, kunnes memory löytyi.

Lopputulos:

```text
items=1
total=1
```

Muisti:

```text
ID: add-124-tNAsZbSVhC
type: note
tags: shl-spaces-test, en-fi
processingStage: ready
isSuccessfullyProcessed: true
```

Sisältö:

```text
SHL public space memory test 2026-10-04
->
SHL julkisen spacen muistitesti 2026-10-04
```

### Space-rajoitettu haku

Haku suoritettiin:

```text
POST /v1/search
```

payloadilla:

```json
{
  "query": "SHL public space memory test 2026-10-04",
  "spaceId": "TAn2v789wN"
}
```

Tulos:

```text
HTTP 200
```

Memory löytyi:

```text
matchType: hybrid
similarity: 0.8397
```

Myös julkisen spacen testi onnistui kokonaisuudessaan.

## Havainto: memoryjen käsittely on asynkronista

Testi osoitti selvästi, että `/v1/add` palauttaa onnistumisen ennen kuin memory näkyy `GET /v1/memories?spaceId=...` -listassa.

Prosessi näyttää käytännössä tältä:

```text
POST /v1/add
      │
      ├── HTTP 200
      │
      ▼
Memory lisätty
      │
      │  käsittely / embedding
      ▼
GET /v1/memories?spaceId=...
      │
      ├── items=0
      │
      │  ...odotetaan...
      │
      ▼
Memory tulee näkyviin
      │
      ▼
Memory voidaan hakea /search-päätepisteellä
```

Tästä syystä välittömästi `/add`-kutsun jälkeen tehty `GET /memories?spaceId=...` ei sovellu yksinään todistamaan, että memoryn lisääminen epäonnistui.

SHL:n testissä tämä ratkaistiin pollingilla.

## Vahvistetut ominaisuudet

Testien perusteella seuraavat asiat on nyt vahvistettu:

1. Space voidaan luoda `/v1/spaces/create`-päätepisteellä.

2. Sekä private- että public-space voidaan luoda API:n kautta.

3. `/v1/add` hyväksyy `spaces`-kentän space UUID:n sisältävänä listana.

4. Memory voidaan sitoa tiettyyn spaceen lisäämisen yhteydessä.

5. `GET /v1/memories?spaceId=<uuid>` palauttaa kyseiseen spaceen kuuluvat memoryt.

6. Memory voi ilmestyä space-kohtaiseen listaan vasta viiveellä.

7. `/v1/search` hyväksyy `spaceId`-rajauksen.

8. Space-rajoitettu haku löytää kyseiseen spaceen lisätyn memoryn.

9. Sekä private- että public-space toimivat näissä operaatioissa.

10. `/v1/search` voi löytää memoryn jo ennen kuin memoryn processing-status on `ready`.

## SHL:n kannalta merkityksellinen rakenne

MyMemory.dev soveltuu tämän testin perusteella hyvin SHL:n translation memory -käyttöön.

SHL voi esimerkiksi tallentaa käännöksen spaceen seuraavan kaltaisena sisältönä:

```text
source text -> translated text
```

ja käyttää language pair -tagia:

```text
en-fi
```

Space voidaan puolestaan valita SHL:n käyttötarkoituksen mukaan.

Esimerkiksi:

```text
SHL Translation Memory
    │
    ├── en-fi
    ├── en-sv
    ├── en-de
    └── ...
```

Space-rajoitettu haku mahdollistaa sen, että SHL ei joudu tekemään jokaista hakua koko memory-kannasta.

## Vielä testaamatta

Tässä testissä ei vielä selvitetty käyttäjien välistä näkyvyyttä.

Erityisesti seuraavat asiat ovat vielä avoinna:

* Näkeekö toinen käyttäjä public-spacen?
* Näkeekö toinen käyttäjä public-spacen memoryt?
* Näkeekö toinen käyttäjä private-spacen?
* Toimiiko `spaceId`-rajoitettu haku toisella käyttäjällä public-spacessa?
* Miten public-spacen oikeudet tarkalleen määräytyvät?

Näiden testaamiseen tarvitaan toinen MyMemory.dev-käyttäjä tai toinen toimiva API-avain.

## Yhteenveto

MyMemory.dev:n spaces- ja memory-toiminnot toimivat SHL:n tarvitsemalla tavalla.

Erityisesti vahvistui, että memory voidaan lisätä suoraan tiettyyn spaceen:

```text
POST /v1/add
    spaces: [space_uuid]
```

ja myöhemmin hakea sekä listauksella:

```text
GET /v1/memories?spaceId=<space_uuid>
```

että semanttisella haulla:

```text
POST /v1/search
    query: ...
    spaceId: <space_uuid>
```

Tärkein käytännön huomio on asynkroninen käsittely. `/add` voi palauttaa HTTP 200:n, vaikka memory ei vielä hetkeen näy space-kohtaisessa listassa tai ole valmis embedding-käsittelystä.

Tämän vuoksi SHL:n mahdollisen MyMemory.dev-integraation ei pidä tulkita välitöntä tyhjää memory-listaa lisäyksen epäonnistumiseksi.


# MyMemory.dev – Spaces API:n testaus ja havainnot

## Tarkoitus

Tässä testissä tutkitaan MyMemory.dev API:n `Spaces`-toimintoa ja sen suhdetta muistiin (`memories`).

Testin tavoitteena on selvittää:

* miten käyttäjän omat spacit listataan
* miten julkiset ja yksityiset spacit erotellaan
* mitä tietoja yksittäisestä spacesta palautetaan
* voiko uuden spacen luoda yksityisenä tai julkisena
* miten spacen muistot listataan
* näkyvätkö julkiset ja yksityiset spacit samalla tavalla omistajalle.

Testi käyttää MyMemory.dev:n API:a suoraan Pythonin standardikirjaston `urllib`-moduulilla. Erillisiä HTTP-riippuvuuksia, kuten `requests`-kirjastoa, ei käytetä.

API-avain luetaan SHL:n ympäristölataajan kautta:

```python
from shl.utils.env_loader import get_env_value

API_KEY = get_env_value("MYMEMORY_DEV_API_KEY")
```

Testi suoritetaan SHL-projektin juuresta moduulina:

```bash
python3 -m tests.test_mymemory_dev_spaces
```

## Spaces-listaus

Endpoint:

```text
GET /v1/spaces
```

Palautus sisältää yhden `spaces`-listan. Julkisia ja yksityisiä spaceja ei siis palauteta erillisinä listoina.

Esimerkiksi:

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

Julkinen tai yksityinen tila tunnistetaan kentästä:

```text
isPublic
```

Arvo:

```text
true
```

tarkoittaa julkista spacea.

Arvo:

```text
false
```

tarkoittaa yksityistä spacea.

Näin ollen SHL:n mahdollinen oma käyttöliittymä voi saada kaikki spacit yhdellä API-kutsulla ja jakaa ne tarvittaessa käyttöliittymässä julkisiin ja yksityisiin.

## Testin alkuperäinen Spaces-listaus

Testin alussa käyttäjällä oli kuusi spacea.

Kaikki kuusi olivat yksityisiä:

```text
Total:   6
Public:  0
Private: 6
```

Listassa olivat muun muassa:

```text
SHL Regression Test
SHL Test Space
SHL Private Memory
```

Kaikissa käyttäjän omistamissa spaceissa oli seuraavat oikeudet:

```json
{
  "canRead": true,
  "canEdit": true,
  "isOwner": true
}
```

Lisäksi listauksessa esiintyivät kentät:

```text
accessType
favorited
owner
permissions
```

Testissä omistajan omien spacejen kohdalla:

```text
accessType = null
favorited = false
owner = null
```

`permissions`-objekti sisälsi kuitenkin varsinaiset käyttöoikeustiedot.

## Yksityisen spacen luominen

Endpoint:

```text
POST /v1/spaces/create
```

Pyyntö:

```json
{
  "spaceName": "SHL Private Space Investigation",
  "isPublic": false
}
```

API palautti HTTP 200 -vastauksen ja loi spacen onnistuneesti.

Luodun spacen UUID oli:

```text
W6WEqizeba
```

Palautuksessa olivat muun muassa:

```json
{
  "uuid": "W6WEqizeba",
  "name": "SHL Private Space Investigation",
  "ownerId": 124,
  "isPublic": false
}
```

## Julkisen spacen luominen

Myös julkinen space voitiin luoda samalla endpointilla.

Pyyntö:

```json
{
  "spaceName": "SHL Public Space Investigation",
  "isPublic": true
}
```

API palautti HTTP 200 -vastauksen.

Luodun spacen UUID oli:

```text
PT8od4asev
```

Palautuksessa:

```json
{
  "uuid": "PT8od4asev",
  "name": "SHL Public Space Investigation",
  "ownerId": 124,
  "isPublic": true
}
```

## Uusi Spaces-listaus

Kun uudet spacit oli luotu, `/v1/spaces` palautti yhteensä kahdeksan spacea.

Jakauma oli:

```text
Total:   8
Public:  1
Private: 7
```

Julkinen space löytyi samasta `spaces`-listasta kuin yksityisetkin.

Tässä tapauksessa:

```text
SHL Public Space Investigation
isPublic = true
```

ja:

```text
SHL Private Space Investigation
isPublic = false
```

Tämä vahvistaa, että API ei käytä omistajan näkökulmasta erillisiä public/private-listausendpointeja, vaan palauttaa spacit yhtenä kokonaisuutena.

## Yksittäisen spacen hakeminen

Yksittäinen space voidaan hakea UUID:n perusteella:

```text
GET /v1/spaces/{uuid}
```

Esimerkiksi:

```text
GET /v1/spaces/W6WEqizeba
```

palautti HTTP 200 ja seuraavan kaltaisen rakenteen:

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

Julkinen space palautti vastaavasti:

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

Huomionarvoista on, että yksittäisen spacen vastauksessa `permissions` sisältää myös `isPublic`-kentän.

## Spacen muistojen listaaminen

Spacen muistit voidaan hakea endpointilla:

```text
GET /v1/memories?spaceId={uuid}
```

Esimerkiksi:

```text
GET /v1/memories?spaceId=W6WEqizeba
```

ja:

```text
GET /v1/memories?spaceId=PT8od4asev
```

palauttivat molemmat HTTP 200.

Koska juuri luotuihin spaceihin ei ollut vielä lisätty muistoja, vastaukset olivat:

```json
{
  "items": [],
  "total": 0
}
```

Tämä osoittaa, että `spaceId`-suodatus toimii HTTP-tasolla ja palauttaa tyhjän tuloksen, kun kyseisessä spacessa ei ole muistoja.

Testi ei tämän osan perusteella osoita, että `spaceId` olisi rikki.

Aikaisemmassa regressiotestissä havaittu tyhjä tulos heti muiston lisäämisen jälkeen on siten syytä käsitellä erillisenä kysymyksenä, koska uuden muiston käsittely voi olla vielä kesken.

## Varmistetut havainnot

Testin perusteella voidaan tällä hetkellä pitää varmistettuina seuraavia asioita:

1. `GET /v1/spaces` toimii.
2. API palauttaa julkiset ja yksityiset spacit samassa `spaces`-listassa.
3. `isPublic` kertoo, onko space julkinen.
4. `POST /v1/spaces/create` on oikea endpoint uuden spacen luomiseen.
5. `isPublic: false` luo yksityisen spacen.
6. `isPublic: true` luo julkisen spacen.
7. Luodut spacit näkyvät myöhemmin `/v1/spaces`-listauksessa.
8. Yksittäisen spacen voi hakea UUID:lla osoitteesta `/v1/spaces/{uuid}`.
9. Yksittäisen spacen vastauksessa palautetaan käyttöoikeuksia kuvaava `permissions`-objekti.
10. Spacen muistit voidaan hakea osoitteesta `/v1/memories?spaceId={uuid}`.
11. Tyhjä space palauttaa HTTP 200 ja `total: 0`.
12. Omistajalla on omiin spaceihinsa `canRead`, `canEdit` ja `isOwner` -oikeudet.

## Mitä testi ei vielä selvitä

Testiä suoritettiin yhden käyttäjän API-avaimella. Siksi se ei vielä osoita, miten julkiset ja yksityiset spacit näkyvät toiselle käyttäjälle.

Erityisesti seuraavat asiat ovat edelleen testaamatta:

* näkeekö toinen käyttäjä julkisen spacen `/v1/spaces`-listassa
* näkeekö toinen käyttäjä yksityisen spacen
* voiko toinen käyttäjä lukea julkisen spacen muistoja
* voiko toinen käyttäjä muokata julkista spacea
* voiko toinen käyttäjä lisätä muistoja julkiseen spaceen
* estetäänkö yksityisen spacen käyttö toiselta käyttäjältä API-tasolla.

Näiden testaamiseen tarvittaisiin käytännössä toinen MyMemory.dev-käyttäjä tai toinen API-avain.

## Merkitys SHL:n kannalta

MyMemory.dev:n Spaces-rakenne sopii hyvin SHL:n mahdolliseen translation memory -malliin.

SHL voisi esimerkiksi käyttää omaa yksityistä spacea translation memorylle ja tallentaa sinne käännöksiä kieliparikohtaisesti esimerkiksi tageilla:

```text
en-fi
fi-en
en-swe
```

Spaces mahdollistaisi myöhemmin myös eri käyttötarkoitusten erottamisen. Esimerkiksi:

```text
SHL Translation Memory
SHL Project Memory
SHL Shared Memory
```

Yksityinen space voisi sisältää käyttäjän oman translation memoryn, kun taas julkista spacea voitaisiin mahdollisesti käyttää jaettuun muistiin.

Tätä käyttötapaa ei kuitenkaan pidä vielä toteuttaa SHL:ään pelkästään tämän testin perusteella. Julkisten spacejen todelliset käyttöoikeudet eri käyttäjien välillä täytyy ensin varmistaa.

## Testin jäljelle jäävät kysymykset

Seuraava hyödyllinen testi olisi lisätä vähintään yksi memory sekä julkiseen että yksityiseen spaceen ja tarkistaa:

```text
POST /v1/add
GET /v1/memories?spaceId=...
POST /v1/search
```

Näin voidaan selvittää, miten spacen sisältö käyttäytyy käytännössä ja kuinka nopeasti lisätty memory ilmestyy `spaceId`-listaukseen.

Sen jälkeen olisi hyödyllistä tehdä sama testi toisella käyttäjätilillä. Vasta silloin voidaan tehdä varma johtopäätös siitä, mitä `isPublic` tarkoittaa käyttäjien välisessä näkyvyydessä ja muokkausoikeuksissa.

## Yhteenveto

MyMemory.dev:n Spaces API käyttää yhtä yhteistä spaces-listaa. Julkinen ja yksityinen tila erotetaan `isPublic`-kentällä.

Uusi space luodaan endpointilla:

```text
POST /v1/spaces/create
```

ja yksityisyys määritetään:

```json
{
  "isPublic": false
}
```

tai:

```json
{
  "isPublic": true
}
```

Yksittäinen space voidaan hakea UUID:n perusteella:

```text
GET /v1/spaces/{uuid}
```

ja spacen muistot:

```text
GET /v1/memories?spaceId={uuid}
```

Tähän mennessä testit vahvistavat Spaces API:n perusrakenteen ja toiminnan. Julkisen ja yksityisen spacen välinen käyttäjäkohtainen näkyvyys ja käyttöoikeus on kuitenkin vielä erikseen varmistettava.


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
- API-avain: MYMEMORY_DEV_API_KEY ympäristömuuttujassa

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
