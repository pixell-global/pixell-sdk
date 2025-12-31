"""A2A Protocol Module - JSON-RPC based agent-to-agent communication."""

from pixell.sdk.a2a.protocol import (
    A2AMessage,
    MessagePart,
    TextPart,
    DataPart,
    FilePart,
    TaskStatus,
    TaskState,
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCError,
    SendMessageParams,
    StreamMessageParams,
    RespondParams,
)
from pixell.sdk.a2a.streaming import SSEStream, SSEEvent
from pixell.sdk.a2a.handlers import A2AHandler, MessageContext, ResponseContext

__all__ = [
    # Protocol types
    "A2AMessage",
    "MessagePart",
    "TextPart",
    "DataPart",
    "FilePart",
    "TaskStatus",
    "TaskState",
    "JSONRPCRequest",
    "JSONRPCResponse",
    "JSONRPCError",
    "SendMessageParams",
    "StreamMessageParams",
    "RespondParams",
    # Streaming
    "SSEStream",
    "SSEEvent",
    # Handlers
    "A2AHandler",
    "MessageContext",
    "ResponseContext",
]
