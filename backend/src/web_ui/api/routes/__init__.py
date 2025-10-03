"""API routes module for React frontend integration."""

from .auth import router as auth_router
from .router import router

__all__ = ["auth_router", "router"]
