"""
This package contains modules for ChromaDB management.
"""

from .connection import get_chroma_client
from .documents.chroma_manager import ChromaManager
from .documents.document_pipeline import DocumentPipeline

__all__ = [
    "get_chroma_client",
    "ChromaManager",
    "DocumentPipeline",
]