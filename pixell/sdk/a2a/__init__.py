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
from pixell.sdk.a2a.client import (
    A2AClient,
    A2ASession,
    A2AEvent,
    A2AError,
    A2AConnectionError,
    A2ATimeoutError,
    A2AClarificationNeeded,
    AgentInfo,
)

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
    # Client (for agent-to-agent calls)
    "A2AClient",
    "A2ASession",
    "A2AEvent",
    "A2AError",
    "A2AConnectionError",
    "A2ATimeoutError",
    "A2AClarificationNeeded",
    "AgentInfo",
]
