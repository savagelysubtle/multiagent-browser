"""
ChromaDB Connection Manager

This module handles the connection to the ChromaDB client, ensuring a singleton
instance is used throughout the application.
"""

import chromadb
from chromadb.config import Settings
from web_ui.utils.paths import get_project_root
from web_ui.utils.logging_config import get_logger

logger = get_logger(__name__)

# --- Singleton ChromaDB Client Instance ---
_chroma_client = None


def get_chroma_client() -> chromadb.Client:
    """
    Get the singleton ChromaDB client instance.

    Initializes the client on the first call. Subsequent calls return the
    existing instance.

    Returns:
        The ChromaDB client instance.
    """
    global _chroma_client

    if _chroma_client is None:
        logger.info("Initializing ChromaDB client...")
        try:
            chroma_db_path = str(get_project_root() / "data" / "chroma_db")
            logger.debug(f"ChromaDB persistent path: {chroma_db_path}")

            _chroma_client = chromadb.PersistentClient(
                path=chroma_db_path,
                settings=Settings(
                    anonymized_telemetry=False, # Disable telemetry
                    is_persistent=True,
                ),
            )
            logger.info(f"ChromaDB client initialized successfully. Server version: {_chroma_client.get_version()}")
        except Exception as e:
            logger.exception(f"Failed to initialize ChromaDB client: {e}")
            # As a fallback, try an in-memory instance
            logger.warning("Attempting to fall back to in-memory ChromaDB instance.")
            try:
                _chroma_client = chromadb.Client(
                    Settings(anonymized_telemetry=False)
                )
                logger.info("In-memory ChromaDB client initialized successfully.")
            except Exception as fallback_e:
                logger.exception(f"Failed to initialize in-memory ChromaDB client: {fallback_e}")
                raise

    return _chroma_client