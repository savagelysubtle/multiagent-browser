"""
SQLAlchemy User Database for Authentication and User State.
"""

import json
from uuid import uuid4
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from web_ui.utils.logging_config import get_logger
from .models import Base, User, UserState

logger = get_logger(__name__)

class UserDatabase:
    """SQLite database for user authentication and management using SQLAlchemy."""

    def __init__(self, database_url: str = None):
        """Initialize the user database with proper engine configuration."""
        from ...session import DATABASE_URL

        self.database_url = database_url or DATABASE_URL
        self.engine = create_engine(
            self.database_url,
            connect_args={"check_same_thread": False},
            echo=False
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        # Create tables if they don't exist
        Base.metadata.create_all(bind=self.engine)
        logger.info("UserDatabase initialized and tables created")

    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()

    def user_exists(self, db: Session, email: str) -> bool:
        """Check if a user exists by email."""
        logger.debug(f"Checking if user exists with email: {email}")
        return self.get_user_by_email(db, email) is not None

    def create_user(self, db: Session, email: str, **kwargs) -> User:
        logger.info(f"Attempting to create user with email: {email}")
        user = User(id=str(uuid4()), email=email, created_at=datetime.utcnow().isoformat(), **kwargs)
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Successfully created user {user.id} with email {email}.")
        return user

    def get_user_by_email(self, db: Session, email: str) -> Optional[User]:
        logger.debug(f"Querying for user with email: {email}")
        user = db.query(User).filter(User.email == email).first()
        if user:
            logger.debug(f"Found user {user.id} for email: {email}")
        else:
            logger.debug(f"No user found for email: {email}")
        return user

    def get_user_by_id(self, db: Session, user_id: str) -> Optional[User]:
        logger.debug(f"Querying for user with ID: {user_id}")
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            logger.debug(f"Found user with ID: {user_id}")
        else:
            logger.debug(f"No user found with ID: {user_id}")
        return user

    def update_user(self, db: Session, user_id: str, **kwargs) -> bool:
        logger.info(f"Attempting to update user ID: {user_id}")
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            for key, value in kwargs.items():
                logger.debug(f"Updating user {user_id}: setting {key} to {value}")
                setattr(user, key, value)
            db.commit()
            logger.info(f"Successfully updated user {user_id}.")
            return True
        logger.warning(f"Update failed: User with ID {user_id} not found.")
        return False

    def update_last_login(self, db: Session, user_id: str) -> bool:
        """Update a user's last login timestamp."""
        logger.debug(f"Updating last_login for user ID: {user_id}")
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.last_login = datetime.utcnow().isoformat()
            db.commit()
            logger.info(f"Successfully updated last_login for user {user_id}.")
            return True
        logger.warning(f"last_login update failed: User with ID {user_id} not found.")
        return False

    def save_user_state(self, db: Session, user_id: str, state: Dict[str, Any]) -> bool:
        logger.debug(f"Saving state for user ID: {user_id}")
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            state_json = json.dumps(state, default=str)
            user_state = db.query(UserState).filter(UserState.user_id == user_id).first()
            if user_state:
                logger.debug(f"Updating existing state for user {user_id}.")
                user_state.state_json = state_json
            else:
                logger.debug(f"Creating new state for user {user_id}.")
                user_state = UserState(id=str(uuid4()), user_id=user_id, state_json=state_json)
                db.add(user_state)
            db.commit()
            logger.info(f"Successfully saved state for user {user_id}.")
            return True
        logger.warning(f"State save failed: User with ID {user_id} not found.")
        return False

    def get_user_state(self, db: Session, user_id: str) -> Optional[Dict[str, Any]]:
        logger.debug(f"Getting state for user ID: {user_id}")
        user_state = db.query(UserState).filter(UserState.user_id == user_id).first()
        if user_state:
            logger.debug(f"Found state for user {user_id}.")
            return json.loads(user_state.state_json)
        logger.debug(f"No state found for user {user_id}.")
        return None

    def clear_all_users(self) -> int:
        """Clear all users from the database (development only)."""
        try:
            with self.get_session() as db:
                count = db.query(User).count()
                db.query(User).delete()
                db.query(UserState).delete()
                db.commit()
                logger.info(f"Cleared {count} users from database")
                return count
        except Exception as e:
            logger.error(f"Error clearing users: {e}")
            return 0