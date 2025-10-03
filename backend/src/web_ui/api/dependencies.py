"""
Shared dependencies for API routes.

Provides common dependencies like orchestrator instance, database connections, etc.
"""

from fastapi import Depends, HTTPException, Request

from ..agent.orchestrator.simple_orchestrator import SimpleAgentOrchestrator
from ..database.sql.user import UserDatabase
from .auth.auth_service import AuthService, User

# Global references to singleton instances, managed by the server's lifespan
_orchestrator: SimpleAgentOrchestrator | None = None
_user_db: UserDatabase | None = None
_auth_service: AuthService | None = None


def get_auth_service() -> AuthService:
    """Dependency to get the current auth service instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service


async def get_current_user(request: Request, auth_service: AuthService = Depends(get_auth_service)) -> User:
    """Dependency to get the current user from the request's token."""
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = token.replace("Bearer ", "")
    user = await auth_service.get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


def get_user_db() -> UserDatabase:
    """Dependency to get the current user database instance."""
    global _user_db
    if _user_db is None:
        _user_db = UserDatabase()
    return _user_db


def set_orchestrator(orchestrator: SimpleAgentOrchestrator) -> None:
    """Set the global orchestrator instance (called at startup)."""
    global _orchestrator
    _orchestrator = orchestrator


def get_orchestrator() -> SimpleAgentOrchestrator:
    """Dependency to get the current orchestrator instance."""
    if _orchestrator is None:
        raise HTTPException(
            status_code=503,
            detail="Orchestrator is not available or still initializing.",
        )
    return _orchestrator