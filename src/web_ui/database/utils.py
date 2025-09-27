"""Database utilities and helper functions."""

import logging
from typing import List, Dict, Any, Optional
from uuid import uuid4
from datetime import datetime
import hashlib

from .models import DocumentModel, CollectionConfig, SearchResult
from .chroma_manager import ChromaManager

logger = logging.getLogger(__name__)


class DatabaseUtils:
    """Utility class for common database operations."""

    def __init__(self):
        """Initialize database utilities."""
        self.manager = ChromaManager()

    @staticmethod
    def generate_document_id(content: str, source: Optional[str] = None) -> str:
        """Generate a unique document ID based on content and source."""
        # Create a hash of the content and source for deterministic IDs
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
        source_hash = hashlib.md5((source or '').encode('utf-8')).hexdigest()
        return f"doc_{content_hash[:8]}_{source_hash[:8]}"

    @staticmethod
    def create_document_from_text(
        content: str,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None
    ) -> DocumentModel:
        """Create a DocumentModel from text content."""
        if doc_id is None:
            doc_id = DatabaseUtils.generate_document_id(content, source)

        return DocumentModel(
            id=doc_id,
            content=content,
            metadata=metadata or {},
            source=source,
            timestamp=datetime.now()
        )

    def setup_default_collections(self) -> Dict[str, bool]:
        """Set up default collections for the application."""
        results = {}

        default_collections = [
            CollectionConfig(
                name="documents",
                metadata={"description": "General document storage", "type": "documents"}
            ),
            CollectionConfig(
                name="browser_sessions",
                metadata={"description": "Browser session data", "type": "sessions"}
            ),
            CollectionConfig(
                name="user_interactions",
                metadata={"description": "User interaction logs", "type": "interactions"}
            ),
            CollectionConfig(
                name="agent_logs",
                metadata={"description": "Agent operation logs", "type": "logs"}
            ),
            CollectionConfig(
                name="mcp_configurations",
                metadata={
                    "description": "MCP server configurations with versioning",
                    "type": "mcp_configs",
                    "auto_startup": True,
                    "max_versions": 10
                }
            )
        ]

        for config in default_collections:
            try:
                self.manager.create_collection(config)
                results[config.name] = True
                logger.info(f"Created default collection: {config.name}")
            except Exception as e:
                results[config.name] = False
                logger.error(f"Failed to create default collection '{config.name}': {e}")

        return results

    def store_browser_session(
        self,
        session_id: str,
        url: str,
        title: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Store browser session data."""
        try:
            session_metadata = {
                "session_id": session_id,
                "url": url,
                "title": title,
                "type": "browser_session",
                **(metadata or {})
            }

            document = DocumentModel(
                id=f"session_{session_id}_{datetime.now().timestamp()}",
                content=content,
                metadata=session_metadata,
                source=url,
                timestamp=datetime.now()
            )

            return self.manager.add_document("browser_sessions", document)

        except Exception as e:
            logger.error(f"Failed to store browser session: {e}")
            return False

    def store_user_interaction(
        self,
        interaction_type: str,
        interaction_data: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Store user interaction data."""
        try:
            interaction_metadata = {
                "interaction_type": interaction_type,
                "type": "user_interaction",
                **(metadata or {})
            }

            document = DocumentModel(
                id=f"interaction_{uuid4()}",
                content=interaction_data,
                metadata=interaction_metadata,
                source="web_ui",
                timestamp=datetime.now()
            )

            return self.manager.add_document("user_interactions", document)

        except Exception as e:
            logger.error(f"Failed to store user interaction: {e}")
            return False

    def search_documents(
        self,
        query: str,
        collection_name: str = "documents",
        limit: int = 10,
        metadata_filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Search for documents with optional metadata filtering."""
        from .models import QueryRequest

        query_request = QueryRequest(
            query=query,
            collection_name=collection_name,
            limit=limit,
            metadata_filters=metadata_filters or {}
        )

        return self.manager.search(query_request)

    def get_collection_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all collections."""
        collections_info = {}

        for collection_name in self.manager.list_collections():
            stats = self.manager.get_collection_stats(collection_name)
            collections_info[collection_name] = stats

        return collections_info

    def cleanup_old_data(self, days_old: int = 30) -> Dict[str, int]:
        """Clean up old data from collections."""
        # This is a placeholder for future implementation
        # Would require querying by timestamp and deleting old documents
        logger.info(f"Cleanup requested for data older than {days_old} days")
        return {"cleaned_documents": 0}

    def export_collection(self, collection_name: str) -> Optional[List[Dict[str, Any]]]:
        """Export all documents from a collection."""
        try:
            collection = self.manager.get_collection(collection_name)
            if collection is None:
                return None

            # This would require implementing a method to get all documents
            # For now, return collection stats
            stats = self.manager.get_collection_stats(collection_name)
            return [{"collection_stats": stats}]

        except Exception as e:
            logger.error(f"Failed to export collection '{collection_name}': {e}")
            return None

    def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the database."""
        try:
            # Test basic operations
            collections = self.manager.list_collections()

            health_status = {
                "status": "healthy",
                "collections_count": len(collections),
                "collections": collections,
                "timestamp": datetime.now().isoformat()
            }

            return health_status

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }