from fastapi import APIRouter

# Import all sub-routers
from .a2a import router as a2a_router
from .ag_ui import router as ag_ui_router
from .agents import router as agents_router
from .auth import router as auth_router
from .copilotkit import router as copilotkit_router
from .dev_routes import router as dev_routes_router
from .documents import router as documents_router
from .logging import router as logging_router
from ..websocket.router import router as websocket_router # Import from sibling directory

router = APIRouter()

# Include all sub-routers
router.include_router(a2a_router)
router.include_router(ag_ui_router)
router.include_router(agents_router)
router.include_router(auth_router, prefix="/auth") # Auth routes typically have a /auth prefix
router.include_router(copilotkit_router, prefix="/copilotkit")
router.include_router(dev_routes_router)
router.include_router(documents_router, prefix="/documents")
router.include_router(logging_router, prefix="/logs")
router.include_router(websocket_router, prefix="/ws") # Websocket routes typically have a /ws prefix

@router.get("/health", tags=["Routes"])
async def routes_health():
    """
    Health check endpoint for the routes API.
    """
    return {"status": "ok"}
