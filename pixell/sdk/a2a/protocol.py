"""A2A Protocol Types - JSON-RPC message types for agent communication."""

from enum import Enum
from typing import Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
import uuid


class TaskState(str, Enum):
    """Task execution states."""

    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass
class TextPart:
    """Text content part."""

    text: str

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text}


@dataclass
class DataPart:
    """Structured data part."""

    data: dict[str, Any]
    mimeType: str = "application/json"

    def to_dict(self) -> dict[str, Any]:
        return {"data": self.data, "mimeType": self.mimeType}


@dataclass
class FilePart:
    """File reference part."""

    file: dict[str, Any]  # {name, mimeType, bytes or uri}

    def to_dict(self) -> dict[str, Any]:
        return {"file": self.file}


MessagePart = Union[TextPart, DataPart, FilePart]


@dataclass
class A2AMessage:
    """A2A protocol message."""

    role: str  # "user" | "agent"
    parts: list[MessagePart]
    messageId: str = field(default_factory=lambda: str(uuid.uuid4()))

    @classmethod
    def user(cls, text: str) -> "A2AMessage":
        """Create a user message with text."""
        return cls(role="user", parts=[TextPart(text=text)])

    @classmethod
    def agent(cls, text: str) -> "A2AMessage":
        """Create an agent message with text."""
        return cls(role="agent", parts=[TextPart(text=text)])

    @classmethod
    def agent_with_data(cls, text: str, data: dict[str, Any]) -> "A2AMessage":
        """Create an agent message with text and structured data."""
        return cls(role="agent", parts=[TextPart(text=text), DataPart(data=data)])

    @property
    def text(self) -> str:
        """Get concatenated text from all text parts."""
        return "".join(part.text for part in self.parts if isinstance(part, TextPart))

    def to_dict(self) -> dict[str, Any]:
        return {
            "messageId": self.messageId,
            "role": self.role,
            "parts": [part.to_dict() if hasattr(part, "to_dict") else part for part in self.parts],
        }


@dataclass
class TaskStatus:
    """Task execution status."""

    state: TaskState
    message: Optional[A2AMessage] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "state": self.state.value,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.message:
            result["message"] = self.message.to_dict()
        return result


@dataclass
class JSONRPCError:
    """JSON-RPC error object."""

    code: int
    message: str
    data: Optional[dict[str, Any]] = None

    # Standard error codes
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # A2A custom error codes
    TASK_NOT_FOUND = -32000
    TASK_CANCELED = -32001
    INPUT_REQUIRED = -32002

    def to_dict(self) -> dict[str, Any]:
        result = {"code": self.code, "message": self.message}
        if self.data:
            result["data"] = self.data
        return result


@dataclass
class JSONRPCRequest:
    """JSON-RPC 2.0 request."""

    method: str
    params: dict[str, Any]
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    jsonrpc: str = "2.0"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JSONRPCRequest":
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            method=data["method"],
            params=data.get("params", {}),
            id=data.get("id", str(uuid.uuid4())),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "jsonrpc": self.jsonrpc,
            "method": self.method,
            "params": self.params,
            "id": self.id,
        }


@dataclass
class JSONRPCResponse:
    """JSON-RPC 2.0 response."""

    id: str
    result: Optional[dict[str, Any]] = None
    error: Optional[JSONRPCError] = None
    jsonrpc: str = "2.0"

    @classmethod
    def success(cls, id: str, result: dict[str, Any]) -> "JSONRPCResponse":
        return cls(id=id, result=result)

    @classmethod
    def failure(cls, id: str, error: JSONRPCError) -> "JSONRPCResponse":
        return cls(id=id, error=error)

    def to_dict(self) -> dict[str, Any]:
        result = {"jsonrpc": self.jsonrpc, "id": self.id}
        if self.error:
            result["error"] = self.error.to_dict()
        else:
            result["result"] = self.result
        return result


@dataclass
class SendMessageParams:
    """Parameters for message/send method."""

    message: A2AMessage
    sessionId: Optional[str] = None
    workflowId: Optional[str] = None  # Root correlation ID from orchestrator
    metadata: Optional[dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SendMessageParams":
        msg_data = data["message"]
        parts = []
        for part in msg_data.get("parts", []):
            if "text" in part:
                parts.append(TextPart(text=part["text"]))
            elif "data" in part:
                parts.append(
                    DataPart(data=part["data"], mimeType=part.get("mimeType", "application/json"))
                )
            elif "file" in part:
                parts.append(FilePart(file=part["file"]))

        message = A2AMessage(
            messageId=msg_data.get("messageId", str(uuid.uuid4())),
            role=msg_data.get("role", "user"),
            parts=parts,
        )

        return cls(
            message=message,
            sessionId=data.get("sessionId"),
            workflowId=data.get("workflowId"),
            metadata=data.get("metadata"),
        )


@dataclass
class StreamMessageParams(SendMessageParams):
    """Parameters for message/stream method (same as send)."""

    pass


@dataclass
class RespondParams:
    """Parameters for respond method (user response to input-required)."""

    clarificationId: Optional[str] = None
    selectionId: Optional[str] = None
    planId: Optional[str] = None
    answers: Optional[dict[str, Any]] = None
    selectedIds: Optional[list[str]] = None
    approved: Optional[bool] = None
    sessionId: Optional[str] = None
    workflowId: Optional[str] = None  # Root correlation ID from orchestrator

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RespondParams":
        return cls(
            clarificationId=data.get("clarificationId"),
            selectionId=data.get("selectionId"),
            planId=data.get("planId"),
            answers=data.get("answers"),
            selectedIds=data.get("selectedIds"),
            approved=data.get("approved"),
            sessionId=data.get("sessionId"),
            workflowId=data.get("workflowId"),
        )
