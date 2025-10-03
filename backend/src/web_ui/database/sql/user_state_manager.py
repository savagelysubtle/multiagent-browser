"""
Manages user state persistence in the database.
"""

import json
from typing import Any, Dict, Optional

from web_ui.utils.logging_config import get_logger
from .user.user_db import UserDatabase

logger = get_logger(__name__)

class UserStateManager:
    """Handles saving and retrieving user state from the database."""

    def __init__(self):
        """Initialize the UserStateManager."""
        self.db = UserDatabase()
        logger.info("UserStateManager initialized.")

    def save_state(self, user_id: str, state: Dict[str, Any]) -> bool:
        """Save user state to the database."""
        logger.debug(f"Saving state for user_id: {user_id}")
        try:
            with self.db.get_session() as db:
                success = self.db.save_user_state(db, user_id, state)
                if success:
                    logger.info(f"Successfully saved state for user {user_id}.")
                else:
                    logger.warning(f"Failed to save state for user {user_id} (user not found).")
                return success
        except Exception as e:
            logger.exception(f"Error saving state for user {user_id}: {e}")
            return False

    def get_state(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user state from the database."""
        logger.debug(f"Retrieving state for user_id: {user_id}")
        try:
            with self.db.get_session() as db:
                state = self.db.get_user_state(db, user_id)
                if state:
                    logger.info(f"Successfully retrieved state for user {user_id}.")
                else:
                    logger.info(f"No state found for user {user_id}.")
                return state
        except Exception as e:
            logger.exception(f"Error retrieving state for user {user_id}: {e}")
            return None

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        try:
            with self.db.get_session() as db:
                user_count = db.query(User).count()
                state_count = db.query(UserState).count()
                return {
                    "total_users": user_count,
                    "total_states": state_count,
                    "database_type": "SQLite",
                }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"error": str(e)}