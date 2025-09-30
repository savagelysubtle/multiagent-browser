"""
Authentication API routes for React frontend.

Provides JWT-based authentication endpoints including login, logout,
user management, and Google OAuth integration.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr

from ...database.user_state_manager import UserStateManager
from ...utils.logging_config import get_logger
from ..auth.auth_service import User, auth_service
from ..auth.dependencies import get_current_user
from ..auth.google_auth import get_google_oauth_status, google_callback, google_login

logger = get_logger(__name__)

# Create router
router = APIRouter(tags=["authentication"])

# User state manager for handling user preferences
user_state_manager = UserStateManager()


# Request/Response models
class LoginRequest(BaseModel):
    """Request model for user login."""

    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    """Request model for user registration."""

    email: EmailStr
    password: str
    name: str | None = None


class TokenResponse(BaseModel):
    """Response model for authentication tokens."""

    access_token: str
    token_type: str = "bearer"
    user: dict[str, Any]


class UserResponse(BaseModel):
    """Response model for user information."""

    id: str
    email: str
    name: str | None = None
    picture: str | None = None
    is_active: bool
    created_at: str
    last_login: str | None = None


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


class UserStateRequest(BaseModel):
    """Request model for user state updates."""

    state: dict[str, Any]


class PreferenceRequest(BaseModel):
    """Request model for preference updates."""

    key: str
    value: Any


# Authentication endpoints


@router.post("/dev-login", response_model=TokenResponse)
async def dev_login():
    """
    Development-only auto-login with admin credentials.

    Only available when ENV=development and admin credentials are configured.
    """
    try:
        env = os.getenv("ENV", "production")
        admin_email = os.getenv("ADMIN_EMAIL")

        if env != "development":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Endpoint not available in production",
            )

        if not admin_email:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Admin credentials not configured",
            )

        # Ensure admin user exists (create if needed)
        user = await auth_service.ensure_admin_user()
        if not user:
            # Try to get existing admin user
            user = await auth_service.get_user_by_email(admin_email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Admin user not found and could not be created",
            )

        # Generate access token
        access_token = auth_service.create_access_token(user.id)

        # Load user state or create default
        user_state = await user_state_manager.get_user_state(user.id)
        if not user_state:
            # Initialize default user state for admin
            default_state = {
                "preferences": {
                    "theme": "dark",
                    "sidebarWidth": 250,
                    "editorFontSize": 14,
                },
                "workspace": {
                    "openDocuments": [],
                    "activeDocument": None,
                    "recentFiles": [],
                },
                "agentSettings": {},
            }
            await user_state_manager.save_user_state(user.id, default_state)
            user_state = default_state

        logger.info(f"Development auto-login for admin user: {user.email}")

        return TokenResponse(
            access_token=access_token,
            user={
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "picture": user.picture,
                "is_active": user.is_active,
                "state": user_state,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Dev login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Development login failed",
        )


@router.post("/login", response_model=TokenResponse)
async def login(login_data: LoginRequest):
    """
    Authenticate user with email and password.

    Returns JWT access token on successful authentication.
    """
    try:
        user = await auth_service.authenticate_user(
            login_data.email, login_data.password
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )

        # Generate access token
        access_token = auth_service.create_access_token(user.id)

        # Load user state
        user_state = await user_state_manager.get_user_state(user.id) or {}

        logger.info(f"User logged in: {user.email}")

        return TokenResponse(
            access_token=access_token,
            user={
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "picture": user.picture,
                "is_active": user.is_active,
                "state": user_state,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed",
        )


@router.post("/register", response_model=TokenResponse)
async def register(register_data: RegisterRequest):
    """
    Register a new user account.

    Creates a new user and returns JWT access token.
    """
    try:
        # Check if user already exists
        existing_user = await auth_service.get_user_by_email(register_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Create new user
        user = await auth_service.create_user(
            email=register_data.email,
            password=register_data.password,
            name=register_data.name,
        )

        # Generate access token
        access_token = auth_service.create_access_token(user.id)

        # Initialize default user state
        default_state = {
            "preferences": {"theme": "dark", "sidebarWidth": 250, "editorFontSize": 14},
            "workspace": {
                "openDocuments": [],
                "activeDocument": None,
                "recentFiles": [],
            },
            "agentSettings": {},
        }
        await user_state_manager.save_user_state(user.id, default_state)

        logger.info(f"New user registered: {user.email}")

        return TokenResponse(
            access_token=access_token,
            user={
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "picture": user.picture,
                "is_active": user.is_active,
                "state": default_state,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        )


@router.post("/logout", response_model=MessageResponse)
async def logout(current_user: User = Depends(get_current_user)):
    """
    Logout current user.

    Note: JWT tokens can't be invalidated server-side without a blacklist.
    Client should remove the token.
    """
    try:
        logger.info(f"User logged out: {current_user.email}")
        return MessageResponse(message="Successfully logged out")

    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Logout failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current user information.

    Returns user details for authenticated user.
    """
    try:
        return UserResponse(
            id=current_user.id,
            email=current_user.email,
            name=current_user.name or "",
            picture=current_user.picture or "",
            is_active=current_user.is_active,
            created_at=current_user.created_at.isoformat(),
            last_login=current_user.last_login.isoformat()
            if current_user.last_login
            else None,
        )

    except Exception as e:
        logger.error(f"Get user info error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information",
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(current_user: User = Depends(get_current_user)):
    """
    Refresh user access token.

    Generates a new JWT token for the current user.
    """
    try:
        # Generate new access token
        access_token = auth_service.create_access_token(current_user.id)

        # Get current user state
        user_state = await user_state_manager.get_user_state(current_user.id) or {}

        logger.info(f"Token refreshed for user: {current_user.email}")

        return TokenResponse(
            access_token=access_token,
            user={
                "id": current_user.id,
                "email": current_user.email,
                "name": current_user.name,
                "picture": current_user.picture,
                "is_active": current_user.is_active,
                "state": user_state,
            },
        )

    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed",
        )


