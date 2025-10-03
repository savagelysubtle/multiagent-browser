"""
Development-only API routes for testing and debugging.
"""

import os
from fastapi import APIRouter, Depends, HTTPException
from ..dependencies import get_user_db
from ...database.sql.user.user_db import UserDatabase

router = APIRouter()

@router.post("/dev/clear-users", tags=["Development"])
def clear_users(db: UserDatabase = Depends(get_user_db)):
    """
    Clear all users from the database. This is a development-only endpoint.
    """
    if os.getenv("ENV") != "development":
        raise HTTPException(status_code=404, detail="Not Found")

    try:
        # Use the database instance directly since it has the clear method
        user_db = UserDatabase()
        deleted_count = user_db.clear_all_users()
        return {"message": f"Successfully deleted {deleted_count} users."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dev/database-status", tags=["Development"])
def get_database_status():
    """
    Get database status and connection information.
    """
    if os.getenv("ENV") != "development":
        raise HTTPException(status_code=404, detail="Not Found")

    try:
        from ...database.session import DATABASE_URL
        from ...database.sql.user.models import User, UserState
        user_db = UserDatabase()
        with user_db.get_session() as db:
            user_count = db.query(User).count()
            state_count = db.query(UserState).count()

        return {
            "database_url": DATABASE_URL,
            "database_type": "SQLite",
            "status": "connected",
            "user_count": user_count,
            "state_count": state_count,
        }
    except Exception as e:
        return {
            "database_url": DATABASE_URL,
            "database_type": "SQLite",
            "status": "error",
            "error": str(e),
        }