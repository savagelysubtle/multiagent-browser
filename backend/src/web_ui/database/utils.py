"""Database utilities and helper functions."""

import hashlib
from datetime import datetime
from typing import Any
from uuid import uuid4

from ..utils.logging_config import get_logger
from .chroma_manager import ChromaManager
from .models import CollectionConfig, DocumentModel, SearchResult

logger = get_logger(__name__)


class DatabaseUtils:
    """Utility class for common database operations."""

    def __init__(self):
        """Initialize database utilities."""
        self.manager = ChromaManager()
        # Initialize user document service for enhanced document operations
        try:
            from ..services.user_document_service import UserDocumentService
            self.user_document_service = UserDocumentService()
        except ImportError:
            logger.warning("UserDocumentService not available, using basic document operations")
            self.user_document_service = None

    @staticmethod
    def generate_document_id(content: str, source: str | None = None) -> str:
        """Generate a unique document ID based on content and source."""
        # Create a hash of the content and source for deterministic IDs
        content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()
        source_hash = hashlib.md5((source or "").encode("utf-8")).hexdigest()
        return f"doc_{content_hash[:8]}_{source_hash[:8]}"

    @staticmethod
    def create_document_from_text(
        content: str,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
        doc_id: str | None = None,
    ) -> DocumentModel:
        """Create a DocumentModel from text content."""
        if doc_id is None:
            doc_id = DatabaseUtils.generate_document_id(content, source)

        return DocumentModel(
            id=doc_id,
            content=content,
            metadata=metadata or {},
            source=source,
            timestamp=datetime.now(),
        )

    def setup_default_collections(self) -> dict[str, bool]:
        """Set up default collections for the application."""
        results = {}

        default_collections = [
            CollectionConfig(
                name="documents",
                metadata={
                    "description": "General document storage",
                    "type": "documents",
                },
            ),
            CollectionConfig(
                name="browser_sessions",
                metadata={"description": "Browser session data", "type": "sessions"},
            ),
            CollectionConfig(
                name="user_interactions",
                metadata={
                    "description": "User interaction logs",
                    "type": "interactions",
                },
            ),
            CollectionConfig(
                name="agent_logs",
                metadata={"description": "Agent operation logs", "type": "logs"},
            ),
            CollectionConfig(
                name="mcp_configurations",
                metadata={
                    "description": "MCP server configurations with versioning",
                    "type": "mcp_configs",
                    "auto_startup": True,
                    "max_versions": 10,
                },
            ),
        ]

        for config in default_collections:
            try:
                self.manager.create_collection(config)
                results[config.name] = True
                logger.info(f"Created default collection: {config.name}")
            except Exception as e:
                results[config.name] = False
                logger.error(
                    f"Failed to create default collection '{config.name}': {e}"
                )

        return results

    def store_browser_session(
        self,
        session_id: str,
        url: str,
        title: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Store browser session data."""
        try:
            session_metadata = {
                "session_id": session_id,
                "url": url,
                "title": title,
                "type": "browser_session",
                **(metadata or {}),
            }

            document = DocumentModel(
                id=f"session_{session_id}_{datetime.now().timestamp()}",
                content=content,
                metadata=session_metadata,
                source=url,
                timestamp=datetime.now(),
            )

            return self.manager.add_document("browser_sessions", document)

        except Exception as e:
            logger.error(f"Failed to store browser session: {e}")
            return False

    def store_user_interaction(
        self,
        interaction_type: str,
        interaction_data: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Store user interaction data."""
        try:
            interaction_metadata = {
                "interaction_type": interaction_type,
                "type": "user_interaction",
                **(metadata or {}),
            }

            document = DocumentModel(
                id=f"interaction_{uuid4()}",
                content=interaction_data,
                metadata=interaction_metadata,
                source="web_ui",
                timestamp=datetime.now(),
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
        metadata_filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Search for documents with optional metadata filtering."""
        from .models import QueryRequest

        query_request = QueryRequest(
            query=query,
            collection_name=collection_name,
            limit=limit,
            metadata_filters=metadata_filters or {},
        )

        return self.manager.search(query_request)

    def get_collection_info(self) -> dict[str, dict[str, Any]]:
        """Get information about all collections."""
        collections_info = {}

        for collection_name in self.manager.list_collections():
            stats = self.manager.get_collection_stats(collection_name)
            collections_info[collection_name] = stats

        return collections_info

    def cleanup_old_data(self, days_old: int = 30) -> dict[str, int]:
        """Clean up old data from collections."""
        # This is a placeholder for future implementation
        # Would require querying by timestamp and deleting old documents
        logger.info(f"Cleanup requested for data older than {days_old} days")
        return {"cleaned_documents": 0}

    def export_collection(self, collection_name: str) -> list[dict[str, Any]] | None:
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

    def health_check(self) -> dict[str, Any]:
        """Perform a health check on the database."""
        try:
            # Test basic operations
            collections = self.manager.list_collections()

            health_status = {
                "status": "healthy",
                "collections_count": len(collections),
                "collections": collections,
                "timestamp": datetime.now().isoformat(),
            }

            return health_status

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def store_user_created_document(
        self,
        title: str,
        content: str,
        document_type: str = "markdown",
        template_used: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[bool, str]:
        """Store a document created by a user with enhanced metadata."""
        try:
            doc_id = f"user_doc_{hashlib.md5(f'{title}_{datetime.now().isoformat()}'.encode()).hexdigest()[:12]}"

            enhanced_metadata = {
                "title": title,
                "document_type": document_type,
                "template_used": template_used,
                "created_by": "user",
                "creation_method": "user_interface",
                "word_count": len(content.split()),
                "character_count": len(content),
                "created_at": datetime.now().isoformat(),
                "last_modified": datetime.now().isoformat(),
                "version": 1,
                "is_user_document": True,
                **(metadata or {})
            }

            document = DocumentModel(
                id=doc_id,
                content=content,
                metadata=enhanced_metadata,
                source="user_creation",
                timestamp=datetime.now(),
            )

            success = self.manager.add_document("documents", document)

            if success:
                logger.info(f"Stored user-created document: {title} ({doc_id})")
                return True, doc_id
            else:
                return False, "Failed to store document in database"

        except Exception as e:
            logger.error(f"Error storing user-created document: {e}")
            return False, f"Error storing document: {str(e)}"

    async def export_document_with_user_service(
        self,
        document_id: str,
        export_format: str,
        title: str | None = None,
    ) -> dict[str, Any]:
        """Export document using the user document service if available."""
        try:
            # Get document from database
            document = self.manager.get_document("documents", document_id)
            if not document:
                return {
                    "success": False,
                    "error": f"Document not found: {document_id}"
                }

            # Use user document service if available
            if self.user_document_service:
                doc_title = title or document.metadata.get("title", "document")
                export_result = await self.user_document_service.export_document(
                    content=document.content,
                    format=export_format,
                    title=doc_title
                )
                return export_result
            else:
                # Fallback to basic export
                return {
                    "success": True,
                    "data": document.content.encode('utf-8'),
                    "mime_type": "text/plain",
                    "filename": f"{title or 'document'}.txt"
                }

        except Exception as e:
            logger.error(f"Error exporting document {document_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def import_document_with_user_service(
        self,
        file_path: str,
        store_in_db: bool = True,
    ) -> dict[str, Any]:
        """Import document using user document service if available."""
        try:
            if self.user_document_service:
                # Use user document service for import
                import_result = await self.user_document_service.import_document(file_path)

                if import_result.get("success") and store_in_db:
                    # Store imported document in main database
                    doc_data = import_result["document"]
                    success, doc_id = await self.store_user_created_document(
                        title=doc_data["title"],
                        content=doc_data["content"],
                        document_type=doc_data["format"],
                        metadata={
                            **doc_data,
                            "imported_from": file_path,
                            "import_method": "user_document_service"
                        }
                    )

                    if success:
                        import_result["stored_document_id"] = doc_id

                return import_result
            else:
                # Fallback to basic import
                from pathlib import Path
                file_path_obj = Path(file_path)

                with open(file_path_obj, 'r', encoding='utf-8') as f:
                    content = f.read()

                if store_in_db:
                    success, doc_id = await self.store_user_created_document(
                        title=file_path_obj.stem,
                        content=content,
                        document_type="plaintext",
                        metadata={
                            "imported_from": file_path,
                            "import_method": "basic"
                        }
                    )

                    return {
                        "success": success,
                        "document": {
                            "title": file_path_obj.stem,
                            "content": content,
                            "format": "plaintext"
                        },
                        "stored_document_id": doc_id if success else None
                    }
                else:
                    return {
                        "success": True,
                        "document": {
                            "title": file_path_obj.stem,
                            "content": content,
                            "format": "plaintext"
                        }
                    }

        except Exception as e:
            logger.error(f"Error importing document {file_path}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_user_documents(
        self,
        user_id: str | None = None,
        document_type: str | None = None,
        limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get documents created by users with filtering options."""
        try:
            # Search for user documents
            from .models import QueryRequest

            query_request = QueryRequest(
                query="user document",
                collection_name="documents",
                limit=limit,
                metadata_filters={"is_user_document": True}
            )

            results = self.manager.search(query_request)

            # Convert to user-friendly format
            user_docs = []
            for result in results:
                # Apply additional filters
                if user_id and result.metadata.get("created_by") != user_id:
                    continue
                if document_type and result.metadata.get("document_type") != document_type:
                    continue

                user_docs.append({
                    "id": result.id,
                    "title": result.metadata.get("title", "Untitled"),
                    "content": result.content,
                    "document_type": result.metadata.get("document_type", "plaintext"),
                    "template_used": result.metadata.get("template_used"),
                    "created_at": result.metadata.get("created_at"),
                    "last_modified": result.metadata.get("last_modified"),
                    "version": result.metadata.get("version", 1),
                    "word_count": result.metadata.get("word_count", 0),
                    "character_count": result.metadata.get("character_count", 0),
                })

            return user_docs

        except Exception as e:
            logger.error(f"Error getting user documents: {e}")
            return []

    async def update_user_document(
        self,
        document_id: str,
        content: str | None = None,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Update a user document with version tracking."""
        try:
            # Get existing document
            existing_doc = self.manager.get_document("documents", document_id)
            if not existing_doc:
                logger.warning(f"Document not found for update: {document_id}")
                return False

            # Prepare updated metadata
            updated_metadata = existing_doc.metadata.copy()
            updated_metadata["last_modified"] = datetime.now().isoformat()
            updated_metadata["version"] = updated_metadata.get("version", 1) + 1

            if title:
                updated_metadata["title"] = title
            if metadata:
                updated_metadata.update(metadata)

            # Update content statistics if content changed
            final_content = content if content is not None else existing_doc.content
            if content is not None:
                updated_metadata["word_count"] = len(final_content.split())
                updated_metadata["character_count"] = len(final_content)

            # Create updated document
            updated_document = DocumentModel(
                id=document_id,
                content=final_content,
                metadata=updated_metadata,
                source=existing_doc.source,
                timestamp=datetime.now(),
            )

            # Remove old and add updated (ChromaDB doesn't have direct update)
            self.manager.delete_document("documents", document_id)
            success = self.manager.add_document("documents", updated_document)

            if success:
                logger.info(f"Updated user document: {document_id}")

            return success

        except Exception as e:
            logger.error(f"Error updating user document {document_id}: {e}")
            return False
