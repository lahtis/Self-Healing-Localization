# Provider Language Cache Data Documentation

## Overview

This JSON document contains language support data for multiple translation service providers. It is auto generated. It is used by the SHL translation router for provider selection and language pair validation. The data is structured under a single top-level `"providers"` key.

---

## Top-Level Structure

```json
{
  "providers": {
    "microsoft_translator": { ... },
    "libretranslate": { ... },
    "papago": [ ... ],
    "mymemory_iso_639_1": [ ... ]
  }
}
```

| Key | Type | Description |
|-----|------|-------------|
| `"providers"` | `object` | Container for all provider language data. |

---

## Provider: `microsoft_translator`

**Type:** `object` (dictionary)

**Format:** `{ "language_code": "Language Name", ... }`

Maps lowercase language codes to human-readable language names for Microsoft Translator.

### Supported Languages

| Code | Name | Code | Name | Code | Name |
|------|------|------|------|------|------|
| `af` | Afrikaans | `am` | Amharic | `ar` | Arabic |
| `as` | Assamese | `az` | Azerbaijani | `ba` | Bashkir |
| `be` | Belarusian | `bg` | Bulgarian | `bho` | Bhojpuri |
| `bn` | Bangla | `bo` | Tibetan | `brx` | Bodo |
| `bs` | Bosnian | `ca` | Catalan | `cs` | Czech |
| `cy` | Welsh | `da` | Danish | `de` | German |
| `doi` | Dogri | `dsb` | Lower Sorbian | `dv` | Divehi |
| `el` | Greek | `en` | English | `es` | Spanish |
| `es-mx` | Spanish (Mexico) | `et` | Estonian | `eu` | Basque |
| `fa` | Persian | `fi` | Finnish | `fil` | Filipino |
| `fj` | Fijian | `fo` | Faroese | `fr` | French |
| `fr-ca` | French (Canada) | `ga` | Irish | `gl` | Galician |
| `gom` | Konkani | `gu` | Gujarati | `ha` | Hausa |
| `he` | Hebrew | `hi` | Hindi | `hne` | Chhattisgarhi |
| `hr` | Croatian | `hsb` | Upper Sorbian | `ht` | Haitian Creole |
| `hu` | Hungarian | `hy` | Armenian | `id` | Indonesian |
| `ig` | Igbo | `ikt` | Inuinnaqtun | `is` | Icelandic |
| `it` | Italian | `iu` | Inuktitut | `iu-latn` | Inuktitut (Latin) |
| `ja` | Japanese | `ka` | Georgian | `kk` | Kazakh |
| `km` | Khmer | `kmr` | Kurdish (Northern) | `kn` | Kannada |
| `ko` | Korean | `ks` | Kashmiri | `ku` | Kurdish (Central) |
| `ky` | Kyrgyz | `lb` | Luxembourgish | `ln` | Lingala |
| `lo` | Lao | `lt` | Lithuanian | `lug` | Ganda |
| `lv` | Latvian | `lzh` | Chinese (Literary) | `mai` | Maithili |
| `mg` | Malagasy | `mi` | Māori | `mk` | Macedonian |
| `ml` | Malayalam | `mn-cyrl` | Mongolian (Cyrillic) | `mn-mong` | Mongolian (Traditional) |
| `mni` | Manipuri | `mr` | Marathi | `ms` | Malay |
| `mt` | Maltese | `mww` | Hmong Daw | `my` | Myanmar (Burmese) |
| `nb` | Norwegian | `ne` | Nepali | `nl` | Dutch |
| `nso` | Sesotho sa Leboa | `nya` | Nyanja | `or` | Odia |
| `otq` | Querétaro Otomi | `pa` | Punjabi | `pl` | Polish |
| `prs` | Dari | `ps` | Pashto | `pt` | Portuguese (Brazil) |
| `pt-pt` | Portuguese (Portugal) | `ro` | Romanian | `ru` | Russian |
| `run` | Rundi | `rw` | Kinyarwanda | `sd` | Sindhi |
| `si` | Sinhala | `sk` | Slovak | `sl` | Slovenian |
| `sm` | Samoan | `sn` | Shona | `so` | Somali |
| `sq` | Albanian | `sr-cyrl` | Serbian (Cyrillic) | `sr-latn` | Serbian (Latin) |
| `st` | Sesotho | `sv` | Swedish | `sw` | Swahili |
| `ta` | Tamil | `te` | Telugu | `th` | Thai |
| `ti` | Tigrinya | `tk` | Turkmen | `tlh-latn` | Klingon (Latin) |
| `tlh-piqd` | Klingon (pIqaD) | `tn` | Setswana | `to` | Tongan |
| `tr` | Turkish | `tt` | Tatar | `ty` | Tahitian |
| `ug` | Uyghur | `uk` | Ukrainian | `ur` | Urdu |
| `uz` | Uzbek (Latin) | `vi` | Vietnamese | `xh` | Xhosa |
| `yo` | Yoruba | `yua` | Yucatec Maya | `yue` | Cantonese (Traditional) |
| `zh-hans` | Chinese Simplified | `zh-hant` | Chinese Traditional | `zu` | Zulu |

