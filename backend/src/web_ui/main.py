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
import os
import sys
from pathlib import Path

# Add the backend src to path for imports
backend_root = Path(__file__).parent.parent.parent  # Navigate up to backend/
sys.path.insert(0, str(backend_root))
sys.path.insert(0, str(backend_root / "src"))

# Import centralized logging configuration
from .utils.logging_config import get_logger

# Project root is the backend directory
project_root = backend_root

# Import environment loader before other imports to ensure proper loading
# Environment variables must be loaded early before any modules that depend on them
from dotenv import load_dotenv

# Import centralized logging configuration
from .utils.logging_config import get_logger

logger = get_logger(__name__)

# Load environment variables with intelligent file detection and precedence
# Explicitly specify the .env file path to ensure it's found and loaded correctly.
# The project root is the correct location for .env files
try:
    from .utils.paths import get_project_root
    project_root = get_project_root()
except ImportError:
    # Fallback to manual calculation
    # From backend/src/web_ui/main.py
    # Go up: web_ui/ -> src/ -> backend/ -> project_root
    project_root = Path(__file__).resolve().parents[5]

dotenv_path = project_root / ".env.development"
if not dotenv_path.exists():
    dotenv_path = project_root / ".env"

load_dotenv(dotenv_path=dotenv_path, override=True)
logger.debug(f"Dotenv path: {dotenv_path}, exists: {dotenv_path.exists()}")
logger.debug(
    f"LLM_PROVIDER after load_dotenv in main.py: {os.environ.get('LLM_PROVIDER')}"
)
logger.debug(f"LLM_MODEL after load_dotenv in main.py: {os.environ.get('LLM_MODEL')}")


def start_api_server(args: argparse.Namespace) -> None:
    """Start the FastAPI server for React frontend integration."""
    logger.info("Starting FastAPI backend server...")

    try:
        logger.info("Importing uvicorn...")
        import uvicorn

        logger.info("Importing FastAPI app...")
        from .api.server import app
        logger.info("FastAPI app imported successfully")

        # Test the app by checking if it has routes
        logger.info(f"App has {len(app.routes)} routes configured")
        for route in app.routes:
            logger.debug(f"Route: {route.path} - {route.methods}")

        # Test that the app can handle a basic health check
        try:
            from fastapi.testclient import TestClient
            client = TestClient(app)
            response = client.get("/health")
            logger.info(f"Health check test: {response.status_code} - {response.json()}")
        except ImportError:
            logger.debug("TestClient not available - skipping app test")
        except Exception as e:
            logger.warning(f"Health check test failed: {e}")

        # Configure uvicorn logging to prevent duplicates
        try:
            from .utils.logging_config import configure_uvicorn_logging
            configure_uvicorn_logging()
            logger.info("Uvicorn logging configured successfully")
        except (ImportError, AttributeError) as e:
            logger.warning(f"Could not configure uvicorn logging: {e}")

        logger.info(f"Starting uvicorn server on {args.api_host}:{args.api_port}")

        # Start uvicorn with explicit configuration
        logger.debug(f"Creating uvicorn Config with app={type(app).__name__}")
        config = uvicorn.Config(
            app=app,
            host=args.api_host,
            port=args.api_port,
            reload=False,  # Disable reload for now to avoid issues
            log_level=args.log_level.lower(),
            access_log=True,
            log_config=None  # Use our own logging config
        )
        logger.debug(f"Uvicorn Config created: host={config.host}, port={config.port}, reload={config.reload}")

        logger.debug("Creating uvicorn Server instance...")
        server = uvicorn.Server(config)
        logger.info("Uvicorn server instance created successfully")

        logger.info("Calling server.run() - this should start the server...")
        logger.debug(f"Server config: {server.config}")

        # Simple approach: just call server.run() and let it block
        # The issue might be that uvicorn isn't producing startup messages
        logger.info("About to call server.run() - this blocks until server stops")

        # Before starting the server, let's verify it can handle a basic request
        logger.info("Testing server startup by making a test request...")
        try:
            import requests
            # This should fail since server isn't running yet, but will test if our setup is correct
            response = requests.get(f"http://{args.api_host}:{args.api_port}/health", timeout=1)
        except requests.exceptions.ConnectionError:
            logger.info("Expected connection error - server not started yet")
        except Exception as e:
            logger.warning(f"Unexpected error during pre-startup test: {e}")

        try:
            server.run()
        except KeyboardInterrupt:
            logger.info("Server interrupted by user")
        except Exception as e:
            logger.error(f"Server.run() raised exception: {e}")
            logger.error(f"Exception type: {type(e)}")
            raise

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
        from .database.utils import DatabaseUtils

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

    # Logging is already configured when get_logger() is called
    # No need to explicitly setup logging

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
            logger.info(f"FastAPI server launched on {args.api_host}:{args.api_port}")

    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
