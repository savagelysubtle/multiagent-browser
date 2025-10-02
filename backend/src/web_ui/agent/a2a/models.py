"""Typed representations of key Google A2A protocol objects.

These models intentionally cover the portion of the specification that the
current implementation needs: JSON-RPC envelopes, messages, tasks, and
identifiers used by the , , and 
procedures.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, Field, root_validator, validator


class JSONRPCError(BaseModel):
    """Standard JSON-RPC error structure."""

    code: int
    message: str
    data: Any | None = None


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 response envelope."""

    jsonrpc: Literal["2.0"] = "2.0"
    id: Union[str, int, None]
    result: Any | None = None
    error: JSONRPCError | None = None

    @root_validator
    def _validate_result_or_error(cls, values: dict[str, Any]) -> dict[str, Any]:
        result, error = values.get("result"), values.get("error")
        if result is None and error is None:
            raise ValueError("Either result or error must be provided for a JSON-RPC response")
        if result is not None and error is not None:
            raise ValueError("JSON-RPC responses cannot contain both result and error")
        return values


class FileResource(BaseModel):
    """Representation of the file metadata used inside file/data parts."""

    name: str | None = None
    uri: str | None = None
    mime_type: str | None = Field(default=None, alias="mimeType")

    class Config:
        allow_population_by_field_name = True


class PartKind(str, Enum):
    """Supported message part kinds."""

    TEXT = "text"
    FILE = "file"
    DATA = "data"


class Part(BaseModel):
    """Union type across text, file, and data parts."""

    kind: PartKind
    text: str | None = None
    data: Any | None = None
    file: FileResource | None = None
    mime_type: str | None = Field(default=None, alias="mimeType")
    metadata: dict[str, Any] | None = None

    @validator("text", always=True)
    def _validate_text(cls, value: str | None, values: dict[str, Any]):
        if values.get("kind") == PartKind.TEXT and not value:
            raise ValueError("Text parts must include a non-empty 'text' field")
        return value

    @validator("file", always=True)
    def _validate_file(cls, value: FileResource | None, values: dict[str, Any]):
        if values.get("kind") == PartKind.FILE and value is None:
            raise ValueError("File parts require a 'file' descriptor")
        return value

    @validator("data", always=True)
    def _validate_data(cls, value: Any | None, values: dict[str, Any]):
        if values.get("kind") == PartKind.DATA and value is None:
            raise ValueError("Data parts must include structured 'data'")
        return value

    class Config:
        use_enum_values = True
        allow_population_by_field_name = True


class MessageRole(str, Enum):
    USER = "user"
    AGENT = "agent"


class Message(BaseModel):
    """A message exchanged between client and agent."""

    role: MessageRole
    parts: list[Part]
    metadata: dict[str, Any] | None = None
    reference_task_ids: list[str] | None = Field(default=None, alias="referenceTaskIds")
    message_id: str | None = Field(default=None, alias="messageId")
    task_id: str | None = Field(default=None, alias="taskId")
    context_id: str | None = Field(default=None, alias="contextId")
    kind: Literal["message"] | None = "message"

    class Config:
        use_enum_values = True
        allow_population_by_field_name = True


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

    artifact_id: str = Field(alias="artifactId")
    name: str | None = None
    parts: list[Part]
    metadata: dict[str, Any] | None = None
    kind: Literal["artifact"] = "artifact"

    class Config:
        allow_population_by_field_name = True


class Task(BaseModel):
    """Full task snapshot returned by tasks/get and message/send."""

    id: str
    context_id: str = Field(alias="contextId")
    status: TaskStatus
    artifacts: list[Artifact] | None = None
    history: list[Message] | None = None
    metadata: dict[str, Any] | None = None
    kind: Literal["task"] | None = "task"

    class Config:
        allow_population_by_field_name = True


class TaskQueryParams(BaseModel):
    id: str
    history_length: int | None = Field(default=None, alias="historyLength")
    metadata: dict[str, Any] | None = None

    class Config:
        allow_population_by_field_name = True


class TaskIdParams(BaseModel):
    id: str
    metadata: dict[str, Any] | None = None


class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 request envelope."""

    jsonrpc: Literal["2.0"]
    method: str
    id: Union[str, int, None] = None
    params: dict[str, Any] | None = None

    @validator("jsonrpc")
    def _enforce_version(cls, value: str) -> str:
        if value != "2.0":
            raise ValueError("Only JSON-RPC 2.0 is supported")
        return value
