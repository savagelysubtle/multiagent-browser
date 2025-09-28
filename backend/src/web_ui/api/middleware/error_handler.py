"""
Error handling middleware for the React frontend migration.

Provides comprehensive error handling with custom exception classes,
global error middleware, and circuit breaker patterns for resilient operation.
"""

from __future__ import annotations

import logging
import os
import traceback
from datetime import datetime

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base application exception with structured error information."""

    def __init__(
        self,
        message: str,
        code: str = "APP_ERROR",
        status_code: int = 500,
        details: dict | None = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AgentException(AppException):
    """Agent-specific exceptions with agent context."""

    def __init__(
        self,
        message: str,
        agent_name: str,
        action: str | None = None,
        code: str = "AGENT_ERROR",
    ):
        self.agent_name = agent_name
        self.action = action
        details = {"agent_name": agent_name}
        if action:
            details["action"] = action
        super().__init__(message, code, status_code=500, details=details)


class ValidationException(AppException):
    """Input validation exceptions with field-level detail."""

    def __init__(
        self, message: str, field: str | None = None, value: str | None = None
    ):
        self.field = field
        self.value = value
        details = {}
        if field:
            details["field"] = field
        if value:
            details["value"] = str(value)
        super().__init__(message, "VALIDATION_ERROR", status_code=400, details=details)


class AuthenticationException(AppException):
    """Authentication and authorization exceptions."""

    def __init__(
        self, message: str = "Authentication required", code: str = "AUTH_REQUIRED"
    ):
        super().__init__(message, code, status_code=401)


class RateLimitException(AppException):
    """Rate limiting exceptions."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 60):
        details = {"retry_after": retry_after}
        super().__init__(
            message, "RATE_LIMIT_EXCEEDED", status_code=429, details=details
        )


class WebSocketException(AppException):
    """WebSocket-specific exceptions."""

    def __init__(
        self, message: str, user_id: str | None = None, code: str = "WEBSOCKET_ERROR"
    ):
        details = {}
        if user_id:
            details["user_id"] = user_id
        super().__init__(message, code, status_code=500, details=details)


# Global error handlers
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle custom application exceptions."""
    logger.error(
        f"Application error: {exc.message} (code: {exc.code})",
        extra={
            "error_code": exc.code,
            "status_code": exc.status_code,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method,
            "user_agent": request.headers.get("user-agent", "unknown"),
        },
        exc_info=True,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "timestamp": datetime.utcnow().isoformat(),
                "path": request.url.path,
            }
        },
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors with detailed field information."""
    errors = []
    for error in exc.errors():
        field_path = ".".join(str(loc) for loc in error["loc"])
        errors.append(
            {
                "field": field_path,
                "message": error["msg"],
                "type": error["type"],
                "input": error.get("input"),
            }
        )

    logger.warning(
        f"Validation error on {request.method} {request.url.path}",
        extra={"validation_errors": errors, "error_count": len(errors)},
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid input data",
                "details": {"field_errors": errors, "error_count": len(errors)},
                "timestamp": datetime.utcnow().isoformat(),
                "path": request.url.path,
            }
        },
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle HTTP exceptions (404, etc.) with consistent format."""
    logger.info(
        f"HTTP exception: {exc.status_code} on {request.method} {request.url.path}",
        extra={"status_code": exc.status_code, "detail": exc.detail},
    )

    # Map status codes to user-friendly messages
    status_messages = {
        404: "The requested resource was not found",
        405: "Method not allowed for this endpoint",
        403: "Access to this resource is forbidden",
        401: "Authentication required",
    }

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": status_messages.get(exc.status_code, exc.detail),
                "timestamp": datetime.utcnow().isoformat(),
                "path": request.url.path,
            }
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with appropriate security measures."""
    # Generate a unique error ID for tracking
    error_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S") + f"_{id(exc) % 10000:04d}"

    logger.error(
        f"Unexpected error [ID: {error_id}]: {str(exc)}",
        extra={
            "error_id": error_id,
            "exception_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method,
            "traceback": traceback.format_exc(),
        },
        exc_info=True,
    )

    # Don't expose internal errors in production
    is_development = os.getenv("ENV", "production").lower() == "development"

    if is_development:
        message = f"{type(exc).__name__}: {str(exc)}"
        details = {
            "exception_type": type(exc).__name__,
            "traceback": traceback.format_exc().split("\n")[-10:],  # Last 10 lines
        }
    else:
        message = "An unexpected error occurred. Please contact support if the issue persists."
        details = {"error_id": error_id}

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": message,
                "details": details,
                "timestamp": datetime.utcnow().isoformat(),
                "path": request.url.path,
            }
        },
    )


# Circuit breaker pattern for external service calls
class CircuitBreaker:
    """Simple circuit breaker implementation for resilient service calls."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                raise AppException(
                    "Service temporarily unavailable due to repeated failures",
                    "SERVICE_UNAVAILABLE",
                    503,
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt to reset."""
        if self.last_failure_time is None:
            return True
        return (
            datetime.utcnow().timestamp() - self.last_failure_time
        ) > self.recovery_timeout

    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        self.state = "CLOSED"

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow().timestamp()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


# Global circuit breakers for different services
agent_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
database_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)


def with_circuit_breaker(circuit_breaker: CircuitBreaker):
    """Decorator to apply circuit breaker to a function."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            return circuit_breaker.call(func, *args, **kwargs)

        return wrapper

    return decorator


# Utility functions for error reporting
def create_error_response(
    code: str, message: str, status_code: int = 500, details: dict | None = None
) -> JSONResponse:
    """Create a standardized error response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
                "timestamp": datetime.utcnow().isoformat(),
            }
        },
    )


def log_performance_issue(operation: str, duration: float, threshold: float = 1.0):
    """Log performance issues for monitoring."""
    if duration > threshold:
        logger.warning(
            f"Performance issue detected: {operation} took {duration:.2f}s",
            extra={
                "operation": operation,
                "duration": duration,
                "threshold": threshold,
                "performance_issue": True,
            },
        )
