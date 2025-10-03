"""Authentication module for React frontend integration."""

from .auth_service import AuthService, User
from .router import router

__all__ = ["AuthService", "User", "router"]
