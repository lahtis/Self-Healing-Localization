# SHL — Itsekorjautuvan lokalisointikirjaston dokumentaatio
## Täydellinen tekninen API-viite

> **Versio:** 0.2.3
> **Tekijä:** Tuomas Lähteenmäki
> **Lisenssi:** MIT
> **Laajuus:** Ydinmoottori, käännösjärjestelmä, palveluntarjoajat, apuohjelmat ja GLFM-integraatio.

---

Tervetuloa itsekorjautuvan lokalisointikirjaston dokumentaatioon. SHL on älykäs, nolla-riippuvuutta vaativa lokalisointikirjasto, joka sisältää automaattisen puuttuvien avainten käännöksen ja vankat kielivaraketjut.

## Pikalinkit

- [Aloittaminen](oppaat/v0_2_0/getting_started.md)
- [Määritysopas](oppaat/v0_2_0/configuration.md)
- [Käyttöopas](oppaat/v0_2_0/usage.md)
- [API-viite](api/v0_2_0/engine.md)
- [Täydellinen opas](api/v0_2_3/SHL_Complete_API_Reference_v023.md)
- [Kehitys](kehitys/readme.md)

---

# Mikä tekee SHL:stä erilaisen?

## Ominaisuuksien vertailu

| Ominaisuus | SHL | Perinteinen i18n | Muu (gettext, Babel) |

|---------|-----|-------------------|-----------------------|
| Puuttuvat avaimet luodaan automaattisesti | ✅ Kyllä | ❌ Ei | ❌ Ei |
| Puuttuvat kielitiedostot luodaan automaattisesti | ✅ Kyllä | ❌ Ei | ❌ Ei |
| Ei suorituksenaikaisia ​​riippuvuuksia | ✅ Kyllä | ❌ Ei | ❌ Ei (usein vaatii gettextin, Babelin jne.) |
| BCP-47-alueen alitunnisteiden tuki | ✅ Kyllä | ⚠️ Rajoitettu | ⚠️ Rajoitettu |
| GLFM-kielen validointi (yli 7 900 kieltä) | ✅ Kyllä | ❌ Ei | ❌ Ei |
| Itsekorjaavat varaketjut | ✅ Kyllä | ❌ Ei | ❌ Ei |
| Älykäs käännösten reititys | ✅ Kyllä | ❌ Ei | ❌ Ei |
| Palveluntarjoajasta riippumaton arkkitehtuuri | ✅ Kyllä | ❌ Ei | ❌ Ei |
| DeepL-, Google-, Papago- ja MyMemory-tuki | ✅ Kyllä | ❌ Ei | ❌ Ei |
| Tekoälyllä toimiva laadunvarmistus (tulevaisuudessa) | ✅ Suunnitelmissa | ❌ Ei | ❌ Ei |
| Ihmisen muokattavissa olevat käännöstiedostot | ✅ Kyllä | ✅ Kyllä | ✅ Kyllä |
| Käännösmuistia (TM) ei vaadita | ✅ Kyllä | ⚠️ Valinnainen | ⚠️ Valinnainen |

---

## Käännösominaisuudet

| Ominaisuus | SHL | Perinteinen i18n | Muu |
|----------|------|-----------------|---------|
| Yksittäiset sanat | ✅ Kyllä | ✅ Kyllä | ✅ Kyllä |
| Kokonaiset lauseet | ✅ Kyllä | ❌ Ei | ❌ Ei |
| Dynaaminen teksti | ✅ Kyllä | ❌ Ei | ❌ Ei |
| Kysymykset | ✅ Kyllä | ❌ Ei | ❌ Ei |
| Virheilmoitukset | ✅ Kyllä | ❌ Ei | ❌ Ei |
| Paikkamerkit ja muuttujat | ✅ Kyllä | ⚠️ Vain manuaalinen | ⚠️ Vain manuaalinen |
| Kontekstitietoiset käännökset | ✅ Suunniteltu | ❌ Ei | ❌ Ei |
| Muodollisuustasot | ✅ Vain DeepL | ❌ Ei | ❌ Ei |
| HTML/Markdown-säilytys | ✅ DeepL/Google | ❌ Ei | ❌ Ei |
| Sanastotuki | ✅ DeepL | ❌ Ei | ❌ Ei |

