#!/usr/bin/env python3
"""
Test script to verify the server starts correctly with centralized logging.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend" / "src"))

from web_ui.main import main
from web_ui.utils.logging_config import LoggingConfig

if __name__ == "__main__":
    print("Testing server startup with centralized logging...")
    print("=" * 50)

    # Initialize logging first
    LoggingConfig.setup_logging(level="INFO")

    # Test that we can get a logger
    import logging

    test_logger = logging.getLogger("test")
    test_logger.info("Test logging message - this should appear only once")

    print("\nStarting main application...")
    print("=" * 50)

    # Start the application
    sys.argv = ["webui.py", "--api-only"]  # Test API-only mode
    main()
