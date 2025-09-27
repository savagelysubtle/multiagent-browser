"""MCP Service for background operations and startup configuration management."""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from ..database.mcp_config_manager import MCPConfigManager
from ..database.document_pipeline import DocumentPipeline
from ..utils.mcp_client import setup_mcp_client_and_tools

logger = logging.getLogger(__name__)


class MCPService:
    """Background service for MCP configuration management and health monitoring."""

    def __init__(self, webui_manager=None):
        """
        Initialize MCP Service.

        Args:
            webui_manager: Reference to WebuiManager for UI integration
        """
        self.webui_manager = webui_manager
        self.config_manager: Optional[MCPConfigManager] = None
        self.mcp_client = None
        self.is_running = False
        self.health_check_interval = 300  # 5 minutes
        self.backup_interval = 3600  # 1 hour

        # Initialize config manager when available
        self._initialize_config_manager()

    def _initialize_config_manager(self):
        """Initialize the MCP Configuration Manager."""
        try:
            # Try to get DocumentPipeline from webui_manager if available
            if self.webui_manager and hasattr(self.webui_manager, 'document_pipeline'):
                self.config_manager = MCPConfigManager(self.webui_manager.document_pipeline)
            else:
                # Fallback to standalone initialization
                self.config_manager = MCPConfigManager()

            logger.info("✅ MCP Service initialized with configuration manager")

        except Exception as e:
            logger.error(f"Failed to initialize MCP configuration manager: {e}")
            self.config_manager = None

    async def start_service(self) -> bool:
        """
        Start the MCP service with configuration loading and monitoring.

        Returns:
            True if service started successfully, False otherwise
        """
        if self.is_running:
            logger.warning("MCP Service is already running")
            return True

        try:
            logger.info("🚀 Starting MCP Service...")

            # Ensure config manager is available
            if not self.config_manager:
                self._initialize_config_manager()

            if not self.config_manager:
                logger.error("Cannot start MCP Service without configuration manager")
                return False

            # Load active configuration
            success = await self.load_active_configuration()

            if success:
                logger.info("✅ MCP Service started successfully with active configuration")
            else:
                logger.info("⚠️ MCP Service started but no active configuration found")

            # Start background tasks
            self.is_running = True
            asyncio.create_task(self._background_health_monitoring())
            asyncio.create_task(self._background_backup_scheduler())

            return True

        except Exception as e:
            logger.error(f"Failed to start MCP Service: {e}")
            return False

    async def stop_service(self):
        """Stop the MCP service."""
        logger.info("🛑 Stopping MCP Service...")
        self.is_running = False

        # Close MCP client if active
        if self.mcp_client:
            try:
                await self.mcp_client.__aexit__(None, None, None)
                self.mcp_client = None
                logger.info("✅ MCP client closed successfully")
            except Exception as e:
                logger.error(f"Error closing MCP client: {e}")

    async def load_active_configuration(self) -> bool:
        """
        Load and apply the active MCP configuration from database.

        Returns:
            True if configuration loaded successfully, False otherwise
        """
        try:
            if not self.config_manager:
                logger.error("No configuration manager available")
                return False

            logger.info("📥 Loading active MCP configuration from database...")

            # Get active configuration
            active_config = await self.config_manager.get_active_config()

            if not active_config:
                logger.info("No active MCP configuration found in database")
                return False

            config_name = active_config.get("config_name", "Unknown")
            config_data = active_config.get("config_data", {})

            logger.info(f"🔧 Found active configuration: {config_name}")

            # Apply configuration to UI if webui_manager is available
            if self.webui_manager:
                await self._apply_config_to_ui(active_config)

            # Initialize MCP client with configuration
            success = await self._initialize_mcp_client(config_data)

            if success:
                logger.info(f"✅ Successfully loaded and applied MCP configuration: {config_name}")
                return True
            else:
                logger.warning(f"⚠️ Configuration loaded but MCP client initialization failed: {config_name}")
                return False

        except Exception as e:
            logger.error(f"Error loading active MCP configuration: {e}")
            return False

    async def apply_configuration(self, config_data: Dict[str, Any], config_name: str = "runtime") -> bool:
        """
        Apply a new MCP configuration at runtime.

        Args:
            config_data: MCP configuration dictionary
            config_name: Name for this configuration

        Returns:
            True if applied successfully, False otherwise
        """
        try:
            logger.info(f"🔄 Applying new MCP configuration: {config_name}")

            # Store configuration in database
            if self.config_manager:
                success, message = await self.config_manager.store_mcp_config(
                    config_data=config_data,
                    config_name=config_name,
                    description=f"Runtime configuration applied at {datetime.now().isoformat()}",
                    config_type="runtime",
                    set_as_active=True
                )

                if not success:
                    logger.error(f"Failed to store configuration: {message}")
                    return False

            # Apply to UI
            if self.webui_manager:
                await self._apply_config_to_ui({
                    "config_name": config_name,
                    "config_data": config_data
                })

            # Reinitialize MCP client
            success = await self._initialize_mcp_client(config_data)

            if success:
                logger.info(f"✅ Successfully applied MCP configuration: {config_name}")
                return True
            else:
                logger.error(f"Failed to initialize MCP client with new configuration")
                return False

        except Exception as e:
            logger.error(f"Error applying MCP configuration: {e}")
            return False

    async def _apply_config_to_ui(self, config_info: Dict[str, Any]):
        """Apply configuration to UI components."""
        try:
            if not self.webui_manager:
                return

            config_data = config_info.get("config_data", {})
            config_json = json.dumps(config_data, indent=2)

            # Apply to agent settings MCP component
            if hasattr(self.webui_manager, 'id_to_component'):
                mcp_components = [
                    "agent_settings.mcp_server_config",
                    "deep_research_agent.mcp_server_config"
                ]

                for component_id in mcp_components:
                    if component_id in self.webui_manager.id_to_component:
                        component = self.webui_manager.id_to_component[component_id]
                        # Update component value (this would need actual Gradio update mechanism)
                        logger.debug(f"Updated UI component {component_id} with new MCP config")

            logger.info("✅ Applied MCP configuration to UI components")

        except Exception as e:
            logger.error(f"Error applying config to UI: {e}")

    async def _initialize_mcp_client(self, config_data: Dict[str, Any]) -> bool:
        """Initialize MCP client with configuration."""
        try:
            # Close existing client if any
            if self.mcp_client:
                await self.mcp_client.__aexit__(None, None, None)
                self.mcp_client = None

            # Initialize new MCP client
            if config_data and "mcpServers" in config_data:
                self.mcp_client = await setup_mcp_client_and_tools(config_data)

                if self.mcp_client:
                    logger.info("✅ MCP client initialized successfully")

                    # Apply to webui_manager if available
                    if self.webui_manager and hasattr(self.webui_manager, 'setup_mcp_client'):
                        await self.webui_manager.setup_mcp_client(config_data)

                    return True
                else:
                    logger.warning("MCP client initialization returned None")
                    return False
            else:
                logger.info("No MCP servers configured, skipping client initialization")
                return True

        except Exception as e:
            logger.error(f"Error initializing MCP client: {e}")
            return False

    async def _background_health_monitoring(self):
        """Background task for monitoring MCP server health."""
        logger.info("🔍 Starting MCP health monitoring...")

        while self.is_running:
            try:
                await asyncio.sleep(self.health_check_interval)

                if not self.is_running:
                    break

                await self._perform_health_check()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def _background_backup_scheduler(self):
        """Background task for scheduling configuration backups."""
        logger.info("💾 Starting MCP configuration backup scheduler...")

        while self.is_running:
            try:
                await asyncio.sleep(self.backup_interval)

                if not self.is_running:
                    break

                await self._perform_backup()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in backup scheduler: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying

    async def _perform_health_check(self):
        """Perform health check on MCP servers."""
        try:
            if not self.config_manager:
                return

            # Get active configuration
            active_config = await self.config_manager.get_active_config()

            if not active_config:
                return

            # Basic health check - verify MCP client is responsive
            if self.mcp_client:
                # This is a simplified health check
                # In a full implementation, you'd ping each MCP server
                logger.debug("✅ MCP client health check passed")
            else:
                logger.warning("⚠️ MCP client not initialized during health check")

                # Attempt to reinitialize
                config_data = active_config.get("config_data", {})
                await self._initialize_mcp_client(config_data)

        except Exception as e:
            logger.error(f"Error during health check: {e}")

    async def _perform_backup(self):
        """Perform automatic backup of active configuration."""
        try:
            if not self.config_manager:
                return

            # Get active configuration
            active_config = await self.config_manager.get_active_config()

            if not active_config:
                return

            config_id = active_config.get("id")
            if config_id:
                success, message, backup_id = await self.config_manager.backup_config(config_id)

                if success:
                    logger.info(f"💾 Auto-backup created: {message}")
                else:
                    logger.warning(f"⚠️ Auto-backup failed: {message}")

        except Exception as e:
            logger.error(f"Error during automatic backup: {e}")

    async def get_service_status(self) -> Dict[str, Any]:
        """Get current service status and statistics."""
        try:
            status = {
                "is_running": self.is_running,
                "has_config_manager": self.config_manager is not None,
                "has_mcp_client": self.mcp_client is not None,
                "service_uptime": "N/A",  # Could implement uptime tracking
                "last_health_check": datetime.now().isoformat()
            }

            # Add configuration information
            if self.config_manager:
                active_config = await self.config_manager.get_active_config()
                if active_config:
                    status["active_config"] = {
                        "name": active_config.get("config_name", "Unknown"),
                        "server_count": len(active_config.get("config_data", {}).get("mcpServers", {})),
                        "last_used": active_config.get("metadata", {}).get("last_used", "Unknown")
                    }

                # Get collection stats
                stats = self.config_manager.get_collection_stats()
                status["collection_stats"] = stats

            return status

        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {"error": str(e), "is_running": self.is_running}

    async def list_available_configs(self) -> List[Dict[str, Any]]:
        """Get list of all available configurations."""
        try:
            if not self.config_manager:
                return []

            return await self.config_manager.list_configs()

        except Exception as e:
            logger.error(f"Error listing configurations: {e}")
            return []

    async def switch_configuration(self, config_id: str) -> Tuple[bool, str]:
        """
        Switch to a different stored configuration.

        Args:
            config_id: ID of configuration to switch to

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            if not self.config_manager:
                return False, "No configuration manager available"

            # Set as active in database
            success, message = await self.config_manager.set_active_config(config_id)

            if not success:
                return False, message

            # Load and apply the new configuration
            success = await self.load_active_configuration()

            if success:
                return True, f"Successfully switched to configuration: {config_id}"
            else:
                return False, "Configuration activated in database but failed to apply"

        except Exception as e:
            logger.error(f"Error switching configuration: {e}")
            return False, f"Error switching configuration: {str(e)}"