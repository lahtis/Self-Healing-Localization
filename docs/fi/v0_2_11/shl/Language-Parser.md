# language_parser.py – tekninen dokumentaatio

**Moduuli:** `shl/language_parser.py`  
**Versio:** 0.2.11  
**Lisenssi:** MIT  
**Tekijä:** Tuomas Lähteenmäki

## Yleiskuvaus

`language_parser.py` on SHL:n (self-healing-localization) kielten tunnistus- ja normalisointimoduuli. Se ratkaisee käyttäjän antaman kielitunnisteen GLFM:n (Global Language Family Mapper) kautta ja muuntaa ratkaistun ISO 639-3 -kielen palveluntarjoajakohtaiseksi kielikoodiksi käyttäen palveluntarjoajien kielivälimuistia.

Moduuli ei sisällä palveluntarjoajakohtaisia kielialiaksia itse — kielen identiteetti ratkaistaan aina GLFM:n kautta, ja ISO 639-3 toimii SHL:n sisäisenä kanonisena kielitunnisteena.

### Resoluutioketju

```
Käyttäjän syöte
      ↓
   GLFM
      ↓
 ISO 639-3
      ↓
Palveluntarjoajan kielivälimuisti
      ↓
Palveluntarjoajakohtainen koodi
```

## Luokka: ParsedLanguage

Edustaa GLFM:n kautta ratkaistua kieltä. Kevyt data-luokka ilman omaa logiikkaa — `LanguageParser.parse()`-metodin palautusarvo.

### Attribuutit

| Attribuutti | Tyyppi | Kuvaus |
| :--- | :--- | :--- |
| `input` | `str` | Alkuperäinen käyttäjän antama syöte sellaisenaan |
| `iso639_3` | `str` | Ratkaistu ISO 639-3 -koodi (pienillä kirjaimilla) |
| `bcp47` | `Optional[str]` | GLFM:n antama BCP 47 -tagi kielelle |
| `input_bcp47` | `Optional[str]` | Syötteestä jäsennetty BCP 47 -muoto, jos syöte sisälsi kieli+skripti/alue-tiedon |
| `script` | `Optional[str]` | Syötteestä tunnistettu kirjoitusjärjestelmä (esim. `Hant`) |
| `region` | `Optional[str]` | Syötteestä tunnistettu alue (esim. `TW`), isoilla kirjaimilla |
| `name` | `Optional[str]` | GLFM:n antama kielen nimi |
| `glfm_info` | `Dict[str, Any]` | Koko GLFM-tietue sellaisenaan |

#### `__repr__`
Palauttaa luettavan debug-esityksen kentistä `input`, `iso639_3`, `bcp47`, `input_bcp47`, `script`, `region` ja `name`.

## Luokka: LanguageParser

Päävastuu: kielitunnisteiden ratkaisu GLFM:n avulla sekä ratkaistun kielen kuvaaminen palveluntarjoajan omaksi kielikoodiksi.

### Luokkavakiot

| Vakio | Arvo | Kuvaus |
| :--- | :--- | :--- |
| `DEFAULT_CACHE_FILENAME` | `".languages_cache.json"` | Oletustiedostonimi palveluntarjoajien kielivälimuistille |

### Rakentaja: `__init__(validator=None, cache_path=None)`

| Parametri | Tyyppi | Kuvaus |
| :--- | :--- | :--- |
| `validator` | `Optional[LanguageValidator]` | GLFM-validaattori. Jos `None`, luodaan uusi `LanguageValidator()`. |
| `cache_path` | `Optional[str \| Path]` | Polku palveluntarjoajien kielivälimuistiin. Jos `None`, käytetään pakettijuuren `.languages_cache.json`-tiedostoa. |

Sisäinen tila: `_provider_cache` alustetaan arvoon `None` (laiska lataus).

### `parse(language: str) -> ParsedLanguage`

Ratkaisee kielitunnisteen GLFM:n kautta.

**Hyväksytyt syötemuodot:**
- kielen nimi
- ISO 639-1
- ISO 639-3
- BCP 47
- GLFM-kielitunniste

**Toimintalogiikka:**
1. Validoi, että syöte on merkkijono (muuten `TypeError`).
2. Trimmaa syötteen ja tarkistaa, ettei se ole tyhjä (muuten `ValueError`).
3. Hakee kielitiedot `LanguageValidator.get_language_info()`-metodilla.
4. Jos tietoja ei löydy tai `iso639_3`-kenttä puuttuu, nostaa `ValueError`.
5. Jäsentää syötteen `parse_bcp47()`-apufunktiolla mahdollisen skripti-/aluetiedon poimimiseksi (esim. `zh-Hant-TW`).
6. Rakentaa ja palauttaa `ParsedLanguage`-olion.