---

## Provider: `libretranslate`

**Type:** `object` (empty)

```json
"libretranslate": {}
```

Currently empty. Populated at runtime or by the cache generation process.

---

## Provider: `papago`

**Type:** `array` of `string`

List of lowercase language codes supported by Papago (Naver).

### Supported Language Codes

```
"de", "en", "es", "fr", "id", "it", "ja", "ko",
"ru", "th", "vi", "zh-cn", "zh-tw"
```

| Code | Language |
|------|----------|
| `de` | German |
| `en` | English |
| `es` | Spanish |
| `fr` | French |
| `id` | Indonesian |
| `it` | Italian |
| `ja` | Japanese |
| `ko` | Korean |
| `ru` | Russian |
| `th` | Thai |
| `vi` | Vietnamese |
| `zh-cn` | Chinese Simplified |
| `zh-tw` | Chinese Traditional |

---

## Provider: `mymemory_iso_639_1`

**Type:** `array` of `string`

Complete list of ISO 639-1 language codes supported by MyMemory.

### Supported Language Codes

```
aa, ab, ae, af, ak, am, an, ar, as, av, ay, az, ba, be, bg, bh, bi, bm, bn,
bo, br, bs, ca, ce, ch, co, cr, cs, cu, cv, cy, da, de, dv, dz, ee, el, en,
eo, es, et, eu, fa, ff, fi, fj, fo, fr, fy, ga, gd, gl, gn, gu, gv, ha, he,
hi, ho, hr, ht, hu, hy, hz, ia, id, ie, ig, ii, ik, io, is, it, iu, ja, jv,
ka, kg, ki, kj, kk, kl, km, kn, ko, kr, ks, kv, kw, ky, la, lb, lg, li, ln,
lo, lt, lu, lv, mg, mh, mi, mk, ml, mn, mr, ms, mt, my, na, nb, nd, ne, ng,
nl, nn, no, nr, nv, ny, oc, oj, om, or, os, pa, pi, pl, ps, pt, qu, rm, rn,
ro, ru, rw, sa, sc, sd, se, sg, si, sk, sl, sm, sn, so, sq, sr, ss, st, su,
sv, sw, ta, te, tg, th, ti, tk, tl, tn, to, tr, ts, tt, tw, ty, ug, uk, ur,
uz, ve, vi, vo, wa, wo, xh, yi, yo, za, zh, zu
```

