"""
FastAPI server for React frontend integration.

This server provides REST API endpoints for the DocumentEditingAgent
to enable seamless integration with the React frontend.
"""

import json
import logging
import os

# Ensure we can import from src
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from ..agent.document_editor import DocumentEditingAgent

logger = logging.getLogger(__name__)

# Global agent instance
document_agent: Optional[DocumentEditingAgent] = None


# Pydantic models for API requests/responses
class DocumentCreateRequest(BaseModel):
    filename: str
    content: str = ""
    document_type: str = "document"
    metadata: Optional[Dict[str, Any]] = None


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


class ChatMessage(BaseModel):
    sender: str
    text: str


class ChatRequest(BaseModel):
    message: str
    context_document_id: Optional[str] = None
    use_streaming: bool = True


class ChatResponse(BaseModel):
    id: str
    sender: str = "assistant"
    text: str


class AgentStatusResponse(BaseModel):
    initialized: bool
    mcp_tools_available: int
    session_id: Optional[str]
    current_document: Optional[str]
    database_stats: Optional[Dict[str, Any]]
    message: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global document_agent

    # Startup
    logger.info("Starting API server...")
    await initialize_document_agent()

    yield

    # Shutdown
    logger.info("Shutting down API server...")
    if document_agent:
        await document_agent.close()


async def initialize_document_agent():
    """Initialize the DocumentEditingAgent."""
    global document_agent

    try:
        # Get environment variables for LLM configuration
        llm_provider_name = os.getenv("LLM_PROVIDER", "ollama")
        llm_model_name = os.getenv("LLM_MODEL", "llama3.2")
        llm_temperature = float(os.getenv("LLM_TEMPERATURE", "0.3"))
        llm_api_key = os.getenv("LLM_API_KEY")
        llm_base_url = os.getenv("LLM_BASE_URL")

        # Initialize the agent
        document_agent = DocumentEditingAgent(
            llm_provider_name=llm_provider_name,
            llm_model_name=llm_model_name,
            llm_temperature=llm_temperature,
            llm_api_key=llm_api_key,
            llm_base_url=llm_base_url,
            working_directory="./tmp/documents",
        )

        # Initialize with MCP tools
        success = await document_agent.initialize()
        if success:
            logger.info("DocumentEditingAgent initialized successfully with MCP tools")
        else:
            logger.warning("DocumentEditingAgent initialized without MCP tools")

    except Exception as e:
        logger.error(f"Failed to initialize DocumentEditingAgent: {e}")
        document_agent = None


# Create FastAPI app
app = FastAPI(
    title="Web UI Document Editor API",
    description="API for AI-powered document editing with DocumentEditingAgent",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*",
    ],  # Allow React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Web UI Document Editor API", "status": "running"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "agent_initialized": document_agent is not None,
        "mcp_tools_available": len(document_agent.mcp_tools) if document_agent else 0,
    }


@app.get("/agent/status", response_model=AgentStatusResponse)
async def get_agent_status():
    """Get DocumentEditingAgent status."""
    if not document_agent:
        return AgentStatusResponse(
            initialized=False,
            mcp_tools_available=0,
            session_id=None,
            current_document=None,
            database_stats=None,
            message="Agent not initialized",
        )

    try:
        stats = await document_agent.get_database_stats()
        return AgentStatusResponse(
            initialized=True,
            mcp_tools_available=len(document_agent.mcp_tools),
            session_id=document_agent.session_id,
            current_document=document_agent.current_document_id,
            database_stats=stats,
            message="Agent ready",
        )
    except Exception as e:
        logger.error(f"Error getting agent status: {e}")
        return AgentStatusResponse(
            initialized=True,
            mcp_tools_available=len(document_agent.mcp_tools),
            session_id=document_agent.session_id,
            current_document=document_agent.current_document_id,
            database_stats=None,
            message=f"Error: {str(e)}",
        )


