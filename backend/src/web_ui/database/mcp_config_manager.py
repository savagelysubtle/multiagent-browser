"""MCP Configuration Manager for ChromaDB storage."""

import json
from datetime import datetime
from typing import Any

from ..utils.logging_config import get_logger
from .chroma_manager import ChromaManager
from .document_pipeline import DocumentPipeline
from .models import CollectionConfig, DocumentModel, QueryRequest

logger = get_logger(__name__)


class MCPConfigManager:
    """Manages MCP server configurations in ChromaDB with versioning and metadata."""

    def __init__(self, document_pipeline: DocumentPipeline = None):
        """Initialize the MCP Configuration Manager."""
        if document_pipeline:
            self.pipeline = document_pipeline
            self.manager = document_pipeline.manager
        else:
            self.manager = ChromaManager()

        self.collection_name = "mcp_configurations"
        self._ensure_collection_exists()

    def _ensure_collection_exists(self):
        """Ensure the MCP configurations collection exists."""
        try:
            collection = self.manager.get_collection(self.collection_name)
            if collection is None:
                # Create the collection with metadata
                config = CollectionConfig(
                    name=self.collection_name,
                    metadata={
                        "description": "MCP server configurations with versioning",
                        "type": "mcp_configs",
                        "auto_startup": True,
                        "max_versions": 10,
                        "created_at": datetime.now().isoformat(),
                    },
                )
                self.manager.create_collection(config)
                logger.info(
                    f"Created MCP configurations collection: {self.collection_name}"
                )
        except Exception as e:
            logger.error(f"Failed to ensure MCP collection exists: {e}")

    async def store_mcp_config(
        self,
        config_data: dict[str, Any],
        config_name: str = "primary",
        description: str = "",
        config_type: str = "custom",
        set_as_active: bool = True,
    ) -> tuple[bool, str]:
        """
        Store MCP configuration in ChromaDB.

        Args:
            config_data: The MCP configuration dictionary
            config_name: Name for this configuration
            description: Human-readable description
            config_type: Type of config (primary, backup, custom)
            set_as_active: Whether to set this as the active configuration

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Validate MCP configuration structure
            if not self._validate_mcp_config(config_data):
                return False, "Invalid MCP configuration structure"

            # Extract server information
            servers = []
            server_count = 0
            if "mcpServers" in config_data:
                servers = list(config_data["mcpServers"].keys())
                server_count = len(servers)

            # Generate unique ID
            config_id = (
                f"mcp_config_{config_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )

            # Prepare metadata
            metadata = {
                "config_name": config_name,
                "config_type": config_type,
                "version": "1.0.0",
                "created_at": datetime.now().isoformat(),
                "last_used": datetime.now().isoformat(),
                "server_count": str(server_count),  # Convert to string for ChromaDB
                "servers": ", ".join(
                    servers
                ),  # Store as string for ChromaDB compatibility
                "is_active": "true"
                if set_as_active
                else "false",  # Store as string for ChromaDB
                "description": description,
                "upload_source": "api_storage",
            }

            # Create document model
            document = DocumentModel(
                id=config_id,
                content=json.dumps(config_data, indent=2),
                metadata=metadata,
                source="mcp_config_manager",
                timestamp=datetime.now(),
            )

            # Store in database
            success = self.manager.add_document(self.collection_name, document)

            if success:
                # If setting as active, deactivate other configs
                if set_as_active:
                    await self._deactivate_other_configs(config_id)

                logger.info(f"Stored MCP configuration: {config_name} ({config_id})")
                return True, f"Successfully stored MCP configuration: {config_name}"
            else:
                return False, "Failed to store configuration in database"

        except Exception as e:
            logger.error(f"Error storing MCP configuration: {e}")
            return False, f"Error storing configuration: {str(e)}"

    async def get_active_config(self) -> dict[str, Any] | None:
        """
        Retrieve the currently active MCP configuration.

        Returns:
            Dictionary containing the active MCP configuration, or None if not found
        """
        try:
            # First try to get all configurations and filter for active ones
            # This is more reliable than using metadata filters in the search
            query_request = QueryRequest(
                query="MCP server configuration",
                collection_name=self.collection_name,
                limit=50,
                include_metadata=True,
            )

            results = self.manager.search(query_request)

            if results:
                # Get the most recently used active config
                active_config = None
                latest_time = None

                for result in results:
                    if result.metadata.get("is_active") == "true":
                        last_used = result.metadata.get("last_used")
                        if not latest_time or (last_used and last_used > latest_time):
                            latest_time = last_used
                            active_config = result

                if active_config:
                    # Parse the JSON content
                    config_data = json.loads(active_config.content)

                    # Update last_used timestamp
                    await self._update_last_used(active_config.id)

                    return {
                        "id": active_config.id,
                        "config_name": active_config.metadata.get(
                            "config_name", "Unknown"
                        ),
                        "description": active_config.metadata.get("description", ""),
                        "config_data": config_data,
                        "metadata": active_config.metadata,
                    }

            logger.info("No active MCP configuration found")
            return None

        except Exception as e:
            logger.error(f"Error retrieving active MCP configuration: {e}")
            return None

    async def list_configs(self) -> list[dict[str, Any]]:
        """
        List all stored MCP configurations.

        Returns:
            List of configuration summaries
        """
        try:
            # Get all MCP configurations
            query_request = QueryRequest(
                query="MCP server configuration",
                collection_name=self.collection_name,
                limit=50,
                include_metadata=True,
            )

            results = self.manager.search(query_request)

            configs = []
            for result in results:
                config_summary = {
                    "id": result.id,
                    "config_name": result.metadata.get("config_name", "Unknown"),
                    "config_type": result.metadata.get("config_type", "custom"),
                    "description": result.metadata.get("description", ""),
                    "server_count": int(
                        result.metadata.get("server_count", "0")
                    ),  # Convert back to int
                    "servers": result.metadata.get("servers", ""),
                    "is_active": result.metadata.get("is_active") == "true",
                    "created_at": result.metadata.get("created_at", ""),
                    "last_used": result.metadata.get("last_used", ""),
                    "version": result.metadata.get("version", "1.0.0"),
                }
                configs.append(config_summary)

            # Sort by last_used, most recent first
            configs.sort(key=lambda x: x["last_used"], reverse=True)

            return configs

        except Exception as e:
            logger.error(f"Error listing MCP configurations: {e}")
            return []

    async def set_active_config(self, config_id: str) -> tuple[bool, str]:
        """
        Set a specific configuration as active.

        Args:
            config_id: ID of the configuration to activate

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Get the configuration
            config = self.manager.get_document(self.collection_name, config_id)
            if not config:
                return False, f"Configuration not found: {config_id}"

            # Deactivate other configurations
            await self._deactivate_other_configs(config_id)

            # Update this configuration's metadata to set as active
            updated_metadata = config.metadata.copy()
            updated_metadata["is_active"] = "true"
            updated_metadata["last_used"] = datetime.now().isoformat()

            # Create updated document
            updated_document = DocumentModel(
                id=config_id,
                content=config.content,
                metadata=updated_metadata,
                source=config.source,
                timestamp=datetime.now(),
            )

            # Delete old and add updated
            self.manager.delete_document(self.collection_name, config_id)
            success = self.manager.add_document(self.collection_name, updated_document)

            if success:
                config_name = updated_metadata.get("config_name", config_id)
                logger.info(f"Activated MCP configuration: {config_name}")
                return True, f"Successfully activated configuration: {config_name}"
            else:
                return False, "Failed to update configuration in database"

        except Exception as e:
            logger.error(f"Error setting active MCP configuration: {e}")
            return False, f"Error activating configuration: {str(e)}"

    async def delete_config(self, config_id: str) -> tuple[bool, str]:
        """
        Delete a stored MCP configuration.

        Args:
            config_id: ID of the configuration to delete

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Get config info before deletion
            config = self.manager.get_document(self.collection_name, config_id)
            if not config:
                return False, f"Configuration not found: {config_id}"

            config_name = config.metadata.get("config_name", config_id)
            is_active = config.metadata.get("is_active") == "true"

            # Don't allow deletion of active config if it's the only one
            if is_active:
                all_configs = await self.list_configs()
                if len(all_configs) <= 1:
                    return False, "Cannot delete the only remaining configuration"

            # Delete the configuration
            success = self.manager.delete_document(self.collection_name, config_id)

            if success:
                logger.info(f"Deleted MCP configuration: {config_name}")
                return True, f"Successfully deleted configuration: {config_name}"
            else:
                return False, "Failed to delete configuration from database"

        except Exception as e:
            logger.error(f"Error deleting MCP configuration: {e}")
            return False, f"Error deleting configuration: {str(e)}"

    async def backup_config(self, config_id: str) -> tuple[bool, str, str | None]:
        """
        Create a backup of an existing configuration.

        Args:
            config_id: ID of the configuration to backup

        Returns:
            Tuple of (success: bool, message: str, backup_id: str)
        """
        try:
            # Get the original configuration
            config = self.manager.get_document(self.collection_name, config_id)
            if not config:
                return False, f"Configuration not found: {config_id}", None

            # Parse the config data
            config_data = json.loads(config.content)

            # Create backup with new name
            original_name = config.metadata.get("config_name", "Unknown")
            backup_name = (
                f"{original_name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )

            success, message = await self.store_mcp_config(
                config_data=config_data,
                config_name=backup_name,
                description=f"Backup of {original_name}",
                config_type="backup",
                set_as_active=False,
            )

            if success:
                # Extract backup ID from message or generate
                backup_id = f"mcp_config_{backup_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                return True, f"Successfully created backup: {backup_name}", backup_id
            else:
                return False, f"Failed to create backup: {message}", None

        except Exception as e:
            logger.error(f"Error creating backup for MCP configuration: {e}")
            return False, f"Error creating backup: {str(e)}", None

    def _validate_mcp_config(self, config_data: dict[str, Any]) -> bool:
        """
        Validate MCP configuration structure.

        Args:
            config_data: Configuration to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            # Basic structure validation
            if not isinstance(config_data, dict):
                return False

            # Check for mcpServers key
            if "mcpServers" not in config_data:
                logger.warning("MCP config missing 'mcpServers' key")
                return False

            mcp_servers = config_data["mcpServers"]
            if not isinstance(mcp_servers, dict):
                logger.warning("'mcpServers' must be a dictionary")
                return False

            # Validate each server configuration
            for server_name, server_config in mcp_servers.items():
                if not isinstance(server_config, dict):
                    logger.warning(
                        f"Server config for '{server_name}' must be a dictionary"
                    )
                    return False

                # Check for required fields (command is typically required)
                if "command" not in server_config:
                    logger.warning(
                        f"Server '{server_name}' missing required 'command' field"
                    )
                    return False

            return True

        except Exception as e:
            logger.error(f"Error validating MCP configuration: {e}")
            return False

    async def _deactivate_other_configs(self, exclude_config_id: str):
        """Deactivate all configurations except the specified one."""
        try:
            # This is a simplified approach - in a production system,
            # you'd want to implement a more efficient batch update
            configs = await self.list_configs()

            for config in configs:
                if config["id"] != exclude_config_id and config["is_active"]:
                    # Get full document
                    doc = self.manager.get_document(self.collection_name, config["id"])
                    if doc:
                        # Update metadata
                        updated_metadata = doc.metadata.copy()
                        updated_metadata["is_active"] = "false"

                        # Create updated document
                        updated_document = DocumentModel(
                            id=config["id"],
                            content=doc.content,
                            metadata=updated_metadata,
                            source=doc.source,
                            timestamp=datetime.now(),
                        )

                        # Replace document
                        self.manager.delete_document(self.collection_name, config["id"])
                        self.manager.add_document(
                            self.collection_name, updated_document
                        )

        except Exception as e:
            logger.error(f"Error deactivating other configurations: {e}")

    async def _update_last_used(self, config_id: str):
        """Update the last_used timestamp for a configuration."""
        try:
            config = self.manager.get_document(self.collection_name, config_id)
            if config:
                updated_metadata = config.metadata.copy()
                updated_metadata["last_used"] = datetime.now().isoformat()

                updated_document = DocumentModel(
                    id=config_id,
                    content=config.content,
                    metadata=updated_metadata,
                    source=config.source,
                    timestamp=datetime.now(),
                )

                self.manager.delete_document(self.collection_name, config_id)
                self.manager.add_document(self.collection_name, updated_document)

        except Exception as e:
            logger.error(f"Error updating last_used timestamp: {e}")

    async def get_config_by_name(self, config_name: str) -> dict[str, Any] | None:
        """
        Retrieve a configuration by its name.

        Args:
            config_name: Name of the configuration to retrieve

        Returns:
            Configuration dictionary or None if not found
        """
        try:
            query_request = QueryRequest(
                query=f"MCP configuration {config_name}",
                collection_name=self.collection_name,
                limit=10,
                include_metadata=True,
                metadata_filters={"config_name": config_name},
            )

            results = self.manager.search(query_request)

            for result in results:
                if result.metadata.get("config_name") == config_name:
                    config_data = json.loads(result.content)
                    return {
                        "id": result.id,
                        "config_name": config_name,
                        "description": result.metadata.get("description", ""),
                        "config_data": config_data,
                        "metadata": result.metadata,
                    }

            return None

        except Exception as e:
            logger.error(f"Error retrieving configuration by name '{config_name}': {e}")
            return None

    def get_collection_stats(self) -> dict[str, Any]:
        """Get statistics about the MCP configurations collection."""
        try:
            stats = self.manager.get_collection_stats(self.collection_name)
            return stats
        except Exception as e:
            logger.error(f"Error getting MCP collection stats: {e}")
            return {"error": str(e)}