---

## Tekoälyllä toimiva käännöslaatu

### Nykytila ​​(v0.2.3)

SHL käyttää useita käännöspalveluntarjoajia parhaan laadun varmistamiseksi:

| Palveluntarjoaja | Paras käyttökohde | Ominaisuudet |
|----------|-----------|-----------|
| **DeepL** | Eurooppalaiset kielet | Muodollisuus, sanasto, konteksti, HTML-säilytys |
| **Papago** | Aasialaiset kielet (korea, japani, kiina) | Kulttuuritarkkuus |
| **Google Translate v2** | Laaja kielivalikoima | HTML-muoto, vikasietoisuus |
| **LibreTranslate** | Yksityisyys, itseisännöinti ja offline-käyttö | Avoimen lähdekoodin itseisännöity API, offline-tuki, Argos-kääntäjä |
| **myMemory** | Ilmainen, aina saatavilla | Yhteisön käännökset |


## Käännös-API:iden vertailu

### Ominaisuusvertailu

| SHL | Palveluntarjoaja | HTML-muoto | Glossaries | Formal/informal tone | Contextual suggestions | Honorifics | Kielen tunnistus | Dokumenttikäännös | Verkkosivukäännös | Eräkäännös | Huomioitavaa |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| + | **DeepL** | + | + | + | – | – | – | + (rajoitettu) | – | + | Korkein laatu erityisesti eurooppalaisilla kielillä. Ilmainen kiintiö 500k merkkiä/kk (kertaluonteinen). |
| + | **Papago** | – | + | + (vain tietyt kielet) | – | + | + | + | + | – | Vahva Aasian kielissä, erityisesti koreassa. |
| + | **Google Translate v2** | + | – (v2) / + (v3) | + | + | – | + | + | – | + | Laajin kielituki (100+ kieltä). Ilmainen 500k merkkiä/kk. |
| + | **LibreTranslate** | + (*) | – | – (***) | – | – | + | + | – | + | Ainoa ilmainen ja itseisännöitävä vaihtoehto. Laatu jää kaupallisista. |
| + | **myMemory** | – | – | – | – | – | + (rajoitettu) | + | – | + | Ilmainen, mutta rajoitettu 5000 merkkiin/päivä. Hyödyntää valtavaa käännösmuistia. |
| - | **Microsoft Azure Translator** | + | + | + | – | – | + | + | – | + | Edullisin isoista pilvipalveluista (n. $10 / milj. merkkiä). |
| - | **Amazon Translate** | ? | + | – | – | – | + | + | – | + | S3-batch-käännökset ja syvä AWS-integraatio. |
| - | **ModernMT** | ? | + (Adaptiivinen) | ? | + | ? | ? | + (DOCX) | ? | + | Oppii reaaliajassa käännösmuistista, 200+ kieltä. |
| - | **SYSTRAN** | ? | + | ? | ? | ? | ? | ? | ? | ? | Vahva erikoistuneilla aloilla (esim. juridinen, tekninen). |
| - | **IBM Watson** | ? | + | ? | ? | ? | ? | ? | ? | ? | Räätälöitävissä omalle datalle ja toimialalle. |
| - | **Yandex Translate** | ? | + | ? | ? | ? | ? | ? | ? | ? | Laaja kielituki ja yritystason tuki. |
| - | **OpenAI (GPT-4o ym.)** | + (kautta promptin) | + (kautta promptin) | + (kautta promptin) | + | + (kautta promptin) | + | – | – | + | Erinomainen sävyn, tyylin ja kontekstin hallintaan, mutta kallis ja hidas verrattuna NMT-API:hin. |

#### Merkkien selitykset

| Merkki | Selitys |
| :---: | :--- |
| **+** | Täysi tai vahva tuki |
| **–** | Ei tukea tai ei merkittävä ominaisuus |
| **?** | Tietoa ei ollut saatavissa |
| **(*)** | Kokeellinen |
| **(***)** | Kehitteillä |
| **SHL +** | Palvelu on mukana alkuperäisessä listassa |
| **SHL –** | Palvelu on lisätty vertailuun myöhemmin |

### Ominaisuuksien kuvaukset

