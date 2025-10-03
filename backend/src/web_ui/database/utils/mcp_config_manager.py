"""
Manages loading and accessing of MCP (Multi-Context Prompt) tool configurations.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from web_ui.utils.logging_config import get_logger
from web_ui.utils.paths import get_project_root

logger = get_logger(__name__)

class MCPConfigManager:
    """Loads and provides access to tool configurations from mcp.json."""

    _config: Optional[Dict[str, Any]] = None

    @classmethod
    def load_config(cls) -> Dict[str, Any]:
        """Load the mcp.json configuration file."""
        if cls._config is None:
            config_path = get_project_root() / "data" / "mcp.json"
            logger.info(f"Loading MCP configuration from: {config_path}")
            if not config_path.exists():
                logger.error(f"MCP configuration file not found at {config_path}")
                raise FileNotFoundError(f"mcp.json not found at {config_path}")
            
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    cls._config = json.load(f)
                logger.info("Successfully loaded MCP configuration.")
            except json.JSONDecodeError as e:
                logger.exception(f"Failed to decode mcp.json: {e}")
                raise
            except Exception as e:
                logger.exception(f"Failed to read mcp.json: {e}")
                raise

        return cls._config

    @classmethod
    def get_tool_config(cls, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get the configuration for a specific tool."""
        logger.debug(f"Requesting configuration for tool: '{tool_name}'")
        config = cls.load_config()
        tool_config = config.get("tools", {}).get(tool_name)
        
        if tool_config:
            logger.debug(f"Found configuration for tool: '{tool_name}'")
        else:
            logger.warning(f"No configuration found for tool: '{tool_name}'")
            
        return tool_config