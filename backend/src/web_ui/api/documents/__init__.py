
"""
This package contains modules for document-related API endpoints.
"""

from .general import router as general_documents_router
from .user import router as user_documents_router

__all__ = ["general_documents_router", "user_documents_router"]
