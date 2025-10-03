"""
FastAPI application for web-ui backend.
"""

from .auth.router import router as auth_router

__all__ = ["auth_router"]
