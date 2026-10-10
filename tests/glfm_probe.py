"""Probe how GLFM and LanguageParser resolve script/region variants.

Run from the repo root (put this file in tests/):

    python3 -m tests.glfm_probe

Makes no network calls and uses no API quota.
"""

import gzip
import json
import sys
from pathlib import Path

from shl.language_validator import LanguageValidator
from shl.language_parser import LanguageParser

# Raw GLFM database. Override with: python3 -m tests.glfm_probe PATH
DEFAULT_DB = "output/unified/languages_top20.json.gz"

INPUTS = [
    # Chinese: bare, region, script, script+region, other ISO codes
    "zh", "zh-TW", "zh-HK", "zh-CN", "zh-SG", "zh-MO",
    "zh-Hant", "zh-Hans", "zh-Hant-TW", "zh-Hans-CN",
    "zho", "cmn", "cmn-Hant", "zho-Hant", "yue", "lzh",
    # Other multi-script languages
    "sr", "sr-Latn", "sr-Cyrl", "uz-Cyrl", "uz-Latn",
    # Control cases that should keep working
    "en-GB", "pt-BR", "fi", "fi-FI",
]

PROVIDERS = ["deepl", "microsoft", "libretranslate", "yandex"]

FIELDS = (
    "id", "iso639_1", "iso639_3", "bcp47",
    "default_region", "default_script", "written_scripts", "name",
)


def short(info):
    if not info:
        return None
    return {k: info.get(k) for k in FIELDS}


def raw_database(path: str) -> None:
    """Inspect the GLFM .json.gz directly, bypassing the validator."""
    print(f"=== Raw GLFM database: {path} ===")
    db_path = Path(path)
    if not db_path.exists():
        print("NOT FOUND - pass the path as an argument")
        return

    with gzip.open(db_path, "rt", encoding="utf-8") as f:
        db = json.load(f)

    print(f"records: {len(db)}")

    print("\n--- Chinese-related and multi-script ids ---")
    for lid in ("zho", "cmn", "yue", "lzh", "wuu", "hak", "nan",
                "srp", "uzb", "mon"):
        rec = db.get(lid)
        print(f"{lid}: {short(rec) if rec else 'not in database'}")

    print("\n--- Records whose bcp47 mentions Hant/Hans or region TW/HK ---")
    hits = 0
    for lid, rec in db.items():
        tag = str(rec.get("bcp47", ""))
        if any(s in tag for s in ("Hant", "Hans", "-TW", "-HK", "-MO")):
            print(f"{lid}: {short(rec)}")
            hits += 1
            if hits >= 20:
                print("... (truncated at 20)")
                break
    if not hits:
        print("none")

    print("\n--- Records with more than one written script (first 15) ---")
    multi = [
        (lid, rec.get("written_scripts"))
        for lid, rec in db.items()
        if isinstance(rec.get("written_scripts"), list)
        and len(rec["written_scripts"]) > 1
    ]
    print(f"count: {len(multi)}")
    for lid, scripts in multi[:15]:
        print(f"{lid}: {scripts}")

    print("\n--- All distinct top-level keys across records ---")
    keys = set()
    for rec in db.values():
        keys.update(rec.keys())
    print(sorted(keys))


def main() -> None:
    raw_database(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB)
    print()

    v = LanguageValidator()
    p = LanguageParser(validator=v)

    print("=== LanguageValidator public attributes ===")
    print([a for a in dir(v) if not a.startswith("_")])

    print("\n=== Full key list of the zh record ===")
    zh = v.get_language_info("zh")
    print(sorted(zh.keys()) if zh else None)

    print("\n=== Any key mentioning script/region/variant/likely in zh record ===")
    if zh:
        for k, val in zh.items():
            if any(w in k.lower() for w in ("script", "region", "variant", "likely", "alias")):
                print(f"{k}: {val}")

    print("\n=== get_language_info(input) ===")
    for x in INPUTS:
        try:
            print(f"{x:11} -> {short(v.get_language_info(x))}")
        except Exception as exc:
            print(f"{x:11} -> ERROR {type(exc).__name__}: {exc}")

    print("\n=== LanguageParser.parse(input) ===")
    for x in INPUTS:
        try:
            r = p.parse(x)
            print(
                f"{x:11} -> iso3={r.iso639_3} bcp47={r.bcp47} "
                f"script={r.script} region={r.region}"
            )
        except Exception as exc:
            print(f"{x:11} -> ERROR {type(exc).__name__}: {exc}")

    print("\n=== get_provider_code(input, provider) ===")
    print(f"{'input':11} " + " ".join(f"{pr:15}" for pr in PROVIDERS))
    for x in INPUTS:
        row = []
        for pr in PROVIDERS:
            try:
                row.append(str(p.get_provider_code(x, pr)))
            except Exception as exc:
                row.append(f"ERR:{type(exc).__name__}")
        print(f"{x:11} " + " ".join(f"{c:15}" for c in row))


if __name__ == "__main__":
    main()
