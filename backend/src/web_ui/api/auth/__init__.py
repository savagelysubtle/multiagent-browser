"""Authentication module for React frontend integration."""

from .auth_service import AuthService, User
from .dependencies import get_current_user
from .google_auth import setup_google_oauth

__all__ = ["AuthService", "User", "setup_google_oauth", "get_current_user"]
