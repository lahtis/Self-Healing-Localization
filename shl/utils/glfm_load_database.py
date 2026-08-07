import gzip
import json
from pathlib import Path

# Polku SHL-paketin sisäiseen tiivistettyyn dataan
DATA_PATH = Path(__file__).resolve().parent / "data" / "languages_top5.json.gz"


def load_language_data(db_path: Path = DATA_PATH) -> dict:
    """Lataa GLFM-kielitietokannan lennossa muistiin.

    Käyttää Pythonin vakiokirjastoa (gzip + json), joten ulkoisia
    riippuvuuksia ei tarvita.
    """
    if not db_path.exists():
        raise FileNotFoundError(
            f"SHL-kielitietokantaa ei löytynyt polusta: {db_path}"
        )

    with gzip.open(db_path, "rt", encoding="utf-8") as f:
        return json.load(f)
