# SHL Kehityskohteet ja Puutteet

> **Kriittinen bugi (havaittu 2026-08-18):** Kun kaikki käännöspalvelut epäonnistuvat (`MyMemory` palauttaa muuttumattoman tekstin → kaikki providerit fail → `translate_text` palauttaa alkuperäisen), SHL tallentaa väärän kielitiedoston. Kohdekielen (`fi`) sijaan luodaan/tallennetaan `en.json`. Tämä on fallback-bugi, joka saastuttaa kielitiedostot.
>
> Loki:
> ```
> Provider 'mymemory' failed attempt 1/2: MyMemory returned unchanged text.
> Provider 'mymemory' failed attempt 2/2: MyMemory returned unchanged text.
> translate_text wrapper: All available translation services failed or timed out within 30.0s.
> ```


Kooste dokumentointiprosessin aikana havaituista puutteista ja kehityskohteista.

---

## 1. Konfiguraatio (`shl-config.json` / `config.conf` / `.env`)

| # | Puute | Vaikutus | Ehdotus |
|---|-------|----------|---------|
| 1.1 | **Ei skeemavalidointia** | Voi sisältää typoja tai väärän tyyppisiä arvoja (esim. `ttl: "3600"` stringinä numeron sijaan) | Lisää skeemavalidointi tai `TypedDict` / `dataclass` -pohjainen config-objekti |
| 1.2 | **Ei hot-reloadia** | `config.json`:n muutos vaatii sovelluksen uudelleenkäynnistyksen | `ConfigManager`-tyylinen tiedostovalvonta (kuten `policy-manager.py`:ssä) |
| 1.3 | **Hajallaan useissa paikoissa** | `.env`, `shl-config.json`, `config.conf` — ei selkeää erottelua mikä kuuluu minne | Yksi kerros: `.env` = salaisuudet, `shl-config.json` = SHL-asetukset, `config.conf` = sovelluskohtainen |
| 1.4 | **`get_config_value()` lukee tiedoston joka kerta** | `shl/utils/config.py`:n `get_config_value()` avaa ja parsii JSON:n joka kutsulla | Lisää välimuisti tai yhdistä `shl/config/config.py`:n kanssa |
| 1.5 | **Ei tyyppitarkistusta** | `get_config_value()` palauttaa `Any`, kutsuja ei tiedä odottaako `int`, `str` vai `bool` | Lisää `get_config_int()`, `get_config_bool()`, `get_config_str()` |

---

## 2. Provider-kielitukivälimuisti (`provider_cache.py`)

| # | Puute | Vaikutus | Ehdotus |
|---|-------|----------|---------|
| 2.1 | **Ei TTL:ää välimuistille** | `languages_cache.json` jää ikuisesti voimaan, vaikka provider lisäisi kieliä | Lisää `cache_generated_at`-aikaleima ja automaattinen uudelleengenerointi |
| 2.2 | **Ei automaattista päivitystä** | `generate_cache()` pitää kutsua manuaalisesti | Jos cache on vanhempi kuin X päivää, generoi automaattisesti |
| 2.3 | **Ei virheenkäsittelyä verkkoon** | Jos `fetch_microsoft_translator()` tai `fetch_libretranslate()` epäonnistuu, koko `generate_cache()` kaatuu | Catchaa verkkovirheet provider-kohtaisesti, tallenna mitä saatiin |
| 2.4 | **Papago/MyMemory staattinen** | `data/papago_mymemory.json` on manuaalinen, ei päivity automaattisesti | Dokumentoi päivitysprosessi tai harkitse API-haun lisäämistä |
| 2.5 | **Ei säieturvallisuutta** | `generate_cache()` kirjoittaa tiedostoon ilman lukitusta | Lisää `threading.Lock` tai atomiset tiedosto-operaatiot |

---

## 3. Välimuisti (`TranslationCache` vs. `Localizer` / `TemplateLocalizer`)

| # | Puute | Vaikutus | Ehdotus |
|---|-------|----------|---------|
| 3.1 | **`Localizer` / `TemplateLocalizer` ei käytä `TranslationCache`:a** | Omat yksinkertaiset `dict`-välimuistit (`_loaded_langs`) ilman TTL:ää, koon rajaa tai eviktiota | Refaktoroi käyttämään `TranslationCache`:a tai yhtenäistä välimuistikerros |
| 3.2 | **`TranslationCache` ei ole persistoitu** | Häviää sovelluksen sulkemisen yhteydessä | Opt-in SQLite-persistointi (WAL-tila, `check_same_thread=False`) |
| 3.3 | **Ei jaettua välimuistia prosesseille** | Jokainen worker/instanssi pitää omaa muistivälimuistiaan | SQLite-cache opt-in: yhteinen persistoitu cache, warm start, jaettu quota |

---

## 4. Virheenkäsittely ja API

