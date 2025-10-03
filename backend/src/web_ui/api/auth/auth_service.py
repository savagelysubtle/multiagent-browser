"""
Authentication Service for React Frontend Integration.

This service provides JWT-based authentication with user management
and SQLite integration for persistent user storage.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any

from uuid import uuid4
from fastapi.security import HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from ...database.sql.user import UserDatabase
from ...utils.logging_config import get_logger

logger = get_logger(__name__)

# Password hashing - use pbkdf2_sha256 for compatibility
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
logger.info("Using pbkdf2_sha256 for password hashing (bcrypt compatibility issues)")

# Security configuration
security = HTTPBearer()


class User(BaseModel):
    """User model for authentication."""

    id: str
    email: str
    name: str | None = None
    picture: str | None = None
    is_active: bool = True
    created_at: datetime
    last_login: datetime | None = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class AuthService:
    """Authentication service with JWT and user management."""

    def __init__(self):
        """Initialize the authentication service."""
        self.secret_key = os.getenv("JWT_SECRET", "dev-secret-key-change-in-production")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 1440  # 24 hours

        logger.info("AuthService initialized")

    async def ensure_admin_user(self, db: Session):
        """Create admin user if it doesn't exist and we're in development mode."""
        try:
            env = os.getenv("ENV", "production")
            admin_email = os.getenv("ADMIN_EMAIL")
            admin_password = os.getenv("ADMIN_PASSWORD")
            admin_name = os.getenv("ADMIN_NAME", "Administrator")

            logger.info(f"Environment: {env}, Admin Email: {admin_email}, Password Set: {bool(admin_password)}")

            if env == "development" and admin_email and admin_password:
                # Check if admin user already exists
                existing_admin = await self.get_user_by_email(db, admin_email)
                if not existing_admin:
                    try:
                        admin_user = await self.create_user(
                            db=db, email=admin_email, password=admin_password, name=admin_name
                        )
                        logger.info(f"Created admin user: {admin_email}")
                        return admin_user
                    except Exception as e:
                        logger.error(f"Failed to create admin user: {e}")
                        return None
                else:
                    logger.info(f"Admin user already exists: {admin_email}")
                    return existing_admin
            else:
                logger.info("Admin user creation skipped - not in development mode or missing credentials")
            return None

        except Exception as e:
            logger.error(f"Error in admin user creation: {e}")
            return None

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Hash a password for storage."""
        # Ensure password is not too long for bcrypt (72 byte limit)
        if len(password.encode("utf-8")) > 72:
            logger.warning("Password truncated to 72 bytes for bcrypt compatibility")
            password = password[:72]
        return pwd_context.hash(password)

    def create_access_token(
        self, user_id: str, expires_delta: timedelta | None = None
    ) -> str:
        """Create a JWT access token for a user."""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=self.access_token_expire_minutes
            )

        to_encode = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access_token",
        }

        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> str | None:
        """Verify a JWT token and return the user ID."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id = payload.get("sub")
            token_type = payload.get("type", "access_token")

            if user_id is None or token_type != "access_token":
                return None

            return user_id
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            return None

    async def get_user_from_token(self, token: str) -> User | None:
        """Get a user from a JWT token."""
        user_id = self.verify_token(token)
        if not user_id:
            return None
        return await self.get_user_by_id(user_id)

    async def get_user_by_id(self, db: Session, user_id: str) -> User | None:
        """Get a user by their ID from SQLite."""
        try:
            user_db = UserDatabase()
            user_data = user_db.get_user_by_id(db, user_id)
            if user_data:
                # Convert datetime strings back to datetime objects
                if isinstance(user_data.created_at, str):
                    user_data.created_at = datetime.fromisoformat(
                        user_data.created_at
                    )
                if user_data.last_login and isinstance(
                    user_data.last_login, str
                ):
                    user_data.last_login = datetime.fromisoformat(
                        user_data.last_login
                    )

                # Remove password_hash before creating User object
                user_data_dict = user_data.__dict__.copy()
                user_data_dict.pop("password_hash", None)
                user_data_dict.pop("metadata", None)
                user_data_dict.pop("auth_provider", None)
                user_data_dict.pop("_sa_instance_state", None)

                return User(**user_data_dict)
            return None
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {e}")
            return None

    async def get_user_by_email(self, db: Session, email: str) -> User | None:
        """Get a user by their email from SQLite."""
        try:
            user_db = UserDatabase()
            user_data = user_db.get_user_by_email(db, email)
            if user_data:
                # Convert datetime strings back to datetime objects
                if isinstance(user_data.created_at, str):
                    user_data.created_at = datetime.fromisoformat(
                        user_data.created_at
                    )
                if user_data.last_login and isinstance(
                    user_data.last_login, str
                ):
                    user_data.last_login = datetime.fromisoformat(
                        user_data.last_login
                    )

                # Remove password_hash before creating User object
                user_data_dict = user_data.__dict__.copy()
                user_data_dict.pop("password_hash", None)
                user_data_dict.pop("metadata", None)
                user_data_dict.pop("auth_provider", None)
                user_data_dict.pop("_sa_instance_state", None)

                return User(**user_data_dict)
            return None
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            return None

    async def create_user(
        self,
        db: Session,
        email: str,
        name: str | None = None,
        picture: str | None = None,
        password: str | None = None,
    ) -> User:
        """Create a new user in SQLite."""
        try:
            user_db = UserDatabase()
            # Check if user already exists
            if await self.get_user_by_email(db, email):
                raise ValueError(f"User with email {email} already exists")

            # Hash password if provided
            password_hash = self.get_password_hash(password) if password else None

            # Create user in SQLite
            user_data = user_db.create_user(
                db=db,
                email=email,
                name=name or email.split("@")[0],
                password_hash=password_hash,
                picture=picture,
                auth_provider="local" if password else "google",
                metadata={},
            )

            # Convert created_at to datetime
            user_data.created_at = datetime.fromisoformat(user_data.created_at)

            user = User(**user_data.__dict__)
            logger.info(f"Created new user: {email}")
            return user

        except Exception as e:
            logger.error(f"Error creating user {email}: {e}")
            raise

    async def create_or_update_user(
        self, db: Session, email: str, name: str | None = None, picture: str | None = None
    ) -> User:
        """Create or update a user (used for Google SSO)."""
        try:
            user_db = UserDatabase()
            existing_user = await self.get_user_by_email(db, email)

            if existing_user:
                # Update existing user
                user_db.update_user(
                    db,
                    existing_user.id,
                    name=name or existing_user.name,
                    picture=picture or existing_user.picture,
                    last_login=datetime.utcnow().isoformat(),
                )

                logger.info(f"Updated existing user: {email}")
                # Return updated user
                updated_user = await self.get_user_by_id(db, existing_user.id)
                if updated_user:
                    return updated_user
                else:
                    # This shouldn't happen but handle it gracefully
                    raise RuntimeError(
                        f"Failed to retrieve updated user: {existing_user.id}"
                    )
            else:
                # Create new user
                return await self.create_user(db, email, name, picture)

        except Exception as e:
            logger.error(f"Error creating/updating user {email}: {e}")
            raise

    async def authenticate_user(self, db: Session, email: str, password: str) -> User | None:
        """Authenticate a user with email and password."""
        try:
            user_db = UserDatabase()
            # Get user data with password hash
            user_data = user_db.get_user_by_email(db, email)
            if not user_data:
                return None

            stored_password_hash = user_data.get("password_hash")
            if not stored_password_hash:
                logger.warning(f"User {email} has no password hash (may be OAuth only)")
                return None

            if not self.verify_password(password, stored_password_hash):
                return None

            # Update last login
            user_db.update_last_login(db, user_data.id)

            # Convert to User object
            user_data.created_at = datetime.fromisoformat(user_data.created_at)
            user_data.last_login = datetime.utcnow()

            # Remove password_hash before creating User object
            user_data_dict = user_data.__dict__.copy()
            user_data_dict.pop("password_hash", None)
            user_data_dict.pop("metadata", None)
            user_data_dict.pop("auth_provider", None)
            user_data_dict.pop("_sa_instance_state", None)

            return User(**user_data_dict)

        except Exception as e:
            logger.error(f"Error authenticating user {email}: {e}")
            return None

    async def update_last_login(self, db: Session, user_id: str) -> bool:
        """Update the user's last login timestamp."""
        try:
            user_db = UserDatabase()
            return user_db.update_last_login(db, user_id)
        except Exception as e:
            logger.error(f"Error updating last login for user {user_id}: {e}")
            return False

    async def delete_user(self, db: Session, user_id: str) -> bool:
        """Delete a user from the database."""
        try:
            user_db = UserDatabase()
            # First check if user exists
            user = await self.get_user_by_id(db, user_id)
            if not user:
                logger.warning(f"Attempted to delete non-existent user: {user_id}")
                return False

            # Delete user from SQLite
            success = user_db.delete_user(db, user_id)
            if success:
                logger.info(f"Deleted user: {user.email} (ID: {user_id})")
            else:
                logger.error(f"Failed to delete user: {user_id}")

            return success

        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            return False

    async def delete_user_by_email(self, db: Session, email: str) -> bool:
        """Delete a user by their email address."""
        try:
            user = await self.get_user_by_email(db, email)
            if not user:
                logger.warning(f"Attempted to delete non-existent user: {email}")
                return False

            return await self.delete_user(db, user.id)

        except Exception as e:
            logger.error(f"Error deleting user by email {email}: {e}")
            return False

    def get_user_stats(self, db: Session) -> dict[str, Any]:
        """Get user statistics."""
        try:
            user_db = UserDatabase()
            return {
                "total_users": user_db.get_user_count(db),
                "database_type": "SQLite",
                "last_updated": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {"error": str(e)}



# Global instance
auth_service = AuthService()
