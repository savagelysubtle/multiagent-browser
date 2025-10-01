

import os
from fastapi import APIRouter, Depends, HTTPException
from ..dependencies import get_user_db
from ...database.user_db import UserDatabase

router = APIRouter()

@router.post("/dev/clear-users", tags=["Development"])
def clear_users(db: UserDatabase = Depends(get_user_db)):
    """
    Clear all users from the database. This is a development-only endpoint.
    """
    if os.getenv("ENV") != "development":
        raise HTTPException(status_code=404, detail="Not Found")
    try:
        deleted_count = db.clear_all_users()
        return {"message": f"Successfully deleted {deleted_count} users."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
