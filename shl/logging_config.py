"""
File: logging_config.py
Author: Tuomas Lähteenmäki
Version: 0.2.4
License: MIT
Description:
    Unified logging configuration for the Self-Healing Localization Layer.
    - Consistent log formatting across all modules
    - Console output for development
    - File output for errors (error.log)
    - Configurable log levels
    - Rotating file handler to prevent disk overflow
    - API key masking for secure logging
    
Usage:
    # Before anything else is run:
    from shl.logging_config import setup_logging
    setup_logging()
    
    # Then in modules:
    import logging
    logger = logging.getLogger(__name__)
    
    # Mask API keys in logs:
    from shl.logging_config import mask_api_key
    logger.debug(f"API key: {mask_api_key(api_key)}")
"""

import logging
import sys
import os
import glob
from logging.handlers import RotatingFileHandler
from typing import Optional, List, Dict, Any


# Default log levels
DEFAULT_CONSOLE_LEVEL = logging.INFO
DEFAULT_FILE_LEVEL = logging.WARNING
DEFAULT_LOG_FILE = "error.log"
DEFAULT_MAX_BYTES = 1 * 1024 * 1024  # 1 MB
DEFAULT_BACKUP_COUNT = 3

# Whether logging has been initialized
_logging_initialized = False

# Store active log file for stats
_active_log_files: List[str] = []


def mask_api_key(key: Optional[str]) -> str:
    """
    Mask API key for safe logging.

    Args:
        key: API key string or None

    Returns:
        Masked string:
        - "(not set)" if key is None or empty
        - "*****" if key is 8 characters or less
        - "abcd***********wxyz" for longer keys (first 4 + last 4 visible)

    Examples:
        >>> mask_api_key("my-secret-key-12345")
        'my-s*****************12345'
        >>> mask_api_key("short")
        '*****'
        >>> mask_api_key(None)
        '(not set)'
    """
    if not key:
        return "(not set)"

    key_str = str(key).strip()
    if not key_str:
        return "(not set)"

    if len(key_str) <= 8:
        return "*" * len(key_str)

    return key_str[:4] + "*" * (len(key_str) - 8) + key_str[-4:]


def setup_logging(
    console_level: int = DEFAULT_CONSOLE_LEVEL,
    file_level: int = DEFAULT_FILE_LEVEL,
    log_file: str = DEFAULT_LOG_FILE,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
    force: bool = False
) -> logging.Logger:
    """
    Configure unified logging for the entire SHL library.
    
    This is typically called once at application startup.
    To change settings later, use force=True.
    
    Args:
        console_level: Console output log level (default: INFO)
        file_level: File output log level (default: WARNING)
        log_file: Log file path (default: "error.log")
        max_bytes: Maximum file size before rotation (default: 1MB)
        backup_count: Number of old log files to keep (default: 3)
        force: Force re-initialization even if already initialized
    
    Returns:
        Root logger object
    
    Example:
        >>> setup_logging()
        >>> setup_logging(console_level=logging.DEBUG, force=True)
    """
    global _logging_initialized, _active_log_files
    
    if _logging_initialized and not force:
        return logging.getLogger()
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # All levels allowed, handlers filter
    
    # Remove old handlers (if force=True)
    if force:
        root_logger.handlers.clear()
        _active_log_files.clear()
    
    # === Console handler ===
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(logging.Formatter(
        '%(levelname)-8s [%(name)s] %(message)s'
    ))
    root_logger.addHandler(console_handler)
    
    # === File handler (error.log) ===
    try:
        # Ensure directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(file_level)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        root_logger.addHandler(file_handler)
        
        # Store active log file for stats
        if log_file not in _active_log_files:
            _active_log_files.append(log_file)
        
    except Exception as e:
        # If file handler creation fails, log to console
        root_logger.warning(f"Log file handler creation failed: {e}")
    
    # === SHL library logger levels ===
    
    # Set library-specific levels
    shl_logger = logging.getLogger('shl')
    shl_logger.setLevel(logging.DEBUG)
    
    # Quiet down external libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    _logging_initialized = True
    
    # Log initialization
    root_logger.info(
        f"SHL logging initialized (console={logging.getLevelName(console_level)}, "
        f"file={logging.getLevelName(file_level)}, path='{log_file}')"
    )
    
    return root_logger


def get_logger(
    name: str,
    add_shl_prefix: bool = True
) -> logging.Logger:
    """
    Return a logger for the named module.
    
    Args:
        name: Module name (typically __name__)
        add_shl_prefix: If True, ensure logger is in SHL namespace
    
    Returns:
        Logger object
    
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Message")
        >>> logger = get_logger("my_module", add_shl_prefix=False)
    """
    if add_shl_prefix and not name.startswith('shl'):
        name = f'shl.{name}'
    
    return logging.getLogger(name)


