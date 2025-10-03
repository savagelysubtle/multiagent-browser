"""
Database session management for SQLAlchemy.
"""

import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

try:
    from ..utils.logging_config import get_logger

    logger = get_logger(__name__)
except ImportError:
    # Fallback logging if centralized logging is not available
    import logging

    logger = logging.getLogger(__name__)
    logger.warning("Could not import centralized logging, using fallback")

# Database configuration - use absolute path for SQLite
try:
    from ..utils.paths import get_project_root
    project_root = get_project_root()
    database_path = project_root / "data" / "users.db"
except ImportError:
    # Fallback to manual calculation if paths module not available
    project_root = Path(__file__).parent.parent.parent.parent
    database_path = project_root / "data" / "users.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{database_path}")

logger.info(f"Database URL: {DATABASE_URL}")

# Ensure the data directory exists
database_path.parent.mkdir(parents=True, exist_ok=True)

# Create engine and session factory ONCE at module level (not per request!)
try:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,  # Set to True for SQL debugging
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info("Database engine created successfully")
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    # Create mock objects for development if database fails
    from unittest.mock import MagicMock

    engine = MagicMock()
    SessionLocal = MagicMock()
    logger.warning("Using mock database objects for development")

# For development, also support the existing database path
import os

if os.path.exists("./data/dev.db"):
    DATABASE_URL = "sqlite:///./data/dev.db"


def get_db() -> Generator[Session]:
    """
    FastAPI dependency that provides a database session.

    This function yields a database session that FastAPI will inject
    into route handlers via Depends(get_db). The session is automatically
    closed after the request completes.

    Yields:
        Session: SQLAlchemy database session

    Example:
        @router.post("/login")
        async def login(db: Session = Depends(get_db)):
            # Use db here
            user = db.query(User).filter(...).first()
    """
    db = SessionLocal()
    try:
        logger.debug("Database session created")
        yield db
    finally:
        db.close()
        logger.debug("Database session closed")
