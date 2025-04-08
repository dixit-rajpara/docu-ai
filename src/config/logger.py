"""Logging configuration for the application.

This module provides a centralized way to configure logging across the application.
It reads logging settings from the application configuration and provides
utility functions to get configured loggers.
"""

import logging.config
from typing import Any, Dict

from .settings import settings


def get_logging_config() -> Dict[str, Any]:
    """Get the logging configuration dictionary.

    Returns:
        Dict containing the logging configuration.
    """
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "detailed": {
                "format": (
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s "
                    "- [%(pathname)s:%(lineno)d]"
                ),
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "level": settings.core.log_level,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": "logs/app.log",
                "maxBytes": 1024 * 1024 * 5,  # 5 MB
                "backupCount": 5,
                "formatter": "detailed",
                "level": settings.core.log_level,
            },
        },
        "loggers": {
            "": {  # Root logger
                "handlers": ["console", "file"],
                "level": settings.core.log_level,
                "propagate": True,
            },
            "src": {  # Application logger
                "handlers": ["console", "file"],
                "level": settings.core.log_level,
                "propagate": False,
            },
        },
    }


def setup_logging() -> None:
    """Configure logging for the application."""
    # Ensure logs directory exists
    import os

    os.makedirs("logs", exist_ok=True)

    # Configure logging
    config = get_logging_config()
    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name.

    Args:
        name: Name of the logger, typically __name__ of the module.

    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)
