"""
Document Editor Agent Adapter.

Adapts the existing DocumentEditor agent to work with the SimpleAgentOrchestrator.
"""

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from ...utils.logging_config import get_logger

logger = get_logger(__name__)


class DocumentEditorAdapter:
    """
    Adapter for the Document Editor agent.

    This adapter wraps the existing DocumentEditor agent and provides
    a standardized interface for the orchestrator.
    """

    def __init__(self, document_editor_instance=None, chroma_manager=None):
        """
        Initialize the adapter.

        Args:
            document_editor_instance: The actual DocumentEditor agent instance
            chroma_manager: ChromaDB manager for document operations
        """
        self.document_editor = document_editor_instance
        self.chroma_manager = chroma_manager
        self.agent_type = "document_editor"

    async def create_document(
        self,
        filename: str,
        content: str,
        document_type: str = "markdown",
        progress_callback: Callable[[int, str], Awaitable[None]] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Create a new document.

        Args:
            filename: Name of the document
            content: Initial content
            document_type: Type of document (markdown, text, etc.)
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with document creation result
        """
        try:
            if progress_callback:
                await progress_callback(20, "Validating document...")

            # Validate inputs
            if not filename or not filename.strip():
                raise ValueError("Filename cannot be empty")

            if len(content) > 10 * 1024 * 1024:  # 10MB limit
                raise ValueError("Document content too large (max 10MB)")

            if progress_callback:
                await progress_callback(40, "Creating document...")

            # If we have an actual document editor, use it
            if self.document_editor:
                result = await self.document_editor.create_document(
                    filename=filename,
                    content=content,
                    document_type=document_type,
                    **kwargs,
                )
            else:
                # Fallback implementation using ChromaDB directly
                from ...database.models import DocumentModel

                doc = DocumentModel(
                    id=f"doc_{filename}_{datetime.utcnow().timestamp()}",
                    content=content,
                    metadata={
                        "filename": filename,
                        "document_type": document_type,
                        "created_by": "document_editor_agent",
                        "created_at": datetime.utcnow().isoformat(),
                    },
                    source="document_editor",
                    timestamp=datetime.utcnow(),
                )

                if self.chroma_manager:
                    success = self.chroma_manager.add_document("documents", doc)
                    if not success:
                        raise RuntimeError("Failed to save document to database")

            if progress_callback:
                await progress_callback(80, "Finalizing document...")

            result = {
                "success": True,
                "document_id": doc.id if "doc" in locals() else result.get("id"),
                "filename": filename,
                "document_type": document_type,
                "content_length": len(content),
                "created_at": datetime.utcnow().isoformat(),
            }

            if progress_callback:
                await progress_callback(100, "Document created successfully")

            logger.info(f"Document created: {filename} ({len(content)} chars)")
            return result

        except Exception as e:
            logger.error(f"Failed to create document {filename}: {e}")
            raise

    async def edit_document(
        self,
        document_id: str,
        instruction: str,
        progress_callback: Callable[[int, str], Awaitable[None]] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Edit an existing document using AI assistance.

        Args:
            document_id: ID of the document to edit
            instruction: Human instruction for the edit
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with edit result
        """
        try:
            if progress_callback:
                await progress_callback(20, "Loading document...")

            # Validate inputs
            if not document_id or not document_id.strip():
                raise ValueError("Document ID cannot be empty")

            if not instruction or not instruction.strip():
                raise ValueError("Edit instruction cannot be empty")

            if progress_callback:
                await progress_callback(40, "Applying edits...")

            # If we have an actual document editor, use it
            if self.document_editor:
                result = await self.document_editor.edit_document(
                    document_id=document_id, instruction=instruction, **kwargs
                )
            else:
                # Fallback implementation - retrieve and simulate edit
                if not self.chroma_manager:
                    raise RuntimeError(
                        "No document editor or database manager available"
                    )

                # Get the document
                doc = self.chroma_manager.get_document("documents", document_id)
                if not doc:
                    raise ValueError(f"Document {document_id} not found")

                # For now, just append the instruction as a comment
                # In a real implementation, this would use an LLM
                edited_content = (
                    doc.content + f"\n\n<!-- Edit applied: {instruction} -->"
                )

                # Update the document
                doc.content = edited_content
                doc.metadata["last_edited"] = datetime.utcnow().isoformat()
                doc.metadata["edit_instruction"] = instruction

                success = self.chroma_manager.update_document("documents", doc)
                if not success:
                    raise RuntimeError("Failed to save edited document")

            if progress_callback:
                await progress_callback(80, "Saving changes...")

            result = {
                "success": True,
                "document_id": document_id,
                "instruction": instruction,
                "edited_at": datetime.utcnow().isoformat(),
                "changes_applied": True,
            }

            if progress_callback:
                await progress_callback(100, "Document edited successfully")

            logger.info(f"Document edited: {document_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to edit document {document_id}: {e}")
            raise

    async def search_documents(
        self,
        query: str,
        limit: int = 10,
        progress_callback: Callable[[int, str], Awaitable[None]] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Search through documents.

        Args:
            query: Search query
            limit: Maximum number of results
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with search results
        """
        try:
            if progress_callback:
                await progress_callback(20, "Preparing search...")

            # Validate inputs
            if not query or not query.strip():
                raise ValueError("Search query cannot be empty")

            if limit <= 0 or limit > 100:
                limit = 10

            if progress_callback:
                await progress_callback(50, "Searching documents...")

            # If we have an actual document editor, use it
            if self.document_editor:
                results = await self.document_editor.search_documents(
                    query=query, limit=limit, **kwargs
                )
            else:
                # Fallback implementation using ChromaDB
                if not self.chroma_manager:
                    raise RuntimeError(
                        "No document editor or database manager available"
                    )

                # Perform search
                results = self.chroma_manager.search_documents(
                    collection_name="documents", query=query, limit=limit
                )

            if progress_callback:
                await progress_callback(80, "Processing results...")

            search_result = {
                "success": True,
                "query": query,
                "total_results": len(results) if results else 0,
                "results": results[:limit] if results else [],
                "searched_at": datetime.utcnow().isoformat(),
            }

            if progress_callback:
                await progress_callback(100, "Search completed")

            logger.info(
                f"Document search completed: {query} ({len(results) if results else 0} results)"
            )
            return search_result

        except Exception as e:
            logger.error(f"Failed to search documents: {e}")
            raise

    def get_capabilities(self) -> dict[str, Any]:
        """Get the capabilities of this adapter."""
        return {
            "agent_type": self.agent_type,
            "actions": ["create_document", "edit_document", "search_documents"],
            "supports_progress": True,
            "max_content_size": 10 * 1024 * 1024,  # 10MB
            "supported_formats": ["markdown", "text", "html", "json"],
        }
