"""Application-specific configuration for SHL 2.0."""
import json
from typing import Any, Dict

from shl.gui.paths import Paths


class AppConfig:
    """Application-specific settings (language, theme, etc.)."""

    DEFAULT_DATA: Dict[str, Any] = {
        "language": "en",
        "base_lang": "en",
    }

    def __init__(self, app_name: str):
        self.app_name = app_name
        self.path = Paths.app_config_file(app_name)
        Paths.ensure_app_dirs(app_name)
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            self._save(self.DEFAULT_DATA.copy())
            return self.DEFAULT_DATA.copy()
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            merged = self.DEFAULT_DATA.copy()
            merged.update(data)
            return merged
        except (OSError, json.JSONDecodeError):
            return self.DEFAULT_DATA.copy()

    def _save(self, data: Dict[str, Any]) -> bool:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".json.tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            tmp.replace(self.path)
            return True
        except OSError:
            return False

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def save(self) -> bool:
        return self._save(self.data)

    @property
    def language(self) -> str:
        return self.get("language", "en")

    @language.setter
    def language(self, value: str) -> None:
        self.set("language", value)

    @property
    def base_lang(self) -> str:
        return self.get("base_lang", "en")
