Käyttö

Peruskäyttö – kirjoita base-tiedosto:
bash

shl-extract extract src/ --output locales/en.json

Raportti interaktiivisesti:
bash

shl-extract extract src/

Tulostaa:
text

SHL extraction report
=====================

Files scanned:     24
Keys found:        42
  with default:    42
  without default: 0

Function usage:
  ui_text                38
  template                4

Dynamic calls (cannot be extracted): 3
  src/main.py:142  L(...)  [f-string]
  src/dialog.py:88  L(...)  [variable 'msg']
  src/utils.py:12  L(...)  [concatenation]

Lista putkeen:
bash

shl-extract list src/ | wc -l

CI-tarkistus:
bash

shl-extract check src/ --locales locales/ --base en

Tulostaa:
text

SHL locale check
================

Missing from base locale (4):
  ui.archive
  ui.restore
  error.not_found
  error.permission_denied

Language coverage:
  lang       total   done  missing  empty  stale      %
  de            42     20       22      0      5   47.6%
  en            42     42        0      0      0  100.0%
  fi            42     38        4      0      0   90.5%
  sv            42     35        7      0      2   83.3%

Tiukka CI-tarkistus:
bash

shl-extract check src/ --locales locales/ --strict

Epäonnistuu myös jos on vanhentuneita avaimia tai ristiriitaisia oletuksia.

Koneparsittava JSON:
bash

shl-extract check src/ --locales locales/ --json

Mitä tämä tekee ja mitä ei

Tekee:

    Löytää ui_text(...), L(...), get_text(...), template(...), ensure_ui_key(...), ensure_template_key(...)

    Tukee ast.Attribute-muotoa (engine.ui_text, self.localizer.L)

    Tukee key= ja default= / default_value= avainsanoja

    Raportoi dynaamiset kutsut syineen ("f-string", "variable 'x'")

    Vertaa locale-tiedostoja lähdekoodiin

    Raportoi kielikohtainen kattavuus

    Toimii CI:ssä selkeillä exit-koodeilla

    Ei aja koodia, ei importtaa mitään

Ei tee:

    Ymmärrä f"key_{var}" – raportoi dynaamisena

    Ymmärrä key = "x"; ui_text(key) – raportoi dynaamisena

    Ymmärrä ui_text("a" + "b") – raportoi dynaamisena

    Ymmärrä **kwargs-kutsuja

    Tue monikkomuotoja (vielä)

    Tue kontekstitageja (vielä)

Nämä ovat AST:n perusrajoituksia. Sama koskee xgettext-työkaluja. Ja ne on dokumentoitu dynaamisten kutsujen raportissa – käyttäjä tietää mitä ei löytynyt.
