"""A2A Handlers - Request handling and context management."""

from typing import Any, Optional, Callable, Awaitable, TYPE_CHECKING
from dataclasses import dataclass, field
import uuid

from pixell.sdk.a2a.protocol import (
    A2AMessage,
    SendMessageParams,
    RespondParams,
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCError,
)
from pixell.sdk.a2a.streaming import SSEStream

if TYPE_CHECKING:
    from pixell.sdk.plan_mode import PlanModeContext
    from pixell.sdk.translation import TranslationContext


@dataclass
class MessageContext:
    """Context for handling incoming messages.

    Provides access to the message, plan mode context, translation context,
    and SSE stream for emitting events.

    Attributes:
        message: The incoming A2A message
        session_id: Session identifier
        metadata: Request metadata (user preferences, language, etc.)
        plan_mode: Plan mode context for phase management
        translation: Translation context for i18n
        stream: SSE stream for emitting events
    """

    message: A2AMessage
    session_id: str
    stream: SSEStream
    metadata: dict[str, Any] = field(default_factory=dict)
    plan_mode: Optional["PlanModeContext"] = None
    translation: Optional["TranslationContext"] = None

    @property
    def text(self) -> str:
        """Get message text."""
        return self.message.text

    @property
    def user_language(self) -> str:
        """Get user's preferred language from metadata."""
        return self.metadata.get("language", "en")

    async def emit_status(self, state: str, message: str, **data: Any) -> None:
        """Emit a status update event."""
        await self.stream.emit_status(state, message, **data)

    async def emit_progress(self, percent: float, message: Optional[str] = None) -> None:
        """Emit a progress update."""
        await self.stream.emit_progress(percent, message)

    async def emit_result(self, text: str, data: Optional[dict[str, Any]] = None) -> None:
        """Emit a result message."""
        if data:
            msg = A2AMessage.agent_with_data(text, data)
        else:
            msg = A2AMessage.agent(text)
        await self.stream.emit_result(msg)

    async def emit_file_created(
        self,
        path: str,
        *,
        name: Optional[str] = None,
        format: Optional[str] = None,
        summary: Optional[str] = None,
        size: Optional[int] = None,
    ) -> None:
        """Emit a file_created event for orchestrator to upload to S3.

        This is the standard way for agents to notify the system that a file
        has been created and should be uploaded to user storage.

        Args:
            path: Path to the file (relative to agent's outputs_dir)
            name: Display name for the file (defaults to filename from path)
            format: File format/type (e.g., "html", "json", "csv")
            summary: Human-readable description of the file
            size: File size in bytes (optional)

        Example:
            await ctx.emit_file_created(
                path="exports/report.html",
                name="Analysis Report",
                format="html",
                summary="Reddit research results for user query"
            )
        """
        # Auto-detect name from path if not provided
        if not name:
            from pathlib import Path as PathLib

            name = PathLib(path).name

        # Auto-detect format from extension if not provided
        if not format:
            from pathlib import Path as PathLib

            suffix = PathLib(path).suffix.lower()
            format = suffix[1:] if suffix else "unknown"

        await self.stream.emit_status(
            "working",
            f"File created: {name}",
            step="file_created",
            path=path,
            name=name,
            format=format,
            summary=summary,
            size=size,
        )


@dataclass
class ResponseContext:
    """Context for handling user responses to input-required states.

    This is used when the user responds to clarification, selection, or preview.

    Attributes:
        clarification_id: ID of the clarification being responded to
        selection_id: ID of the selection being responded to
        plan_id: ID of the plan being approved/rejected
        answers: User answers to clarification questions
        selected_ids: Selected item IDs
        approved: Whether plan was approved
        session_id: Session identifier
        stream: SSE stream for emitting events
    """

    session_id: str
    stream: SSEStream
    clarification_id: Optional[str] = None
    selection_id: Optional[str] = None
    plan_id: Optional[str] = None
    answers: Optional[dict[str, Any]] = None
    selected_ids: Optional[list[str]] = None
    approved: Optional[bool] = None
    plan_mode: Optional["PlanModeContext"] = None
    translation: Optional["TranslationContext"] = None

    @property
    def response_type(self) -> str:
        """Determine the type of response."""
        if self.clarification_id:
            return "clarification"
        elif self.selection_id:
            return "selection"
        elif self.plan_id:
            return "plan"
        return "unknown"

    async def emit_status(self, state: str, message: str, **data: Any) -> None:
        """Emit a status update event."""
        await self.stream.emit_status(state, message, **data)

    async def emit_result(self, text: str, data: Optional[dict[str, Any]] = None) -> None:
        """Emit a result message."""
        if data:
            msg = A2AMessage.agent_with_data(text, data)
        else:
            msg = A2AMessage.agent(text)
        await self.stream.emit_result(msg)

    async def emit_file_created(
        self,
        path: str,
        *,
        name: Optional[str] = None,
        format: Optional[str] = None,
        summary: Optional[str] = None,
        size: Optional[int] = None,
    ) -> None:
        """Emit a file_created event for orchestrator to upload to S3.

        This is the standard way for agents to notify the system that a file
        has been created and should be uploaded to user storage.

        Args:
            path: Path to the file (relative to agent's outputs_dir)
            name: Display name for the file (defaults to filename from path)
            format: File format/type (e.g., "html", "json", "csv")
            summary: Human-readable description of the file
            size: File size in bytes (optional)

        Example:
            await ctx.emit_file_created(
                path="exports/report.html",
                name="Analysis Report",
                format="html",
                summary="Reddit research results for user query"
            )
        """
        # Auto-detect name from path if not provided
        if not name:
            from pathlib import Path as PathLib

            name = PathLib(path).name

        # Auto-detect format from extension if not provided
        if not format:
            from pathlib import Path as PathLib

            suffix = PathLib(path).suffix.lower()
            format = suffix[1:] if suffix else "unknown"

        await self.stream.emit_status(
            "working",
            f"File created: {name}",
            step="file_created",
            path=path,
            name=name,
            format=format,
            summary=summary,
            size=size,
        )


