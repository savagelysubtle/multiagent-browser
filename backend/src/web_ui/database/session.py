"""
Database session management for SQLAlchemy.
"""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from ..utils.logging_config import get_logger

logger = get_logger(__name__)

# Database configuration - use absolute path for SQLite
project_root = Path(__file__).parent.parent.parent.parent
database_path = project_root / "data" / "users.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{database_path}")

logger.info(f"Database URL: {DATABASE_URL}")

def get_db() -> Session:
    """Get database session."""
    try:
        # Ensure the data directory exists
        database_path.parent.mkdir(parents=True, exist_ok=True)

        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False},
            echo=False  # Set to True for SQL debugging
        )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        logger.info("Database session created successfully")
        return db
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise