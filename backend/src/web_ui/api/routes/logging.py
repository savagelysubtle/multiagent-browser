"""
Frontend logging API routes.

Provides endpoints for the frontend to submit logs to the backend
for centralized logging and debugging.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from ...utils.logging_config import get_logger
from ..auth.dependencies import get_optional_user

logger = get_logger(__name__)

# Create router
router = APIRouter(tags=["frontend-logging"])


class FrontendLogRequest(BaseModel):
    """Request model for frontend log submissions."""

    log_content: str


@router.post("/frontend")
async def receive_frontend_logs(
    request: Request,
    log_data: FrontendLogRequest,
    current_user = Depends(get_optional_user),
):
    """
    Receive and store frontend logs.

    This endpoint accepts log data from the frontend and writes it to
    the centralized log file for debugging and monitoring purposes.
    """
    try:
        # Get user info if available
        user_info = "anonymous"
        if current_user:
            user_info = f"user:{current_user.id}:{current_user.email}"

        # Log directory path
        log_dir = Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)

        # Frontend log file
        frontend_log_file = log_dir / "frontend.log"

        # Format the log entry with user context
        timestamp = request.headers.get("X-Timestamp", "")
        user_agent = request.headers.get("User-Agent", "")

        formatted_log = f"FRONTEND [{user_info}] [{timestamp}] [{user_agent}] {log_data.log_content}\n"

        # Write to frontend log file
        with open(frontend_log_file, "a", encoding="utf-8") as f:
            f.write(formatted_log)

        # Also log to main application log for visibility
        logger.info(f"Frontend log received from {user_info}", extra={
            "frontend_log": True,
            "user_id": current_user.id if current_user else None,
            "log_preview": log_data.log_content[:200] + "..." if len(log_data.log_content) > 200 else log_data.log_content,
        })

        return {"status": "success", "message": "Logs received"}

    except Exception as e:
        logger.error(f"Failed to process frontend logs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process logs",
        )


@router.get("/frontend/status")
async def get_frontend_logging_status(current_user = Depends(get_current_user_optional)):
    """
    Get status information about frontend logging.

    Returns information about the logging configuration and recent activity.
    """
    try:
        log_dir = Path("logs")
        frontend_log_file = log_dir / "frontend.log"

        # Check if log file exists and get basic stats
        if frontend_log_file.exists():
            stat = frontend_log_file.stat()
            file_size = stat.st_size
            modified_time = stat.st_mtime

            # Count lines (approximate)
            line_count = 0
            try:
                with open(frontend_log_file, "r", encoding="utf-8") as f:
                    line_count = sum(1 for _ in f)
            except Exception:
                line_count = 0

            return {
                "status": "active",
                "log_file": str(frontend_log_file),
                "file_size": file_size,
                "line_count": line_count,
                "last_modified": modified_time,
                "last_modified_human": str(modified_time),
            }
        else:
            return {
                "status": "inactive",
                "log_file": str(frontend_log_file),
                "file_size": 0,
                "line_count": 0,
                "message": "Frontend log file does not exist yet",
            }

    except Exception as e:
        logger.error(f"Failed to get frontend logging status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get logging status",
        )