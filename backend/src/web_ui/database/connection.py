"""ChromaDB connection management."""

from __future__ import annotations

import os
from pathlib import Path

from chromadb import PersistentClient
from chromadb.config import Settings

from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class ChromaConnection:
    """Singleton class for managing ChromaDB connections."""

    _instance: ChromaConnection | None = None
    _client: PersistentClient | None = None

    def __new__(cls) -> ChromaConnection:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._setup_client()

    def _setup_client(self) -> None:
        """Initialize the ChromaDB client with proper configuration."""
        try:
            # Get database path from environment or use default
            db_path = os.getenv("CHROMA_DB_PATH", "./data/chroma_db")
            db_path = Path(db_path).resolve()

            # Ensure the directory exists
            db_path.mkdir(parents=True, exist_ok=True)

            # Create ChromaDB client with persistent storage
            settings = Settings(
                persist_directory=str(db_path),
                anonymized_telemetry=False,  # Disable telemetry for privacy
                allow_reset=True,  # Allow reset operations
                is_persistent=True,
            )

            self._client = PersistentClient(path=str(db_path), settings=settings)

            logger.info(
                f"ChromaDB client initialized with persistent storage at: {db_path}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {e}")
            raise

    @property
    def client(self) -> PersistentClient:
        """Get the ChromaDB client instance."""
        if self._client is None:
            self._setup_client()
        return self._client

    def reset_connection(self) -> None:
        """Reset the ChromaDB connection."""
        logger.warning("Resetting ChromaDB connection")
        self._client = None
        self._setup_client()

    def close(self) -> None:
        """Close the ChromaDB connection."""
        if self._client is not None:
            # ChromaDB PersistentClient doesn't have an explicit close method
            # The connection is automatically managed
            logger.info("ChromaDB connection closed")
            self._client = None


def get_chroma_client() -> PersistentClient:
    """Get a ChromaDB client instance."""
    connection = ChromaConnection()
    return connection.client


def close_chroma_connection() -> None:
    """Close the ChromaDB connection."""
    connection = ChromaConnection()
    connection.close()


# Environment variable configuration
def get_db_config() -> dict:
    """Get database configuration from environment variables."""
    return {
        "db_path": os.getenv("CHROMA_DB_PATH", "./data/chroma_db"),
        "collection_prefix": os.getenv("CHROMA_COLLECTION_PREFIX", "webui_"),
        "default_embedding_function": os.getenv("CHROMA_EMBEDDING_FUNCTION", "default"),
        "max_connections": int(os.getenv("CHROMA_MAX_CONNECTIONS", "10")),
        "enable_telemetry": os.getenv("CHROMA_ENABLE_TELEMETRY", "false").lower()
        == "true",
    }
