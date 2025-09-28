"""
FastAPI server for React frontend integration.

This server provides REST API endpoints for the DocumentEditingAgent
to enable seamless integration with the React frontend.
"""

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

# Ensure we can import from src
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from ..agent.document_editor import DocumentEditingAgent
from ..agent.orchestrator.simple_orchestrator import (
    SimpleAgentOrchestrator,
    initialize_orchestrator,
)
from ..utils.logging_config import get_logger
from .dependencies import set_document_agent, set_orchestrator
from .middleware.error_handler import (
    AppException,
    app_exception_handler,
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from .routes.agents import router as agents_router
from .routes.auth import router as auth_router
from .routes.documents import router as documents_router

logger = get_logger(__name__)

# --- Singleton Service Instances (Managed by Lifespan) ---
document_agent: DocumentEditingAgent | None = None
orchestrator: SimpleAgentOrchestrator | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager. Initializes and shuts down services gracefully.
    """
    global document_agent, orchestrator

    # --- Startup ---
    logger.info("Starting API server and initializing services...")

    # 1. Initialize WebSocket manager (it's a global instance)
    from .websocket.websocket_manager import ws_manager

    # 2. Initialize agent orchestrator
    orchestrator = initialize_orchestrator(ws_manager)
    set_orchestrator(orchestrator)
    logger.info("Agent orchestrator initialized")

    # 3. Initialize document agent
    try:
        llm_provider_name = os.getenv("LLM_PROVIDER", "ollama")
        llm_model_name = os.getenv("LLM_MODEL", "llama3.2")
        llm_temperature = float(os.getenv("LLM_TEMPERATURE", "0.3"))
        llm_api_key = os.getenv("LLM_API_KEY")
        llm_base_url = os.getenv("LLM_BASE_URL")

        document_agent = DocumentEditingAgent(
            llm_provider_name=llm_provider_name,
            llm_model_name=llm_model_name,
            llm_temperature=llm_temperature,
            llm_api_key=llm_api_key,
            llm_base_url=llm_base_url,
            working_directory="./tmp/documents",
        )
        await document_agent.initialize()
        set_document_agent(document_agent)
        logger.info("DocumentEditingAgent initialized successfully")

        # 4. Register agent with orchestrator
        if orchestrator:
            orchestrator.register_agent("document_editor", document_agent)
            logger.info("DocumentEditingAgent registered with orchestrator")

    except Exception as e:
        logger.critical(
            f"Failed to initialize DocumentEditingAgent at startup: {e}", exc_info=True
        )
        # Set to None to indicate failure
        document_agent = None
        set_document_agent(None)

    yield

    # --- Shutdown ---
    logger.info("Shutting down API server and services...")
    if document_agent:
        await document_agent.close()
        logger.info("DocumentEditingAgent shut down gracefully.")


# --- FastAPI App Initialization ---
app = FastAPI(
    title="Web UI Document Editor API",
    description="API for AI-powered document editing with DocumentEditingAgent",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Register Routers ---
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(documents_router, prefix="/api/documents", tags=["Documents"])
app.include_router(agents_router, prefix="/api/agents", tags=["Agents"])

# --- Register Error Handlers ---
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)


# --- WebSocket Endpoint ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """WebSocket endpoint with authentication."""
    from .auth.auth_service import auth_service
    from .websocket.websocket_manager import ws_manager

    user_id = auth_service.verify_token(token)
    if not user_id:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await ws_manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_json()
            await ws_manager.handle_user_message(user_id, data)
    except WebSocketDisconnect:
        logger.info(f"User {user_id} disconnected from WebSocket.")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}", exc_info=True)
    finally:
        await ws_manager.disconnect(user_id)


# --- Root and Health Check Endpoints ---
@app.get("/", tags=["System"])
async def root():
    """Root endpoint."""
    return {"message": "Web UI Document Editor API", "status": "running"}


@app.get("/health", tags=["System"])
async def health_check(agent: DocumentEditingAgent = Depends(get_document_agent)):
    """Health check endpoint."""
    return {
        "status": "healthy",
        "agent_initialized": agent is not None,
        "mcp_tools_available": len(agent.mcp_tools) if agent else 0,
    }


# --- Server Runner ---
def run_api_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = False,
    log_level: str = "info",
):
    """Run the FastAPI server."""
    import uvicorn

    from ..utils.logging_config import LoggingConfig

    logger.info(f"Starting API server on {host}:{port}")
    log_config = LoggingConfig.configure_uvicorn_logging(log_level.upper())

    uvicorn.run(
        "web_ui.api.server:app",
        host=host,
        port=port,
        reload=reload,
        log_config=log_config,
    )


if __name__ == "__main__":
    run_api_server()