def set_level(
    level: int,
    logger_name: Optional[str] = None
) -> None:
    """
    Change log level on the fly.
    
    Args:
        level: New log level (e.g. logging.DEBUG)
        logger_name: Logger name (None = root)
    
    Example:
        >>> set_level(logging.DEBUG)
        >>> set_level(logging.WARNING, 'shl.engine.localizer')
    """
    logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
    logger.setLevel(level)
    logging.getLogger().info(f"Log level changed: {logging.getLevelName(level)}")


def remove_handler(
    handler_type: str,
    logger_name: Optional[str] = None
) -> int:
    """
    Remove handlers of a specific type from a logger.
    
    Args:
        handler_type: Handler class name (e.g., 'StreamHandler', 'RotatingFileHandler')
        logger_name: Logger name (None = root)
    
    Returns:
        Number of handlers removed
    
    Example:
        >>> remove_handler('StreamHandler')  # Remove console logging
        >>> remove_handler('RotatingFileHandler')  # Remove file logging
    """
    logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
    removed = 0
    handlers_to_remove = []
    
    for handler in logger.handlers:
        if handler.__class__.__name__ == handler_type:
            handlers_to_remove.append(handler)
    
    for handler in handlers_to_remove:
        logger.removeHandler(handler)
        removed += 1
        
        # Also remove from active log files if it's a file handler
        if handler_type == 'RotatingFileHandler':
            global _active_log_files
            if hasattr(handler, 'baseFilename'):
                filename = handler.baseFilename
                if filename in _active_log_files:
                    _active_log_files.remove(filename)
    
    if removed > 0:
        logging.getLogger().info(f"Removed {removed} {handler_type} handler(s)")
    
    return removed


def get_log_stats() -> Dict[str, Any]:
    """
    Return logging statistics.
    
    Returns:
        Dictionary with logging information
    
    Example:
        >>> stats = get_log_stats()
        >>> print(stats['log_files'])
    """
    stats: Dict[str, Any] = {
        'initialized': _logging_initialized,
        'handlers': len(logging.getLogger().handlers),
        'log_files': list(_active_log_files),
        'handler_types': [],
    }
    
    # Handler types
    for handler in logging.getLogger().handlers:
        stats['handler_types'].append(handler.__class__.__name__)
    
    # Check first active log file
    if _active_log_files and os.path.exists(_active_log_files[0]):
        log_file = _active_log_files[0]
        stats['log_file_size'] = os.path.getsize(log_file)
        
        backup_files = glob.glob(f"{log_file}.*")
        stats['backup_files'] = len(backup_files)
    else:
        stats['log_file_size'] = 0
        stats['backup_files'] = 0
    
    return stats


def reset_logging() -> None:
    """
    Reset logging configuration.
    
    This removes all handlers and resets the initialized state.
    Useful for testing or reconfiguration.
    
    Example:
        >>> reset_logging()
        >>> setup_logging(console_level=logging.DEBUG)
    """
    global _logging_initialized, _active_log_files
    
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    _active_log_files.clear()
    _logging_initialized = False


# --- Test and example ---

if __name__ == "__main__":
    # Initialize logging at DEBUG level for testing
    setup_logging(console_level=logging.DEBUG, file_level=logging.DEBUG)
    
    logger = get_logger(__name__)
    
    print("=== SHL Logging Test ===\n")
    
    logger.debug("This is a DEBUG message (detailed)")
    logger.info("This is an INFO message (general info)")
    logger.warning("This is a WARNING message (caution)")
    logger.error("This is an ERROR message (error)")
    
    # Test API key masking
    print("\n=== API Key Masking Test ===")
    test_keys = [
        None,
        "",
        "short",
        "my-secret-api-key-12345",
        "abcdefghijklmnopqrstuvwxyz",
    ]
    for key in test_keys:
        print(f"  {repr(key)} -> {mask_api_key(key)}")
    
    # Test exception logging
    try:
        raise ValueError("Test error!")
    except Exception as e:
        logger.exception("Exception logged:")
    
    # Show statistics
    print("\n=== Logging Statistics ===")
    stats = get_log_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print(f"\n=== Check '{DEFAULT_LOG_FILE}' to see all logs ===")
    
    # Test remove_handler
    print("\n=== Testing remove_handler ===")
    print(f"Handlers before: {len(logging.getLogger().handlers)}")
    remove_handler('StreamHandler')
    print(f"Handlers after removing StreamHandler: {len(logging.getLogger().handlers)}")
