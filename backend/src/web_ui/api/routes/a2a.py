"""FastAPI router exposing the Google A2A JSON-RPC surface."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import ValidationError
from starlette.responses import JSONResponse

from ...agent.a2a import (
    JSONRPCError,
    JSONRPCRequest,
    JSONRPCResponse,
    MessageSendParams,
    TaskIdParams,
    TaskQueryParams,
)
from ...agent.orchestrator.simple_orchestrator import SimpleAgentOrchestrator
from ..dependencies import get_orchestrator

router = APIRouter(prefix="/a2a/agents", tags=["a2a"])


def _success(id_value: Any, result: Any) -> JSONResponse:
    """Build a JSON-RPC success envelope."""

    response = JSONRPCResponse(id=id_value, result=result)
    return JSONResponse(
        status_code=200,
        content=response.dict(by_alias=True, exclude_none=True),
    )


def _error(id_value: Any, code: int, message: str, data: Any | None = None) -> JSONResponse:
    """Build a JSON-RPC error envelope."""

    response = JSONRPCResponse(
        id=id_value,
        error=JSONRPCError(code=code, message=message, data=data),
    )
    return JSONResponse(
        status_code=200,
        content=response.dict(by_alias=True, exclude_none=True),
    )


@router.post("/{agent_id}")
async def handle_jsonrpc(
    agent_id: str,
    request: Request,
    orchestrator: SimpleAgentOrchestrator = Depends(get_orchestrator),
):
    """Entry point for JSON-RPC 2.0 requests."""

    try:
        payload = await request.json()
    except Exception as exc:  # noqa: BLE001 - propagate JSON-RPC error envelope
        return _error(None, -32700, "Parse error", data=str(exc))

    try:
        rpc_request = JSONRPCRequest.parse_obj(payload)
    except ValidationError as exc:
        return _error(payload.get("id"), -32600, "Invalid request", data=exc.errors())

    method = rpc_request.method

    if method == "message/send":
        try:
            params = MessageSendParams.parse_obj(rpc_request.params or {})
        except ValidationError as exc:
            return _error(rpc_request.id, -32602, "Invalid params", data=exc.errors())

        try:
            result = await orchestrator.handle_a2a_message_send(agent_id, params, rpc_request.id)
        except NotImplementedError:
            return _error(rpc_request.id, -32004, "A2A message/send not implemented")
        except LookupError as exc:
            return _error(rpc_request.id, -32001, "Agent not found", data=str(exc))
        except Exception as exc:  # noqa: BLE001 - convert to JSON-RPC error
            return _error(rpc_request.id, -32000, "Server error", data=str(exc))

        return _success(rpc_request.id, result)

    if method == "tasks/get":
        try:
            params = TaskQueryParams.parse_obj(rpc_request.params or {})
        except ValidationError as exc:
            return _error(rpc_request.id, -32602, "Invalid params", data=exc.errors())

        try:
            result = await orchestrator.handle_a2a_tasks_get(params)
        except NotImplementedError:
            return _error(rpc_request.id, -32004, "A2A tasks/get not implemented")
        except LookupError as exc:
            return _error(rpc_request.id, -32001, "Task not found", data=str(exc))
        except Exception as exc:  # noqa: BLE001
            return _error(rpc_request.id, -32000, "Server error", data=str(exc))

        return _success(rpc_request.id, result)

    if method == "tasks/cancel":
        try:
            params = TaskIdParams.parse_obj(rpc_request.params or {})
        except ValidationError as exc:
            return _error(rpc_request.id, -32602, "Invalid params", data=exc.errors())

        try:
            result = await orchestrator.handle_a2a_tasks_cancel(params)
        except NotImplementedError:
            return _error(rpc_request.id, -32004, "A2A tasks/cancel not implemented")
        except LookupError as exc:
            return _error(rpc_request.id, -32001, "Task not found", data=str(exc))
        except Exception as exc:  # noqa: BLE001
            return _error(rpc_request.id, -32000, "Server error", data=str(exc))

        return _success(rpc_request.id, result)

    return _error(rpc_request.id, -32601, "Method not found", data={"method": method})
