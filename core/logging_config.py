"""
Logging Configuration

Centralized logging setup for the application.
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional


def setup_logging(
    app_name: str = 'aftereffects_automation',
    log_level: int = logging.INFO,
    log_dir: str = 'logs',
    console_output: bool = True
) -> logging.Logger:
    """
    Setup application logging with file and console handlers.

    Args:
        app_name: Name of the application logger
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory to store log files
        console_output: Whether to output logs to console

    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # Get or create logger
    logger = logging.getLogger(app_name)
    logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_path / 'app.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Error-specific file handler
    error_handler = logging.handlers.RotatingFileHandler(
        log_path / 'errors.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)

    # Console handler
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    logger.info(f"Logging initialized for {app_name}")
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name. If None, returns the root app logger.

    Returns:
        Logger instance
    """
    if name is None:
        name = 'aftereffects_automation'
    return logging.getLogger(name)


def get_service_logger(service_name: str) -> logging.Logger:
    """
    Get a logger for a specific service.

    Args:
        service_name: Name of the service

    Returns:
        Logger instance for the service
    """
    return logging.getLogger(f'aftereffects_automation.services.{service_name}')


# Module-level logger instance
_main_logger: Optional[logging.Logger] = None


def get_main_logger() -> logging.Logger:
    """Get the main application logger, creating it if necessary."""
    global _main_logger
    if _main_logger is None:
        _main_logger = setup_logging()
    return _main_logger
