"""
Document management API routes for React frontend.

Provides CRUD operations for documents with ChromaDB integration
and DocumentEditingAgent support.
"""

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ...api.server import document_agent
from ...database.chroma_manager import ChromaManager
from ...database.models import DocumentModel
from ...utils.logging_config import get_logger
from ..auth.auth_service import User
from ..auth.dependencies import get_current_user

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/documents", tags=["documents"])

# Document manager instance
document_manager = ChromaManager()


# Request/Response models
class DocumentCreateRequest(BaseModel):
    """Request model for document creation."""

    title: str
    content: str = ""
    document_type: str = "document"
    metadata: dict[str, Any] | None = None


class DocumentUpdateRequest(BaseModel):
    """Request model for document updates."""

    title: str | None = None
    content: str | None = None
    metadata: dict[str, Any] | None = None


class DocumentResponse(BaseModel):
    """Response model for document information."""

    id: str
    title: str
    content: str
    document_type: str
    metadata: dict[str, Any]
    created_at: str
    updated_at: str
    owner_id: str


class DocumentListResponse(BaseModel):
    """Response model for document lists."""

    documents: list[DocumentResponse]
    total: int
    page: int
    page_size: int


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


# Document management endpoints


@router.post("/", response_model=DocumentResponse)
async def create_document(
    document_data: DocumentCreateRequest, current_user: User = Depends(get_current_user)
):
    """
    Create a new document.

    Creates a document and stores it in ChromaDB with user ownership.
    """
    try:
        doc_id = str(uuid.uuid4())

        # Create document model
        document = DocumentModel(
            id=doc_id,
            content=f"Title: {document_data.title}\n\n{document_data.content}",
            metadata={
                "title": document_data.title,
                "document_type": document_data.document_type,
                "owner_id": current_user.id,
                "created_by": current_user.email,
                **(document_data.metadata or {}),
            },
            source="document_api",
        )

        # Store in ChromaDB
        success = document_manager.add_document("documents", document)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create document",
            )

        logger.info(f"Created document {doc_id} for user {current_user.email}")

        return DocumentResponse(
            id=doc_id,
            title=document_data.title,
            content=document_data.content,
            document_type=document_data.document_type,
            metadata=document.metadata,
            created_at=document.timestamp.isoformat(),
            updated_at=document.timestamp.isoformat(),
            owner_id=current_user.id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create document",
        )


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    page: int = 1,
    page_size: int = 20,
    document_type: str | None = None,
    current_user: User = Depends(get_current_user),
):
    """
    List user's documents.

    Returns paginated list of documents owned by the current user.
    """
    try:
        # Get user's documents
        # Note: This is a simplified implementation
        # In a real scenario, you'd want to filter by owner_id

        # For now, return empty list as placeholder
        return DocumentListResponse(
            documents=[],
            total=0,
            page=page,
            page_size=page_size,
        )

    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list documents",
        )


@router.post("/create-live", response_model=DocumentResponse)
async def create_document_live(
    request: DocumentCreateRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a new document using the document agent directly."""
    logger.info(f"Creating document for user {current_user.id}: {request.title}")

    try:
        # Get or create document agent
        from ...api.server import document_agent

        if not document_agent:
            raise HTTPException(status_code=503, detail="Document agent not available")

        # Create document using agent
        success, message, document_id = await document_agent.create_document(
            filename=request.title,
            content=request.content,
            document_type=request.document_type or "markdown",
            metadata={
                "user_id": current_user.id,
                "created_via": "web_ui",
                "tags": request.metadata.get("tags", []) if request.metadata else [],
            },
        )

        if success and document_id:
            # Get the created document
            document = document_manager.get_document("documents", document_id)
            if document:
                return DocumentResponse(
                    id=document.id,
                    title=document.metadata.get("filename", request.title),
                    content=document.content,
                    document_type=document.metadata.get("document_type", "markdown"),
                    created_at=document.metadata.get(
                        "created_at", datetime.now().isoformat()
                    ),
                    updated_at=document.metadata.get(
                        "updated_at", datetime.now().isoformat()
                    ),
                    metadata=document.metadata,
                    owner_id=current_user.id,
                )

        raise HTTPException(
            status_code=400, detail=message or "Failed to create document"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating document: {e}")
        raise HTTPException(
            status_code=500, detail=f"Internal error creating document: {str(e)}"
        )


@router.put("/edit-live/{document_id}", response_model=DocumentResponse)
async def edit_document_live(
    document_id: str,
    request: DocumentUpdateRequest,
    current_user: User = Depends(get_current_user),
):
    """Edit an existing document using the document agent directly."""
    logger.info(f"Editing document {document_id} for user {current_user.id}")

    try:
        # Get or create document agent
        from ...api.server import document_agent

        if not document_agent:
            raise HTTPException(status_code=503, detail="Document agent not available")

        # Prepare instruction from update request
        instruction = request.content if request.content else ""
        if request.title:
            instruction = f"Update title to: {request.title}\n{instruction}"

        # Edit document using agent
        success, message, updated_id = await document_agent.edit_document(
            document_id=document_id,
            instruction=instruction,
            use_llm=False,  # Direct edit without LLM processing
        )

        if success and updated_id:
            # Get the updated document
            document = document_manager.get_document("documents", updated_id)
            if document:
                return DocumentResponse(
                    id=document.id,
                    title=document.metadata.get(
                        "filename", document.metadata.get("title", "Untitled")
                    ),
                    content=document.content,
                    document_type=document.metadata.get("document_type", "markdown"),
                    created_at=document.metadata.get(
                        "created_at", datetime.now().isoformat()
                    ),
                    updated_at=document.metadata.get(
                        "updated_at", datetime.now().isoformat()
                    ),
                    metadata=document.metadata,
                    owner_id=current_user.id,
                )

        raise HTTPException(
            status_code=400, detail=message or "Failed to edit document"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error editing document: {e}")
        raise HTTPException(
            status_code=500, detail=f"Internal error editing document: {str(e)}"
        )


@router.post("/chat", response_model=dict)
async def chat_with_document_agent(
    request: dict,
    current_user: User = Depends(get_current_user),
):
    """Chat with the document agent for assistance."""
    logger.info(f"Chat request from user {current_user.id}")

    try:
        # Get or create document agent

        if not document_agent:
            raise HTTPException(status_code=503, detail="Document agent not available")

        message = request.get("message", "")
        context_document_id = request.get("context_document_id")

        # Get response from agent
        response = await document_agent.chat_with_user(
            message=message, context_document_id=context_document_id
        )

        return {"response": response, "timestamp": datetime.now().isoformat()}

    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")
