"""
CopilotKit integration endpoints for the Web-UI.

Provides endpoints compatible with CopilotKit's agent protocol.
"""

import json
import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ...agent.document_editor import DocumentEditingAgent
from ...utils.logging_config import get_logger
from ..dependencies import get_document_agent
from ...agent.orchestrator.simple_orchestrator import SimpleAgentOrchestrator
from ..dependencies import get_orchestrator
from ag_ui.core import (
    RunAgentInput,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
)

logger = get_logger(__name__)

# Create router
router = APIRouter()

# --- CopilotKit Compatible Models ---

class CopilotKitMessage(BaseModel):
    """CopilotKit message format."""
    id: Optional[str] = None
    role: str
    content: str
    name: Optional[str] = None

class CopilotKitRequest(BaseModel):
    """CopilotKit request format."""
    messages: List[CopilotKitMessage]
    model: Optional[str] = "gpt-4"
    stream: bool = True
    tools: Optional[List[Dict[str, Any]]] = None
    temperature: Optional[float] = 0.7

# --- CopilotKit Endpoints ---

@router.post("/info")
async def copilotkit_info(
    request: Request, orchestrator: SimpleAgentOrchestrator = Depends(get_orchestrator)
):
    """CopilotKit info endpoint that returns available agents and actions."""
    try:
        # Get available agents from orchestrator
        available_agents = orchestrator.get_available_agents()

        # Format response according to CopilotKit expectations
        agents = []
        actions = []

        for agent_info in available_agents:
            # Add agent info
            agents.append(
                {
                    "name": agent_info["type"],
                    "description": agent_info["description"],
                    "type": "agent",
                }
            )

            # Add agent actions
            for action in agent_info.get("actions", []):
                actions.append(
                    {
                        "name": f"{agent_info['type']}.{action['name']}",
                        "description": action["description"],
                        "parameters": action.get("parameters", []),
                    }
                )

        return {
            "actions": actions,
            "agents": agents,
            "sdkVersion": "1.0.0",  # Version of our implementation
        }
    except Exception as e:
        return {"actions": [], "agents": [], "sdkVersion": "1.0.0", "error": str(e)}

@router.post("/")
async def copilotkit_chat(
    request_data: dict,
    agent: DocumentEditingAgent = Depends(get_document_agent),
):
    """
    CopilotKit compatible chat endpoint.

    This endpoint accepts CopilotKit format requests and returns streaming responses
    compatible with the OpenAI chat completions API format that CopilotKit expects.
    """
    try:
        if not agent:
            raise HTTPException(status_code=503, detail="Document agent not available")

        # Parse the request data
        messages = request_data.get("messages", [])
        stream = request_data.get("stream", True)
        model = request_data.get("model", "gpt-4")

        # Get the last user message
        user_message_content = ""
        if messages:
            for message in reversed(messages):
                if message.get("role") == "user":
                    user_message_content = message.get("content", "")
                    break

        if not user_message_content:
            user_message_content = "Hello"

        # If streaming is requested (default for CopilotKit)
        if stream:
            async def generate_response() -> AsyncGenerator[str, None]:
                try:
                    # Use the document agent's chat functionality
                    response = await agent.chat_with_user(
                        message=user_message_content,
                        context_document_id=None
                    )

                    chunk_id = f"chatcmpl-{int(time.time())}"

                    # Stream each word/token
                    words = response.split()
                    for i, word in enumerate(words):
                        chunk = {
                            "id": chunk_id,
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": model,
                            "choices": [{
                                "index": 0,
                                "delta": {
                                    "content": word + (" " if i < len(words) - 1 else "")
                                },
                                "finish_reason": None
                            }]
                        }

                        yield f"data: {json.dumps(chunk)}\n\n"

                    # Send final chunk
                    final_chunk = {
                        "id": chunk_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }]
                    }

                    yield f"data: {json.dumps(final_chunk)}\n\n"
                    yield "data: [DONE]\n\n"

                except Exception as e:
                    logger.error(f"Error in CopilotKit chat stream: {e}", exc_info=True)
                    error_chunk = {
                        "error": {
                            "message": str(e),
                            "type": "internal_error"
                        }
                    }
                    yield f"data: {json.dumps(error_chunk)}\n\n"

            return StreamingResponse(
                generate_response(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Methods": "*",
                }
            )

        else:
            # Non-streaming response
            response = await agent.chat_with_user(
                message=user_message_content,
                context_document_id=None
            )

            return {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            }

    except Exception as e:
        logger.error(f"Error in CopilotKit chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@router.options("/")
async def copilotkit_options():
    """Handle CORS preflight requests for CopilotKit."""
    return {
        "message": "CORS preflight OK"
    }

@router.get("/health")
async def copilotkit_health():
    """Health check for CopilotKit integration."""
    return {
        "status": "healthy",
        "service": "copilotkit-integration",
        "timestamp": int(time.time())
    }
