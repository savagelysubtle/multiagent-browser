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
    logger.debug("get_db() called - creating database session")

    try:
        logger.debug("Attempting to import get_session_local from database.session")
        from ..database.session import get_session_local

        logger.debug("Successfully imported get_session_local from database.session")

        logger.debug("Calling get_session_local() to get session factory")
        SessionLocal = get_session_local()

        logger.debug("Creating database session instance")
        db = SessionLocal()

        logger.debug("Database session created successfully, yielding to caller")
        try:
            yield db
        finally:
            logger.debug("Closing database session")
            db.close()
            logger.debug("Database session closed successfully")

    except ImportError as e:
        logger.error(f"Failed to import get_session_local: {e}")
        logger.error(f"ImportError details: {type(e).__name__}: {e.args}")
        logger.error("Database session not available, using mock for development")
        logger.warning(
            "Check if database session module exists and imports are correct"
        )
        from unittest.mock import MagicMock

        mock_db = MagicMock()
        logger.debug("Using mock database session for development")
        yield mock_db

    except Exception as e:
        logger.error(f"Error creating database session: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception args: {e.args}")
        logger.error("Using mock database session for development")
        logger.debug("Full exception traceback:", exc_info=True)
        from unittest.mock import MagicMock

        mock_db = MagicMock()
        logger.debug("Using mock database session for development")
        yield mock_db


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user."""
    logger.debug("get_current_user() called - validating JWT token")
    logger.debug(f"Token length: {len(token)} characters")

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        logger.debug("Attempting to decode JWT token.")
        logger.debug(f"Using SECRET_KEY: {SECRET_KEY[:10]}... (truncated)")
        logger.debug(f"Using ALGORITHM: {ALGORITHM}")

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")

        logger.debug(f"JWT payload keys: {list(payload.keys())}")
        logger.debug(f"JWT expiration: {payload.get('exp', 'Not set')}")
        logger.debug(f"JWT issued at: {payload.get('iat', 'Not set')}")

        if email is None:
            logger.warning("JWT token is missing 'sub' (email) field.")
            logger.debug(f"JWT payload: {payload}")
            raise credentials_exception

        logger.debug(f"Token decoded successfully for email: {email}")
        logger.info(f"JWT validation successful for user: {email}")

    except jwt.ExpiredSignatureError as e:
        logger.warning(
            f"JWT token expired for email: {email if 'email' in locals() else 'unknown'}"
        )
        logger.error(f"JWT ExpiredSignatureError: {e}")
        raise credentials_exception
    except jwt.JWTError as e:
        logger.warning(f"JWT decoding failed: {e}")
        logger.error(f"JWT Error type: {type(e).__name__}")
        logger.error(f"JWT Error args: {e.args}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Unexpected error during JWT decoding: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.debug("Full exception traceback:", exc_info=True)
        raise credentials_exception

    try:
        logger.debug(f"Looking up user in database: {email}")
        user_db = UserDatabase()

        logger.debug("Calling user_db.get_user_by_email()")
        user = user_db.get_user_by_email(db, email)

        if user is None:
            logger.warning(f"User not found for email: {email}")
            logger.warning("This could indicate:")
            logger.warning("  - User doesn't exist in database")
            logger.warning("  - Database connection issue")
            logger.warning("  - Email field mismatch in database")
            raise credentials_exception

        logger.debug(f"Successfully authenticated user: {user.email} (ID: {user.id})")
        logger.info(f"User authentication successful: {user.email}")
        return user

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error accessing user database for email {email}: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception args: {e.args}")
        logger.debug("Full exception traceback:", exc_info=True)

        # Return a mock user for development if database is not available
        logger.warning(
            f"Returning mock user for development due to database error: {email}"
        )
        from ..database.sql.user.models import User

        mock_user = User(
            id="mock-user-id",
            email=email,
            name="Mock User",
            is_active=True,
            created_at="2024-01-01T00:00:00",
        )
        logger.debug("Mock user created for development")
        return mock_user
