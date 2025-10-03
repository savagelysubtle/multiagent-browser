"""A2A (Agent-to-Agent) JSON-RPC router."""

from fastapi import APIRouter

from ...utils.logging_config import get_logger

# Temporarily comment out a2a model imports until Pydantic v2 migration is complete
# from ...agent.a2a import (
#     JSONRPCRequest,
#     JSONRPCResponse,
#     MessageSendParams,
#     TaskIdParams,
#     TaskQueryParams,
# )

logger = get_logger(__name__)

router = APIRouter(prefix="/a2a", tags=["A2A"])

# Temporarily disable A2A endpoints until Pydantic v2 migration is complete
# The endpoints will be re-enabled once the models are properly migrated


@router.get("/status")
async def a2a_status():
    """Get A2A interface status."""
    return {
        "status": "temporarily_disabled",
        "message": "A2A endpoints are disabled during Pydantic v2 migration",
        "available": False,
    }


# Commented out endpoints that depend on a2a models:
# @router.post("/agents/{agent_type}")
# async def a2a_message_send(
#     agent_type: str,
#     request: JSONRPCRequest,
#     orchestrator=Depends(get_orchestrator),
# ) -> JSONRPCResponse:
#     """Handle JSON-RPC message/send for a specific agent."""
#     try:
#         if request.method != "message/send":
#             return JSONRPCResponse(
#                 jsonrpc="2.0",
#                 id=request.id,
#                 error={
#                     "code": -32601,
#                     "message": f"Method '{request.method}' not found",
#                 },
#             )
#
#         params = MessageSendParams(**request.params)
#         task = await orchestrator.handle_a2a_message_send(
#             agent_type, params, request.id
#         )
#
#         return JSONRPCResponse(
#             jsonrpc="2.0",
#             id=request.id,
#             result=task.dict() if hasattr(task, 'dict') else task.__dict__,
#         )
#
#     except Exception as e:
#         logger.error(f"A2A message/send error: {e}", exc_info=True)
#         return JSONRPCResponse(
#             jsonrpc="2.0",
#             id=request.id,
#             error={
#                 "code": -32603,
#                 "message": f"Internal error: {str(e)}",
#             },
#         )

# Other commented endpoints...
# @router.post("/tasks/get")
# @router.post("/tasks/cancel")
