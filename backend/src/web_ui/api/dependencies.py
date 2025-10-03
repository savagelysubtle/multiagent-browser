"""
Dependency injection for FastAPI routes.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from sqlalchemy.orm import Session

from ..database.sql.user import UserDatabase
from ..database.sql.user.models import User
from ..utils.logging_config import get_logger

logger = get_logger(__name__)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# In production, use proper secret key management
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"


def get_db() -> Session:
    """Get database session."""
    try:
        from ..database.session import SessionLocal

        logger.debug("Successfully imported SessionLocal from database.session")

        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    except ImportError as e:
        logger.error(f"Failed to import SessionLocal: {e}")
        logger.warning("Database session not available, using mock for development")
        from unittest.mock import MagicMock

        mock_db = MagicMock()
        yield mock_db
    except Exception as e:
        logger.error(f"Error creating database session: {e}")
        logger.warning("Using mock database session for development")
        from unittest.mock import MagicMock

        mock_db = MagicMock()
        yield mock_db


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        logger.debug("Attempting to decode JWT token.")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            logger.warning("JWT token is missing 'sub' (email) field.")
            raise credentials_exception
        logger.debug(f"Token decoded successfully for email: {email}")
    except jwt.PyJWTError as e:
        logger.warning(f"JWT decoding failed: {e}")
        raise credentials_exception

    try:
        user_db = UserDatabase()
        user = user_db.get_user_by_email(db, email)
        if user is None:
            logger.warning(f"User not found for email: {email}")
            raise credentials_exception

        logger.debug(f"Successfully authenticated user: {user.email}")
        return user
    except Exception as e:
        logger.error(f"Error accessing user database: {e}")
        # Return a mock user for development if database is not available
        logger.warning("Returning mock user for development")
        from ..database.sql.user.models import User

        mock_user = User(
            id="mock-user-id",
            email=email,
            name="Mock User",
            is_active=True,
            created_at="2024-01-01T00:00:00",
        )
        return mock_user
