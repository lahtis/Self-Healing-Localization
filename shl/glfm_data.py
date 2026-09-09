import os
import gzip
import json
from typing import Dict, List, Optional, Tuple

# ------------------------------------------------
# 1. Lataa master-kanta ja cache muistiin
# ------------------------------------------------

def load_master_db(path: str = "data/languages_top20.json.gz") -> Dict:
    """Lataa master-kannan gzipatusta JSON-tiedostosta."""
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)

def load_cache() -> Dict:
    """
    Lukee olemassa olevan .languages_cache.json -tiedoston.
    Etsii nykyisestä hakemistosta, ylemmältä tasolta ja skriptin hakemistosta.
    Jos tiedostoa ei löydy, palauttaa tyhjän sanakirjan (ei luo uutta tiedostoa).
    """
    possible_paths = [
        ".languages_cache.json",
        "../.languages_cache.json",
        os.path.join(os.path.dirname(__file__), ".languages_cache.json"),
        os.path.join(os.path.dirname(__file__), "..", ".languages_cache.json"),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    
    print("VAROITUS: .languages_cache.json -tiedostoa ei löytynyt. Palautetaan tyhjä cache.")
    return {"providers": {}, "last_updated": None}

# Ladataan tiedot
MASTER_DB = load_master_db()
CACHE = load_cache()

# ------------------------------------------------
# 2. Normalisointi: käyttäjän syöte → BCP 47
# ------------------------------------------------

def normalize_to_bcp47(user_code: str, master_db: Dict) -> Tuple[str, Dict]:
    """
    Muuntaa käyttäjän syöttämän kielikoodin BCP 47 -muotoon.
    Palauttaa (bcp47_koodi, master_tietue). 
    Jos master-tietuetta ei löydy, palautetaan tyhjä sanakirja,
    mutta bcp47-koodi on kelvollinen (esim. "zh-Hant-TW").
    """
    user_code = user_code.strip().lower()
    
    # 1) Suora osuma master-avaimella
    if user_code in master_db:
        data = master_db[user_code]
        return data.get("bcp47", user_code), data
    
    # 2) Synonyymit (laajennettu)
    synonyms = {
        "zh": "zh-Hans-CN",
        "zh-cn": "zh-Hans-CN",
        "zh-tw": "zh-Hant-TW",
        "zh-hans": "zh-Hans-CN",
        "zh-hant": "zh-Hant-TW",
        "yue": "yue-Hant-HK",
        "sr": "sr-Cyrl-RS",
        "az": "az-Latn-AZ",
        "en": "en-Latn-US",
        "fi": "fi-Latn-FI",
        "sv": "sv-Latn-SE",
        "de": "de-Latn-DE",
        "fr": "fr-Latn-FR",
        "es": "es-Latn-ES",
        "it": "it-Latn-IT",
        "ru": "ru-Cyrl-RU",
        "ja": "ja-Jpan-JP",
        "ko": "ko-Kore-KR",
    }
    if user_code in synonyms:
        target_bcp = synonyms[user_code]
        # Etsi masterista tietue, jonka bcp47 on target_bcp
        for key, data in master_db.items():
            if data.get("bcp47") == target_bcp:
                return target_bcp, data
        # Jos ei löydy masterista, palautetaan silti BCP 47 -koodi (ilman master-tietuetta)
        return target_bcp, {}
    
    # 3) Kokeile pelkkää kieliosaa
    lang_part = user_code.split("-")[0]
    for key, data in master_db.items():
        if key.startswith(lang_part + "-") or key == lang_part:
            return data.get("bcp47", key), data
    
    # 4) Kokeile iso639_1 tai iso639_3
    for key, data in master_db.items():
        if data.get("iso639_1", "").lower() == user_code:
            return data.get("bcp47", key), data
        if data.get("iso639_3", "").lower() == user_code:
            return data.get("bcp47", key), data
    
    raise ValueError(f"Tuntematon kielikoodi: {user_code}")

# ------------------------------------------------
# 3. Automaattinen vastinehaku cachen perusteella
# ------------------------------------------------

def find_best_match(bcp47: str, provider: str, cache: Dict) -> Optional[str]:
    """
    Palauttaa parhaan mahdollisen koodin, jonka provider tukee.
    """
    supported = cache["providers"].get(provider)
    if not supported:
        return None
    
    if isinstance(supported, dict):
        supported_codes = list(supported.keys())
    elif isinstance(supported, list):
        supported_codes = supported
    else:
        return None
    
    # 1) Tarkka osuma
    if bcp47 in supported_codes:
        return bcp47
    
    # 2) Puretaan BCP 47 osiin
    parts = bcp47.split("-")
    lang = parts[0]
    
    script = None
    region = None
    for p in parts[1:]:
        if p in ["Hans", "Hant", "Latn", "Cyrl", "Jpan", "Kore", "Arab", "Deva", "Beng", "Grek", "Hang", "Thai", "Hebr", "Taml"]:
            script = p
        elif len(p) == 2 and p.isupper():
            region = p
    
    # 3) Muodostetaan ehdokkaat
    candidates = []
    
    if script and region:
        candidates.append(f"{script}-{region}")
        candidates.append(f"{lang}-{script}-{region}")
    if script:
        candidates.append(script)
        candidates.append(script.lower())
        candidates.append(f"{lang}-{script}")
        candidates.append(f"{lang}-{script.lower()}")
    if region:
        candidates.append(region)
        candidates.append(region.lower())
        candidates.append(f"{lang}-{region}")
        candidates.append(f"{lang}-{region.lower()}")
    candidates.append(lang)
    
    for cand in candidates:
        if cand in supported_codes:
            return cand
    
    return None

# ------------------------------------------------
# 4. Palvelukonfiguraatio
# ------------------------------------------------

def load_service_config() -> Dict:
    """Lukee palvelukonfiguraation (shl-policy-config.json)."""
    possible_paths = [
        "../shl-policy-config.json",
        os.path.join(os.path.dirname(__file__), "..", "shl-policy-config.json"),
    ]
    for path in possible_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError("Palvelukonfiguraatiota ei löytynyt.")

SERVICE_CONFIG = load_service_config()

def get_active_services(config: Dict) -> List[Tuple[str, Dict]]:
    """Palauttaa aktiiviset palvelut prioriteetin mukaan lajiteltuna."""
    active = [
        (name, data)
        for name, data in config.items()
        if data.get("enabled", False)
    ]
    active.sort(key=lambda x: x[1].get("priority", 999))
    return active

# ------------------------------------------------
# 5. Kartta konfiguraation nimistä cachen avaimiksi
# ------------------------------------------------

PROVIDER_TO_CACHE_KEY = {
    "MyMemory": "mymemory",
    "DeepL": "deepl",
    "LibreTranslate": "libretranslate",
    "Papago": "papago",
    "Google": "google_translate",
    "MicrosoftTranslator": "microsoft_translator",
    "Yandex": "yandex",
    "Local": "local",
}

# ------------------------------------------------
# 6. API-kutsujen abstraktio (mock)
# ------------------------------------------------

def call_api(provider_name: str, text: str, lang_code: str, cache_key: str) -> str:
    """Mock API-kutsu. Korvaa oikealla toteutuksella."""
    if cache_key == "deepl":
        return f"[DeepL] Käännös kielelle {lang_code}: {text}"
    elif cache_key == "mymemory":
        return f"[MyMemory] Käännös kielelle {lang_code}: {text}"
    elif cache_key == "microsoft_translator":
        return f"[Microsoft] Käännös kielelle {lang_code}: {text}"
    elif cache_key == "papago":
        return f"[Papago] Käännös kielelle {lang_code}: {text}"
    elif cache_key == "libretranslate":
        return f"[LibreTranslate] Käännös kielelle {lang_code}: {text}"
    else:
        raise NotImplementedError(f"Tuntematon cache-avain: {cache_key}")

# ------------------------------------------------
# 7. Pääfunktio: käännä teksti
# ------------------------------------------------

def translate(text: str, user_lang_code: str) -> str:
    try:
        bcp47, _ = normalize_to_bcp47(user_lang_code, MASTER_DB)
    except ValueError as e:
        return f"Virhe: {e}"
    
    active_services = get_active_services(SERVICE_CONFIG)
    if not active_services:
        return "Virhe: Yhtään käännöspalvelua ei ole käytössä."
    
    last_error = None
    for provider_name, provider_config in active_services:
        cache_key = PROVIDER_TO_CACHE_KEY.get(provider_name)
        if not cache_key:
            continue
        
        service_code = find_best_match(bcp47, cache_key, CACHE)
        if not service_code:
            continue
        
        try:
            result = call_api(provider_name, text, service_code, cache_key)
            return result
        except Exception as e:
            last_error = e
            continue
    
    return f"Virhe: Kaikki käännöspalvelut epäonnistuivat. Viimeisin virhe: {last_error}"

# ------------------------------------------------
# 8. Esimerkkiajo
# ------------------------------------------------

if __name__ == "__main__":
    test_cases = [
        ("Hello world", "en"),
        ("Moi maailma", "fi"),
        ("你好世界", "zh-cn"),
        ("你好世界", "zh-tw"),
        ("世界你好", "yue"),
        ("Свет", "sr"),
        ("Salam", "az"),
        ("Привет, мир!",  "ru"),
        ("Tuntematon kieli", "xyz"),
    ]
    
    for text, lang in test_cases:
        print(f"\n--- Käännös: {text} -> {lang} ---")
        result = translate(text, lang)
        print(result)
