"""
Simple Agent Orchestrator for per-user task management.

This orchestrator manages agent tasks with real-time WebSocket updates,
user isolation, and comprehensive error handling.
"""

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ag_ui.core import (
    RunAgentInput,
    EventType,
    RunStartedEvent,
    RunFinishedEvent,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
)

from ...utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class AgentTask:
    """Represents a task submitted to an agent."""

    id: str
    user_id: str
    agent_type: str
    action: str
    payload: dict[str, Any]
    status: str = "pending"  # pending, running, completed, failed, cancelled
    result: Any | None = None
    error: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    progress: dict[str, Any] | None = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.progress is None:
            self.progress = {"percentage": 0, "message": "Waiting to start"}


class SimpleAgentOrchestrator:
    """
    Simplified agent orchestration for per-user tasks.

    Features:
    - User-isolated task management
    - Real-time WebSocket notifications
    - Agent registration and discovery
    - Task lifecycle management
    - Error handling and recovery
    """

    def __init__(self, ws_manager=None):
        self.agents = {}  # agent_type -> agent_instance
        self.user_tasks: dict[str, list[str]] = {}  # user_id -> task_ids
        self.task_store: dict[str, AgentTask] = {}  # task_id -> task
        self.running_tasks: dict[str, asyncio.Task] = {}  # task_id -> asyncio.Task
        self.ws_manager = ws_manager
        self.max_concurrent_tasks = 5
        self.task_timeout = 300  # 5 minutes default timeout

    def register_agent(self, agent_type: str, agent_instance):
        """Register an agent for task execution."""
        self.agents[agent_type] = agent_instance
        logger.info(f"Registered agent: {agent_type}")

    def get_available_agents(self) -> list[dict[str, Any]]:
        """Get list of available agents and their capabilities."""
        return [
            {
                "type": "document_editor",
                "name": "Document Editor",
                "description": "Create and edit documents with AI assistance",
                "actions": [
                    {
                        "name": "create_document",
                        "description": "Create a new document",
                        "parameters": ["filename", "content", "document_type"],
                    },
                    {
                        "name": "edit_document",
                        "description": "Edit an existing document",
                        "parameters": ["document_id", "instruction"],
                    },
                    {
                        "name": "search_documents",
                        "description": "Search through documents",
                        "parameters": ["query", "limit"],
                    },
                ],
            },
            {
                "type": "browser_use",
                "name": "Browser Agent",
                "description": "Browse the web and extract information",
                "actions": [
                    {
                        "name": "browse",
                        "description": "Navigate to a URL and interact with it",
                        "parameters": ["url", "instruction"],
                    },
                    {
                        "name": "extract",
                        "description": "Extract specific information from a webpage",
                        "parameters": ["url", "selectors"],
                    },
                ],
            },
            {
                "type": "deep_research",
                "name": "Research Agent",
                "description": "Conduct in-depth research on topics",
                "actions": [
                    {
                        "name": "research",
                        "description": "Research a topic comprehensively",
                        "parameters": ["topic", "depth", "sources"],
                    }
                ],
            },
        ]

    async def handle_ag_ui_chat_input(
        self,
        input_data: RunAgentInput,
        user_id: str,
    ):
        """Handle incoming AG-UI chat input and stream events."""
        logger.info(f"Orchestrator received AG-UI chat input for run_id: {input_data.run_id}, user_id: {user_id}")
        logger.debug(f"AG-UI input_data: {input_data.model_dump_json()}")

        message_content = ""
        for message in input_data.messages:
            if message.role == "user" and message.content:
                message_content = message.content
                break

        message_content = ""
        for message in input_data.messages:
            if message.role == "user" and message.content:
                message_content = message.content
                break

        # Safely access metadata
        metadata = input_data.metadata if hasattr(input_data, "metadata") and input_data.metadata is not None else {}

        agent_type = metadata.get("selectedAgent") # Use 'selectedAgent' from frontend
        action = metadata.get("action")

        # Basic inference if not provided in metadata
        if not agent_type:
            lower_message = message_content.lower()
            if "browse" in lower_message or "website" in lower_message:
                agent_type = "browser_use"
                action = "browse" # Default action for browser
            elif "research" in lower_message or "topic" in lower_message:
                agent_type = "deep_research"
                action = "research" # Default action for research
            elif "document" in lower_message or "edit" in lower_message or "create" in lower_message:
                agent_type = "document_editor"
                action = "chat" # Default chat action for document editor
            else:
                agent_type = "document_editor" # Default fallback
                action = "chat" # Default chat action

        if not action:
            # Fallback action if agent_type was inferred but action wasn't
            if agent_type == "browser_use":
                action = "browse"
            elif agent_type == "deep_research":
                action = "research"
            else:
                action = "chat" # Default chat action

        logger.debug(f"Extracted message: '{message_content}', inferred agent_type: '{agent_type}', inferred action: '{action}'")

        # Basic inference if not provided in metadata
        if not agent_type:
            lower_message = message_content.lower()
            if "browse" in lower_message or "website" in lower_message:
                agent_type = "browser_use"
                action = "browse" # Default action for browser
            elif "research" in lower_message or "topic" in lower_message:
                agent_type = "deep_research"
                action = "research" # Default action for research
            elif "document" in lower_message or "edit" in lower_message or "create" in lower_message:
                agent_type = "document_editor"
                action = "chat" # Default chat action for document editor
            else:
                agent_type = "document_editor" # Default fallback
                action = "chat" # Default chat action

        if not action:
            # Fallback action if agent_type was inferred but action wasn't
            if agent_type == "browser_use":
                action = "browse"
            elif agent_type == "deep_research":
                action = "research"
            else:
                action = "chat" # Default chat action

        logger.debug(f"Extracted message: '{message_content}', inferred agent_type: '{agent_type}', inferred action: '{action}'")

        # Create a task for the orchestrator
        task = AgentTask(
            id=input_data.run_id,
            user_id=user_id,
            agent_type=agent_type,
            action=action,
            payload={
                "message": message_content,
                "context_document_id": None, # Placeholder for now
            },
            created_at=datetime.utcnow(),
        )
        self.task_store[task.id] = task
        logger.info(f"Created AgentTask {task.id} for AG-UI chat input.")

        # Execute the task and stream AG-UI events
        async for event in self._execute_agent_action(task):
            yield event

    async def submit_task(
        self,
        agent_type: str,
        action: str,
        payload: dict[str, Any],
        user_id: str | None = None,
    ) -> str:
        """Submit a task to an agent and return task ID."""
        logger.info(f"Submit_task called for agent_type: {agent_type}, action: {action}, user_id: {user_id}")
        if agent_type not in self.agents:
            logger.error(f"Unknown agent type: {agent_type} for task submission.")
            raise ValueError(f"Unknown agent type: {agent_type}")

        # Create task object
        task = AgentTask(
            id=str(uuid.uuid4()),
            user_id=user_id or "anonymous",
            agent_type=agent_type,
            action=action,
            payload=payload,
            created_at=datetime.utcnow(),
        )

        self.task_store[task.id] = task
        logger.info(f"Created AgentTask {task.id} for submission.")

        # For now, directly execute the task. In future, this might queue it.
        # The _execute_agent_action will handle streaming AG-UI events if applicable.
        # For submit_task, we don't stream events back directly, but update task status.
        asyncio.create_task(self._execute_agent_action(task, is_ag_ui_stream=False))

        return task.id

    async def _execute_agent_action(self, task: AgentTask, is_ag_ui_stream: bool = True):
        """Execute a task with comprehensive error handling and optional AG-UI event streaming."""
        logger.info(f"Executing agent action for task {task.id}: agent_type={task.agent_type}, action={task.action}")
        message_id = str(uuid.uuid4())
        if is_ag_ui_stream:
            logger.debug(f"Yielding TextMessageStartEvent for task {task.id}")
            yield TextMessageStartEvent(
                type=EventType.TEXT_MESSAGE_START,
                message_id=message_id,
                role="assistant",
            )

        try:
            # Update status to running
            task.status = "running"
            task.started_at = datetime.utcnow()
            task.progress = {"percentage": 10, "message": "Starting agent..."}
            await self._notify_task_status(task)
            logger.debug(f"Task {task.id} status updated to running.")

            # Get agent
            agent = self.agents.get(task.agent_type)
            if not agent:
                logger.error(f"Agent {task.agent_type} not found for task {task.id}")
                raise ValueError(f"Agent {task.agent_type} not available")

            # Check if agent has the requested action
            if not hasattr(agent, task.action):
                logger.error(f"Agent {task.agent_type} has no action {task.action} for task {task.id}")
                raise AttributeError(
                    f"Agent {task.agent_type} has no action {task.action}"
                )

            # Update progress
            task.progress = {"percentage": 25, "message": "Executing task..."}
            await self._notify_task_status(task)
            logger.debug(f"Task {task.id} progress updated to executing.")

            # Execute the action with timeout
            method = getattr(agent, task.action)
            logger.debug(f"Calling agent method {task.agent_type}.{task.action} for task {task.id} with payload: {task.payload}")

            # Create progress callback for long-running tasks
            async def progress_callback(percentage: int, message: str):
                task.progress = {
                    "percentage": max(25, min(95, percentage)),
                    "message": message,
                }
                await self._notify_task_status(task)
                logger.debug(f"Task {task.id} progress callback: {percentage}% - {message}")

            # Add progress callback to payload if agent supports it
            if "progress_callback" in method.__code__.co_varnames:
                task.payload["progress_callback"] = progress_callback

            # Execute with timeout
            # If the agent method is a generator, iterate and yield AG-UI events
            result = None
            agent_response = await asyncio.wait_for(
                method(**task.payload), timeout=self.task_timeout
            )
            logger.debug(f"Agent {task.agent_type}.{task.action} for task {task.id} returned: {agent_response}")

            if isinstance(agent_response, str):
                # Simple string response, send as one message
                if is_ag_ui_stream:
                    logger.debug(f"Yielding TextMessageContentEvent (string) for task {task.id}")
                    yield TextMessageContentEvent(
                        type=EventType.TEXT_MESSAGE_CONTENT,
                        message_id=message_id,
                        delta=agent_response,
                    )
                result = {"response": agent_response}
            elif isinstance(agent_response, dict) and "response" in agent_response:
                # Dictionary with a 'response' key
                if is_ag_ui_stream:
                    logger.debug(f"Yielding TextMessageContentEvent (dict) for task {task.id}")
                    yield TextMessageContentEvent(
                        type=EventType.TEXT_MESSAGE_CONTENT,
                        message_id=message_id,
                        delta=agent_response["response"],
                    )
                result = agent_response
            else:
                # Assume it's a more complex object or already handled by agent
                result = agent_response
                if is_ag_ui_stream:
                    logger.debug(f"Yielding TextMessageContentEvent (complex object) for task {task.id}")
                    yield TextMessageContentEvent(
                        type=EventType.TEXT_MESSAGE_CONTENT,
                        message_id=message_id,
                        delta=f"Agent returned: {str(agent_response)}",
                    )

            # Task completed successfully
            task.status = "completed"
            task.result = result
            task.completed_at = datetime.utcnow()
            task.progress = {
                "percentage": 100,
                "message": "Task completed successfully",
            }

            logger.info(f"Task {task.id} completed successfully")

        except TimeoutError:
            logger.error(f"Task {task.id} timed out after {self.task_timeout} seconds")
            task.status = "failed"
            task.error = f"Task timed out after {self.task_timeout} seconds"
            task.completed_at = datetime.utcnow()
            task.progress = {"percentage": 100, "message": "Task timed out"}
            if is_ag_ui_stream:
                yield TextMessageContentEvent(
                    type=EventType.TEXT_MESSAGE_CONTENT,
                    message_id=message_id,
                    delta=f"Error: Task timed out after {self.task_timeout} seconds",
                )

        except asyncio.CancelledError:
            logger.info(f"Task {task.id} was cancelled")
            task.status = "cancelled"
            task.completed_at = datetime.utcnow()
            task.progress = {"percentage": 100, "message": "Task was cancelled"}
            if is_ag_ui_stream:
                yield TextMessageContentEvent(
                    type=EventType.TEXT_MESSAGE_CONTENT,
                    message_id=message_id,
                    delta="Error: Task was cancelled",
                )

        except Exception as e:
            logger.error(f"Task {task.id} failed: {e}", exc_info=True)
            task.status = "failed"
            task.error = str(e)
            task.completed_at = datetime.utcnow()
            task.progress = {
                "percentage": 100,
                "message": f"Task failed: {str(e)[:100]}",
            }
            if is_ag_ui_stream:
                yield TextMessageContentEvent(
                    type=EventType.TEXT_MESSAGE_CONTENT,
                    message_id=message_id,
                    delta=f"Error: {str(e)}",
                )

        finally:
            # Clean up
            if task.id in self.running_tasks:
                del self.running_tasks[task.id]

            # Final notification
            await self._notify_task_status(task)

            if is_ag_ui_stream:
                logger.debug(f"Yielding TextMessageEndEvent for task {task.id}")
                yield TextMessageEndEvent(
                    type=EventType.TEXT_MESSAGE_END,
                    message_id=message_id,
                )

    async def _notify_task_status(
        self, task: AgentTask, custom_message: dict | None = None
    ):
        """Notify user of task status change via WebSocket."""
        if not self.ws_manager:
            return

        message = custom_message or {
            "type": "task_update",
            "task_id": task.id,
            "status": task.status,
            "result": task.result if task.status == "completed" else None,
            "error": task.error if task.status == "failed" else None,
            "progress": task.progress,
            "timestamp": datetime.utcnow().isoformat(),
        }

        await self.ws_manager.send_message(task.user_id, message)

    def _get_user_running_tasks(self, user_id: str) -> list[str]:
        """Get list of running task IDs for a user."""
        user_task_ids = self.user_tasks.get(user_id, [])
        return [
            task_id
            for task_id in user_task_ids
            if task_id in self.task_store
            and self.task_store[task_id].status == "running"
        ]

    async def get_user_tasks(
        self, user_id: str, limit: int = 50, status_filter: str | None = None
    ) -> list[AgentTask]:
        """Get recent tasks for a user with optional status filtering."""
        task_ids = self.user_tasks.get(user_id, [])
        tasks = [self.task_store[tid] for tid in task_ids if tid in self.task_store]

        # Apply status filter if provided
        if status_filter:
            tasks = [task for task in tasks if task.status == status_filter]

        # Sort by created_at descending (handle None values)
        tasks.sort(key=lambda t: t.created_at or datetime.min, reverse=True)

        return tasks[:limit]

    async def cancel_task(self, user_id: str, task_id: str) -> bool:
        """Cancel a pending or running task."""
        task = self.task_store.get(task_id)

        if not task or task.user_id != user_id:
            return False

        if task.status == "pending":
            task.status = "cancelled"
            task.completed_at = datetime.utcnow()
            task.progress = {"percentage": 100, "message": "Task cancelled"}
            await self._notify_task_status(task)
            return True

        elif task.status == "running" and task_id in self.running_tasks:
            # Cancel the running asyncio task
            asyncio_task = self.running_tasks[task_id]
            asyncio_task.cancel()

            # Status will be updated in the _execute_task finally block
            logger.info(f"Cancelled running task {task_id}")
            return True

        return False

    async def get_task_by_id(self, user_id: str, task_id: str) -> AgentTask | None:
        """Get a specific task by ID if it belongs to the user."""
        task = self.task_store.get(task_id)
        if task and task.user_id == user_id:
            return task
        return None

    def get_agent_stats(self) -> dict[str, Any]:
        """Get orchestrator statistics."""
        total_tasks = len(self.task_store)
        running_tasks = len(self.running_tasks)

        status_counts = {}
        for task in self.task_store.values():
            status_counts[task.status] = status_counts.get(task.status, 0) + 1

        return {
            "total_tasks": total_tasks,
            "running_tasks": running_tasks,
            "registered_agents": list(self.agents.keys()),
            "status_distribution": status_counts,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "task_timeout": self.task_timeout,
        }


# Global orchestrator instance - will be initialized with WebSocket manager
orchestrator: SimpleAgentOrchestrator | None = None


def initialize_orchestrator(ws_manager):
    """Initialize the global orchestrator with WebSocket manager."""
    global orchestrator
    orchestrator = SimpleAgentOrchestrator(ws_manager)
    logger.info("Agent orchestrator initialized")
    return orchestrator
