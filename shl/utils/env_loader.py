# shl/utils/env_loader.py

import os
import logging
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)

_env_loaded = False


def load_dotenv_file(env_file: Path) -> bool:
    """
    Load .env file manually without external dependencies.
    
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
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse KEY=value
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    # Set environment variable
                    os.environ[key] = value
                    
        return True
    
    except Exception as e:
        logger.error(f"Failed to load .env file {env_file}: {e}")
        return False


def load_shl_env(force: bool = False) -> bool:
    """Load .env from ./.env/shl/ directory."""
    global _env_loaded
    
    if _env_loaded and not force:
        logger.debug("SHL environment already loaded")
        return True
    
    env_file = Path.cwd() / ".env" / "shl" / ".env"
    
    if env_file.exists():
        loaded = load_dotenv_file(env_file)
        if loaded:
            _env_loaded = True
            logger.debug(f"Loaded environment from {env_file}")
            return True
    
    # Fallback: project root .env
    root_env = Path.cwd() / ".env"
    if root_env.exists():
        loaded = load_dotenv_file(root_env)
        if loaded:
            _env_loaded = True
            logger.debug(f"Loaded environment from {root_env} (fallback)")
            return True
    
    logger.debug("No .env file found")
    _env_loaded = True
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
    
    return key_str[:4] + "*" * (len(key_str) - 8) + key_str[-4:]


def get_env_value(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable value."""
    load_shl_env()
    return os.getenv(key, default)


def get_env_value_masked(key: str, default: Optional[str] = None) -> str:
    """Get masked environment variable value."""
    value = get_env_value(key, default)
    return mask_api_key(value)


def get_env_file_path() -> Path:
    """Return the path to the SHL .env file."""
    return Path.cwd() / ".env" / "shl" / ".env"


def is_env_loaded() -> bool:
    """Check if SHL environment has been loaded."""
    global _env_loaded
    return _env_loaded


def reset_env_loader() -> None:
    """Reset environment loader state."""
    global _env_loaded
    _env_loaded = False
    logger.debug("Environment loader reset")
