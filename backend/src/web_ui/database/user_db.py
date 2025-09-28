"""
SQLite User Database for Authentication.

This module provides a proper relational database for user authentication,
replacing the misuse of ChromaDB for user storage.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class UserDatabase:
    """SQLite database for user authentication and management."""

    def __init__(self, db_path: str | None = None):
        """Initialize the user database."""
        if db_path is None:
            # Default to data/users.db
            db_path_obj = Path("data/users.db")
        else:
            db_path_obj = Path(db_path)

        # Ensure directory exists
        db_path_obj.parent.mkdir(parents=True, exist_ok=True)

        self.db_path = str(db_path_obj)
        self._init_database()
        logger.info(f"User database initialized at: {self.db_path}")

    def _init_database(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    name TEXT,
                    password_hash TEXT,
                    picture TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    auth_provider TEXT DEFAULT 'local',
                    created_at TEXT NOT NULL,
                    last_login TEXT,
                    metadata TEXT
                )
            """)

            # Create indexes for fast lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_email
                ON users(email)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_created
                ON users(created_at)
            """)

            conn.commit()
            logger.debug("User database schema initialized")

    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper error handling."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            yield conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def create_user(
        self,
        email: str,
        name: str | None = None,
        password_hash: str | None = None,
        picture: str | None = None,
        auth_provider: str = "local",
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Create a new user."""
        user_id = str(uuid4())
        created_at = datetime.utcnow().isoformat()

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT INTO users (
                        id, email, name, password_hash, picture,
                        is_active, auth_provider, created_at, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        user_id,
                        email,
                        name,
                        password_hash,
                        picture,
                        1,
                        auth_provider,
                        created_at,
                        json.dumps(metadata) if metadata else None,
                    ),
                )

                conn.commit()

                logger.info(f"Created user: {email} (ID: {user_id})")

                return {
                    "id": user_id,
                    "email": email,
                    "name": name,
                    "picture": picture,
                    "is_active": True,
                    "auth_provider": auth_provider,
                    "created_at": created_at,
                    "last_login": None,
                }

        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                logger.warning(f"User already exists: {email}")
                raise ValueError(f"User with email {email} already exists")
            raise

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        """Get user by email address."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, email, name, password_hash, picture, is_active,
                       auth_provider, created_at, last_login, metadata
                FROM users
                WHERE email = ?
            """,
                (email,),
            )

            row = cursor.fetchone()

            if row:
                return self._row_to_user_dict(row)

            return None

    def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        """Get user by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, email, name, password_hash, picture, is_active,
                       auth_provider, created_at, last_login, metadata
                FROM users
                WHERE id = ?
            """,
                (user_id,),
            )

            row = cursor.fetchone()

            if row:
                return self._row_to_user_dict(row)

            return None

    def update_user(self, user_id: str, **kwargs) -> bool:
        """Update user fields."""
        allowed_fields = {"name", "picture", "is_active", "last_login", "metadata"}

        # Filter out invalid fields
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return False

        # Build update query
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values())
        values.append(user_id)

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)

                conn.commit()

                return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False

    def update_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp."""
        return self.update_user(user_id, last_login=datetime.utcnow().isoformat())

    def delete_user(self, user_id: str) -> bool:
        """Delete a user."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
                conn.commit()

                return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            return False

    def user_exists(self, email: str) -> bool:
        """Check if user exists by email."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT 1 FROM users WHERE email = ? LIMIT 1", (email,))

            return cursor.fetchone() is not None

    def get_user_count(self) -> int:
        """Get total number of users."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM users")
            return cursor.fetchone()[0]

    def _row_to_user_dict(self, row) -> dict[str, Any]:
        """Convert database row to user dictionary."""
        user_dict = {
            "id": row["id"],
            "email": row["email"],
            "name": row["name"],
            "password_hash": row["password_hash"],
            "picture": row["picture"],
            "is_active": bool(row["is_active"]),
            "auth_provider": row["auth_provider"],
            "created_at": row["created_at"],
            "last_login": row["last_login"],
        }

        # Parse metadata if present
        if row["metadata"]:
            try:
                user_dict["metadata"] = json.loads(row["metadata"])
            except json.JSONDecodeError:
                user_dict["metadata"] = {}
        else:
            user_dict["metadata"] = {}

        return user_dict

    def migrate_from_chroma(self, chroma_users: list[dict]) -> dict[str, int]:
        """Migrate users from ChromaDB to SQLite."""
        results = {"migrated": 0, "skipped": 0, "errors": 0}

        for user_data in chroma_users:
            try:
                # Check if user already exists
                if self.user_exists(user_data.get("email", "")):
                    results["skipped"] += 1
                    continue

                # Create user in SQLite
                self.create_user(
                    email=user_data["email"],
                    name=user_data.get("name"),
                    password_hash=user_data.get("password_hash"),
                    picture=user_data.get("picture"),
                    auth_provider=user_data.get("auth_provider", "local"),
                    metadata=user_data.get("metadata"),
                )

                results["migrated"] += 1

            except Exception as e:
                logger.error(f"Error migrating user {user_data.get('email')}: {e}")
                results["errors"] += 1

        logger.info(f"Migration complete: {results}")
        return results
