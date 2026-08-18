# SHL-asetukset

SHL käyttää kevyttä riippuvuudetonta asetustasoa palvelun tarjoajan asetuksille ja ympäristömuuttujille.

Asetusten hallinta sijaitsee polussa:

```text
shl/
└── config/
    ├── __init__.py
    └── manager.py
```

Sovelluksen asetukset säilytetän yleensä projektin juuressa:

```text
my_project/
├── shl-config.json
├── .env
└── shl/
    └── ...
```

## Asetustiedosto

Oletusarvoisesti SHL etsii tiedostoa `shl-config.json` nykyisestä projektikansiosta.

Palvelun tarjoaja voidaan määrittää `enabled`, `allow` ja `deny` -asetuksilla.

Esimerkki:

```json
{
    "MyMemory": {
        "enabled": true,
        "allow": [],
        "deny": ["html"]
    },
    "DeepL": {
        "enabled": true,
        "allow": [],
        "deny": ["html"]
    },
    "Google": {
        "enabled": true,
        "allow": [],
        "deny": ["html"]
    }
}
```

Erillistä·· `fallback`-lippua ei ole.

## Palvelun tarjoajan `enabled`

`enabled` määrittää, onko palveluntarjoaja käytössä SHL:lle.

```json
"DeepL": {
    "enabled": true
}
```

Kun `enabled` on `false`, tarjoajaa ei sisällytetä käytössä olevien palvelun tarjoajien joukkoon käännöksiä tai varajärjestelmää varten.

Käytössä olevat palveluntarjoajat ovat saatavilla funktion kautta:

```python
config.get_enabled_providers()
```

## Automaattinen varajärjestelmä

SHL käsittelee muita käytössä olevia palvelun tarjoajia mahdollisina varajärjestelminä.

Palvelun tarjoaja ei voi koskaan olla oma varajärjestelmänsä.

Esimerkiksi, kun nykyinen palvelun tarjoaja on `DeepL`:

```python
config.get_fallback_providers("DeepL")
```

palauttaa muut käytössä olevat palveluntarjoajat.

Jos asetukset ovat:

```json
{
    "MyMemory": {
        "enabled": true
    },
    "DeepL": {
        "enabled": true
    },
    "Google": {
        "enabled": false
    }
}
```

varajärjestelmäsuhde on tehokkaasti:

```text
MyMemory → DeepL
DeepL    → MyMemory
```

Googlea ei sisällytetä, koska se on poissa käytöstä.

Jos vain yksi palvelun tarjoaja on käytössä:

```json
{
    "MyMemory": {
        "enabled": true
    },
    "DeepL": {
        "enabled": false
    },
    "Google": {
        "enabled": false
    }
}
```

niin MyMemoryllä ei ole vaihtoehtoista palvelun tarjoajaa.

Tällöin SHL ei yritä käyttää MyMemoryä omana varajärjestelmänään. Jos palvelun tarjoaja ei pysty tuottamaan käännöstä, suoritusaika voi näyttää `base_lang`-tekstin.

## `base_lang` ei ole tallennettu käännös

`base_lang`-varajärjestelmä on suoritusaikainen näyttövarajärjestelmä.

Jos mikään palveluntarjoaja ei pysty tuottamaan käännöstä, SHL voi näyttää lähdekielisen tekstin sovelluksen käytössä pitämiseksi.

Tätä arvoa ei saa kirjoittaa kohdekieliseen käännöstiedostoon.

Esimerkiksi:

```text
Pyydetty: fi → de

Käännöstiedosto:
    Saksankielinen käännös puuttuu

Tarjoaja:
    MyMemory epäonnistuu

Varajärjestelmät:
    ei yhtään

Suoritusaika:
    näytä base_lang (suomenkielinen teksti)
```

Suomenkielinen teksti näytetään, mutta sitä ei tallenneta saksan käännökseksi.

Tämä on tärkeää SHL:n itsekorjautuvalle toiminnalle. Kun käännös tarjoaja tulee taas saataville, SHL voi tuottaa todellisen käännöksen ja tallentaa sen sopivaan kohdekieliseen tiedostoon.

Virtaus on siis:

```text
käännös on olemassa
    ↓
käytä käännöstä

käännös puuttuu
    ↓
palveluntarjoaja onnistuu
    ↓
käytä käännöstä
    ↓
tallenna kohdekielinen käännös

käännös puuttuu
    ↓
kaikki sopivat palvelun tarjoajat epäonnistuvat
    ↓
näytä base_lang
base_lang → fi
text      → "Tervetuloa sovellukseen"
    ↓
 ÄLÄ tallenna base_lang:ia käännökseksi
```

## `allow` ja `deny`

`allow` ja `deny` ohjaavat, onko palvelun tarjoaja sopiva tietylle kohteelle, kuten muodolle.

Esimerkki:

```json
"DeepL": {
    "enabled": true,
    "allow": [],
    "deny": ["html"]
}
```

Säännöt arvioidaan tässä järjestyksessä:

1. Kohde `deny`-listalla hylätään.
2. Jos `allow` on tyhjä, käytetään asetettua oletusarvoa.
3. Jos `allow` sisältää kohteen, se hyväksytään.
4. Muuten kohde hylätään.

Esimerkiksi:

```python
config.is_allowed("DeepL", "html")
```

palauttaa `False`, kun `html` on tarjoajan `deny`-listalla.

