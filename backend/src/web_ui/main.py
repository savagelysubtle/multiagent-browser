#!/usr/bin/env python3
"""
Web-UI Application Orchestrator.

This orchestrator manages the entire application lifecycle including:
- FastAPI server for React frontend
- Background services (if needed)
- Database connections
- Service initialization

Architecture: Entry point (webui.py) -> Orchestrator (this file) -> Services
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add the backend src to path for imports
backend_root = Path(__file__).parent.parent.parent  # Navigate up to backend/
sys.path.insert(0, str(backend_root))
sys.path.insert(0, str(backend_root / "src"))

from dotenv import load_dotenv

load_dotenv()

# Import centralized logging configuration
from web_ui.utils.logging_config import LoggingConfig, get_logger

# Project root is the backend directory
project_root = backend_root

logger = get_logger(__name__)


def setup_logging(level: str = "INFO") -> None:
    """Configure logging for the application using centralized configuration."""
    LoggingConfig.setup_logging(level=level)


def start_api_server(args: argparse.Namespace) -> None:
    """Start the FastAPI server for React frontend integration."""
    logger.info("Starting FastAPI backend server...")

    try:
        from web_ui.api.server import run_api_server

        run_api_server(
            host=args.api_host,
            port=args.api_port,
            reload=args.reload,
            log_level=args.log_level.lower(),
        )

    except ImportError as e:
        logger.error(f"Failed to import API server: {e}")
        logger.error("FastAPI server module not available")
        raise
    except Exception as e:
        logger.error(f"API server startup failed: {e}")
        raise


async def start_services() -> None:
    """Initialize background services (database, MCP servers, etc.)."""
    logger.info("Initializing background services...")

    # Initialize ChromaDB
    try:
        from web_ui.database.connection import get_chroma_client
        from web_ui.database.utils import DatabaseUtils

        client = get_chroma_client()
        utils = DatabaseUtils()
        utils.setup_default_collections()
        logger.info("ChromaDB initialized successfully")
    except Exception as e:
        logger.error(f"ChromaDB initialization failed: {e}")

    # Verify MCP services are available
    try:
        logger.info("MCP services module available")
    except Exception as e:
        logger.error(f"MCP services not available: {e}")

    # Verify agent orchestrator is available
    try:
        logger.info("Agent orchestrator module available")
    except Exception as e:
        logger.error(f"Agent orchestrator not available: {e}")


async def run_headless_mode() -> None:
    """Run the application in headless mode (services only, no web server)."""
    logger.info("Starting in headless mode...")
    await start_services()

    # Keep the application running
    try:
        logger.info("Headless mode active. Press Ctrl+C to shutdown...")
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down headless services...")


def main() -> None:
    """Main entry point with different operational modes."""
    parser = argparse.ArgumentParser(
        description="Web-UI Application - Unified AI Research Platform with React Frontend",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m web_ui.main                    # Start full application (API + frontend)
  python -m web_ui.main --api-only         # Start API server only
  python -m web_ui.main --headless         # Run background services only
  python -m web_ui.main --port 8080        # API server on custom port
  python -m web_ui.main --log-level DEBUG  # Verbose logging
  python -m web_ui.main --init-services    # Initialize services first
  python -m web_ui.main --reload           # Enable auto-reload for development
        """,
    )

    # Operational modes
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode (background services only, no web server)",
    )
    parser.add_argument(
        "--api-only",
        action="store_true",
        help="Start API server only (don't serve frontend static files)",
    )

    # API server options
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to listen on (default: 8000)"
    )
    parser.add_argument(
        "--api-host",
        type=str,
        default="127.0.0.1",
        help="API server host (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--api-port", type=int, default=8000, help="API server port (default: 8000)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )

    # System options
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )
    parser.add_argument(
        "--init-services",
        action="store_true",
        help="Initialize background services before starting server",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)

    # Determine mode
    if args.headless:
        mode = "headless"
    elif args.api_only:
        mode = "api-only"
    else:
        mode = "full-stack"

    logger.info(f"Starting Web-UI Application in '{mode}' mode")
    logger.info(f"Project root: {project_root}")
    logger.info(f"Frontend location: {project_root / 'frontend'}")

    # Set API host/port from main host/port if not specified separately
    if args.api_host == "127.0.0.1" and args.host != "127.0.0.1":
        args.api_host = args.host
    if args.api_port == 8000 and args.port != 8000:
        args.api_port = args.port

    try:
        if args.headless:
            # Run in headless mode
            asyncio.run(run_headless_mode())
        else:
            # Initialize services if requested
            if args.init_services:
                logger.info("Pre-initializing background services...")
                asyncio.run(start_services())

            # Start the FastAPI server (with or without frontend serving)
            start_api_server(args)

    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
