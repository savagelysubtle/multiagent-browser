from fastapi import APIRouter

router = APIRouter()

@router.get("/health", tags=["Middleware"])
async def middleware_health():
    """
    Health check endpoint for the middleware API.
    """
    return {"status": "ok"}
