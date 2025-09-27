#!/usr/bin/env python3
"""
Main entry point for the Web-UI Application.

This serves as a unified orchestrator that can:
- Start the web UI (default)
- Initialize background services
- Run in different modes (web-only, headless, etc.)
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Ensure we can import from src
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO"):
    """Configure logging for the application."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('web-ui.log')
        ]
    )


def start_webui(args):
    """Start the Gradio web interface."""
    logger.info("Starting Web UI...")

    # Import and run the existing webui
    from webui import main as webui_main

    # Override sys.argv to pass args to webui
    original_argv = sys.argv.copy()
    sys.argv = ['webui.py']
    if args.ip:
        sys.argv.extend(['--ip', args.ip])
    if args.port:
        sys.argv.extend(['--port', str(args.port)])
    if args.theme:
        sys.argv.extend(['--theme', args.theme])

    try:
        webui_main()
    finally:
        sys.argv = original_argv


async def start_services():
    """Initialize background services (database, MCP servers, etc.)."""
    logger.info("Initializing background services...")

    # Initialize ChromaDB
    try:
        from src.web_ui.database.connection import get_chroma_client
        from src.web_ui.database.utils import DatabaseUtils

        client = get_chroma_client()
        utils = DatabaseUtils()
        utils.setup_default_collections()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")

    # TODO: Add other service initializations here
    # - MCP servers
    # - Agent pools
    # - Background tasks


async def run_headless_mode():
    """Run the application in headless mode (API/services only)."""
    logger.info("Starting in headless mode...")
    await start_services()

    # Keep the application running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")


def main():
    """Main entry point with different operational modes."""
    parser = argparse.ArgumentParser(
        description="Web-UI Application - Unified AI Research Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                      # Start web UI (default)
  python main.py --headless          # Run services only
  python main.py --port 8080         # Web UI on custom port
  python main.py --log-level DEBUG   # Verbose logging
        """
    )

    # Operational modes
    parser.add_argument('--headless', action='store_true',
                       help='Run in headless mode (services only, no web UI)')

    # Web UI options
    parser.add_argument('--ip', type=str, default='127.0.0.1',
                       help='IP address to bind to (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=8000,
                       help='Port to listen on (default: 8000)')
    parser.add_argument('--theme', type=str, default='Ocean',
                       help='UI theme (default: Ocean)')

    # System options
    parser.add_argument('--log-level', type=str, default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level (default: INFO)')
    parser.add_argument('--init-services', action='store_true',
                       help='Initialize background services before starting UI')

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)
    logger.info(f"Starting Web-UI Application in {'headless' if args.headless else 'web'} mode")

    try:
        if args.headless:
            # Run in headless mode
            asyncio.run(run_headless_mode())
        else:
            # Initialize services if requested
            if args.init_services:
                asyncio.run(start_services())

            # Start the web UI
            start_webui(args)

    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()