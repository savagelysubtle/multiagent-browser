"""
Centralized, multi-file logging configuration for the web-ui backend.
"""

import logging
import logging.handlers
import sys
from pathlib import Path

from .paths import get_project_root

# --- Configuration ---
try:
    LOG_DIR = get_project_root() / "logs"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
except Exception as e:
    # Fallback to current directory if project root fails
    print(
        f"Warning: Failed to create logs directory at project root: {e}",
        file=sys.stderr,
    )
    LOG_DIR = Path("logs")
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e2:
        print(f"Error: Failed to create logs directory: {e2}", file=sys.stderr)
        # Use temp directory as last resort
        import tempfile

        LOG_DIR = Path(tempfile.gettempdir()) / "web-ui-logs"
        LOG_DIR.mkdir(parents=True, exist_ok=True)

# Mapping from logger name to filename
LOG_FILES = {
    "api": "api.log",
    "database": "database.log",
    "agent": "agent.log",
    "auth": "auth.log",
    "default": "backend_default.log",
}

FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# --- State ---
_loggers = {}


def get_logger(name: str) -> logging.Logger:
    """
    Gets a configured logger instance for a specific part of the application.

    The logger name determines which file it logs to based on the
    component names defined in LOG_FILES (api, database, etc.).

    Args:
        name: The name for the logger, typically __name__.
              The first part of the name (e.g., 'web_ui.api') is used
              to determine the log file.

    Returns:
        A configured logger instance.
    """
    # Determine the logger's component name (e.g., 'api', 'database')
    # Check more specific paths first!
    if "web_ui.api.auth" in name or "auth" in name:
        component_name = "auth"
    elif "web_ui.api" in name:
        component_name = "api"
    elif "web_ui.database" in name:
        component_name = "database"
    elif "web_ui.agent" in name:
        component_name = "agent"
    else:
        component_name = "default"

    # Return existing logger if already configured
    if component_name in _loggers:
        return _loggers[component_name]

    # Create a new logger
    logger = logging.getLogger(component_name)
    logger.setLevel(logging.DEBUG)  # Set the lowest level to capture all messages
    logger.propagate = False  # Prevent messages from bubbling up to the root logger

    formatter = logging.Formatter(FORMAT, DATE_FORMAT)

    # --- Console Handler ---
    # Logs INFO and above to the console.
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # --- File Handler ---
    # Logs DEBUG and above to a component-specific file.
    log_file_name = LOG_FILES.get(component_name, "backend_default.log")
    log_file_path = LOG_DIR / log_file_name

    try:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.info(
            f"Logger '{component_name}' initialized. Logging to {log_file_path}"
        )
    except Exception as e:
        # If file logging fails, just use console logging
        print(
            f"Warning: Failed to setup file logging for {component_name}: {e}",
            file=sys.stderr,
        )
        logger.warning(
            f"File logging disabled for '{component_name}' due to error: {e}"
        )

    _loggers[component_name] = logger

    return logger


def configure_uvicorn_logging():
    """
    Redirects Uvicorn's default loggers to our custom logger setup.
    This ensures Uvicorn's output goes to the 'api.log' file.
    """
    try:
        api_logger = get_logger("web_ui.api")  # Get the logger configured for the API

        # Clear existing handlers from uvicorn loggers and redirect
        for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
            log = logging.getLogger(logger_name)
            log.handlers = api_logger.handlers
            log.setLevel(api_logger.level)
            log.propagate = False  # Important to prevent duplicate messages
    except Exception as e:
        print(f"Warning: Failed to configure uvicorn logging: {e}", file=sys.stderr)
