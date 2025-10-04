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
def get_database_url():
    """Get database URL, checking for existing database files."""
    try:
        from ..utils.paths import get_project_root
        project_root = get_project_root()
        database_path = project_root / "data" / "users.db"
    except ImportError:
        # Fallback to manual calculation if paths module not available
        # From backend/src/web_ui/database/session.py
        # Go up: database/ -> web_ui/ -> src/ -> backend/ -> project_root
        project_root = Path(__file__).parent.parent.parent.parent.parent
        database_path = project_root / "data" / "users.db"

    # Check if there's an existing dev.db file to use
    dev_db_path = project_root / "data" / "dev.db"
    if dev_db_path.exists():
        logger.info(f"Using existing database: {dev_db_path}")
        return f"sqlite:///{dev_db_path}"

    # Use users.db as default
    database_path.parent.mkdir(parents=True, exist_ok=True)
    return os.getenv("DATABASE_URL", f"sqlite:///{database_path}")

DATABASE_URL = get_database_url()
logger.info(f"Database URL: {DATABASE_URL}")

# Create engine and session factory LAZILY (only when first needed)
_engine = None
_SessionLocal = None

def get_engine():
    """Get or create database engine."""
    global _engine
    if _engine is None:
        try:
            _engine = create_engine(
                DATABASE_URL,
                connect_args={"check_same_thread": False},
                echo=False,  # Set to True for SQL debugging
            )
            logger.info("Database engine created successfully")
        except Exception as e:
            logger.error(f"Failed to create database engine: {e}")
            # Create mock objects for development if database fails
            from unittest.mock import MagicMock
            _engine = MagicMock()
            logger.warning("Using mock database engine for development")
    return _engine

def get_session_local():
    """Get or create session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        if engine:
            _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        else:
            # Create mock session factory
            from unittest.mock import MagicMock
            _SessionLocal = MagicMock()
    return _SessionLocal


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
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        logger.debug("Database session created")
        yield db
    finally:
        db.close()
        logger.debug("Database session closed")
