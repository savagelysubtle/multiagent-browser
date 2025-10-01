#!/usr/bin/env python3
"""
Web-UI Entry Point - Simple router to orchestrator.

This is the "front door" that routes user commands to the application orchestrator.
Follows the orchestrator pattern: keep entry point minimal (< 50 lines).
"""

import sys
from pathlib import Path

import os

# Ensure we can import from backend/src
backend_src = Path(__file__).parent / "backend" / "src"
sys.path.insert(0, str(backend_src))

from dotenv import load_dotenv

load_dotenv()


def main():
    """Route all commands to the application orchestrator."""
    # Import the orchestrator
    from web_ui.main import main as orchestrator_main

    # Let the orchestrator handle everything
    orchestrator_main()


if __name__ == "__main__":
    main()
