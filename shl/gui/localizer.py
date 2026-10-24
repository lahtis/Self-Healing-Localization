"""Read-only gettext-style localizer for SHL 2.0.

This class only reads pre-built JSON files. It never translates,
never saves, never writes. Building the JSON files is the job of
shl.gui.preload.preload().
"""
import json
import os
from typing import Dict, Optional

from shl.gui.paths import Paths


class GuiLocalizer:
    """Pure reader. No save, no translate. gettext-style L()."""

    def __init__(self, app_name: str, lang_code: str = "en"):
        self.app_name = app_name
        self.lang_code = lang_code
        self.locales_dir = Paths.app_locales_dir(app_name)
        self.lang_file = self.locales_dir / f"{lang_code}.json"
        self.texts: Dict[str, str] = self._load()

    def _load(self) -> Dict[str, str]:
        if not self.lang_file.exists():
            return {}
        try:
            with open(self.lang_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return {}
            return {str(k): str(v) for k, v in data.items() if v is not None}
        except (OSError, json.JSONDecodeError):
            return {}

    def L(self, key: str, default: str = "") -> str:
        """gettext-style lookup. Returns key or default when missing."""
        if not key:
            return default or ""
        value = self.texts.get(key)
        if value is None:
            return default or key
        return value

    def get(self, key: str, default: str = "") -> str:
        return self.L(key, default)

    def has_key(self, key: str) -> bool:
        return key in self.texts

    def keys(self):
        return list(self.texts.keys())

    def __contains__(self, key: str) -> bool:
        return self.has_key(key)

    def __getitem__(self, key: str) -> str:
        return self.L(key)

    def __len__(self) -> int:
        return len(self.texts)

    def __repr__(self) -> str:
        return f"GuiLocalizer(app={self.app_name!r}, lang={self.lang_code!r}, keys={len(self.texts)})"

    def set_language(self, lang_code: str) -> None:
        """Switch active language and reload texts."""
        if lang_code == self.lang_code:
            return
        self.lang_code = lang_code
        self.lang_file = self.locales_dir / f"{lang_code}.json"
        self.texts = self._load()
