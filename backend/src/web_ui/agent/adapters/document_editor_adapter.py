"""
Document Editor Agent Adapter.

Adapts the existing DocumentEditor agent to work with the SimpleAgentOrchestrator.
Supports Google A2A (Agent-to-Agent) protocol for inter-agent communication.
"""

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from ...utils.logging_config import get_logger

logger = get_logger(__name__)


class DocumentEditorAdapter:
    """
    Adapter for the Document Editor agent with A2A protocol support.

    This adapter wraps the existing DocumentEditor agent and provides
    a standardized interface for the orchestrator, including A2A messaging.
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
        self.agent_id = "document_editor_agent"
        self.a2a_enabled = True
        self.message_handlers = {}
        self._register_a2a_handlers()

    def _register_a2a_handlers(self):
        """Register A2A message type handlers."""
        self.message_handlers = {
            "task_request": self._handle_task_request,
            "capability_query": self._handle_capability_query,
            "status_query": self._handle_status_query,
            "document_query": self._handle_document_query,
            "collaboration_request": self._handle_collaboration_request,
        }

    async def handle_a2a_message(self, message: Any) -> dict[str, Any]:
        """
        Handle incoming A2A protocol messages following Google A2A specification.

        Args:
            message: A2A message object with attributes:
                - message_id: Unique message identifier
                - message_type: Type of message (message/send, tasks/get, etc.)
                - sender_id: Sending agent ID
                - receiver_id: Receiving agent ID
                - payload: Message payload
                - conversation_id: Conversation identifier

        Returns:
            Dict with response data following A2A spec
        """
        try:
            logger.info(
                f"DocumentEditorAdapter received A2A message: {message.message_type} from {message.sender_id}"
            )

            # Get appropriate handler based on Google A2A message types
            handler = self.message_handlers.get(
                message.message_type, self._handle_unknown_message
            )

            # Process message
            response = await handler(message)

            logger.info(f"A2A message processed successfully: {message.message_id}")
            return response

        except Exception as e:
            logger.error(f"Error handling A2A message: {e}")
            return {
                "success": False,
                "error": str(e),
                "message_id": message.message_id if hasattr(message, "message_id") else None,
            }

    async def _handle_task_request(self, message: Any) -> dict[str, Any]:
        """Handle A2A task request."""
        try:
            payload = message.payload
            action = payload.get("action", "create_document")
            params = payload.get("params", {})

            logger.info(f"Processing A2A task request: action={action}")

            # Route to appropriate method
            if action == "create_document":
                result = await self.create_document(
                    filename=params.get("filename", "untitled.md"),
                    content=params.get("content", ""),
                    document_type=params.get("document_type", "markdown"),
                    **params.get("kwargs", {}),
                )
            elif action == "edit_document":
                result = await self.edit_document(
                    document_id=params.get("document_id", ""),
                    instruction=params.get("instruction", ""),
                    **params.get("kwargs", {}),
                )
            elif action == "search_documents":
                result = await self.search_documents(
                    query=params.get("query", ""),
                    limit=params.get("limit", 10),
                    **params.get("kwargs", {}),
                )
            elif action == "chat":
                result = await self._handle_chat_request(params)
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}",
                    "supported_actions": [
                        "create_document",
                        "edit_document",
                        "search_documents",
                        "chat",
                    ],
                }

            return {
                "success": True,
                "action": action,
                "result": result,
                "agent_id": self.agent_id,
                "conversation_id": message.conversation_id,
            }

        except Exception as e:
            logger.error(f"Error in A2A task request: {e}")
            return {"success": False, "error": str(e)}

    async def _handle_capability_query(self, message: Any) -> dict[str, Any]:
        """Handle A2A capability query."""
        return {
            "success": True,
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": self.get_capabilities(),
            "a2a_enabled": self.a2a_enabled,
            "supported_formats": ["markdown", "text", "html", "json"],
        }

    async def _handle_status_query(self, message: Any) -> dict[str, Any]:
        """Handle A2A status query."""
        return {
            "success": True,
            "agent_id": self.agent_id,
            "status": "ready",
            "active": self.document_editor is not None,
            "a2a_enabled": self.a2a_enabled,
            "database_connected": self.chroma_manager is not None,
        }

    async def _handle_document_query(self, message: Any) -> dict[str, Any]:
        """Handle document-specific queries from other agents."""
        try:
            payload = message.payload
            query_type = payload.get("type", "search")

            if query_type == "search":
                results = await self.search_documents(
                    query=payload.get("query", ""), limit=payload.get("limit", 5)
                )
                return {
                    "success": True,
                    "query_type": query_type,
                    "results": results,
                    "agent_id": self.agent_id,
                }
            elif query_type == "retrieve":
                document_id = payload.get("document_id")
                if not self.chroma_manager:
                    return {"success": False, "error": "Database not available"}

                doc = self.chroma_manager.get_document("documents", document_id)
                if doc:
                    return {
                        "success": True,
                        "query_type": query_type,
                        "document": {
                            "id": doc.id,
                            "content": doc.content,
                            "metadata": doc.metadata,
                        },
                        "agent_id": self.agent_id,
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Document not found: {document_id}",
                    }

            return {"success": False, "error": f"Unknown query type: {query_type}"}

        except Exception as e:
            logger.error(f"Error in document query: {e}")
            return {"success": False, "error": str(e)}

    async def _handle_collaboration_request(self, message: Any) -> dict[str, Any]:
        """Handle collaboration request from another agent."""
        try:
            payload = message.payload
            collaboration_type = payload.get("type", "document_assistance")

            logger.info(
                f"Collaboration request from {message.sender_agent}: {collaboration_type}"
            )

            if collaboration_type == "document_assistance":
                # Help another agent with document-related tasks
                request = payload.get("request", "")
                context = payload.get("context", "")

                # Provide relevant documents or templates
                results = await self.search_documents(query=request, limit=3)

                return {
                    "success": True,
                    "collaboration_type": collaboration_type,
                    "documents": results,
                    "agent_id": self.agent_id,
                }

            elif collaboration_type == "save_research":
                # Save research results from another agent
                filename = payload.get("filename", "research_results.md")
                content = payload.get("content", "")

                result = await self.create_document(
                    filename=filename,
                    content=content,
                    document_type="markdown",
                    metadata={
                        "source_agent": message.sender_agent,
                        "collaboration": True,
                        "conversation_id": message.conversation_id,
                    },
                )

                return {
                    "success": True,
                    "collaboration_type": collaboration_type,
                    "document_created": result,
                    "agent_id": self.agent_id,
                }

            return {
                "success": False,
                "error": f"Unknown collaboration type: {collaboration_type}",
            }

        except Exception as e:
            logger.error(f"Error in collaboration request: {e}")
            return {"success": False, "error": str(e)}

    async def _handle_chat_request(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle chat request within A2A context."""
        message = params.get("message", "")
        session_id = params.get("session_id", "a2a_session")
        context_document_id = params.get("context_document_id")

        # Simple chat response
        response = f"Document Editor Agent received: {message}"

        # If document editor has chat capability, use it
        if self.document_editor and hasattr(self.document_editor, "chat"):
            response = await self.document_editor.chat(
                message=message, context_document_id=context_document_id
            )

        return {
            "success": True,
            "response": response,
            "session_id": session_id,
        }

    async def _handle_unknown_message(self, message: Any) -> dict[str, Any]:
        """Handle unknown A2A message types."""
        logger.warning(f"Unknown A2A message type: {message.message_type}")
        return {
            "success": False,
            "error": f"Unknown message type: {message.message_type}",
            "supported_types": list(self.message_handlers.keys()),
        }

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
