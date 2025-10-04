"""
Path utilities for the web-ui project.
"""

from pathlib import Path

def get_project_root() -> Path:
    """Get the project root directory."""
    # From backend/src/web_ui/utils/paths.py
    # Go up 5 levels: utils/ -> web_ui/ -> src/ -> backend/ -> project_root
    return Path(__file__).parent.parent.parent.parent.parent