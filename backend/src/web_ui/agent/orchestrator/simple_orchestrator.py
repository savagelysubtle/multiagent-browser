"""Simple agent orchestrator with Google A2A protocol support."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ...utils.logging_config import get_logger
from ..a2a import (
    Artifact,
    Message,
    MessageRole,
    MessageSendParams,
    Part,
    PartKind,
    Task,
    TaskIdParams,
    TaskQueryParams,
    TaskState,
    TaskStatus,
)

logger = get_logger(__name__)


@dataclass
class AgentTask:
    """Internal representation of an agent task."""

    id: str
    user_id: str
    agent_type: str
    action: str
    payload: dict[str, Any]
    context_id: str
    state: TaskState = TaskState.SUBMITTED
    status_message: Message | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    progress: dict[str, Any] = field(
        default_factory=lambda: {"percentage": 0, "message": "Pending"}
    )
    history: list[Message] = field(default_factory=list)
    artifacts: list[Artifact] = field(default_factory=list)
    metadata: dict[str, Any] | None = None
    origin_message: Message | None = None

    @property
    def status(self) -> str:
        mapping = {
            TaskState.SUBMITTED: "pending",
            TaskState.WORKING: "running",
            TaskState.INPUT_REQUIRED: "input_required",
            TaskState.COMPLETED: "completed",
            TaskState.CANCELED: "canceled",
            TaskState.FAILED: "failed",
            TaskState.REJECTED: "rejected",
            TaskState.AUTH_REQUIRED: "auth_required",
            TaskState.UNKNOWN: "unknown",
        }
        return mapping.get(self.state, "unknown")

    @property
    def status_timestamp(self) -> str:
        if self.completed_at:
            return self.completed_at.isoformat()
        if self.started_at:
            return self.started_at.isoformat()
        return self.created_at.isoformat()

    def to_task(self, history_length: int | None = None) -> Task:
        history: list[Message] | None = self.history
        if history_length is not None and history:
            history = history[-history_length:]
        if not history:
            history = None

        return Task(
            id=self.id,
            contextId=self.context_id,
            status=TaskStatus(
                state=self.state,
                message=self.status_message,
                timestamp=self.status_timestamp,
            ),
            artifacts=self.artifacts or None,
            history=history,
            metadata=self.metadata,
        )


class SimpleAgentOrchestrator:
    """Coordinates agent execution and exposes Google A2A primitives."""

    def __init__(self, ws_manager=None):
        self.agents: dict[str, Any] = {}
        self.agent_capabilities: dict[str, dict[str, Any]] = {}
        self.agent_endpoints: dict[str, str] = {}
        self.task_store: dict[str, AgentTask] = {}
        self.user_tasks: dict[str, list[str]] = {}
        self.running_tasks: dict[str, asyncio.Task] = {}
        self.ws_manager = ws_manager

    # ---------------------------------------------------------------------
    # Agent registration & discovery
    # ---------------------------------------------------------------------
    def register_agent(
        self,
        agent_type: str,
        agent_instance,
        capabilities: dict[str, Any] | None = None,
        a2a_endpoint: str | None = None,
    ) -> None:
        """Register an agent implementation with optional metadata."""

        self.agents[agent_type] = agent_instance
        if capabilities:
            self.agent_capabilities[agent_type] = capabilities
        if a2a_endpoint:
            self.agent_endpoints[agent_type] = a2a_endpoint

        logger.info("Registered agent %s", agent_type)

    def get_available_agents(self) -> list[dict[str, Any]]:
        """Return capability summaries for registered agents."""

        agents: list[dict[str, Any]] = []
        for agent_type, instance in self.agents.items():
            capabilities = self.agent_capabilities.get(agent_type, {})
            actions = capabilities.get("actions")
            if actions is None and hasattr(instance, "get_capabilities"):
                try:
                    capabilities = instance.get_capabilities()  # type: ignore[assignment]
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Capability probe failed for %s: %s", agent_type, exc)
                    capabilities = {}
            if "actions" not in capabilities:
                inferred_actions = [
                    name
                    for name in dir(instance)
                    if not name.startswith("_") and callable(getattr(instance, name))
                ]
                capabilities = {**capabilities, "actions": inferred_actions}

            agents.append(
                {
                    "type": agent_type,
                    "name": capabilities.get("name", agent_type.replace("_", " ").title()),
                    "description": capabilities.get(
                        "description", "Agent registered with orchestrator"
                    ),
                    "actions": [
                        {
                            "name": action,
                            "description": "Action exposed by registered agent",
                            "parameters": [],
                        }
                        for action in capabilities.get("actions", [])
                    ],
                }
            )
        return agents

    # ---------------------------------------------------------------------
    # Task submission & lifecycle
    # ---------------------------------------------------------------------
    async def submit_task(
        self,
        agent_type: str,
        action: str,
        payload: dict[str, Any],
        user_id: str,
        context_id: str | None = None,
        origin_message: Message | None = None,
        blocking: bool = True,
    ) -> str:
        """Create a task and optionally execute it immediately."""

        agent = self._resolve_agent(agent_type)
        context = context_id or str(uuid.uuid4())
        task_id = str(uuid.uuid4())

        task = AgentTask(
            id=task_id,
            user_id=user_id,
            agent_type=agent_type,
            action=action,
            payload=payload,
            context_id=context,
            origin_message=origin_message,
        )
        self.task_store[task_id] = task
        self.user_tasks.setdefault(user_id, []).append(task_id)

        if blocking:
            await self._execute_task(agent, task)
        else:
            runner = asyncio.create_task(self._execute_task(agent, task))
            self.running_tasks[task_id] = runner
            runner.add_done_callback(lambda _: self.running_tasks.pop(task_id, None))

        return task_id

    async def _execute_task(self, agent_instance, task: AgentTask) -> None:
        task.started_at = datetime.utcnow()
        task.state = TaskState.WORKING
        task.progress = {"percentage": 25, "message": "Running"}

        self._ensure_origin_history(task)

        try:
            result = await self._run_agent_action(agent_instance, task)
            task.result = result
            task.state = TaskState.COMPLETED
            task.completed_at = datetime.utcnow()
            task.progress = {"percentage": 100, "message": "Completed"}
            summary = self._summarise_result(result)
            task.status_message = self._make_message(MessageRole.AGENT, summary, task)
            task.history.append(task.status_message)
            task.error = None

        except Exception as exc:  # noqa: BLE001
            logger.exception("Task %s failed", task.id)
            task.error = str(exc)
            task.state = TaskState.FAILED
            task.completed_at = datetime.utcnow()
            task.progress = {"percentage": 100, "message": "Failed"}
            task.status_message = self._make_message(
                MessageRole.AGENT, f"Error: {task.error}", task
            )
            task.history.append(task.status_message)
            if task.result is None:
                task.result = {"success": False, "error": task.error}

    async def _run_agent_action(self, agent_instance, task: AgentTask) -> dict[str, Any]:
        handler = getattr(agent_instance, task.action, None)
        if handler is None or not callable(handler):
            raise LookupError(
                f"Agent '{task.agent_type}' does not support action '{task.action}'"
            )

        result = await handler(**task.payload)
        if isinstance(result, dict):
            return result
        if isinstance(result, str):
            return {"response": result}
        return {"result": result}

    # ------------------------------------------------------------------
    # Task retrieval helpers
    # ------------------------------------------------------------------
    async def get_user_tasks(
        self,
        user_id: str,
        limit: int = 50,
        status_filter: str | None = None,
    ) -> list[AgentTask]:
        ids = self.user_tasks.get(user_id, [])
        tasks = [self.task_store[task_id] for task_id in ids]
        if status_filter:
            tasks = [task for task in tasks if task.status == status_filter]
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks[:limit]

    async def get_task_by_id(self, user_id: str, task_id: str) -> AgentTask | None:
        task = self.task_store.get(task_id)
        if not task or task.user_id != user_id:
            return None
        return task

    def get_task(self, task_id: str) -> AgentTask | None:
        return self.task_store.get(task_id)

    async def cancel_task(self, user_id: str | None, task_id: str) -> bool:
        task = self.task_store.get(task_id)
        if not task:
            return False
        if user_id and task.user_id != user_id:
            return False
        if task.state not in {TaskState.SUBMITTED, TaskState.WORKING}:
            return False

        runner = self.running_tasks.pop(task_id, None)
        if runner:
            runner.cancel()

        task.state = TaskState.CANCELED
        task.completed_at = datetime.utcnow()
        task.progress = {"percentage": 100, "message": "Canceled"}
        task.status_message = self._make_message(
            MessageRole.AGENT, "Task was cancelled", task
        )
        task.history.append(task.status_message)
        return True

    def get_agent_stats(self) -> dict[str, Any]:
        total = len(self.task_store)
        completed = sum(1 for task in self.task_store.values() if task.state == TaskState.COMPLETED)
        failed = sum(1 for task in self.task_store.values() if task.state == TaskState.FAILED)
        running = sum(1 for task in self.task_store.values() if task.state == TaskState.WORKING)
        return {
            "total_tasks": total,
            "completed_tasks": completed,
            "failed_tasks": failed,
            "running_tasks": running,
        }

    def get_agent_status(self, agent_type: str) -> dict[str, Any]:
        agent = self.agents.get(agent_type)
        if not agent:
            return {"registered": False, "error": "Agent not registered"}
        return {
            "registered": True,
            "agent_type": agent_type,
            "capabilities": self.agent_capabilities.get(agent_type, {}),
            "a2a_endpoint": self.agent_endpoints.get(agent_type),
        }

    # ------------------------------------------------------------------
    # Google A2A JSON-RPC helpers
    # ------------------------------------------------------------------
    async def handle_a2a_message_send(
        self,
        agent_type: str,
        params: MessageSendParams,
        request_id: Any,
    ) -> Task:
        agent = self._resolve_agent(agent_type)
        action, payload = self._extract_action_and_payload(agent_type, params)
        context_id = params.message.context_id or str(uuid.uuid4())
        blocking = True
        if params.configuration and params.configuration.blocking is not None:
            blocking = params.configuration.blocking

        task_id = await self.submit_task(
            agent_type=agent_type,
            action=action,
            payload=payload,
            user_id="a2a-client",
            context_id=context_id,
            origin_message=params.message,
            blocking=blocking,
        )

        task = self.task_store[task_id]
        if not blocking:
            task.state = TaskState.SUBMITTED
        return task.to_task()

    async def handle_a2a_tasks_get(self, params: TaskQueryParams) -> Task:
        task = self.task_store.get(params.id)
        if not task:
            raise LookupError(f"Task '{params.id}' not found")
        return task.to_task(history_length=params.history_length)

    async def handle_a2a_tasks_cancel(self, params: TaskIdParams) -> Task:
        success = await self.cancel_task(user_id=None, task_id=params.id)
        if not success:
            raise LookupError(f"Task '{params.id}' cannot be cancelled")
        task = self.task_store[params.id]
        return task.to_task()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _resolve_agent(self, agent_type: str):
        agent = self.agents.get(agent_type)
        if not agent:
            raise LookupError(f"Agent '{agent_type}' is not registered")
        return agent

    def _ensure_origin_history(self, task: AgentTask) -> None:
        if task.origin_message is None:
            return
        origin = task.origin_message
        update_payload = {
            "message_id": origin.message_id or str(uuid.uuid4()),
            "context_id": task.context_id,
            "task_id": task.id,
        }
        task.origin_message = origin.copy(update=update_payload)
        task.history.append(task.origin_message)

    def _make_message(
        self, role: MessageRole, text: str, task: AgentTask
    ) -> Message:
        return Message(
            role=role,
            parts=[Part(kind=PartKind.TEXT, text=text)],
            message_id=str(uuid.uuid4()),
            context_id=task.context_id,
            task_id=task.id,
        )

    def _summarise_result(self, result: dict[str, Any]) -> str:
        for key in ("response", "message", "summary"):
            value = result.get(key) if isinstance(result, dict) else None
            if isinstance(value, str) and value.strip():
                return value
        return "Task completed successfully."

    def _extract_action_and_payload(
        self, agent_type: str, params: MessageSendParams
    ) -> tuple[str, dict[str, Any]]:
        message = params.message
        action: str | None = None
        payload: dict[str, Any] | None = None

        if message.metadata:
            action = message.metadata.get("action")
            metadata_payload = message.metadata.get("payload")
            if isinstance(metadata_payload, dict):
                payload = metadata_payload

        for part in message.parts:
            if part.kind == PartKind.DATA and isinstance(part.data, dict):
                action = part.data.get("action", action)
                content_payload = part.data.get("payload")
                if isinstance(content_payload, dict):
                    payload = content_payload

        if action is None:
            action = "chat" if agent_type == "document_editor" else "chat"

        if payload is None:
            text = self._extract_text(message)
            payload = {"message": text, "context_document_id": message.metadata.get("context_document_id") if message.metadata else None}

        return action, payload

    @staticmethod
    def _extract_text(message: Message) -> str:
        for part in message.parts:
            if part.kind == PartKind.TEXT and part.text:
                return part.text
        return ""


# Global instance helpers -------------------------------------------------
orchestrator: SimpleAgentOrchestrator | None = None


def initialize_orchestrator(ws_manager):
    global orchestrator
    orchestrator = SimpleAgentOrchestrator(ws_manager)
    logger.info("Agent orchestrator initialized")
    return orchestrator
