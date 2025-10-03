
"""
This package contains modules for the Web UI API.
"""

from .agent.router import router as agent_router
from .auth import router as auth_router
from .middleware import router as middleware_router
from .routes import router as routes_router
from .websocket import router as websocket_router
from .documents.general import router as general_documents_router
from .documents.user import router as user_documents_router

__all__ = [
    "agent_router",
    "auth_router",
    "middleware_router",
    "routes_router",
    "websocket_router",
    "general_documents_router",
    "user_documents_router",
]