| Ominaisuus | Kuvaus |
| :--- | :--- |
| **HTML-muoto** | Säilyttää HTML-tagit ja -rakenteen käännöksessä |
| **Glossaries** | Sanastot, joilla varmistetaan tiettyjen termien (esim. tuotenimet) johdonmukainen kääntäminen |
| **Formal/informal tone** | Käännöksen muodollisuusasteen säätäminen (esim. "sinä" vs. "Te") |
| **Contextual suggestions** | Kontekstin huomioivat vaihtoehtoiset käännösehdotukset |
| **Honorifics** | Kunnioittavan muodon (erityisesti aasialaiset kielet) tuki |
| **Kielen tunnistus** | Syötetyn tekstin kielen automaattinen tunnistus |
| **Dokumenttikäännös** | Kokonaisten tiedostojen (PDF, Word, Excel) kääntäminen |
| **Verkkosivukäännös** | Verkkosivujen rakenteen säilyttävä käännös |
| **Eräkäännös** | Useiden tekstien kääntäminen yhdellä pyynnöllä |

## POST-metodin tuki

| SHL | Palveluntarjoaja | POST-tuki | Huomioita |
| :---: | :--- | :---: | :--- |
| + | **DeepL** | **Pakollinen** | DeepL on ilmoittanut, että maaliskuusta 2025 alkaen `/translate`-päätepiste hyväksyy ainoastaan POST-pyyntöjä. GET-pyynnöt ja kyselyparametrit hylätään. Tämä on tehty tietoturvan ja alan standardien noudattamiseksi. |
| + | **Papago** | Kyllä | Papagon tekstikäännöksen API-rajapinta (`/nmt/v1/translation`) toimii POST-pyynnöillä. API-kutsu vaatii Client ID ja Client Secret -tiedot HTTP-headerissa. |
| + | **Google Translate v2** | Kyllä | Google Translation API v2 käyttää POST-pyyntöjä. Teksti lähetään JSON-muodossa pyynnön rungossa (`q`-parametri) ja API-avain toimitetaan joko URL-kyselyparametrina tai headerissa. |
| + | **LibreTranslate** | Kyllä | LibreTranslatessa REST API toimii POST-pyynnöillä `/translate`-päätepisteeseen. Pyynnön runko sisältää JSON-muodossa käännettävän tekstin (`q`), lähde- ja kohdekielikoodit. API-avain voidaan tarvittaessa liittää mukaan. |
| + | **myMemory** | Kyllä | MyMemoryn käännösrajapinta (`/api/v1/translate`) vastaanottaa POST-pyyntöjä. Parametrit (`q` ja `langpair`) lähetetään URL-encoded-muodossa pyynnön rungossa. |
| - | **Microsoft Azure Translator** | Kyllä | Azure Translator Text API käyttää POST-pyyntöjä. Teksti lähetetään JSON-muodossa pyynnön rungossa. |
| - | **Amazon Translate** | Kyllä | Amazon Translate API käyttää POST-pyyntöjä. Teksti lähetetään JSON-muodossa pyynnön rungossa. |
| - | **ModernMT** | Kyllä | ModernMT:n API käyttää POST-pyyntöjä. |
| - | **SYSTRAN** | Kyllä | SYSTRANin API käyttää POST-pyyntöjä. |
| - | **IBM Watson** | Kyllä | IBM Watson Language Translator käyttää POST-pyyntöjä. |
| - | **Yandex Translate** | Kyllä | Yandex Translate API käyttää POST-pyyntöjä. |
| - | **OpenAI (GPT-4o ym.)** | Kyllä | OpenAI:n API käyttää POST-pyyntöjä chat-kompletointiin. |

## Miten valita oikea API?

