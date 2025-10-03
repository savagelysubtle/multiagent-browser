"""
Authentication dependencies for FastAPI routes.

Provides dependency injection for user authentication and authorization.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ...utils.logging_config import get_logger
from .auth_service import User, auth_service

logger = get_logger(__name__)

# Security configuration
security = HTTPBearer(auto_error=False)  # Don't auto-error on missing tokens


from sqlalchemy.orm import Session
from ...database.session import get_db

# ... (rest of the imports)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Get the current authenticated user from JWT token.

    This dependency can be used in FastAPI routes to require authentication.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        token = credentials.credentials
        user_id = auth_service.verify_token(token)

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Get user from database
        user = await auth_service.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
            )

        # Update last login
        await auth_service.update_last_login(db, user_id)

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_current_user: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User | None:
    """
    Get the current user if authenticated, otherwise return None.

    This dependency allows routes to be accessed by both authenticated and anonymous users.
    """
    if not credentials:
        return None

    try:
        token = credentials.credentials
        user_id = auth_service.verify_token(token)

        if not user_id:
            return None

        user = await auth_service.get_user_by_id(db, user_id)
        if not user or not user.is_active:
            return None

        # Update last login
        await auth_service.update_last_login(db, user_id)

        return user

    except Exception as e:
        logger.warning(f"Error in get_optional_user: {e}")
        return None