| Code | Language | Code | Language | Code | Language |
|------|----------|------|----------|------|----------|
| `aa` | Afar | `ab` | Abkhazian | `ae` | Avestan |
| `af` | Afrikaans | `ak` | Akan | `am` | Amharic |
| `an` | Aragonese | `ar` | Arabic | `as` | Assamese |
| `av` | Avaric | `ay` | Aymara | `az` | Azerbaijani |
| `ba` | Bashkir | `be` | Belarusian | `bg` | Bulgarian |
| `bh` | Bihari languages | `bi` | Bislama | `bm` | Bambara |
| `bn` | Bengali | `bo` | Tibetan | `br` | Breton |
| `bs` | Bosnian | `ca` | Catalan | `ce` | Chechen |
| `ch` | Chamorro | `co` | Corsican | `cr` | Cree |
| `cs` | Czech | `cu` | Church Slavic | `cv` | Chuvash |
| `cy` | Welsh | `da` | Danish | `de` | German |
| `dv` | Divehi | `dz` | Dzongkha | `ee` | Ewe |
| `el` | Greek | `en` | English | `eo` | Esperanto |
| `es` | Spanish | `et` | Estonian | `eu` | Basque |
| `fa` | Persian | `ff` | Fulah | `fi` | Finnish |
| `fj` | Fijian | `fo` | Faroese | `fr` | French |
| `fy` | Western Frisian | `ga` | Irish | `gd` | Scottish Gaelic |
| `gl` | Galician | `gn` | Guarani | `gu` | Gujarati |
| `gv` | Manx | `ha` | Hausa | `he` | Hebrew |
| `hi` | Hindi | `ho` | Hiri Motu | `hr` | Croatian |
| `ht` | Haitian Creole | `hu` | Hungarian | `hy` | Armenian |
| `hz` | Herero | `ia` | Interlingua | `id` | Indonesian |
| `ie` | Interlingue | `ig` | Igbo | `ii` | Sichuan Yi |
| `ik` | Inupiaq | `io` | Ido | `is` | Icelandic |
| `it` | Italian | `iu` | Inuktitut | `ja` | Japanese |
| `jv` | Javanese | `ka` | Georgian | `kg` | Kongo |
| `ki` | Kikuyu | `kj` | Kuanyama | `kk` | Kazakh |
| `kl` | Kalaallisut | `km` | Khmer | `kn` | Kannada |
| `ko` | Korean | `kr` | Kanuri | `ks` | Kashmiri |
| `kv` | Komi | `kw` | Cornish | `ky` | Kyrgyz |
| `la` | Latin | `lb` | Luxembourgish | `lg` | Ganda |
| `li` | Limburgan | `ln` | Lingala | `lo` | Lao |
| `lt` | Lithuanian | `lu` | Luba-Katanga | `lv` | Latvian |
| `mg` | Malagasy | `mh` | Marshallese | `mi` | Māori |
| `mk` | Macedonian | `ml` | Malayalam | `mn` | Mongolian |
| `mr` | Marathi | `ms` | Malay | `mt` | Maltese |
| `my` | Burmese | `na` | Nauru | `nb` | Norwegian Bokmål |
| `nd` | North Ndebele | `ne` | Nepali | `ng` | Ndonga |
| `nl` | Dutch | `nn` | Norwegian Nynorsk | `no` | Norwegian |
| `nr` | South Ndebele | `nv` | Navajo | `ny` | Nyanja |
| `oc` | Occitan | `oj` | Ojibwa | `om` | Oromo |
| `or` | Oriya | `os` | Ossetian | `pa` | Punjabi |
| `pi` | Pali | `pl` | Polish | `ps` | Pashto |
| `pt` | Portuguese | `qu` | Quechua | `rm` | Romansh |
| `rn` | Rundi | `ro` | Romanian | `ru` | Russian |
| `rw` | Kinyarwanda | `sa` | Sanskrit | `sc` | Sardinian |
| `sd` | Sindhi | `se` | Northern Sami | `sg` | Sango |
| `si` | Sinhala | `sk` | Slovak | `sl` | Slovenian |
| `sm` | Samoan | `sn` | Shona | `so` | Somali |
| `sq` | Albanian | `sr` | Serbian | `ss` | Swati |
| `st` | Southern Sotho | `su` | Sundanese | `sv` | Swedish |
| `sw` | Swahili | `ta` | Tamil | `te` | Telugu |
| `tg` | Tajik | `th` | Thai | `ti` | Tigrinya |
| `tk` | Turkmen | `tl` | Tagalog | `tn` | Tswana |
| `to` | Tonga | `tr` | Turkish | `ts` | Tsonga |
| `tt` | Tatar | `tw` | Twi | `ty` | Tahitian |
| `ug` | Uyghur | `uk` | Ukrainian | `ur` | Urdu |
| `uz` | Uzbek | `ve` | Venda | `vi` | Vietnamese |
| `vo` | Volapük | `wa` | Walloon | `wo` | Wolof |
| `xh` | Xhosa | `yi` | Yiddish | `yo` | Yoruba |
| `za` | Zhuang | `zh` | Chinese | `zu` | Zulu |

---

## Usage in SHL

This data file is consumed by the `provider_cache.py` module via `load_cache()`. The router uses it to:

1. Determine which providers support a given language pair.
2. Build the provider priority list in `get_provider_priority()`.
3. Validate language availability before making API calls.

The cache can be regenerated at runtime by calling `generate_cache()`, which fetches fresh data from Microsoft Translator and LibreTranslate APIs while preserving the static Papago and MyMemory data.
