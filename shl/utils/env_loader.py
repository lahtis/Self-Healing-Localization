"""
File: shl/utils/env_loader.py - Load .env file
Author: Tuomas Lähteenmäki
Version: 0.2.6
License: MIT
Description: Dependency-free SHL environment loader.
             Loads .env values from the SHL-specific environment file or the project root fallback.
             Supports hot reload controlled by SHL config.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from shl.config import get_config_value

logger = logging.getLogger(__name__)

_env_loaded = False
_env_mtime: float = 0.0
_env_path: Optional[Path] = None


def load_dotenv_file(env_file: Path) -> bool:
    """
    Load a .env file manually without external dependencies.

    Supports:
    - KEY=value
    - KEY="value"
    - KEY='value'
    - # comments
    - empty lines
    """
    if not env_file.exists():
        return False

    try:
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                if not line or line.startswith("#"):
                    continue

                if "=" not in line:
                    continue

                key, value = line.split("=", 1)

                key = key.strip()
                value = value.strip()

                if not key:
                    continue

                if (
                    len(value) >= 2
                    and value[0] == value[-1]
                    and value[0] in ('"', "'")
                ):
                    value = value[1:-1]

                os.environ[key] = value

        return True

    except OSError as exc:
        logger.error(
            "Failed to load .env file %s: %s",
            env_file,
            exc,
        )
        return False


def get_env_file_path() -> Path:
    """
    Return the preferred SHL .env file path.

    The SHL-specific file is preferred over the project root .env.
    """
    shl_env = Path.cwd() / ".env" / "shl" / ".env"

    if shl_env.exists():
        return shl_env

    return Path.cwd() / ".env"


def _get_reload_settings() -> tuple[bool, float]:
    """Return environment reload settings from SHL configuration."""
    enabled = bool(
        get_config_value(
            "reload.enabled",
            True,
        )
    )

    interval = get_config_value(
        "reload.check_interval",
        1.0,
    )

    try:
        interval = max(float(interval), 0.1)
    except (TypeError, ValueError):
        interval = 1.0

    return enabled, interval


def load_shl_env(force: bool = False) -> bool:
    """
    Load the SHL environment.

    The SHL-specific .env file is preferred. The project root .env
    is used as a fallback.

    When hot reload is enabled, changes to the selected .env file
    are detected automatically.
    """
    global _env_loaded
    global _env_mtime
    global _env_path

    env_file = get_env_file_path()

    if not env_file.exists():
        logger.debug("No .env file found")

        _env_loaded = True
        _env_path = env_file
        _env_mtime = 0.0

        return False

    try:
        mtime = env_file.stat().st_mtime

    except OSError as exc:
        logger.error(
            "Failed to access .env file %s: %s",
            env_file,
            exc,
        )
        return False

    enabled, _ = _get_reload_settings()

    if (
        not force
        and _env_loaded
        and _env_path == env_file
        and mtime <= _env_mtime
    ):
        return True

    if not force and not enabled and _env_loaded:
        return True

    loaded = load_dotenv_file(env_file)

    if loaded:
        _env_loaded = True
        _env_path = env_file
        _env_mtime = mtime

        logger.debug(
            "Loaded environment from %s",
            env_file,
        )

        return True

    return False


def mask_api_key(key: Optional[str]) -> str:
    """Mask API key for safe logging."""
    if not key:
        return "(not set)"

    key_str = str(key).strip()

    if not key_str:
        return "(not set)"

    if len(key_str) <= 8:
        return "*" * len(key_str)

    return (
        key_str[:4]
        + "*" * (len(key_str) - 8)
        + key_str[-4:]
    )


def get_env_value(
    key: str,
    default: Optional[str] = None,
) -> Optional[str]:
    """
    Get an environment variable value.

    Automatically checks whether the .env file has changed.
    """
    load_shl_env()

    return os.getenv(key, default)


def get_env_value_masked(
    key: str,
    default: Optional[str] = None,
) -> str:
    """Get a masked environment variable value."""
    value = get_env_value(key, default)

    return mask_api_key(value)


def is_env_loaded() -> bool:
    """Return whether the SHL environment has been loaded."""
    return _env_loaded


def reset_env_loader() -> None:
    """Reset the environment loader state."""
    global _env_loaded
    global _env_mtime
    global _env_path

    _env_loaded = False
    _env_mtime = 0.0
    _env_path = None

    logger.debug("Environment loader reset")
