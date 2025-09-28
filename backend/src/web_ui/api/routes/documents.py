"""
Document management API routes for React frontend.

Provides CRUD operations for documents with ChromaDB integration
and DocumentEditingAgent support.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ...agent.document_editor import DocumentEditingAgent
from ...utils.logging_config import get_logger
from ..dependencies import get_document_agent

logger = get_logger(__name__)

# Create router
router = APIRouter()

# --- Pydantic Models for Document API Requests/Responses ---


class DocumentCreateRequest(BaseModel):
    filename: str
    content: str = ""
    document_type: str = "document"
    metadata: dict[str, Any] | None = None


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


# --- Document Management Endpoints ---


@router.post("/create")
async def create_document(
    request: DocumentCreateRequest,
    agent: DocumentEditingAgent = Depends(get_document_agent),
):
    """Create a new document using the DocumentEditingAgent."""
    try:
        success, message, document_id = await agent.create_document(
            filename=request.filename,
            content=request.content,
            document_type=request.document_type,
            metadata=request.metadata,
        )
        if success:
            return {"success": True, "message": message, "document_id": document_id}
        else:
            raise HTTPException(status_code=400, detail=message)
    except Exception as e:
        logger.error(f"Error creating document: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error creating document: {str(e)}"
        )


@router.post("/edit")
async def edit_document(
    request: DocumentEditRequest,
    agent: DocumentEditingAgent = Depends(get_document_agent),
):
    """Edit a document using the DocumentEditingAgent."""
    try:
        success, message, document_id = await agent.edit_document(
            document_id=request.document_id,
            instruction=request.instruction,
            use_llm=request.use_llm,
        )
        if success:
            document = agent.chroma_manager.get_document(
                "documents", document_id or request.document_id
            )
            return {
                "success": True,
                "message": message,
                "document_id": document_id,
                "content": document.content if document else None,
                "metadata": document.metadata if document else None,
            }
        else:
            raise HTTPException(status_code=400, detail=message)
    except Exception as e:
        logger.error(f"Error editing document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error editing document: {str(e)}")


@router.post("/search")
async def search_documents(
    request: DocumentSearchRequest,
    agent: DocumentEditingAgent = Depends(get_document_agent),
):
    """Search documents using the DocumentEditingAgent."""
    try:
        results = await agent.search_documents(
            query=request.query,
            collection_type=request.collection_type,
            limit=request.limit,
            use_mcp_tools=request.use_mcp_tools,
        )
        return {"success": True, "results": results, "total": len(results)}
    except Exception as e:
        logger.error(f"Error searching documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error searching documents: {str(e)}"
        )


@router.post("/suggestions")
async def get_document_suggestions(
    request: DocumentSuggestionsRequest,
    agent: DocumentEditingAgent = Depends(get_document_agent),
):
    """Get document suggestions using the DocumentEditingAgent."""
    try:
        suggestions = await agent.get_document_suggestions(
            content=request.content, document_type=request.document_type
        )
        return {"success": True, "suggestions": suggestions}
    except Exception as e:
        logger.error(f"Error getting suggestions: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error getting suggestions: {str(e)}"
        )


@router.post("/batch")
async def process_batch_documents(
    request: BatchProcessRequest,
    agent: DocumentEditingAgent = Depends(get_document_agent),
):
    """Process multiple documents in a batch."""
    try:
        results = await agent.process_batch_documents(
            file_paths=request.file_paths, document_type=request.document_type
        )
        return {"success": True, "results": results}
    except Exception as e:
        logger.error(f"Error in batch processing: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error in batch processing: {str(e)}"
        )


@router.post("/store-policy")
async def store_as_policy(
    request: PolicyStoreRequest,
    agent: DocumentEditingAgent = Depends(get_document_agent),
):
    """Store a document as a policy manual."""
    try:
        success, message = await agent.store_as_policy(
            document_id=request.document_id,
            policy_title=request.policy_title,
            policy_type=request.policy_type,
            authority_level=request.authority_level,
        )
        if success:
            return {"success": True, "message": message}
        else:
            raise HTTPException(status_code=400, detail=message)
    except Exception as e:
        logger.error(f"Error storing policy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error storing policy: {str(e)}")


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    agent: DocumentEditingAgent = Depends(get_document_agent),
):
    """Get a specific document by its ID."""
    try:
        document = agent.chroma_manager.get_document("documents", document_id)
        if not document:
            raise HTTPException(
                status_code=404, detail=f"Document not found: {document_id}"
            )
        return {
            "id": document.id,
            "content": document.content,
            "metadata": document.metadata,
            "created_at": document.timestamp.isoformat(),
            "updated_at": document.metadata.get(
                "updated_at", document.timestamp.isoformat()
            ),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting document: {str(e)}")


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    agent: DocumentEditingAgent = Depends(get_document_agent),
):
    """Delete a document by its ID."""
    try:
        success = agent.chroma_manager.delete_document("documents", document_id)
        if success:
            return {"success": True, "message": f"Document {document_id} deleted"}
        else:
            raise HTTPException(
                status_code=404, detail=f"Document not found: {document_id}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error deleting document: {str(e)}"
        )


@router.get("/")
async def list_documents(
    collection_type: str = "documents",
    limit: int = 100,
    offset: int = 0,
    agent: DocumentEditingAgent = Depends(get_document_agent),
):
    """List all documents in a collection with pagination."""
    try:
        documents = agent.chroma_manager.get_all_documents(collection_type)
        total = len(documents)
        paginated_docs = documents[offset : offset + limit]
        return {
            "documents": [
                {
                    "id": doc.id,
                    "name": doc.metadata.get(
                        "filename", doc.metadata.get("title", "Untitled")
                    ),
                    "content": doc.content,
                    "metadata": doc.metadata,
                    "created_at": doc.timestamp.isoformat(),
                    "updated_at": doc.metadata.get(
                        "updated_at", doc.timestamp.isoformat()
                    ),
                    "type": collection_type,
                }
                for doc in paginated_docs
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        logger.error(f"Error listing documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error listing documents: {str(e)}"
        )
