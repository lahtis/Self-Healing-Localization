# SHL Kehityskohteet ja Puutteet — Päivitetty 2026-08-22

> **Korjatut 0.2.5-hotfixissä:** Policy-manager (hot-reload, keskitetty konfiguraatio, säieturvallisuus), provider-cachen virheenkäsittely ja staattiset fallbackit, routerin virheloggaus.
>
> **Kriittinen jäljellä oleva bugi (4.6):** Kun kaikki käännöspalvelut epäonnistuvat, SHL tallentaa kääntämättömän tekstin kohdekielen tiedostoon (esim. `fi.json` täyttyy englanninkielisellä tekstillä).

---

## 1. Konfiguraatio

| # | Puute | Vaikutus | Ehdotus | Priority |
|---|-------|----------|---------|----------|
| 1.1 | **Ei skeemavalidointia** | Typoja tai väärän tyyppisiä arvoja (esim. `ttl: "3600"`) | `TypedDict` / `dataclass` -pohjainen config-objekti | Keski |
| 1.4 | **`get_config_value()` lukee tiedoston joka kerta** | JSON avataan ja parsitaan joka kutsulla | Välimuisti tai yhdistä `ConfigManager`:iin | Keski |
| 1.5 | **Ei tyyppitarkistusta** | `get_config_value()` palauttaa `Any` | `get_config_int()`, `get_config_bool()`, `get_config_str()` | Matala |

---

## 2. Provider-kielituki

| # | Puute | Vaikutus | Ehdotus | Priority |
|---|-------|----------|---------|----------|
| 2.1 | **Ei TTL:ää välimuistille** | `languages_cache.json` jää ikuisesti voimaan | `cache_generated_at`-aikaleima + automaattinen uudelleengenerointi | Keski |
| 2.2 | **Ei automaattista päivitystä** | `generate_cache()` pitää kutsua manuaalisesti | Vanhentunut cache → automaattinen regenerointi | Keski |

---

## 3. Välimuisti

| # | Puute | Vaikutus | Ehdotus | Priority |
|---|-------|----------|---------|----------|
| 3.1 | **`Localizer` / `TemplateLocalizer` ei käytä `TranslationCache`:a** | Omat `dict`-välimuistit ilman TTL:ää tai koon rajaa | Refaktoroi käyttämään yhtenäistä välimuistikerrosta | Korkea |
| 3.2 | **`TranslationCache` ei ole persistoitu** | Häviää sovelluksen sulkemisen yhteydessä | Opt-in SQLite-persistointi (WAL-tila) | Keski |
| 3.3 | **Ei jaettua välimuistia prosesseille** | Jokainen worker pitää omaa muistivälimuistiaan | SQLite-cache: yhteinen, warm start, jaettu quota | Keski |

---

## 4. Virheenkäsittely ja API

| # | Puute | Vaikutus | Ehdotus | Priority |
|---|-------|----------|---------|----------|
| 4.2 | **DRY-rikkomukset `core.py`:ssä** | `_get_text_with_fallback` ja `_get_template_with_fallback` ~95% samaa | Geneerinen `_get_with_fallback(localizer, key)` | Korkea |
| 4.3 | **`base_lang == "en"` on hauras** | Ei erota `None` ja eksplisiittistä `"en"` | Erota "ei annettu" vs. eksplisiittinen arvo | Keski |
| 4.4 | **`Translator` alustetaan aina** | Luodaan vaikka `ai_translation_enabled=False` | Lazy initialization `@property` | Keski |
| 4.5 | **`get_stats()` palauttaa suoran viittauksen** | Käyttäjä voi muokata sisäistä tilaa | Palauta kopio: `self.config.copy()` | Matala |
| 4.6 | **🔴 VIRHETILANTEESSA TALLENNETAAN VÄÄRÄ KIELITIEDOSTO** | Kun kaikki providerit fail, kääntämätön teksti tallentuu kohdekielen tiedostoon (esim. `fi.json` täyttyy englannista) | Älä tallenna kääntämätöntä tekstiä kohdekieleen; merkkaa avain puuttuvaksi tai käytä erillistä virhetiedostoa | **KRIITTINEN** |

---

## 5. Suorituskyky

| # | Puute | Vaikutus | Ehdotus | Priority |
|---|-------|----------|---------|----------|
| 5.1 | **`Localizer.get_text()` lukee levyltä joka kerta** | Toisen kielen tiedosto avataan jokaisella kutsulla | Välimuisti aktiiviselle kielelle | Korkea |
| 5.2 | **`Localizer.L()` tallentaa JSON:n joka kutsulla** | Levylle kirjoitus jokaisella uudella avaimella | `dirty`-flagi + batch-tallennus tai erillinen `save()` | Korkea |
| 5.3 | **`language_validator.py`:n O(n)-haku** | `_find_language()` käy 7900 kieltä läpi joka kerta | Rakenna ISO 639-3 -indeksi alustuksessa | Keski |
| 5.4 | **Globaali tila `router.py`:ssä** | `_translation_cache`, rekisterit — ei lukkoja | `threading.Lock` tai instanssikohtainen | Keski |
| 5.5 | **`ai_translation.py`:n cache-ristiriita** | Globaali vs. instanssikohtainen cache | Yhtenäistä yhdeksi cacheksi | Matala |
| 5.6 | **`_load_env()` moduulitasolla** | Kutsutaan importin yhteydessä, ei konstruktorissa | Siirrä konstruktoriin | Matala |

---

## 6. Ylläpidettävyys

| # | Puute | Ehdotus | Priority |
|---|-------|---------|----------|
| 6.1 | **Ei automaattista API-docin generointia** | `pdoc`, `mkdocstrings` tai `sphinx-autodoc` | Matala |
| 6.2 | **Versiohistoria hajallaan** | Yksi `shl/__init__.py`:n `__version__` riittää | Matala |
| 6.3 | **Legacy-migraatio jättää vanhat tiedostot** | Optio vanhojen `lang_xx.json`-tiedostojen siivoamiseen | Matala |

---

## Suositeltu työjärjestys

| Järjestys | Kohde | Perustelu |
|-----------|-------|-----------|
| 1 | **4.6 Väärä kielitiedosto virhetilanteessa** | Saastuttaa tuotantodataa pysyvästi |
| 2 | **5.1 + 5.2 Localizer/TemplateLocalizer välimuisti** | Pullonkaula jokaisessa käännöspyynnössä |
| 3 | **4.2 DRY-rikkomukset** | Yksinkertaistaa ylläpitoa |
| 4 | **3.2 + 3.3 SQLite-optio** | Välttämätön web-ympäristöön |
| 5 | **2.1 + 2.2 Provider-cachen TTL** | Estää vanhentuneet kielilistat |
| 6 | **1.1 Skeemavalidointi** | Estää hiljaiset konfiguraatiovirheet |

---

*Päivitetty: 2026-08-22 — korjatut kohdat poistettu, prioriteetit päivitetty*
