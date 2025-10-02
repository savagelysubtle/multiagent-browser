import json
import uuid

from ag_ui.core import (
    RunAgentInput,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
)
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from ..agent.orchestrator.simple_orchestrator import SimpleAgentOrchestrator
from ..dependencies import get_orchestrator

router = APIRouter()


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


@router.post("")  # Changed from "/copilotkit" to "" to avoid redundant path
async def copilotkit_endpoint(
    request: Request, orchestrator: SimpleAgentOrchestrator = Depends(get_orchestrator)
):
    """Endpoint for CopilotKit frontend to communicate with the backend LLM."""
    raw_body = await request.json()
    messages = raw_body.get("messages", [])

    user_message_content = ""
    if messages:
        # Get the last user message
        for message in reversed(messages):
            if message.get("role") == "user":
                user_message_content = message.get("content", "")
                break

    if not user_message_content:
        return StreamingResponse(
            (
                f"data: {json.dumps({'type': 'error', 'content': 'No user message found.'})}\n\n"
            ),
            media_type="text/event-stream",
        )

    # For now, using a hardcoded user_id and generating thread_id/run_id
    user_id = "copilotkit_user"
    thread_id = "copilotkit_thread"
    run_id = str(uuid.uuid4())

    # Extract selected agent from query parameters
    selected_agent = request.query_params.get("agent", "document_editor")

    run_agent_input = RunAgentInput(
        thread_id=thread_id,
        run_id=run_id,
        messages=[
            {
                "role": "user",
                "content": user_message_content,
                "message_id": str(uuid.uuid4()),
            }
        ],
        metadata={
            "selectedAgent": selected_agent,  # Use selected_agent from query params
            "source": "copilotkit",
        },
    )

    async def generate_response_stream():
        async for event in orchestrator.handle_ag_ui_chat_input(
            run_agent_input, user_id, session_id=thread_id
        ):
            if isinstance(event, TextMessageStartEvent):
                yield f"data: {json.dumps({'type': 'start', 'content': ''})}\n\n"
            elif isinstance(event, TextMessageContentEvent):
                yield f"data: {json.dumps({'type': 'chunk', 'content': event.delta})}\n\n"
            elif isinstance(event, TextMessageEndEvent):
                yield f"data: {json.dumps({'type': 'end', 'content': ''})}\n\n"
            else:
                # Handle other event types if necessary, or log them
                print(f"Unhandled event type: {event.type}")

    return StreamingResponse(generate_response_stream(), media_type="text/event-stream")
