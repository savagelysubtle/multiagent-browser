"""
Document management API routes for React frontend.

Provides CRUD operations for documents with ChromaDB integration
and DocumentEditingAgent support.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ...database.chroma_manager import ChromaManager
from ...database.models import DocumentModel
from ..auth.auth_service import User
from ..auth.dependencies import get_current_user

logger = logging.getLogger(__name__)

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
    metadata: Optional[Dict[str, Any]] = None


class DocumentUpdateRequest(BaseModel):
    """Request model for document updates."""

    title: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class DocumentResponse(BaseModel):
    """Response model for document information."""

    id: str
    title: str
    content: str
    document_type: str
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str
    owner_id: str


class DocumentListResponse(BaseModel):
    """Response model for document lists."""

    documents: List[DocumentResponse]
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
    document_type: Optional[str] = None,
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
