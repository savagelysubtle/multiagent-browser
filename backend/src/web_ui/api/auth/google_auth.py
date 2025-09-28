"""
Google OAuth integration for React frontend.

Provides Google SSO authentication routes and setup.
Ready for future activation via environment variables.
"""

import os
from typing import Any

from authlib.integrations.starlette_client import OAuth
from fastapi import FastAPI, HTTPException, Request, status

from ...utils.logging_config import get_logger
from .auth_service import auth_service

logger = get_logger(__name__)

# OAuth setup (ready but not active)
oauth = OAuth()


def setup_google_oauth(app: FastAPI) -> bool:
    """
    Setup Google OAuth integration.

    Only activates if ENABLE_GOOGLE_SSO environment variable is set to true.

    Args:
        app: FastAPI application instance

    Returns:
        bool: True if Google OAuth was configured, False otherwise
    """
    try:
        enable_google_sso = os.getenv("ENABLE_GOOGLE_SSO", "false").lower() == "true"

        if not enable_google_sso:
            logger.info("Google SSO is disabled (ENABLE_GOOGLE_SSO=false)")
            return False

        # Check required environment variables
        google_client_id = os.getenv("GOOGLE_CLIENT_ID")
        google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

        if not google_client_id or not google_client_secret:
            logger.warning(
                "Google SSO enabled but missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET"
            )
            return False

        # Configure OAuth
        oauth.register(
            name="google",
            client_id=google_client_id,
            client_secret=google_client_secret,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={
                "scope": "openid email profile",
                "redirect_uri": os.getenv(
                    "GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback"
                ),
            },
        )

        # Initialize OAuth with app
        oauth.init_app(app)

        logger.info("Google OAuth configured successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to setup Google OAuth: {e}")
        return False


# OAuth route handlers (will be added to FastAPI app when Google SSO is enabled)


async def google_login(request: Request) -> dict[str, Any]:
    """
    Initiate Google OAuth login flow.

    Args:
        request: FastAPI request object

    Returns:
        Dict containing redirect URL or error message
    """
    try:
        enable_google_sso = os.getenv("ENABLE_GOOGLE_SSO", "false").lower() == "true"

        if not enable_google_sso:
            return {
                "error": "Google SSO not enabled",
                "message": "Google SSO is currently disabled. Please contact your administrator.",
            }

        # Get the redirect URI for OAuth callback
        redirect_uri = request.url_for("google_callback")

        # Generate authorization URL
        authorization_url = await oauth.google.authorize_redirect(request, redirect_uri)

        return {
            "authorization_url": str(authorization_url.headers.get("location")),
            "message": "Redirect to Google for authentication",
        }

    except Exception as e:
        logger.error(f"Error in Google login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate Google login",
        )


async def google_callback(request: Request) -> dict[str, Any]:
    """
    Handle Google OAuth callback.

    Args:
        request: FastAPI request object containing OAuth response

    Returns:
        Dict containing access token and user info
    """
    try:
        enable_google_sso = os.getenv("ENABLE_GOOGLE_SSO", "false").lower() == "true"

        if not enable_google_sso:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Google SSO not enabled"
            )

        # Get the authorization token from Google
        token = await oauth.google.authorize_access_token(request)

        if not token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get authorization token from Google",
            )

        # Get user info from Google
        user_info = token.get("userinfo")
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user information from Google",
            )

        # Extract user details
        email = user_info.get("email")
        name = user_info.get("name", "")
        picture = user_info.get("picture", "")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not provided by Google",
            )

        # Create or update user in our system
        user = await auth_service.create_or_update_user(
            email=email, name=name, picture=picture
        )

        # Generate JWT access token
        access_token = auth_service.create_access_token(user.id)

        logger.info(f"Google OAuth successful for user: {email}")

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "picture": user.picture,
            },
            "message": "Authentication successful",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Google callback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed",
        )


def get_google_oauth_status() -> dict[str, Any]:
    """
    Get the current status of Google OAuth configuration.

    Returns:
        Dict containing OAuth status information
    """
    enable_google_sso = os.getenv("ENABLE_GOOGLE_SSO", "false").lower() == "true"
    has_client_id = bool(os.getenv("GOOGLE_CLIENT_ID"))
    has_client_secret = bool(os.getenv("GOOGLE_CLIENT_SECRET"))

    return {
        "enabled": enable_google_sso,
        "configured": enable_google_sso and has_client_id and has_client_secret,
        "client_id_set": has_client_id,
        "client_secret_set": has_client_secret,
        "redirect_uri": os.getenv(
            "GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback"
        ),
    }
