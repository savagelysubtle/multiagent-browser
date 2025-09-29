"""
Centralized logging configuration for the web-ui backend.

This module provides a single source of truth for logging configuration,
ensuring consistent logging across all backend components.
"""

import logging
import logging.handlers
import sys
from pathlib import Path


class LoggingConfig:
    """Centralized logging configuration manager."""

    _initialized: bool = False
    _log_dir: Path = Path("logs")
    _log_file: str = "web-ui.log"
    _format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    _date_format: str = "%Y-%m-%d %H:%M:%S"

    @classmethod
    def setup_logging(
        cls,
        level: str = "DEBUG",
        log_dir: Path | None = None,
        log_file: str | None = None,
        force_reinit: bool = False,
    ) -> None:
        """
        Configure logging for the application.

        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir: Directory for log files (default: ./logs)
            log_file: Name of the log file (default: web-ui.log)
            force_reinit: Force re-initialization even if already initialized
        """
        # Prevent multiple initializations unless forced
        if cls._initialized and not force_reinit:
            return

        # Set custom paths if provided
        if log_dir:
            cls._log_dir = Path(log_dir)
        if log_file:
            cls._log_file = log_file

        # Ensure log directory exists
        cls._log_dir.mkdir(parents=True, exist_ok=True)

        # Get the root logger
        root_logger = logging.getLogger()

        # Clear any existing handlers to prevent duplicates
        root_logger.handlers.clear()

        # Also clear handlers from common problematic loggers
        for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
            logger = logging.getLogger(logger_name)
            logger.handlers.clear()
            logger.propagate = True

        # Set the logging level
        root_logger.setLevel(getattr(logging, level.upper()))

        # Create formatter
        formatter = logging.Formatter(fmt=cls._format, datefmt=cls._date_format)

        # Create and configure console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # Create and configure file handler with rotation
        log_file_path = cls._log_dir / cls._log_file
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        # Mark as initialized
        cls._initialized = True

        # Log initialization
        logger = logging.getLogger(__name__)
        logger.info(f"Logging initialized - Level: {level}, File: {log_file_path}")

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get a logger instance with the given name.

        Args:
            name: Logger name (typically __name__)

        Returns:
            Logger instance
        """
        # Ensure logging is set up
        if not cls._initialized:
            cls.setup_logging()

        return logging.getLogger(name)

    @classmethod
    def configure_uvicorn_logging(cls, log_level: str = "INFO") -> dict:
        """
        Get uvicorn-specific logging configuration.

        This prevents uvicorn from setting up its own handlers which
        can cause duplicate log messages.

        Args:
            log_level: Logging level for uvicorn

        Returns:
            Dict with uvicorn log config
        """
        # Ensure our logging is set up first
        if not cls._initialized:
            cls.setup_logging(level=log_level)

        return {
            "version": 1,
            "disable_existing_loggers": False,
            "handlers": {
                # Use our existing handlers by referencing root logger
                "default": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                    "formatter": "default",
                }
            },
            "formatters": {
                "default": {"format": cls._format, "datefmt": cls._date_format}
            },
            "loggers": {
                "uvicorn": {
                    "handlers": [],  # Use root logger handlers
                    "level": log_level.upper(),
                    "propagate": True,
                },
                "uvicorn.error": {
                    "handlers": [],  # Use root logger handlers
                    "level": log_level.upper(),
                    "propagate": True,
                },
                "uvicorn.access": {
                    "handlers": [],  # Use root logger handlers
                    "level": log_level.upper(),
                    "propagate": True,
                },
            },
        }

    @classmethod
    def reset(cls) -> None:
        """Reset the logging configuration state."""
        cls._initialized = False

        # Clear all handlers from root logger
        root_logger = logging.getLogger()
        root_logger.handlers.clear()


# Convenience function for backward compatibility
def setup_logging(level: str = "INFO", **kwargs) -> None:
    """Setup logging using the centralized configuration."""
    LoggingConfig.setup_logging(level=level, **kwargs)


# Convenience function to get a logger
def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return LoggingConfig.get_logger(name)