**Poikkeukset:**
- `TypeError` — syöte ei ole merkkijono.
- `ValueError` — syöte on tyhjä, kieltä ei tunnisteta, tai GLFM-tietueesta puuttuu ISO 639-3 -koodi.

### `normalize(language: str) -> str`
Palauttaa kielen SHL:n kanonisen ISO 639-3 -tunnisteen. Oikotie: `self.parse(language).iso639_3`.

### `get_bcp47(language: str) -> Optional[str]`
Palauttaa GLFM:n BCP 47 -tagin kielelle. Oikotie: `self.parse(language).bcp47`.

### `load_provider_cache() -> Dict[str, Any]`

Lataa palveluntarjoajien kielivälimuistin JSON-tiedostosta ja välimuistittaa tuloksen instanssin sisällä (`_provider_cache`).

**Virheenkäsittely (ei koskaan nosta poikkeusta):**

| Tilanne | Toiminta |
| :--- | :--- |
| Tiedostoa ei löydy | varoitusloki + `{"providers": {}, "last_updated": None}` |
| JSON virheellinen / OSError | varoitusloki + sama tyhjä rakenne |
| Data ei ole dict | varoitusloki + sama tyhjä rakenne |

### `get_provider_code(language: str, provider: str) -> Optional[str]`

Ratkaisee kielen palveluntarjoajan omaksi kielikoodiksi.

**Kulku:**
1. Ratkaisee kielen `parse()`-metodilla.
2. Lataa palveluntarjoajien kielivälimuistin.
3. Etsii `provider`-parametria vastaavan avaimen `providers`-sanakirjasta kirjainkoosta riippumatta.
4. Jos palveluntarjoajaa ei löydy, palauttaa `None`.
5. Poimii tuetut koodit joko sanakirjan avaimista (dict) tai suoraan listasta (list).
6. Delegoi parhaan osuman etsinnän `_find_best_provider_match()`-metodille.

> Palveluntarjoajan kielivälimuisti on aina auktoritatiivinen — palautettu koodi on täsmälleen sellainen kuin se on tallennettu välimuistiin.

### `_find_best_provider_match(language, supported_codes) -> Optional[str]` (sisäinen)

Ydinalgoritmi, joka etsii parhaan mahdollisen palveluntarjoajakoodin ratkaistulle kielelle.

**Täsmäysjärjestys (ensimmäinen osuma voittaa):**

| # | Vaihe | Kuvaus |
| :--- | :--- | :--- |
| 1 | Tarkka input_bcp47-täsmäys | Jos syötteessä oli eksplisiittinen skripti/alue, etsitään tarkka (case-insensitive) täsmäys koko syötteen BCP 47 -muodolle |
| 2a | Skripti + alue | Koodi, jonka kaksi viimeistä `-`-erotettua osaa täsmäävät molempiin |
| 2b | Pelkkä alue | Koodi, jonka viimeinen osa täsmää alueeseen (esim. Papago) |
| 2c | Pelkkä skripti | Koodi, jonka viimeinen osa täsmää skriptiin |
| 3 | Tarkka bcp47-täsmäys | GLFM:n antama BCP 47 -tagi täsmätään suoraan koodilistaan |
| 4 | ISO 639-1 | Jos GLFM antoi ISO 639-1 -koodin, täsmätään se |
| 5 | ISO 639-3 | Täsmätään ratkaistu ISO 639-3 -koodi suoraan |
| 6 | BCP 47 -kantakieli | GLFM:n BCP 47:n ensimmäinen osa (esim. `zh` osasta `zh-Hant`) |
| 7 | Koodin kantakieliprefiksi | Koodi, jonka oma ensimmäinen osa täsmää BCP 47 -kantakieleen |

Jos mikään vaihe ei tuota osumaa, palautetaan `None` ja kirjataan debug-loki.

> **Huom:** Vaiheet 1–2 suoritetaan vain, jos syötteessä oli eksplisiittinen skripti tai alue (esim. `zh-Hant-TW`). Pelkkä kielinimi (esim. `"chinese"`) ohittaa nämä.

### `_find_case_insensitive(value, candidates) -> Optional[str]` (staattinen)

Etsii `value`-arvoa vastaavan alkion `candidates`-listasta kirjainkoosta riippumatta (`casefold()`-vertailu) ja palauttaa alkuperäisen, listassa olevan kirjoitusasun.

## Riippuvuudet

- `shl.language_validator.LanguageValidator` — GLFM-kielitietojen haku
- `shl.utils.lang_utils.parse_bcp47` — BCP 47 -syötteen jäsennys

## Lokitus

```python
logger = logging.getLogger(__name__)
```

| Taso | Milloin |
| :--- | :--- |
| `debug` | Onnistunut kielen ratkaisu, ei-täsmäävä palveluntarjoajakoodi |
| `warning` | Kielivälimuistin lataus epäonnistuu tai on rakenteeltaan virheellinen |