@app.post("/documents/create")
async def create_document(request: DocumentCreateRequest):
    """Create a new document using DocumentEditingAgent."""
    if not document_agent:
        await initialize_document_agent()
        if not document_agent:
            raise HTTPException(
                status_code=500, detail="DocumentEditingAgent not available"
            )

    try:
        success, message, document_id = await document_agent.create_document(
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
        logger.error(f"Error creating document: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error creating document: {str(e)}"
        )


@app.post("/documents/edit")
async def edit_document(request: DocumentEditRequest):
    """Edit a document using DocumentEditingAgent."""
    if not document_agent:
        await initialize_document_agent()
        if not document_agent:
            raise HTTPException(
                status_code=500, detail="DocumentEditingAgent not available"
            )

    try:
        success, message, document_id = await document_agent.edit_document(
            document_id=request.document_id,
            instruction=request.instruction,
            use_llm=request.use_llm,
        )

        if success:
            # Get the updated document content
            document = document_agent.chroma_manager.get_document(
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
        logger.error(f"Error editing document: {e}")
        raise HTTPException(status_code=500, detail=f"Error editing document: {str(e)}")


@app.post("/documents/search")
async def search_documents(request: DocumentSearchRequest):
    """Search documents using DocumentEditingAgent."""
    if not document_agent:
        await initialize_document_agent()
        if not document_agent:
            raise HTTPException(
                status_code=500, detail="DocumentEditingAgent not available"
            )

    try:
        results = await document_agent.search_documents(
            query=request.query,
            collection_type=request.collection_type,
            limit=request.limit,
            use_mcp_tools=request.use_mcp_tools,
        )

        return {"success": True, "results": results, "total": len(results)}

    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error searching documents: {str(e)}"
        )


@app.post("/documents/suggestions")
async def get_document_suggestions(request: DocumentSuggestionsRequest):
    """Get document suggestions using DocumentEditingAgent."""
    if not document_agent:
        await initialize_document_agent()
        if not document_agent:
            raise HTTPException(
                status_code=500, detail="DocumentEditingAgent not available"
            )

    try:
        suggestions = await document_agent.get_document_suggestions(
            content=request.content, document_type=request.document_type
        )

        return {"success": True, "suggestions": suggestions}

    except Exception as e:
        logger.error(f"Error getting suggestions: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error getting suggestions: {str(e)}"
        )


@app.post("/documents/batch")
async def process_batch_documents(
    file_paths: List[str], document_type: str = "document"
):
    """Process multiple documents in batch using DocumentEditingAgent."""
    if not document_agent:
        await initialize_document_agent()
        if not document_agent:
            raise HTTPException(
                status_code=500, detail="DocumentEditingAgent not available"
            )

    try:
        results = await document_agent.process_batch_documents(
            file_paths=file_paths, document_type=document_type
        )

        return {"success": True, "results": results}

    except Exception as e:
        logger.error(f"Error in batch processing: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error in batch processing: {str(e)}"
        )


@app.post("/documents/store-policy")
async def store_as_policy(
    document_id: str,
    policy_title: str,
    policy_type: str = "manual",
    authority_level: str = "medium",
):
    """Store a document as a policy manual using DocumentEditingAgent."""
    if not document_agent:
        await initialize_document_agent()
        if not document_agent:
            raise HTTPException(
                status_code=500, detail="DocumentEditingAgent not available"
            )

    try:
        success, message = await document_agent.store_as_policy(
            document_id=document_id,
            policy_title=policy_title,
            policy_type=policy_type,
            authority_level=authority_level,
        )

        if success:
            return {"success": True, "message": message}
        else:
            raise HTTPException(status_code=400, detail=message)

    except Exception as e:
        logger.error(f"Error storing policy: {e}")
        raise HTTPException(status_code=500, detail=f"Error storing policy: {str(e)}")


@app.get("/llm/providers")
async def get_llm_providers():
    """Get available LLM providers and models."""
    if not document_agent:
        await initialize_document_agent()

    if document_agent:
        return document_agent.get_available_providers()
    else:
        # Fallback to basic provider info
        return {
            "providers": ["ollama", "openai", "anthropic"],
            "models_by_provider": {
                "ollama": ["llama3.2", "llama3.1", "codellama"],
                "openai": ["gpt-4", "gpt-3.5-turbo"],
                "anthropic": ["claude-3-opus", "claude-3-sonnet"],
            },
        }


@app.get("/llm/config")
async def get_llm_config():
    """Get current LLM configuration."""
    if not document_agent:
        await initialize_document_agent()

    if document_agent:
        return document_agent.get_current_llm_config()
    else:
        return {
            "provider": None,
            "model": None,
            "temperature": 0.3,
            "has_llm": False,
            "base_url": None,
            "api_key_set": False,
        }


@app.post("/chat/message")
async def send_chat_message(request: ChatRequest):
    """Send a chat message to the DocumentEditingAgent."""
    if not document_agent:
        await initialize_document_agent()
        if not document_agent:
            raise HTTPException(
                status_code=500, detail="DocumentEditingAgent not available"
            )

    try:
        # Ensure LLM is available
        if not document_agent.llm:
            success = await document_agent.setup_llm()
            if not success:
                raise HTTPException(
                    status_code=503,
                    detail="LLM not available. Please configure LLM settings.",
                )

        # Generate response
        response_text = await document_agent.chat_with_user(
            message=request.message, context_document_id=request.context_document_id
        )

        message_id = str(uuid.uuid4())

        return ChatResponse(id=message_id, sender="assistant", text=response_text)

    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


@app.post("/chat/stream")
async def stream_chat_message(request: ChatRequest):
    """Stream a chat response from the DocumentEditingAgent."""
    if not document_agent:
        await initialize_document_agent()
        if not document_agent:
            raise HTTPException(
                status_code=500, detail="DocumentEditingAgent not available"
            )

    try:
        # Ensure LLM is available
        if not document_agent.llm:
            success = await document_agent.setup_llm()
            if not success:
                raise HTTPException(
                    status_code=503,
                    detail="LLM not available. Please configure LLM settings.",
                )

        async def generate_response() -> AsyncGenerator[str, None]:
            """Generate streaming response."""
            async for chunk in document_agent.chat_with_user_stream(
                message=request.message, context_document_id=request.context_document_id
            ):
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            generate_response(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    except Exception as e:
        logger.error(f"Error in streaming chat: {e}")
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


@app.get("/documents/{document_id}")
async def get_document(document_id: str):
    """Get a specific document by ID."""
    if not document_agent:
        await initialize_document_agent()
        if not document_agent:
            raise HTTPException(
                status_code=500, detail="DocumentEditingAgent not available"
            )

    try:
        document = document_agent.chroma_manager.get_document("documents", document_id)
        if not document:
            raise HTTPException(
                status_code=404, detail=f"Document not found: {document_id}"
            )

        return {
            "id": document.id,
            "content": document.content,
            "metadata": document.metadata,
            "created_at": document.created_at,
            "updated_at": document.updated_at,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting document: {str(e)}")


@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document."""
    if not document_agent:
        await initialize_document_agent()
        if not document_agent:
            raise HTTPException(
                status_code=500, detail="DocumentEditingAgent not available"
            )

    try:
        success = document_agent.chroma_manager.delete_document(
            "documents", document_id
        )
        if success:
            return {"success": True, "message": f"Document {document_id} deleted"}
        else:
            raise HTTPException(
                status_code=404, detail=f"Document not found: {document_id}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error deleting document: {str(e)}"
        )


@app.get("/documents")
async def list_documents(
    collection_type: str = "documents", limit: int = 100, offset: int = 0
):
    """List all documents."""
    if not document_agent:
        await initialize_document_agent()
        if not document_agent:
            raise HTTPException(
                status_code=500, detail="DocumentEditingAgent not available"
            )

    try:
        # Get all documents from the collection
        documents = document_agent.chroma_manager.get_all_documents(collection_type)

        # Apply pagination
        total = len(documents)
        documents = documents[offset : offset + limit]

        return {
            "documents": [
                {
                    "id": doc.id,
                    "name": doc.metadata.get(
                        "filename", doc.metadata.get("title", "Untitled")
                    ),
                    "content": doc.content,
                    "metadata": doc.metadata,
                    "created_at": doc.created_at,
                    "updated_at": doc.updated_at,
                    "type": collection_type,
                }
                for doc in documents
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error listing documents: {str(e)}"
        )


def run_api_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = False,
    log_level: str = "info",
):
    """Run the FastAPI server."""
    import uvicorn

    logger.info(f"Starting API server on {host}:{port}")

    uvicorn.run(
        "src.web_ui.api.server:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )
