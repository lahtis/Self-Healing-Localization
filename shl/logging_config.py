"""
File: logging_config.py
Author: Tuomas Lähteenmäki
Version: 0.1.8
License: MIT
Description:
    Unified logging configuration for the Self-Healing Localization Layer.
    - Consistent log formatting across all modules
    - Console output for development
    - File output for errors (error.log)
    - Configurable log levels
    - Rotating file handler to prevent disk overflow
    
Usage:
    # Before anything else is run:
    from shl.logging_config import setup_logging
    setup_logging()
    
    # Then in modules:
    import logging
    logger = logging.getLogger(__name__)
"""

import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from typing import Optional


# Default log levels
DEFAULT_CONSOLE_LEVEL = logging.INFO
DEFAULT_FILE_LEVEL = logging.WARNING
DEFAULT_LOG_FILE = "error.log"
DEFAULT_MAX_BYTES = 1 * 1024 * 1024  # 1 MB
DEFAULT_BACKUP_COUNT = 3

# Whether logging has been initialized
_logging_initialized = False


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
    global _logging_initialized
    
    if _logging_initialized and not force:
        return logging.getLogger()
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # All levels allowed, handlers filter
    
    # Remove old handlers (if force=True)
    if force:
        root_logger.handlers.clear()
    
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
    root_logger.info(f"SHL logging initialized (console={logging.getLevelName(console_level)}, "
                     f"file={logging.getLevelName(file_level)}, path='{log_file}')")
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Return a logger for the named module.
    
    Ensures the logger follows SHL namespace.
    
    Args:
        name: Module name (typically __name__)
    
    Returns:
        Logger object
    
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Message")
    """
    # Ensure logger is in SHL namespace
    if not name.startswith('shl'):
        name = f'shl.{name}'
    
    return logging.getLogger(name)


def set_level(level: int, logger_name: str = None):
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


def get_log_stats() -> dict:
    """
    Return logging statistics.
    
    Returns:
        Dictionary with logging information
    
    Example:
        >>> stats = get_log_stats()
        >>> print(stats['log_file'])
    """
    import glob
    
    stats = {
        'initialized': _logging_initialized,
        'log_file': DEFAULT_LOG_FILE,
        'handlers': len(logging.getLogger().handlers)
    }
    
    # Check error.log and its backups
    if os.path.exists(DEFAULT_LOG_FILE):
        stats['log_file_size'] = os.path.getsize(DEFAULT_LOG_FILE)
        
        backup_files = glob.glob(f"{DEFAULT_LOG_FILE}.*")
        stats['backup_files'] = len(backup_files)
    
    return stats


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
