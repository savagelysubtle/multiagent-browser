
from fastapi import APIRouter, Depends, HTTPException
from ...database.user_db import UserDatabase
from ..dependencies import get_user_db

router = APIRouter()

@router.post("/dev/clear-users", tags=["Development"])
async def clear_users(db: UserDatabase = Depends(get_user_db)):
    """
    Clear all users from the database. This is a development-only endpoint.
    """
    try:
        deleted_count = db.clear_all_users()
        return {"message": f"Successfully deleted {deleted_count} users."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
