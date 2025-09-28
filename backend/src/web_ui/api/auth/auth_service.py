"""
Authentication Service for React Frontend Integration.

This service provides JWT-based authentication with user management
and ChromaDB integration for persistent user state.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi.security import HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from ...database import ChromaManager, DocumentModel

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security configuration
security = HTTPBearer()


class User(BaseModel):
    """User model for authentication."""

    id: str
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class AuthService:
    """Authentication service with JWT and user management."""

    def __init__(self):
        """Initialize the authentication service."""
        self.secret_key = os.getenv("JWT_SECRET", "dev-secret-key-change-in-production")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 1440  # 24 hours
        self.chroma_manager = ChromaManager()
        self._ensure_users_collection()

        logger.info("AuthService initialized")

    def _ensure_users_collection(self):
        """Ensure the users collection exists in ChromaDB."""
        try:
            from ...database.models import CollectionConfig

            config = CollectionConfig(
                name="users",
                metadata={
                    "description": "User accounts and authentication data",
                    "type": "users",
                    "version": "1.0.0",
                    "created_at": datetime.now().isoformat(),
                },
                embedding_function=None,
            )
            self.chroma_manager.create_collection(config)
            logger.info("Users collection ensured in ChromaDB")
        except Exception as e:
            logger.error(f"Failed to ensure users collection: {e}")

    async def ensure_admin_user(self):
        """Create admin user if it doesn't exist and we're in development mode."""
        try:
            env = os.getenv("ENV", "production")
            admin_email = os.getenv("ADMIN_EMAIL")
            admin_password = os.getenv("ADMIN_PASSWORD")
            admin_name = os.getenv("ADMIN_NAME", "Administrator")

            if env == "development" and admin_email and admin_password:
                # Check if admin user already exists
                existing_admin = await self.get_user_by_email(admin_email)
                if not existing_admin:
                    try:
                        admin_user = await self.create_user(
                            email=admin_email, password=admin_password, name=admin_name
                        )
                        logger.info(f"Created admin user: {admin_email}")
                        return admin_user
                    except Exception as e:
                        logger.error(f"Failed to create admin user: {e}")
                        return None
                else:
                    logger.info(f"Admin user already exists: {admin_email}")
                    return existing_admin
            return None

        except Exception as e:
            logger.error(f"Error in admin user creation: {e}")
            return None

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Hash a password for storage."""
        return pwd_context.hash(password)

    def create_access_token(
        self, user_id: str, expires_delta: Optional[timedelta] = None
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

    def verify_token(self, token: str) -> Optional[str]:
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

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get a user by their ID from ChromaDB."""
        try:
            document = self.chroma_manager.get_document("users", user_id)
            if document:
                user_data = json.loads(
                    document.content
                )  # Use json.loads instead of eval
                # Convert datetime strings back to datetime objects
                if "created_at" in user_data and isinstance(
                    user_data["created_at"], str
                ):
                    user_data["created_at"] = datetime.fromisoformat(
                        user_data["created_at"]
                    )
                if (
                    "last_login" in user_data
                    and user_data["last_login"]
                    and isinstance(user_data["last_login"], str)
                ):
                    user_data["last_login"] = datetime.fromisoformat(
                        user_data["last_login"]
                    )
                return User(**user_data)
            return None
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {e}")
            return None

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by their email from ChromaDB."""
        try:
            from ...database.models import QueryRequest

            query_request = QueryRequest(
                query=f"email:{email}",
                collection_name="users",
                limit=1,
                metadata_filters={"email": email},
                distance_threshold=None,
            )

            results = self.chroma_manager.search(query_request)
            if results:
                user_data = json.loads(
                    results[0].content
                )  # Use json.loads instead of eval
                # Convert datetime strings back to datetime objects
                if "created_at" in user_data and isinstance(
                    user_data["created_at"], str
                ):
                    user_data["created_at"] = datetime.fromisoformat(
                        user_data["created_at"]
                    )
                if (
                    "last_login" in user_data
                    and user_data["last_login"]
                    and isinstance(user_data["last_login"], str)
                ):
                    user_data["last_login"] = datetime.fromisoformat(
                        user_data["last_login"]
                    )
                return User(**user_data)
            return None
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            return None

    async def create_user(
        self,
        email: str,
        name: Optional[str] = None,
        picture: Optional[str] = None,
        password: Optional[str] = None,
    ) -> User:
        """Create a new user in ChromaDB."""
        try:
            # Check if user already exists
            existing_user = await self.get_user_by_email(email)
            if existing_user:
                raise ValueError(f"User with email {email} already exists")

            user_id = str(uuid4())
            user_data = {
                "id": user_id,
                "email": email,
                "name": name or email.split("@")[0],
                "picture": picture,
                "is_active": True,
                "created_at": datetime.now().isoformat(),  # Store as ISO string
                "last_login": None,
            }

            # Store password hash if provided
            if password:
                user_data["password_hash"] = self.get_password_hash(password)

            # Create document in ChromaDB
            document = DocumentModel(
                id=user_id,
                content=json.dumps(user_data),  # Use json.dumps instead of str()
                metadata={
                    "email": email,
                    "name": user_data["name"],
                    "user_type": "regular",
                    "auth_provider": "local" if password else "google",
                    "created_at": user_data["created_at"],
                },
                source="auth_service",
                timestamp=datetime.now(),
            )

            success = self.chroma_manager.add_document("users", document)
            if success:
                # Convert created_at back to datetime for User object
                user_data["created_at"] = datetime.fromisoformat(
                    user_data["created_at"]
                )
                user = User(**user_data)
                logger.info(f"Created new user: {email}")
                return user
            else:
                raise RuntimeError("Failed to store user in database")

        except Exception as e:
            logger.error(f"Error creating user {email}: {e}")
            raise

    async def create_or_update_user(
        self, email: str, name: Optional[str] = None, picture: Optional[str] = None
    ) -> User:
        """Create or update a user (used for Google SSO)."""
        try:
            existing_user = await self.get_user_by_email(email)

            if existing_user:
                # Update existing user
                user_data = existing_user.dict()
                user_data["name"] = name or existing_user.name
                user_data["picture"] = picture or existing_user.picture
                user_data["last_login"] = datetime.now().isoformat()

                # Update document in ChromaDB
                document = DocumentModel(
                    id=existing_user.id,
                    content=json.dumps(user_data),  # Use json.dumps
                    metadata={
                        "email": email,
                        "name": user_data["name"],
                        "user_type": "regular",
                        "auth_provider": "google",
                        "updated_at": datetime.now().isoformat(),
                    },
                    source="auth_service",
                    timestamp=datetime.now(),
                )

                # Delete old and add updated
                self.chroma_manager.delete_document("users", existing_user.id)
                self.chroma_manager.add_document("users", document)

                # Convert datetime strings back to datetime objects
                user_data["created_at"] = datetime.fromisoformat(
                    user_data["created_at"]
                )
                user_data["last_login"] = datetime.fromisoformat(
                    user_data["last_login"]
                )

                logger.info(f"Updated existing user: {email}")
                return User(**user_data)
            else:
                # Create new user
                return await self.create_user(email, name, picture)

        except Exception as e:
            logger.error(f"Error creating/updating user {email}: {e}")
            raise

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user with email and password."""
        try:
            user = await self.get_user_by_email(email)
            if not user:
                return None

            # Get the stored password hash from the document
            document = self.chroma_manager.get_document("users", user.id)
            if not document:
                return None

            user_data = json.loads(document.content)  # Use json.loads instead of eval
            stored_password_hash = user_data.get("password_hash")

            if not stored_password_hash:
                logger.warning(f"User {email} has no password hash (may be OAuth only)")
                return None

            if not self.verify_password(password, stored_password_hash):
                return None

            # Update last login
            user_data["last_login"] = datetime.now().isoformat()
            updated_document = DocumentModel(
                id=user.id,
                content=json.dumps(user_data),  # Use json.dumps
                metadata=document.metadata,
                source="auth_service",
                timestamp=datetime.now(),
            )

            self.chroma_manager.delete_document("users", user.id)
            self.chroma_manager.add_document("users", updated_document)

            # Convert datetime string back to datetime object
            user_data["created_at"] = datetime.fromisoformat(user_data["created_at"])
            user_data["last_login"] = datetime.fromisoformat(user_data["last_login"])

            return User(**user_data)

        except Exception as e:
            logger.error(f"Error authenticating user {email}: {e}")
            return None

    async def update_last_login(self, user_id: str) -> bool:
        """Update the user's last login timestamp."""
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                return False

            document = self.chroma_manager.get_document("users", user_id)
            if not document:
                return False

            user_data = json.loads(document.content)  # Use json.loads instead of eval
            user_data["last_login"] = datetime.now().isoformat()

            updated_document = DocumentModel(
                id=user_id,
                content=json.dumps(user_data),  # Use json.dumps
                metadata=document.metadata,
                source="auth_service",
                timestamp=datetime.now(),
            )

            self.chroma_manager.delete_document("users", user_id)
            return self.chroma_manager.add_document("users", updated_document)

        except Exception as e:
            logger.error(f"Error updating last login for user {user_id}: {e}")
            return False

    def get_user_stats(self) -> Dict[str, Any]:
        """Get user statistics."""
        try:
            stats = self.chroma_manager.get_collection_stats("users")
            return {
                "total_users": stats.get("document_count", 0),
                "collection_name": "users",
                "last_updated": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {"error": str(e)}


# Global instance
auth_service = AuthService()