Tämä mahdollistaa reitittimen valita toisen käytössä olevan palvelun tarjoajan, jos nykyinen palvelun tarjoaja ei sovellu pyyntöön.

## `.env`-tuki

`ConfigManager` voi ladata `.env`-tiedoston ilman ulkoista riippuvuutta.

Oletusarvoisesti:

```text
.env
```

ladataan projektikansiosta.

Esimerkki:

```text
DEEPL_API_KEY=your-key
GOOGLE_API_KEY=your-key
MYMEMORY_EMAIL=example@example.com
```

Arvot tehdään saatavilla prosessin ympäristömuuttujien kautta.

Niihin pääsee käyttämällä:

```python
config.get_env("DEEPL_API_KEY")
```

Ilmeinen oletusarvo voidaan myös antaa:

```python
config.get_env("DEEPL_API_KEY", default=None)
```

`.env`-tiedostoa valvoo asetusten tarkkailija. Kun se muuttuu,
SHL lataa ympäristöarvonsa uudelleen.

Älä sitoudu salaisiin avaimiin lähteenhallintaan.

## `ConfigManager`-luokan käyttö

Tuo hallinta asetuspaketin kautta:

```python
from shl.config import ConfigManager
```

Luo instanssi:

```python
config = ConfigManager()
```

Oletuspolut ovat:

```text
shl-config.json
.env
```

Mukautetut polut voidaan antaa:

```python
from pathlib import Path

config = ConfigManager(
    path=Path("shl-config.json"),
    env_path=Path(".env"),
    check_interval=1.0,
)
```

## Tarjoaja asetusten lukeminen

Hae koko tarjoajan kokoonpano:

```python
deepl = config.get_provider("DeepL")
```

Hae yksi asetus:

```python
enabled = config.get_provider_setting(
    "DeepL",
    "enabled",
    default=False,
)
```

Tai yksinkertaisesti:

```python
enabled = config.is_enabled("DeepL")
```

Hae kaikki käytössä olevat tarjoajat:

```python
providers = config.get_enabled_providers()
```

Hae varajärjestelmäehdokkaat tarjoajalle:

```python
fallbacks = config.get_fallback_providers("DeepL")
```

Hae kaikki tarjoajat:

```python
providers = config.get_provider_list()
```

## Asetusten uudelleenlataus

`ConfigManager` valvoo `shl-config.json`:ia automaattisesti.

Kun tiedosto muuttuu, SHL yrittää ladata sen uudelleen.

Jos uusi JSON on virheellinen, aiempi kelvollinen asetustiedosto säilytetään. Tämä estää väliaikaisen tai keskeneräisen tiedoston kirjoituksen korvaamasta toimivaa asetusta virheellisellä datalla.

Manuaalinen uudelleenlataus on myös mahdollinen:

```python
config.reload()
```

Pakotettu uudelleenlataus voidaan pyytää:

```python
config.reload(force=True)
```

## Uudelleenlatauskutsut

Koodi voi rekisteröidä kutsun, joka suoritetaan onnistuneen asetusten uudelleenlatauksen jälkeen:

```python
def on_config_reload(new_config):
    print("Configuration changed")


config.on_reload(on_config_reload)
```

Kutsu saa kopion uudesta asetustiedostosta.

Kutsu voidaan poistaa:

```python
config.remove_reload_callback(on_config_reload)
```

## Säikeiden turvallisuus

`ConfigManager` suojelee sisäistä asetustaan uudelleenkäynnistyslukolla.

Palautetut asetusrakenteet ovat syväkopioita, joten kutsujat eivät voi vahingossa muokata sisäistä asetusta palautetun sanakirjan tai listan kautta.

Tämä mahdollistaa asetusten tarkkailijan ja sovelluskoodin käyttää hallintaa samanaikaisesti.

## Tarkkailijan elinkaari

Tarkkailija käynnistyy automaattisesti, kun `ConfigManager` luodaan.

Se voidaan pysäyttää eksplisiittisesti:

```python
config.stop_watcher()
```

Se voidaan myös käynnistää uudelleen:

```python
config.start_watcher()
```

Eksplisiittistä resurssienhallintaa varten:

```python
with ConfigManager() as config:
    # k äy tä SHL-asetuksia
    ...
```

Kontekstista poistuminen pysäyttää tarkkailijan.

Vaihtoehtoisesti:

```python
config.close()
```

## Asetusten vastuu

`ConfigManager` on vastuussa asetustilasta ja palvelun tarjoajien saatavuudesta.

Reititin pysyy vastuussa käännösten reitityksestä.

Erityisesti `ConfigManager` ei:

- suorita käännöksiä
- päätä käännöksen semanttisesta laadusta
- kirjoita käännöstiedostoja
- tallenna `base_lang:in tekstiä kohdekäännökseksi
- yritä samaa tarjoajaa omana varajärjestelmä nään

Tarkoitettu erottelu on:

```text
ConfigManager
    │
    ├── palvelun tarjoaja käytössä?
    ├── palvelun tarjoaja sallittu?
    ├── saatavilla olevat varajärjestelmät?
    └── ympäristömuuttujat
             │
             ▼
          Reititin
             │
             ├── valitse palvelun tarjoaja
             ├── yritä varajärjestelmä palvelun tarjoajaa
             └── päätä suoritusaikaisesta varajärjestelmästä
                       │
                       └── base_lang (vain näyttö)
```

Tämä pitää palvelun tarjoaja asetukset erillään reitityslogiikasta ja säilyttää SHL:n itsekorjautuvan toiminnan.