# User state management endpoints


@router.get("/state")
async def get_user_state(current_user: User = Depends(get_current_user)):
    """
    Get user's application state.

    Returns all stored user preferences and workspace state.
    """
    try:
        state = await user_state_manager.get_user_state(current_user.id)
        return {"state": state or {}}

    except Exception as e:
        logger.error(f"Get user state error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user state",
        )


@router.put("/state", response_model=MessageResponse)
async def update_user_state(
    state_data: UserStateRequest, current_user: User = Depends(get_current_user)
):
    """
    Update user's application state.

    Saves user preferences, workspace state, and agent settings.
    """
    try:
        success = await user_state_manager.save_user_state(
            current_user.id, state_data.state
        )

        if success:
            return MessageResponse(message="User state updated successfully")
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save user state",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update user state error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user state",
        )


@router.put("/preferences", response_model=MessageResponse)
async def update_user_preference(
    preference_data: PreferenceRequest, current_user: User = Depends(get_current_user)
):
    """
    Update a specific user preference.

    Updates individual preference key-value pairs.
    """
    try:
        success = await user_state_manager.update_user_preference(
            current_user.id, preference_data.key, preference_data.value
        )

        if success:
            return MessageResponse(
                message=f"Preference '{preference_data.key}' updated successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update preference",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update preference error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preference",
        )


# Google OAuth endpoints (ready for future activation)


@router.get("/google/login")
async def google_oauth_login(request: Request):
    """
    Initiate Google OAuth login flow.

    Only available when Google SSO is enabled.
    """
    try:
        return await google_login(request)

    except Exception as e:
        logger.error(f"Google login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google login failed",
        )


@router.get("/google/callback")
async def google_oauth_callback(request: Request):
    """
    Handle Google OAuth callback.

    Processes Google authentication response and creates/updates user.
    """
    try:
        return await google_callback(request)

    except Exception as e:
        logger.error(f"Google callback error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google authentication failed",
        )


@router.get("/google/status")
async def google_oauth_status():
    """
    Get Google OAuth configuration status.

    Returns whether Google SSO is enabled and properly configured.
    """
    return get_google_oauth_status()


@router.delete("/user/{email}", response_model=MessageResponse)
async def delete_user_by_email_endpoint(email: EmailStr):
    """
    Delete a user by email.

    This is a development-only endpoint to facilitate account management.
    """
    env = os.getenv("ENV", "production")
    if env != "development":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not available in production",
        )

    try:
        success = await auth_service.delete_user_by_email(email)
        if success:
            return MessageResponse(message=f"User {email} deleted successfully")
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {email} not found",
            )
    except Exception as e:
        logger.error(f"Error deleting user {email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user {email}",
        )


# System endpoints


@router.get("/status")
async def auth_system_status():
    """
    Get authentication system status.

    Returns system health and configuration information.
    """
    try:
        user_stats = auth_service.get_user_stats()
        state_stats = user_state_manager.get_collection_stats()
        google_status = get_google_oauth_status()

        return {
            "status": "healthy",
            "users": user_stats,
            "user_states": state_stats,
            "google_oauth": google_status,
            "jwt_configured": bool(
                auth_service.secret_key != "dev-secret-key-change-in-production"
            ),
        }

    except Exception as e:
        logger.error(f"Auth status error: {e}")
        return {"status": "error", "error": str(e)}
