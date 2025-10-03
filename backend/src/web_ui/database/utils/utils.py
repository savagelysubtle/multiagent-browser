"""
General database utilities.
"""

from web_ui.utils.logging_config import get_logger
from ..chroma.documents.chroma_manager import ChromaManager

logger = get_logger(__name__)

class DatabaseUtils:
    """Provides utility functions for database management."""

    def setup_default_collections(self) -> None:
        """Create default ChromaDB collections if they don't exist."""
        logger.info("Setting up default ChromaDB collections...")
        default_collections = ["documents", "research_papers", "code_snippets"]

        for collection_name in default_collections:
            try:
                logger.debug(f"Initializing ChromaManager for default collection: '{collection_name}'")
                # The ChromaManager will automatically get or create the collection upon init
                ChromaManager(collection_name=collection_name)
                logger.info(f"Default collection '{collection_name}' is ready.")
            except Exception as e:
                logger.exception(f"Failed to set up default collection '{collection_name}': {e}")