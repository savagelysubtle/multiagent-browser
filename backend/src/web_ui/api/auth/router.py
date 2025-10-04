"""
Authentication routes for user login, registration, and state management.
"""

import os
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...database.sql.user import UserDatabase
from ...database.sql.user.models import User
from ...utils.logging_config import get_logger
from ..dependencies import get_current_user, get_db

logger = get_logger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


router = APIRouter(tags=["authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# In production, use proper secret key management
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


# Pydantic models for request bodies
class UserCreate(BaseModel):
    email: str
    password: str
    name: str | None = None


class UserLogin(BaseModel):
    email: str
    password: str


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@router.post("/login")
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return access token."""
    logger.info(f"Login attempt for email: {credentials.email}")
    logger.debug(
        f"Login request details: email={credentials.email}, password_length={len(credentials.password)}"
    )

    try:
        logger.debug("Initializing UserDatabase for authentication")
        user_db = UserDatabase()

        logger.debug(f"Attempting to authenticate user: {credentials.email}")
        user = user_db.authenticate_user(db, credentials.email, credentials.password)

        if not user:
            logger.warning(
                f"Authentication failed for email: {credentials.email} - user not found or password incorrect"
            )
            logger.debug(f"Database query result: user={user}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.debug(
            f"Authentication successful for user: {user.email} (ID: {user.id})"
        )
        logger.info(f"User {user.email} successfully logged in.")

        # Update last login
        try:
            logger.debug(f"Updating last login for user ID: {user.id}")
            user_db.update_last_login(db, str(user.id))
            logger.debug("Last login updated successfully")
        except Exception as login_error:
            logger.error(
                f"Failed to update last login for user {user.id}: {login_error}"
            )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Login error for {credentials.email}: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception args: {e.args}")
        logger.debug("Full exception traceback:", exc_info=True)

        # For development, return a mock successful login
        logger.warning("Returning mock login response for development due to error")
        user = type(
            "MockUser",
            (),
            {
                "id": "mock-user-id",
                "email": credentials.email,
                "name": "Mock User",
                "picture": None,
                "is_active": True,
                "created_at": "2024-01-01T00:00:00",
            },
        )()

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": getattr(user, "id", "mock-user-id")},
        expires_delta=access_token_expires,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(getattr(user, "id", "mock-user-id")),
            "email": user.email,
            "name": getattr(user, "name", "Mock User"),
            "picture": getattr(user, "picture", None),
            "is_active": getattr(user, "is_active", True),
            "created_at": getattr(user, "created_at", "2024-01-01T00:00:00"),
        },
    }


@router.post("/register")
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    logger.info(f"Registration attempt for email: {user_data.email}")
    logger.debug(
        f"Registration data: email={user_data.email}, name={user_data.name}, password_length={len(user_data.password)}"
    )

    try:
        logger.debug("Initializing UserDatabase for registration")
        user_db = UserDatabase()

        # Check if user already exists
        logger.debug(f"Checking if user already exists: {user_data.email}")
        existing_user = user_db.get_user_by_email(db, user_data.email)

        if existing_user:
            logger.warning(
                f"Registration failed: Email {user_data.email} already exists (existing user ID: {existing_user.id})"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        logger.debug(f"Creating new user: {user_data.email}")
        # Create new user with password hashing
        user = user_db.create_user(
            db, user_data.email, password=user_data.password, name=user_data.name
        )
        logger.info(f"User {user.email} successfully registered (ID: {user.id})")

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Registration error for {user_data.email}: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception args: {e.args}")
        logger.debug("Full exception traceback:", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed due to server error",
        )

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": str(user.id)},
        expires_delta=access_token_expires,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "is_active": user.is_active,
            "created_at": user.created_at,
        },
    }


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """Get current user information."""
    logger.debug(f"Fetching /me info for user: {current_user.email}")
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "name": current_user.name,
        "picture": current_user.picture,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
        "last_login": current_user.last_login,
    }


@router.get("/state")
async def get_user_state(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get current user's state."""
    logger.debug(f"Fetching state for user: {current_user.email}")
    user_db = UserDatabase()
    state = user_db.get_user_state(db, str(current_user.id))
    return {"state": state}


@router.put("/state")
async def update_user_state(
    state: dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update current user's state."""
    logger.info(f"Updating state for user: {current_user.email}")
    user_db = UserDatabase()
    success = user_db.save_user_state(db, str(current_user.id), state)
    if not success:
        logger.error(f"Failed to save state for user: {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save user state",
        )
    return {"success": True}


@router.put("/preferences")
async def update_user_preferences(
    preferences: dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update current user's preferences."""
    logger.info(f"Updating preferences for user: {current_user.email}")
    user_db = UserDatabase()

    # Get current state
    current_state = user_db.get_user_state(db, str(current_user.id)) or {}

    # Update preferences
    if "preferences" not in current_state:
        current_state["preferences"] = {}
    current_state["preferences"].update(preferences)

    # Save updated state
    success = user_db.save_user_state(db, str(current_user.id), current_state)
    if not success:
        logger.error(f"Failed to update preferences for user: {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences",
        )
    return {"success": True}


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Logout user (client-side token removal)."""
    logger.info(f"User {current_user.email} logged out.")
    return {"message": "Successfully logged out"}


@router.post("/refresh")
async def refresh_token(current_user: User = Depends(get_current_user)):
    """Refresh access token."""
    logger.info(f"Refreshing token for user: {current_user.email}")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user.email, "user_id": str(current_user.id)},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}


# Development-only route for clearing users
@router.post("/dev/clear-users")
async def clear_users():
    """Clear all users from the database (development only)."""
    if os.environ.get("NODE_ENV") != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available in development mode",
        )

    user_db = UserDatabase()
    count = user_db.clear_all_users()
    logger.warning(f"Cleared {count} users from database")
    return {"message": f"Cleared {count} users from database", "count": count}
