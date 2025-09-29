"""
Agents API routes for the React frontend.

Provides endpoints for agent management, task submission, and status monitoring.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ...agent.orchestrator.simple_orchestrator import SimpleAgentOrchestrator
from ...utils.logging_config import get_logger
from ..auth.auth_service import User
from ..auth.dependencies import get_current_user
from ..dependencies import get_orchestrator
from ..middleware.error_handler import AppException

logger = get_logger(__name__)

router = APIRouter(prefix="/api/agents", tags=["agents"])


# Request/Response Models
class TaskSubmissionRequest(BaseModel):
    """Request model for task submission."""

    agent_type: str = Field(..., description="Type of agent to use")
    action: str = Field(..., description="Action to perform")
    payload: dict[str, Any] = Field(..., description="Task parameters")


class TaskSubmissionResponse(BaseModel):
    """Response model for task submission."""

    task_id: str
    status: str
    message: str
    submitted_at: str


class TaskResponse(BaseModel):
    """Response model for task details."""

    id: str
    agent_type: str
    action: str
    status: str
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    result: Any | None = None
    error: str | None = None
    progress: dict[str, Any] | None = None


class TaskListResponse(BaseModel):
    """Response model for task list."""

    tasks: list[TaskResponse]
    total_count: int
    page: int
    limit: int


class AgentCapability(BaseModel):
    """Model for agent capability description."""

    name: str
    description: str
    parameters: list[str]


class AgentInfo(BaseModel):
    """Model for agent information."""

    type: str
    name: str
    description: str
    actions: list[AgentCapability]


class AvailableAgentsResponse(BaseModel):
    """Response model for available agents."""

    agents: list[AgentInfo]
    total_agents: int


# Route Handlers
@router.get("/available", response_model=AvailableAgentsResponse)
async def get_available_agents(user=Depends(get_current_user)):
    """
    Get list of available agents and their capabilities.

    Returns information about all registered agents including:
    - Agent types and names
    - Available actions for each agent
    - Required parameters for each action
    """
    try:
        try:
            orchestrator = get_orchestrator()
        except RuntimeError:
            # Return empty list if orchestrator not ready yet
            logger.warning(
                "Orchestrator not initialized yet, returning empty agent list"
            )
            return AvailableAgentsResponse(agents=[], total_agents=0)

        # Get available agents from orchestrator
        agents_info = orchestrator.get_available_agents()

        # Convert to response model format
        agents = []
        for agent_info in agents_info:
            actions = [
                AgentCapability(
                    name=action["name"],
                    description=action["description"],
                    parameters=action["parameters"],
                )
                for action in agent_info["actions"]
            ]

            agents.append(
                AgentInfo(
                    type=agent_info["type"],
                    name=agent_info["name"],
                    description=agent_info["description"],
                    actions=actions,
                )
            )

        return AvailableAgentsResponse(agents=agents, total_agents=len(agents))

    except Exception as e:
        logger.error(f"Failed to get available agents: {e}")
        raise AppException("Failed to retrieve available agents")


@router.post("/execute", response_model=TaskSubmissionResponse)
async def execute_agent_task(
    request: TaskSubmissionRequest,
    current_user: User = Depends(get_current_user),
    orchestrator: SimpleAgentOrchestrator = Depends(get_orchestrator),
):
    """Execute a task using the specified agent."""
    logger.info(f"Executing task for agent: {request.agent_type}")

    # Validate agent type
    if request.agent_type not in orchestrator.agents:
        raise HTTPException(
            status_code=400, detail=f"Unknown agent type: {request.agent_type}"
        )

    try:
        # Submit task to orchestrator with updated signature
        task_id = await orchestrator.submit_task(
            agent_type=request.agent_type,
            action=request.action,
            payload=request.payload,
            user_id=current_user.id,
        )

        # Get the task to check its status
        task = orchestrator.get_task(task_id)

        return TaskSubmissionResponse(
            task_id=task_id,
            status=task.status,
            message=f"Task {task.status}: {request.action}"
            if task
            else "Task submitted",
        )

    except ValueError as e:
        logger.warning(f"Invalid task request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error executing agent task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to execute task: {str(e)}")


@router.get("/tasks", response_model=TaskListResponse)
async def get_user_tasks(
    limit: int = Query(
        50, ge=1, le=100, description="Maximum number of tasks to return"
    ),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    status: str | None = Query(None, description="Filter by task status"),
    user=Depends(get_current_user),
):
    """
    Get user's agent tasks with pagination and filtering.

    Returns a paginated list of tasks belonging to the authenticated user.
    Tasks are ordered by creation date (newest first).
    """
    try:
        orchestrator = get_orchestrator()
        if not orchestrator:
            raise AppException(
                "Agent orchestrator not initialized", "ORCHESTRATOR_ERROR"
            )

        # Calculate offset for pagination
        offset = (page - 1) * limit

        # Get tasks from orchestrator with status filter
        all_tasks = await orchestrator.get_user_tasks(
            user_id=user.id,
            limit=1000,  # Get more to handle pagination properly
            status_filter=status,
        )

        # Apply pagination
        total_count = len(all_tasks)
        paginated_tasks = all_tasks[offset : offset + limit]

        # Convert to response format
        task_responses = []
        for task in paginated_tasks:
            task_responses.append(
                TaskResponse(
                    id=task.id,
                    agent_type=task.agent_type,
                    action=task.action,
                    status=task.status,
                    created_at=task.created_at.isoformat(),
                    started_at=task.started_at.isoformat() if task.started_at else None,
                    completed_at=task.completed_at.isoformat()
                    if task.completed_at
                    else None,
                    result=task.result if task.status == "completed" else None,
                    error=task.error if task.status == "failed" else None,
                    progress=task.progress,
                )
            )

        return TaskListResponse(
            tasks=task_responses, total_count=total_count, page=page, limit=limit
        )

    except Exception as e:
        logger.error(f"Failed to get user tasks: {e}")
        raise AppException("Failed to retrieve user tasks")


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task_details(task_id: str, user=Depends(get_current_user)):
    """
    Get detailed information about a specific task.

    Returns comprehensive task information including current status,
    results (if completed), and progress information.
    """
    try:
        orchestrator = get_orchestrator()
        if not orchestrator:
            raise AppException(
                "Agent orchestrator not initialized", "ORCHESTRATOR_ERROR"
            )

        # Get task from orchestrator
        task = await orchestrator.get_task_by_id(user.id, task_id)

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        return TaskResponse(
            id=task.id,
            agent_type=task.agent_type,
            action=task.action,
            status=task.status,
            created_at=task.created_at.isoformat() if task.created_at else "",
            started_at=task.started_at.isoformat() if task.started_at else None,
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
            result=task.result if task.status == "completed" else None,
            error=task.error if task.status == "failed" else None,
            progress=task.progress,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task details for {task_id}: {e}")
        raise AppException("Failed to retrieve task details")


@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str, user=Depends(get_current_user)):
    """
    Cancel a pending or running task.

    Only tasks that are in 'pending' or 'running' status can be cancelled.
    Completed or failed tasks cannot be cancelled.
    """
    try:
        orchestrator = get_orchestrator()
        if not orchestrator:
            raise AppException(
                "Agent orchestrator not initialized", "ORCHESTRATOR_ERROR"
            )

        # Attempt to cancel the task
        success = await orchestrator.cancel_task(user.id, task_id)

        if not success:
            # Check if task exists to provide better error message
            task = await orchestrator.get_task_by_id(user.id, task_id)
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Task cannot be cancelled (current status: {task.status})",
                )

        return {"message": "Task cancelled successfully", "task_id": task_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {e}")
        raise AppException("Failed to cancel task")


@router.get("/stats")
async def get_agent_stats(user=Depends(get_current_user)):
    """
    Get agent orchestrator statistics.

    Returns system-wide statistics about agent usage and performance.
    This endpoint provides insights into system health and usage patterns.
    """
    try:
        orchestrator = get_orchestrator()
        if not orchestrator:
            raise AppException(
                "Agent orchestrator not initialized", "ORCHESTRATOR_ERROR"
            )

        # Get general stats from orchestrator
        stats = orchestrator.get_agent_stats()

        # Get user-specific stats
        user_tasks = await orchestrator.get_user_tasks(user.id, limit=1000)
        user_stats = {
            "user_total_tasks": len(user_tasks),
            "user_running_tasks": len([t for t in user_tasks if t.status == "running"]),
            "user_completed_tasks": len(
                [t for t in user_tasks if t.status == "completed"]
            ),
            "user_failed_tasks": len([t for t in user_tasks if t.status == "failed"]),
        }

        return {
            "system_stats": stats,
            "user_stats": user_stats,
            "timestamp": orchestrator.task_store[
                next(iter(orchestrator.task_store))
            ].created_at.isoformat()
            if orchestrator.task_store
            else None,
        }

    except Exception as e:
        logger.error(f"Failed to get agent stats: {e}")
        raise AppException("Failed to retrieve agent statistics")


@router.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring agent system status.

    Returns the current health status of the agent orchestrator
    and registered agents.
    """
    try:
        orchestrator = get_orchestrator()
        health_status = {
            "orchestrator_initialized": orchestrator is not None,
            "registered_agents": list(orchestrator.agents.keys())
            if orchestrator
            else [],
            "active_connections": len(orchestrator.running_tasks)
            if orchestrator
            else 0,
            "status": "healthy" if orchestrator else "unhealthy",
            "timestamp": orchestrator.task_store[
                next(iter(orchestrator.task_store))
            ].created_at.isoformat()
            if orchestrator and orchestrator.task_store
            else None,
        }

        status_code = 200 if orchestrator else 503
        return health_status

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e), "timestamp": None}
