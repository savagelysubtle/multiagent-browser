"""
User State Manager for per-user application state persistence in ChromaDB.

This module manages user preferences, workspace state, and application settings
with ChromaDB backend storage.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from .chroma_manager import ChromaManager
from .models import CollectionConfig, DocumentModel

logger = logging.getLogger(__name__)


class UserStateManager:
    """Manages per-user state persistence in ChromaDB."""

    def __init__(self, chroma_manager: Optional[ChromaManager] = None):
        """
        Initialize the User State Manager.

        Args:
            chroma_manager: Optional ChromaManager instance, creates new one if not provided
        """
        self.chroma = chroma_manager or ChromaManager()
        self.collection_name = "user_states"
        self._ensure_collection()

    def _ensure_collection(self):
        """Ensure user state collection exists."""
        try:
            config = CollectionConfig(
                name=self.collection_name,
                metadata={
                    "description": "Per-user application state storage",
                    "type": "user_state",
                    "version": "1.0.0",
                    "created_at": datetime.now().isoformat(),
                },
                embedding_function=None,
            )
            self.chroma.create_collection(config)
            logger.info(f"User state collection ensured: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to ensure user state collection: {e}")

    async def save_user_state(self, user_id: str, state: Dict[str, Any]) -> bool:
        """
        Save user's application state.

        Args:
            user_id: Unique user identifier
            state: User state dictionary to save

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            doc_id = f"user_state_{user_id}"

            # Validate state structure
            validated_state = self._validate_state(state)

            doc = DocumentModel(
                id=doc_id,
                content=json.dumps(validated_state, default=str),
                metadata={
                    "user_id": user_id,
                    "state_type": "application_state",
                    "last_updated": datetime.now().isoformat(),
                    "version": "1.0",
                    "state_keys": list(validated_state.keys()),
                },
                source="user_state_manager",
                timestamp=datetime.now(),
            )

            # Delete existing state if any
            existing_doc = self.chroma.get_document(self.collection_name, doc_id)
            if existing_doc:
                self.chroma.delete_document(self.collection_name, doc_id)

            success = self.chroma.add_document(self.collection_name, doc)

            if success:
                logger.debug(f"Saved user state for user: {user_id}")
            else:
                logger.error(f"Failed to save user state for user: {user_id}")

            return success

        except Exception as e:
            logger.error(f"Error saving user state for {user_id}: {e}")
            return False

    async def get_user_state(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve user's application state.

        Args:
            user_id: Unique user identifier

        Returns:
            Optional[Dict]: User state dictionary or None if not found
        """
        try:
            doc_id = f"user_state_{user_id}"
            doc = self.chroma.get_document(self.collection_name, doc_id)

            if doc:
                try:
                    state = json.loads(doc.content)
                    logger.debug(f"Retrieved user state for user: {user_id}")
                    return state
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse user state JSON for {user_id}: {e}")
                    return None

            logger.debug(f"No user state found for user: {user_id}")
            return None

        except Exception as e:
            logger.error(f"Error getting user state for {user_id}: {e}")
            return None

    async def update_user_preference(self, user_id: str, key: str, value: Any) -> bool:
        """
        Update a specific user preference.

        Args:
            user_id: Unique user identifier
            key: Preference key to update
            value: New preference value

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            state = await self.get_user_state(user_id) or {}

            if "preferences" not in state:
                state["preferences"] = {}

            state["preferences"][key] = value

            return await self.save_user_state(user_id, state)

        except Exception as e:
            logger.error(f"Error updating user preference {key} for {user_id}: {e}")
            return False

    async def update_workspace_state(
        self, user_id: str, workspace_data: Dict[str, Any]
    ) -> bool:
        """
        Update user's workspace state.

        Args:
            user_id: Unique user identifier
            workspace_data: Workspace state data

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            state = await self.get_user_state(user_id) or {}

            if "workspace" not in state:
                state["workspace"] = {}

            state["workspace"].update(workspace_data)

            return await self.save_user_state(user_id, state)

        except Exception as e:
            logger.error(f"Error updating workspace state for {user_id}: {e}")
            return False

    async def update_agent_settings(
        self, user_id: str, agent_settings: Dict[str, Any]
    ) -> bool:
        """
        Update user's agent settings.

        Args:
            user_id: Unique user identifier
            agent_settings: Agent configuration settings

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            state = await self.get_user_state(user_id) or {}

            if "agentSettings" not in state:
                state["agentSettings"] = {}

            state["agentSettings"].update(agent_settings)

            return await self.save_user_state(user_id, state)

        except Exception as e:
            logger.error(f"Error updating agent settings for {user_id}: {e}")
            return False

    async def get_user_preference(
        self, user_id: str, key: str, default: Any = None
    ) -> Any:
        """
        Get a specific user preference.

        Args:
            user_id: Unique user identifier
            key: Preference key to retrieve
            default: Default value if preference not found

        Returns:
            Any: Preference value or default
        """
        try:
            state = await self.get_user_state(user_id)
            if state and "preferences" in state:
                return state["preferences"].get(key, default)
            return default

        except Exception as e:
            logger.error(f"Error getting user preference {key} for {user_id}: {e}")
            return default

    async def clear_user_state(self, user_id: str) -> bool:
        """
        Clear all user state data.

        Args:
            user_id: Unique user identifier

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            doc_id = f"user_state_{user_id}"
            success = self.chroma.delete_document(self.collection_name, doc_id)

            if success:
                logger.info(f"Cleared user state for user: {user_id}")
            else:
                logger.warning(f"No user state found to clear for user: {user_id}")

            return success

        except Exception as e:
            logger.error(f"Error clearing user state for {user_id}: {e}")
            return False

    def _validate_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize user state data.

        Args:
            state: Raw state dictionary

        Returns:
            Dict: Validated and sanitized state
        """
        validated_state = {}

        # Define allowed top-level keys and their expected types
        allowed_keys = {
            "preferences": dict,
            "workspace": dict,
            "agentSettings": dict,
            "ui": dict,
            "documents": dict,
        }

        for key, value in state.items():
            if key in allowed_keys:
                expected_type = allowed_keys[key]
                if isinstance(value, expected_type):
                    validated_state[key] = value
                else:
                    logger.warning(
                        f"Invalid type for state key {key}: expected {expected_type}, got {type(value)}"
                    )
            else:
                logger.warning(f"Unknown state key ignored: {key}")

        return validated_state

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the user states collection.

        Returns:
            Dict: Collection statistics
        """
        try:
            stats = self.chroma.get_collection_stats(self.collection_name)
            return {
                **stats,
                "collection_type": "user_states",
                "manager": "UserStateManager",
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"error": str(e)}

    async def backup_user_state(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Create a backup of user state.

        Args:
            user_id: Unique user identifier

        Returns:
            Optional[Dict]: Backup data or None if failed
        """
        try:
            state = await self.get_user_state(user_id)
            if state:
                backup_data = {
                    "user_id": user_id,
                    "backup_timestamp": datetime.now().isoformat(),
                    "state": state,
                }
                logger.info(f"Created backup for user: {user_id}")
                return backup_data
            return None

        except Exception as e:
            logger.error(f"Error creating backup for {user_id}: {e}")
            return None

    async def restore_user_state(
        self, user_id: str, backup_data: Dict[str, Any]
    ) -> bool:
        """
        Restore user state from backup.

        Args:
            user_id: Unique user identifier
            backup_data: Backup data containing state

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if "state" not in backup_data:
                logger.error(
                    f"Invalid backup data for user {user_id}: missing 'state' key"
                )
                return False

            state = backup_data["state"]
            success = await self.save_user_state(user_id, state)

            if success:
                logger.info(f"Restored state for user: {user_id}")

            return success

        except Exception as e:
            logger.error(f"Error restoring state for {user_id}: {e}")
            return False
