"""
Document management API routes for React frontend.

Provides CRUD operations for documents with ChromaDB integration,
DocumentEditingAgent support, and UserDocumentService integration.
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# from ...agent.document_editor import DocumentEditingAgent # Obsolete
from ...services.user_document_service import UserDocumentService
from ...utils.logging_config import get_logger
# from ..dependencies import get_document_agent # Obsolete

logger = get_logger(__name__)

# Create router
router = APIRouter()

# Initialize user document service
user_document_service = UserDocumentService()

# --- All endpoints below are disabled because they depend on the obsolete DocumentEditingAgent ---

# --- Enhanced Pydantic Models for Document API Requests/Responses ---


class DocumentCreateRequest(BaseModel):
    filename: str
    content: str = ""
    document_type: str = "markdown"
    metadata: dict[str, Any] | None = None


class DocumentType(BaseModel):
    """Enhanced document type definitions"""

    type: str  # markdown, richtext, plaintext, code, json, pdf
    language: str | None = None  # For code files
    editor_mode: str = "source"  # source, visual, split


class DocumentCreateLiveRequest(BaseModel):
    title: str | None = None
    content: str = ""
    document_type: str = "markdown"
    metadata: dict[str, Any] | None = None


class DocumentEditLiveRequest(BaseModel):
    title: str | None = None
    content: str
    metadata: dict[str, Any] | None = None


class DocumentExportRequest(BaseModel):
    document_id: str
    content: str
    format: str  # pdf, html, docx
    document_type: str = "markdown"


class DocumentEditRequest(BaseModel):
    document_id: str
    instruction: str
    use_llm: bool = True


class DocumentSearchRequest(BaseModel):
    query: str
    collection_type: str = "documents"
    limit: int = 10
    use_mcp_tools: bool = True


class DocumentSuggestionsRequest(BaseModel):
    content: str
    document_type: str = "document"


class PolicyStoreRequest(BaseModel):
    document_id: str
    policy_title: str
    policy_type: str = "manual"
    authority_level: str = "medium"


class BatchProcessRequest(BaseModel):
    file_paths: list[str]
    document_type: str = "document"


class ChatRequest(BaseModel):
    """Request model for chat messages."""

    message: str
    context_document_id: str | None = None


class ChatResponse(BaseModel):
    """Response model for chat messages."""

    response: str


class DocumentVersionRequest(BaseModel):
    document_id: str
    version: int


# --- Enhanced Document Management Endpoints ---

# All endpoints are commented out as they depend on the obsolete DocumentEditingAgent.
# This allows the application to start. The functionality will need to be reimplemented.

# @router.post("/create-live")
# async def create_document_live(
#     request: DocumentCreateLiveRequest,
#     agent: DocumentEditingAgent = Depends(get_document_agent),
# ):
#     pass

# @router.put("/edit-live/{document_id}")
# async def edit_document_live(
#     document_id: str,
#     request: DocumentEditLiveRequest,
#     agent: DocumentEditingAgent = Depends(get_document_agent),
# ):
#     pass

# @router.post("/export")
# async def export_document(
#     request: DocumentExportRequest,
#     agent: DocumentEditingAgent = Depends(get_document_agent),
# ):
#     pass

# @router.post("/export-from-db")
# async def export_document_from_database(
#     request: DocumentExportRequest,
#     agent: DocumentEditingAgent = Depends(get_document_agent),
# ):
#     pass

# @router.get("/types")
# async def get_supported_document_types():
#     pass

# @router.post("/upload")
# async def upload_document(
#     file: UploadFile = File(...),
#     document_type: str = "auto-detect",
#     agent: DocumentEditingAgent = Depends(get_document_agent),
# ):
#     pass

# @router.post("/import-with-user-service")
# async def import_document_with_user_service(
#     file: UploadFile = File(...),
#     agent: DocumentEditingAgent = Depends(get_document_agent),
# ):
#     pass

# @router.get("/{document_id}/versions")
# async def get_document_versions(
#     document_id: str,
#     agent: DocumentEditingAgent = Depends(get_document_agent),
# ):
#     pass

# @router.post("/create")
# async def create_document(
#     request: DocumentCreateRequest,
#     agent: DocumentEditingAgent = Depends(get_document_agent),
# ):
#     pass

# @router.post("/edit")
# async def edit_document(
#     request: DocumentEditRequest,
#     agent: DocumentEditingAgent = Depends(get_document_agent),
# ):
#     pass

# @router.post("/search")
# async def search_documents(
#     request: DocumentSearchRequest,
#     agent: DocumentEditingAgent = Depends(get_document_agent),
# ):
#     pass

# @router.post("/suggestions")
# async def get_document_suggestions(
#     request: DocumentSuggestionsRequest,
#     agent: DocumentEditingAgent = Depends(get_document_agent),
# ):
#     pass

# @router.post("/batch")
# async def process_batch_documents(
#     request: BatchProcessRequest,
#     agent: DocumentEditingAgent = Depends(get_document_agent),
# ):
#     pass

# @router.post("/store-policy")
# async def store_as_policy(
#     request: PolicyStoreRequest,
#     agent: DocumentEditingAgent = Depends(get_document_agent),
# ):
#     pass

# @router.get("/{document_id}")
# async def get_document(
#     document_id: str,
#     agent: DocumentEditingAgent = Depends(get_document_agent),
# ):
#     pass

# @router.delete("/{document_id}")
# async def delete_document(
#     document_id: str,
#     agent: DocumentEditingAgent = Depends(get_document_agent),
# ):
#     pass

# @router.get("/")
# async def list_documents(
#     collection_type: str = "documents",
#     limit: int = 100,
#     offset: int = 0,
#     agent: DocumentEditingAgent = Depends(get_document_agent),
# ):
#     pass

# @router.post("/chat", response_model=ChatResponse)
# async def chat_with_document_agent(
#     request: ChatRequest,
#     agent: DocumentEditingAgent = Depends(get_document_agent),
# ):
#     pass