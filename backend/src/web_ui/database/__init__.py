"""
This package contains modules for database management, separating ChromaDB and SQL concerns.
"""

# Import sub-packages
from . import chroma
from . import sql
from . import utils

# Expose specific components from sub-packages
from .chroma import get_chroma_client, ChromaManager, DocumentPipeline
from .sql.user import UserDatabase as SQLDatabase
from .sql.user_state_manager import UserStateManager
from .utils.utils import DatabaseUtils
from .utils.mcp_config_manager import MCPConfigManager

__all__ = [
    "get_chroma_client",
    "ChromaManager",
    "SQLDatabase",
    "UserStateManager",
    "DatabaseUtils",
    "DocumentPipeline",
    "MCPConfigManager",
]
