from fastapi import APIRouter

router = APIRouter()

@router.get("/health", tags=["Auth"])
async def auth_health():
    """
    Health check endpoint for the auth API.
    """
    return {"status": "ok"}
