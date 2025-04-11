import logging.config
from typing import Any, Dict

# Assuming settings are correctly imported relative to this file's location
# If logger.py is directly in config/, the import is correct.
# If logger.py moved elsewhere, adjust the import path.
from .settings import settings


def get_logging_config() -> Dict[str, Any]:
    """Get the logging configuration dictionary.

    Sets specific levels for noisy external libraries to WARNING.
    """
    app_log_level = settings.core.log_level.upper()  # Ensure level is uppercase
    library_log_level = "WARNING"  # Default level for external libraries

    return {
        "version": 1,
        "disable_existing_loggers": False,  # Keep this False usually
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
            # "console": {
            #     "class": "logging.StreamHandler",
            #     "formatter": "standard",
            #     "level": "DEBUG",  # Handler level should be low to allow messages through
            #     # Logger level controls what gets passed TO the handler
            #     "stream": "ext://sys.stdout",  # Explicitly send to stdout
            # },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": "logs/app.log",
                "maxBytes": 1024 * 1024 * 5,  # 5 MB
                "backupCount": 5,
                "formatter": "detailed",
                "level": "DEBUG",  # Handler level should be low
            },
        },
        "loggers": {
            # --- Root Logger ---
            # Catches logs from libraries NOT explicitly configured below.
            # Set its level high if you want unconfigured libs to be quiet by default.
            # Or set it to app_log_level if you want them to inherit that level.
            "": {
                "handlers": ["file"],
                "level": library_log_level,  # Default for unconfigured libraries
                "propagate": False,  # Root logger shouldn't propagate
            },
            # --- Your Application Logger ---
            # Logs from get_logger("src...") or get_logger("ingestion_pipeline...") etc.
            "src": {
                "handlers": ["file"],
                "level": app_log_level,  # Use level from settings
                "propagate": False,  # Don't pass src logs to root
            },
            "ingestion_pipeline": {  # Add specific top-level dirs if needed
                "handlers": ["file"],
                "level": app_log_level,
                "propagate": False,
            },
            "db": {  # Example for database module
                "handlers": ["file"],
                "level": app_log_level,
                "propagate": False,
            },
            "llm": {  # Example for llm module
                "handlers": ["file"],
                "level": app_log_level,
                "propagate": False,
            },
            # --- External Library Loggers ---
            # Set levels higher (e.g., WARNING) to reduce noise
            "litellm": {
                "handlers": ["file"],
                "level": library_log_level,
                "propagate": False,
            },
            "LiteLLM": {  # Some libraries might use different capitalization
                "handlers": ["file"],
                "level": library_log_level,
                "propagate": False,
            },
            "httpx": {
                "handlers": ["file"],
                "level": library_log_level,
                "propagate": False,
            },
            "httpcore": {
                "handlers": ["file"],
                "level": library_log_level,
                "propagate": False,
            },
            "openai": {  # If using openai library directly elsewhere
                "handlers": ["file"],
                "level": library_log_level,
                "propagate": False,
            },
            "asyncio": {  # Often noisy at DEBUG level
                "handlers": ["file"],
                "level": library_log_level,
                "propagate": False,
            },
            "uvicorn": {  # If you use uvicorn later
                "handlers": ["file"],
                "level": library_log_level,
                "propagate": False,
            },
            "sqlalchemy": {  # Control SQLAlchemy noise (esp. engine)
                "handlers": ["file"],
                "level": library_log_level,  # Or WARNING
                "propagate": False,
            },
            "alembic": {  # Control Alembic noise
                "handlers": ["file"],
                "level": library_log_level,  # Or WARNING
                "propagate": False,
            },
            # Add any other libraries that become too verbose
        },
    }


def setup_logging() -> None:
    """Configure logging for the application."""
    import os

    # Ensure logs directory exists relative to where script is run or use absolute path
    # Assuming run from project root:
    log_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "logs"
    )  # Go up two levels from src/config
    os.makedirs(log_dir, exist_ok=True)

    config = get_logging_config()
    # Adjust filename path to be relative to project root if needed
    # This depends on CWD when the script runs. Better to use absolute path if possible.
    # For simplicity, assume 'logs/app.log' relative to CWD works for now.
    # If running `python src/docu-ai.py`, CWD is likely the project root.
    config["handlers"]["file"]["filename"] = os.path.join(log_dir, "app.log")

    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name.

    Args:
        name: Name of the logger, typically __name__ of the module.

    Returns:
        Configured logger instance.
    """
    # Ensure logger name starts with 'src.' if it's from within src,
    # so it gets picked up by the 'src' logger config.
    # This helps if __name__ is used in files directly under src.
    # However, it's usually better practice to use specific names like 'src.db', 'src.llm'.
    # If __name__ resolves to just 'docu-ai' (from the main script), it won't match 'src'.
    # So, we primarily rely on explicit logger names like "CLI", "src.module", etc.
    return logging.getLogger(name)


# --- Example of how to get logger in other modules ---
# from config.logger import get_logger
# logger = get_logger(__name__) # Uses the module's full path name, e.g., 'src.db.postgres_impl'
# logger = get_logger("IngestionPipeline") # Use a specific descriptive name