| # | Puute | Vaikutus | Ehdotus |
|---|-------|----------|---------|
| 4.1 | **Käännösvirheiden hiljainen nieleminen** | `translate_text()` palauttaa alkuperäisen tekstin virhetilanteessa — kutsuja ei tiedä epäonnistumisesta | Lisää `raise_on_failure=True`-parametri tai palauta tuple `(translated, success)` |
| 4.2 | **DRY-rikkomukset `core.py`:ssä** | `_get_text_with_fallback` ja `_get_template_with_fallback` ovat ~95% samaa koodia | Yhdistä geneeriseksi `_get_with_fallback(localizer, key)` |
| 4.3 | **`base_lang == "en"` on hauras** | Ei erota "ei annettu" (`None`) ja eksplisiittistä `"en"` | Erota `None` ja eksplisiittinen arvo; kehittäjän peruskieli voi olla vaikka japani |
| 4.4 | **`Translator` alustetaan aina** | `core.py`:ssä `Translator` luodaan vaikka `ai_translation_enabled=False` | Tee lazy initialization `@property`-dekoraattorilla |
| 4.5 | **`get_stats()` palauttaa suoran viittauksen** | Palauttaa `self.config`-dictin, käyttäjä voi muokata sisäistä tilaa | Palauta kopio: `self.config.copy()` |
| 4.6 | **Virhetilanteessa luodaan väärä kielitiedosto** | Kun kaikki käännöspalvelut epäonnistuvat, SHL luo/tallentaa `en.json`-tiedoston vaikka kohdekieli olisi muu (esim. `fi`). Fallback-kieli leviää väärään tiedostoon. | Korjaa fallback-logiikka: älä tallenna kääntämätöntä tekstiä kohdekielen tiedostoon; käytä erillistä virhetiedostoa tai merkkaa avain puuttuvaksi |


---

## 5. Suorituskyky ja skaalautuvuus

| # | Puute | Vaikutus | Ehdotus |
|---|-------|----------|---------|
| 5.1 | **`Localizer.get_text()` lukee levyltä joka kerta** | Toisen kielen tiedosto avataan ja parsitaan jokaisella `get_text()`-kutsulla | Lisää välimuisti `Localizer`:iin (käyttää jo `_loaded_langs`, mutta aktiivinen kieli luetaan vain kerran) |
| 5.2 | **`Localizer.L()` tallentaa JSON:n joka kutsulla** | Levylle kirjoitus jokaisella uuden avaimen luonnilla | Lisää `dirty`-flagi ja batch-tallennus tai erillinen `save()`-kutsu |
| 5.3 | **`language_validator.py`:n O(n)-haku** | `_find_language()` käy läpi 7900 kieltä lineaarisesti joka kerta (ISO 639-3) | Rakenna ISO 639-3 -indeksi alustuksessa (ISO 639-1 on jo O(1)) |
| 5.4 | **Globaali tila `router.py`:ssä** | `_translation_cache`, rekisterit, mirror_manager — ei lukkoja | Lisää `threading.Lock` tai erota instanssikohtaiseksi |
| 5.5 | **`ai_translation.py`:n cache-ristiriita** | Globaali `_translation_cache` ja `AITranslator`-instanssin oma cache ovat ristiriidassa | Yhtenäistä yhdeksi cacheksi |
| 5.6 | **`_load_env()` moduulitasolla** | `ai_translation.py`:ssä `_load_env()` kutsutaan importin yhteydessä, ei konstruktorissa | Siirrä konstruktoriin; työhakemiston vaihto importin jälkeen ei vaikuta |

---

## 6. Dokumentaatio ja ylläpidettävyys

| # | Puute | Ehdotus |
|---|-------|---------|
| 6.1 | **Ei automaattista API-docin generointia** | Harkitse `pdoc`, `mkdocstrings` tai `sphinx-autodoc` — vähentää manuaalista doc-työtä |
| 6.2 | **Versiohistoria hajallaan** | Jokaisessa tiedostossa oma `__version__` — yksi `shl/__init__.py`:n `__version__` riittää |
| 6.3 | **Legacy-migraatio jättää vanhat tiedostot** | `lang_xx.json` jää paikalleen migraation jälkeen | Lisää optio vanhojen tiedostojen siivoamiseen migraation yhteydessä |

---

## Ehdotettu prioriteettijärjestys

| Prioriteetti | Kohde | Perustelu |
|--------------|-------|-----------|
| 1 | **Konfiguraation yhtenäistäminen** | Vaikuttaa kaikkeen muuhun; yksi selkeä lähde totuudelle |
| 2 | **Provider-cachen automaattinen vanheneminen** | Estää vanhentuneet kielilistat tuotannossa |
| 3 | **`Localizer` + `TemplateLocalizer` → yhtenäinen välimuisti** | Vähentää muistinkäyttöä ja yksinkertaistaa koodia |
| 4 | **Virheiden näkyvyys (`raise_on_failure`)** | Kriittinen tuotantokäytössä — kutsujan täytyy tietää epäonnistumisesta |
| 5 | **SQLite-optio `TranslationCache`:lle** | Välttämätön web-ympäristöön (FastAPI, Flask, Django) |
| 6 | **Skeemavalidointi konfiguraatioon** | Estää hiljaiset virheet väärän tyyppisistä arvoista |

---

*Dokumentoitu: 2026-08-20*
