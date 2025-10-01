
import uuid
from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from ag_ui.core import (
    RunAgentInput,
    EventType,
    RunStartedEvent,
    RunFinishedEvent,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
)
from ag_ui.encoder import EventEncoder

from ...agent.orchestrator.simple_orchestrator import SimpleAgentOrchestrator
from ..dependencies import get_orchestrator
from ...utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.post("/chat")
async def agentic_chat_endpoint(
    input_data: RunAgentInput,
    request: Request,
    orchestrator: SimpleAgentOrchestrator = Depends(get_orchestrator),
):
    """Agentic chat endpoint"""
    logger.info(f"Received AG-UI chat request: {input_data.run_id}")
    logger.debug(f"AG-UI input_data: {input_data.model_dump_json()}")

    accept_header = request.headers.get("accept")
    encoder = EventEncoder(accept=accept_header)

    async def event_generator():
        logger.debug(f"Starting AG-UI event stream for run_id: {input_data.run_id}")
        # Yield RunStartedEvent immediately
        yield encoder.encode(
            RunStartedEvent(
                type=EventType.RUN_STARTED,
                thread_id=input_data.thread_id,
                run_id=input_data.run_id,
            )
        )
        logger.debug(f"Yielded RunStartedEvent for run_id: {input_data.run_id}")

        user_id = input_data.thread_id # Placeholder: In a real app, get user_id from auth

        try:
            # Call the orchestrator to handle the AG-UI input and stream events
            async for event in orchestrator.handle_ag_ui_chat_input(input_data, user_id):
                logger.debug(f"Yielding event from orchestrator: {event.type} for run_id: {input_data.run_id}")
                yield encoder.encode(event)
        except Exception as e:
            logger.error(f"Error during AG-UI event streaming for run_id {input_data.run_id}: {e}", exc_info=True)
            # Attempt to send an error event if possible
            error_message_id = str(uuid.uuid4())
            yield encoder.encode(
                TextMessageStartEvent(
                    type=EventType.TEXT_MESSAGE_START,
                    message_id=error_message_id,
                    role="assistant",
                )
            )
            yield encoder.encode(
                TextMessageContentEvent(
                    type=EventType.TEXT_MESSAGE_CONTENT,
                    message_id=error_message_id,
                    delta=f"An error occurred: {str(e)}",
                )
            )
            yield encoder.encode(
                TextMessageEndEvent(
                    type=EventType.TEXT_MESSAGE_END,
                    message_id=error_message_id,
                )
            )

        # Yield RunFinishedEvent
        yield encoder.encode(
            RunFinishedEvent(
                type=EventType.RUN_FINISHED,
                thread_id=input_data.thread_id,
                run_id=input_data.run_id,
            )
        )
        logger.debug(f"Yielded RunFinishedEvent for run_id: {input_data.run_id}")

    return StreamingResponse(event_generator(), media_type=encoder.get_content_type())
