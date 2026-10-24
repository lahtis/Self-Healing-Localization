"""Centralized path resolution for SHL 2.0.

Application-specific files live under ~/.config/<app_name>/.
SHL-wide paths are handled by their own modules:
    - config.py     -> ~/.config/shl/config.json
    - policy_manager.py -> ~/.config/shl/shl-policy-config.json
    - env_loader.py -> ~/.config/shl/.env
    - cache.py      -> ~/.cache/shl/shl_cache.json
"""
from pathlib import Path


class Paths:
    """Resolve application-specific paths used by SHL 2.0."""

    @staticmethod
    def app_config_dir(app_name: str) -> Path:
        return Path.home() / ".config" / app_name

    @staticmethod
    def app_config_file(app_name: str) -> Path:
        return Paths.app_config_dir(app_name) / "config.json"

    @staticmethod
    def app_locales_dir(app_name: str) -> Path:
        return Paths.app_config_dir(app_name) / "locales"

    @staticmethod
    def app_lang_file(app_name: str, lang_code: str) -> Path:
        return Paths.app_locales_dir(app_name) / f"{lang_code}.json"

    @staticmethod
    def ensure_app_dirs(app_name: str) -> None:
        """Create application-specific directories."""
        Paths.app_config_dir(app_name).mkdir(parents=True, exist_ok=True)
        Paths.app_locales_dir(app_name).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def ensure_all(app_name: str) -> None:
        """Create application-specific directories.

        SHL-wide directories are created by their own modules when needed.
        """
        Paths.ensure_app_dirs(app_name)
