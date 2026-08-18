# SHL-asetukset

SHL käyttää kevyttä··riippuvuudetonta asetustasoa tarjoaja-asetuksille
ja ympä··ristö···muuttujille.

Asetusten hallinta sijaitsee polussa:

```text
shl/
└── config/
    ├── __init__.py
    └── manager.py
```

Sovelluksen asetukset säilytetä··n yleensä·· projektin juuressa:

```text
my_project/
├── shl-config.json
├── .env
└── shl/
    └── ...
```

## Asetustiedosto

Oletusarvoisesti SHL etsii tiedostoa `shl-config.json` nykyisestä·· projektikansiosta.

Tarjoaja voidaan m ää··ritt ää·· `enabled`, `allow` ja `deny` -asetuksilla.

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

## Tarjoajan `enabled`

`enabled` m ää··ritt ää··, onko tarjoaja k äy t össä·· SHL:lle.

```json
"DeepL": {
    "enabled": true
}
```

Kun `enabled` on `false`, tarjoajaa ei sis ällytet ä k äy t össä·· olevien
tarjoajien joukkoon k ää··nn öksi ä tai varaj ärjestelm ää·· varten.

K äy t össä·· olevat tarjoajat ovat saatavilla funktion kautta:

```python
config.get_enabled_providers()
```

## Automaattinen varaj ärjestelm ä

SHL k äs ittelee muita k äy t össä·· olevia tarjoajia mahdollisina
varaj ärjestelmin ä.

Tarjoaja ei voi koskaan olla oma varaj ärjestelm äns ä.

Esimerkiksi, kun nykyinen tarjoaja on `DeepL`:

```python
config.get_fallback_providers("DeepL")
```

palauttaa muut k äy t össä·· olevat tarjoajat.

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

varaj ärjestelm äsuhde on tehokkaasti:

```text
MyMemory → DeepL
DeepL    → MyMemory
```

Googlea ei sis ällytet ä, koska se on poissa k äy t östä··.

Jos vain yksi tarjoaja on k äy t össä··:

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

niin MyMemoryll ä ei ole vaihtoehtoista tarjoajaa.

T äll öin SHL ei yrit ä k äy tt ää·· MyMemory ä omana
varaj ärjestelm än ää··n. Jos tarjoaja ei pysty tuottamaan k ää··nn östä··,
suoritusaika voi n äy tt ää·· `base_lang`-arvon.

## `base_lang` ei ole tallennettu k ää··nn ös

`base_lang`-varaj ärjestelm ä on suoritusaikainen n äy tt övaraj ärjestelm ä.

Jos mik ää··n tarjoaja ei pysty tuottamaan k ää··nn östä··, SHL voi n äy tt ää··
l ähdekielisen tekstin sovelluksen k äy t össä·· pit ämiseksi.

T ät ä arvoa ei saa kirjoittaa kohdekieliseen k ää··nn östiedostoon.

Esimerkiksi:

```text
Pyydetty: fi → de

K ää··nn östiedosto:
    Saksankielinen k ää··nn ös puuttuu

Tarjoaja:
    MyMemory epä onnistuu

Varaj ärjestelm ät:
    ei yht ää··n

Suoritusaika:
    n äy tä base_lang (suomi)
```

Suomenkielinen teksti n äy tet ää··n, mutta sit ä ei tallenneta saksan
k ää··nn ökseksi.

T äm ä on tärke ää·· SHL:n itsekorjautuvalle toiminnalle. Kun k ää··nn ös
tarjoaja tulee taas saataville, SHL voi tuottaa todellisen k ää··nn öksen
ja tallentaa sen sopivaan kohdekieliseen tiedostoon.

Virtaus on siis:

```text
k ää··nn ös on olemassa
    ↓
k äy tä k ää··nn östä··

k ää··nn ös puuttuu
    ↓
tarjoaja onnistuu
    ↓
k äy tä k ää··nn östä··
    ↓
tallenna kohdekielinen k ää··nn ös

k ää··nn ös puuttuu
    ↓
kaikki sopivat tarjoajat epä onnistuvat
    ↓
n äy tä base_lang
    ↓
 ÄL Ä tallenna base_lang:ia k ää··nn ökseksi
```

## `allow` ja `deny`

`allow` ja `deny` ohjaavat, onko tarjoaja sopiva tietylle
kohteelle, kuten muodolle.

Esimerkki:

```json
"DeepL": {
    "enabled": true,
    "allow": [],
    "deny": ["html"]
}
```

S ää··nn öt arvioidaan t ässä·· j ärjestyksessä··:

1. Kohde `deny`-listalla hyl ät ää··n.
2. Jos `allow` on tyhj ä, k äy tet ää··n asetettua oletusarvoa.
3. Jos `allow` sis ält ää·· kohteen, se hyv äksyt ää··n.
4. Muuten kohde hyl ät ää··n.

