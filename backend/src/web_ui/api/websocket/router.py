from fastapi import APIRouter

router = APIRouter()

@router.get("/health", tags=["WebSocket"])
async def websocket_health():
    """
    Health check endpoint for the websocket API.
    """
    return {"status": "ok"}
