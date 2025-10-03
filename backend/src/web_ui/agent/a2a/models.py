"""Typed representations of key Google A2A protocol objects.

These models intentionally cover the portion of the specification that the
current implementation needs: JSON-RPC envelopes, messages, tasks, and
identifiers used by the ``message/send``, ``tasks/get``, and ``tasks/cancel``
procedures.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class JSONRPCError(BaseModel):
    """Standard JSON-RPC error structure."""

    code: int
    message: str
    data: Any | None = None


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 Response format for A2A communication."""

    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    id: str | int | None = Field(description="Request ID")
    result: Any | None = Field(default=None, description="Result data")
    error: dict[str, Any] | None = Field(default=None, description="Error information")

    @model_validator(mode="after")
    def validate_result_or_error(self):
        """Ensure either result or error is present, but not both."""
        if self.result is not None and self.error is not None:
            raise ValueError("Response cannot have both result and error")
        if self.result is None and self.error is None:
            raise ValueError("Response must have either result or error")
        return self


class FileResource(BaseModel):
    """Representation of the file metadata used inside file/data parts."""

    model_config = ConfigDict(populate_by_name=True)

    name: str | None = None
    uri: str | None = None
    mime_type: str | None = Field(default=None, alias="mimeType")


class PartKind(str, Enum):
    """Supported message part kinds."""

    TEXT = "text"
    FILE = "file"
    DATA = "data"


class Part(BaseModel):
    """Union type across text, file, and data parts."""

    model_config = ConfigDict(populate_by_name=True, use_enum_values=True)

    kind: PartKind
    text: str | None = None
    data: Any | None = None
    file: FileResource | None = None
    mime_type: str | None = Field(default=None, alias="mimeType")
    metadata: dict[str, Any] | None = None

    @field_validator("text", mode="before")
    @classmethod
    def validate_text(cls, v):
        # Note: In Pydantic v2, we need to access other fields differently
        # This validator logic may need to be updated based on the actual validation requirements
        return v

    @field_validator("file", mode="before")
    @classmethod
    def validate_file(cls, v):
        # File validation logic would go here
        return v

    @field_validator("data", mode="before")
    @classmethod
    def validate_data(cls, v):
        # Data validation logic would go here
        return v


class MessageRole(str, Enum):
    USER = "user"
    AGENT = "agent"


class Message(BaseModel):
    """A message exchanged between client and agent."""

    model_config = ConfigDict(populate_by_name=True, use_enum_values=True)

    role: MessageRole
    parts: list[Part]
    metadata: dict[str, Any] | None = None
    reference_task_ids: list[str] | None = Field(default=None, alias="referenceTaskIds")
    message_id: str | None = Field(default=None, alias="messageId")
    task_id: str | None = Field(default=None, alias="taskId")
    context_id: str | None = Field(default=None, alias="contextId")
    kind: Literal["message"] | None = "message"


class MessageSendConfiguration(BaseModel):
    """Subset of configuration parameters relevant to the current server."""

    blocking: bool | None = None


class MessageSendParams(BaseModel):
    """Parameters for the message/send and message/stream RPCs."""

    message: Message
    configuration: MessageSendConfiguration | None = None
    metadata: dict[str, Any] | None = None


class TaskState(str, Enum):
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    CANCELED = "canceled"
    FAILED = "failed"
    REJECTED = "rejected"
    AUTH_REQUIRED = "auth-required"
    UNKNOWN = "unknown"


class TaskStatus(BaseModel):
    """Lifecycle marker for a task."""

    state: TaskState
    message: Message | None = None
    timestamp: str | None = None


class Artifact(BaseModel):
    """Task artifact metadata."""

    model_config = ConfigDict(populate_by_name=True)

    artifact_id: str = Field(alias="artifactId")
    name: str | None = None
    parts: list[Part]
    metadata: dict[str, Any] | None = None
    kind: Literal["artifact"] = "artifact"


class Task(BaseModel):
    """Full task snapshot returned by tasks/get and message/send."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    context_id: str = Field(alias="contextId")
    status: TaskStatus
    artifacts: list[Artifact] | None = None
    history: list[Message] | None = None
    metadata: dict[str, Any] | None = None
    kind: Literal["task"] | None = "task"


class TaskQueryParams(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    history_length: int | None = Field(default=None, alias="historyLength")
    metadata: dict[str, Any] | None = None


class TaskIdParams(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    metadata: dict[str, Any] | None = None


class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 request envelope."""

    jsonrpc: Literal["2.0"]
    method: str
    id: str | int | None = None
    params: dict[str, Any] | None = None

    @field_validator("jsonrpc")
    @classmethod
    def _enforce_version(cls, value: str) -> str:
        if value != "2.0":
            raise ValueError("Only JSON-RPC 2.0 is supported")
        return value