| SHL | Käyttötarkoitus | Suositeltava palvelu |
| :---: | :--- | :--- |
| + | **Korkein laatu (Euroopan kielet)** | **DeepL** on selvä valinta, kun käännöksen sujuvuus ja luonnollisuus ovat tärkeitä. |
| + | **Laajin kielituki ja skaalautuvuus** | **Google Translate** on ylivoimainen kielten määrässä, ja **Microsoft Azure** tarjoaa erittäin kattavan valikoiman edullisesti. |
| - | **Edullisin hinta ja AWS-ekosysteemi** | **Amazon Translate** on looginen valinta AWS-ympäristössä. **Microsoft Azure** on hinnoittelultaan usein halvin. |
| + | **Aasian markkinat (erityisesti Korea)** | **Papago** on vahva, erikoistunut vaihtoehto. |
| + | **Täysi hallinta, yksityisyys ja hinta** | **LibreTranslate** on ainoa vaihtoehto, jonka voit isännöidä itse ilmaiseksi. |
| + | **Nopea prototypointi ilman rekisteröitymistä** | **myMemory** on helppo ja nopea tapa testata käännöksiä ilman API-avainta. |
| - | **Sävy, tyyli ja monimutkainen sisältö** | **LLM-pohjaiset API:t** (OpenAI, Claude, Gemini) loistavat markkinointi- ja brändisisällössä, mutta ovat kalliimpia. |
| - | **Erikoistuneet tai säännellyt alat** | **SYSTRAN** ja **IBM Watson** tarjoavat räätälöintiä ja tietoturvaa, joka sopii esim. juridiikkaan ja terveydenhuoltoon. |


### Tekoälyllä toimiva laatuputki (suunniteltu)

---

### Tärkeimmät edut

- **Ei enää manuaalista JSON-muokkausta.**
- **Ei enää "puuttuvien käännösten" virheitä.**
- **Ei enää keskeneräisiä kielipaketteja.**
- **Kirjoita koodia omalla äidinkielelläsi.** SHL hoitaa loput.

---

## Ominaisuudet

### Peruskieli
Peruskieli (base_lang) on täysin kehittäjän hallinnassa.

Se on kieli, jolla ensisijaisesti kirjoitat sovelluksen tekstejä.

SHL käyttää sitä:
- varakielenä, kun kohdekielen käännös puuttuu
- lähteenä muita kielitiedostoja luotaessa tai synkronoitaessa

### Itsekorjautuva käyttöliittymän lokalisointi
- Puuttuvat kielitiedostot luodaan automaattisesti.
- Puuttuvat avaimet lisätään lennossa.
- Kehittäjän määrittämää peruskieltä käytetään varakielenä.
- Alueen alitunnisteet säilytetään: `zh-TW`, `pt-BR` saavat omat tiedostonsa.

### Itsekorjautuvan tekoälykehotemallin lokalisointi
Suuret kielimallit (LLM) vaativat usein lokalisoituja kehotemalleja lokalisoidun käyttöliittymätekstin lisäksi. SHL hallitsee molempia saman itsekorjaavan lokalisointimoottorin avulla.

- Puuttuvat mallitiedostot luodaan automaattisesti.
- Perusmallit kopioidaan varaksi.
- Puuttuvat malliavaimet lisätään automaattisesti.
- Saman alueen alitunnisteiden tuki kuin käyttöliittymän lokalisoinnissa.

### Yhtenäinen korkean tason moottori
`LocalizationEngine` yhdistää kaiken:
- Varmistaa kielten olemassaolon.
- Synkronoi kaikki kielet peruskielen kanssa.
- Tarjoaa yhden käyttöliittymän käyttöliittymätekstille ja kehotemalleille.
- Valinnainen GLFM-kielen validointi BCP-47-tageilla.

### GLFM-integraatio (yli 7 900 kieltä)
- **GLFM Lite** (oletus): ~428 kt, yli 7 900 kieltä ja 20 lähintä sukukieltä.
- **Täysi GLFM** (valinnainen): ~925 Mt – sisältää yli 7 900 kieltä ja niiden lähimmät kielet (nearest languages, lang2vec / URIEL) tutkimukseen ja tekoälyyn.
- Kielen validointi BCP-47-tageilla.
- Kieliperheen varaketjut.

### Älykäs käännösten reititys (v0.2.0)
- Valitsee automaattisesti parhaan saatavilla olevan palvelun (MyMemory → LibreTranslate -).
- Automaattinen varmistus nopeusrajoitusten tai käyttökatkosten sattuessa.
- Kielituen tunnistus 24 tunnin välimuistilla.
- Konekäännös on valinnainen (oletuksena `m_translation_enabled=False`).

### Nolla riippuvuutta.
