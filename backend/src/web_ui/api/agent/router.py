from fastapi import APIRouter

router = APIRouter()

@router.get("/health", tags=["Agent"])
async def agent_health():
    """
    Health check endpoint for the agent API.
    """
    return {"status": "ok"}
