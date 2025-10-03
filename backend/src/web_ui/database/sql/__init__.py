"""
This package contains modules for SQL database management.
"""

from .user import UserDatabase as SQLDatabase

__all__ = ["SQLDatabase"]