Esimerkiksi:

```python
config.is_allowed("DeepL", "html")
```

palauttaa `False`, kun `html` on tarjoajan `deny`-listalla.

T äm ä mahdollistaa reitittimen valita toisen k äy t össä·· olevan tarjoajan,
kun nykyinen tarjoaja ei sovellu pyynt öö···n.

## `.env`-tuki

`ConfigManager` voi ladata `.env`-tiedoston ilman ulkoista
riippuvuutta.

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

Arvot tehd ää··n saatavilla prosessin ymp ärist ömuuttujien kautta.

Niihin p ää··see k äy tt äm äll ä:

```python
config.get_env("DEEPL_API_KEY")
```

Ilmeinen oletusarvo voidaan myös antaa:

```python
config.get_env("DEEPL_API_KEY", default=None)
```

`.env`-tiedostoa valvoo asetusten tarkkailija. Kun se muuttuu,
SHL lataa ymp ärist öarvonsa uudelleen.

Ä· ·l ä sitoudu salaisiin avaimiin lähteenhallintaan.

## `ConfigManager`-luokan k äy tt ö

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

## Tarjoaja-asetusten lukeminen

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

Hae kaikki k äy t össä·· olevat tarjoajat:

```python
providers = config.get_enabled_providers()
```

Hae varaj ärjestelm äehdokkaat tarjoajalle:

```python
fallbacks = config.get_fallback_providers("DeepL")
```

Hae kaikki tarjoajat:

```python
providers = config.get_provider_list()
```

## Asetusten uudelleenlataus

`ConfigManager` valvoo `shl-config.json`:ia automaattisesti.

Kun tiedosto muuttuu, SHL yritt ää·· ladata sen uudelleen.

Jos uusi JSON on virheellinen, aiempi kelvollinen asetustiedosto
s äilytet ää··n. T äm ä est ää·· v äliaikaisen tai keskener äisen
tiedoston kirjoituksen korvaamasta toimivaa asetusta virheellisellä··
datalla.

Manuaalinen uudelleenlataus on myös mahdollinen:

```python
config.reload()
```

Pakotettu uudelleenlataus voidaan pyyt ää··:

```python
config.reload(force=True)
```

## Uudelleenlatauskutsut

Koodi voi rekister öid ä kutsun, joka suoritetaan onnistuneen
asetusten uudelleenlatauksen j älkeen:

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

`ConfigManager` suojelee sis äistä·· asetustaan uudelleenk äy nnilukolla.

Palautetut asetusrakenteet ovat syv äkopioita, joten kutsujat eivät voi
vahingossa muokata sis äistä·· asetusta palautetun
sanakirjan tai listan kautta.

T äm ä mahdollistaa asetusten tarkkailijan ja sovelluskoodin k äy tt ää··
hallintaa samanaikaisesti.

## Tarkkailijan elinkaari

Tarkkailija k äy nnistyy automaattisesti, kun `ConfigManager` luodaan.

Se voidaan pys äy tt ää·· eksplisiittisesti:

```python
config.stop_watcher()
```

Se voidaan myös k äy nnist ää·· uudelleen:

```python
config.start_watcher()
```

Eksplisiittistä·· resurssienhallintaa varten:

```python
with ConfigManager() as config:
    # k äy tä SHL-asetuksia
    ...
```

Kontekstista poistuminen pys äy tt ää·· tarkkailijan.

Vaihtoehtoisesti:

```python
config.close()
```

## Asetusten vastuu

`ConfigManager` on vastuussa asetustilasta ja tarjoajien
saatavuudesta.

Reititin pysyy vastuussa k ää··nn östen reitityksestä··.

Erityisesti `ConfigManager` ei:

- suorita k ää··nn öksi ä
- p ää··t ä k ää··nn öksen semanttisesta laadusta
- kirjoita k ää··nn östiedostoja
- tallenna `base_lang`:ia kohdek ää··nn ökseksi
- yrit ä samaa tarjoajaa omana varaj ärjestelm än ää··n

Tarkoitettu erottelu on:

```text
ConfigManager
    │
    ├── tarjoaja k äy t össä··?
    ├── tarjoaja sallittu?
    ├── saatavilla olevat varaj ärjestelm ät?
    └── ymp ärist ömuuttujat
             │
             ▼
          Reititin
             │
             ├── valitse tarjoaja
             ├── yrit ä varaj ärjestelm ätarjoajaa
             └── p ää··t ä suoritusaikaisesta varaj ärjestelm ästä··
                       │
                       └── base_lang (vain n äy tt ö)
```

T äm ä pitää tarjoaja-asetukset erill ää··n reitityslogiikasta ja s äilytt ää··
SHL:n itsekorjautuvan toiminnan.