MessageHandler = Callable[[MessageContext], Awaitable[None]]
ResponseHandler = Callable[[ResponseContext], Awaitable[None]]


class A2AHandler:
    """Handler registration and dispatch for A2A protocol methods.

    This class manages handler functions for different A2A methods
    and provides JSON-RPC dispatch logic.

    Example:
        handler = A2AHandler()

        @handler.on_message
        async def handle_message(ctx: MessageContext):
            await ctx.emit_status("working", "Processing...")
            # ... agent logic
            await ctx.emit_result("Done!")

        @handler.on_respond
        async def handle_respond(ctx: ResponseContext):
            if ctx.response_type == "clarification":
                # Handle clarification response
                pass
    """

    def __init__(self) -> None:
        self._message_handler: Optional[MessageHandler] = None
        self._respond_handler: Optional[ResponseHandler] = None

    def on_message(self, func: MessageHandler) -> MessageHandler:
        """Decorator to register message handler.

        Args:
            func: Async function that takes MessageContext

        Returns:
            The registered function
        """
        self._message_handler = func
        return func

    def on_respond(self, func: ResponseHandler) -> ResponseHandler:
        """Decorator to register respond handler.

        Args:
            func: Async function that takes ResponseContext

        Returns:
            The registered function
        """
        self._respond_handler = func
        return func

    async def handle_request(
        self,
        request: JSONRPCRequest,
        stream: SSEStream,
        plan_mode: Optional["PlanModeContext"] = None,
        translation: Optional["TranslationContext"] = None,
    ) -> JSONRPCResponse:
        """Handle a JSON-RPC request.

        Args:
            request: The JSON-RPC request
            stream: SSE stream for events
            plan_mode: Optional plan mode context
            translation: Optional translation context

        Returns:
            JSON-RPC response
        """
        try:
            if request.method in ("message/send", "message/stream"):
                return await self._handle_message(request, stream, plan_mode, translation)
            elif request.method == "respond":
                return await self._handle_respond(request, stream, plan_mode, translation)
            else:
                return JSONRPCResponse.failure(
                    request.id,
                    JSONRPCError(
                        code=JSONRPCError.METHOD_NOT_FOUND,
                        message=f"Method not found: {request.method}",
                    ),
                )
        except Exception as e:
            return JSONRPCResponse.failure(
                request.id,
                JSONRPCError(
                    code=JSONRPCError.INTERNAL_ERROR,
                    message=str(e),
                ),
            )

    async def _handle_message(
        self,
        request: JSONRPCRequest,
        stream: SSEStream,
        plan_mode: Optional["PlanModeContext"],
        translation: Optional["TranslationContext"],
    ) -> JSONRPCResponse:
        """Handle message/send or message/stream request."""
        if not self._message_handler:
            return JSONRPCResponse.failure(
                request.id,
                JSONRPCError(
                    code=JSONRPCError.INTERNAL_ERROR,
                    message="No message handler registered",
                ),
            )

        params = SendMessageParams.from_dict(request.params)
        session_id = params.sessionId or str(uuid.uuid4())

        ctx = MessageContext(
            message=params.message,
            session_id=session_id,
            stream=stream,
            metadata=params.metadata or {},
            plan_mode=plan_mode,
            translation=translation,
        )

        await self._message_handler(ctx)

        return JSONRPCResponse.success(request.id, {"sessionId": session_id})

    async def _handle_respond(
        self,
        request: JSONRPCRequest,
        stream: SSEStream,
        plan_mode: Optional["PlanModeContext"],
        translation: Optional["TranslationContext"],
    ) -> JSONRPCResponse:
        """Handle respond request."""
        if not self._respond_handler:
            return JSONRPCResponse.failure(
                request.id,
                JSONRPCError(
                    code=JSONRPCError.INTERNAL_ERROR,
                    message="No respond handler registered",
                ),
            )

        params = RespondParams.from_dict(request.params)
        session_id = params.sessionId or str(uuid.uuid4())

        ctx = ResponseContext(
            session_id=session_id,
            stream=stream,
            clarification_id=params.clarificationId,
            selection_id=params.selectionId,
            plan_id=params.planId,
            answers=params.answers,
            selected_ids=params.selectedIds,
            approved=params.approved,
            plan_mode=plan_mode,
            translation=translation,
        )

        await self._respond_handler(ctx)

        return JSONRPCResponse.success(request.id, {"sessionId": session_id})
