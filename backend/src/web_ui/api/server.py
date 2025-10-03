"""
FastAPI server for React frontend integration.
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

# Ensure we can import from src
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from ..agent.orchestrator.simple_orchestrator import (
    initialize_orchestrator,
)
from ..database.session import get_db
from .auth.auth_service import auth_service
from .dependencies import set_orchestrator
from ..utils.logging_config import get_logger

logger = get_logger(__name__)

from .middleware.error_handler import (
    AppException,
    app_exception_handler,
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from .routes.a2a import router as a2a_router
from .routes.ag_ui import router as ag_ui_router
from .routes.agents import router as agents_router
from .routes.auth import router as auth_router
from .routes.copilotkit import router as copilotkit_router
from .routes.documents import router as documents_router
from .documents.user import router as user_documents_router
from .routes.logging import router as logging_router
from .routes.dev_routes import router as dev_router

# ... (rest of the imports)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager. Initializes and shuts down services gracefully.
    """
    global orchestrator

    # --- Startup ---
    logger.info("Starting API server and initializing services...")

    # 1. Initialize WebSocket manager (it's a global instance)
    from .websocket.websocket_manager import ws_manager

    # 2. Initialize agent orchestrator
    orchestrator = initialize_orchestrator(ws_manager)
    set_orchestrator(orchestrator)
    logger.info("Agent orchestrator initialized")

    # 3. Initialize authentication service and ensure admin user exists
    try:
        # Get database session - get_db() returns a Session object directly
        db = get_db()
        await auth_service.ensure_admin_user(db)
        logger.info("Auth service initialized and admin user checked.")
        db.close()  # Close the session after use
    except Exception as e:
        logger.critical(f"Failed to initialize auth service: {e}", exc_info=True)
        # Don't close db if there was an error getting it

    yield

    # --- Shutdown ---
    logger.info("Shutting down API server and services...")


# --- FastAPI App Initialization ---
def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Web-UI Agent API",
        description="API for Web-UI Agent Dashboard",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,  # Add the lifespan manager
    )

    # Add CORS middleware for React frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "*",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers with proper prefixes
    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    app.include_router(copilotkit_router, prefix="/api/copilotkit", tags=["copilotkit"])
    app.include_router(documents_router, prefix="/api/documents", tags=["documents"])
    app.include_router(
        user_documents_router, prefix="/api/user-documents", tags=["user-documents"]
    )
    app.include_router(a2a_router)
    app.include_router(agents_router, prefix="/api/agents", tags=["Agents"])
    app.include_router(logging_router, prefix="/api/logs", tags=["Frontend Logging"])
    app.include_router(ag_ui_router, prefix="/api/ag_ui", tags=["AG-UI"])
    app.include_router(dev_router, prefix="/api", tags=["Development"])

    # --- Register Error Handlers ---
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    return app


app = create_app()


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
    return {"message": "Web UI Agent API", "status": "running"}


@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# --- Server Runner ---
def run_api_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = False,
    log_level: str = "info",
):
    """Run the FastAPI server."""
    import uvicorn

    from web_ui.utils.logging_config import configure_uvicorn_logging

    logger.info(f"Starting API server on {host}:{port}")
    # Configure uvicorn to use our custom logging setup
    configure_uvicorn_logging()

    uvicorn.run(
        "web_ui.api.server:app",
        host=host,
        port=port,
        reload=reload,
        log_config=None,  # Uvicorn's logging is now handled by our config
    )
    logger.info(f"Uvicorn server started and listening on {host}:{port}")


if __name__ == "__main__":
    run_api_server()