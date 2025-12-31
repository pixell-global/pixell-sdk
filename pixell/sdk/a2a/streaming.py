"""SSE Streaming - Server-Sent Events for real-time progress."""

import json
import asyncio
from typing import Any, Optional, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime

from pixell.sdk.a2a.protocol import A2AMessage


@dataclass
class SSEEvent:
    """Server-Sent Event."""

    event: str
    data: dict[str, Any]
    id: Optional[str] = None
    retry: Optional[int] = None

    def encode(self) -> str:
        """Encode as SSE format string."""
        lines = []
        if self.id:
            lines.append(f"id: {self.id}")
        if self.retry:
            lines.append(f"retry: {self.retry}")
        lines.append(f"event: {self.event}")
        lines.append(f"data: {json.dumps(self.data)}")
        return "\n".join(lines) + "\n\n"


class SSEStream:
    """Server-Sent Events stream for real-time progress.

    This class provides methods for emitting SSE events during task execution.
    It integrates with plan mode and handles the A2A protocol event types.

    All events automatically include workflowId and sessionId for correlation.
    These IDs are passed from the orchestrator and enable reliable message tracking.

    Example:
        async with SSEStream(workflow_id="...", session_id="...") as stream:
            await stream.emit_status("working", "Processing request...")
            await stream.emit_clarification(clarification)
            await stream.emit_result(message)
    """

    def __init__(
        self,
        workflow_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Initialize SSE stream with correlation IDs.

        Args:
            workflow_id: Root workflow correlation ID from orchestrator.
                         If provided, auto-injected into all events.
            session_id: Session ID from orchestrator.
                        If provided, auto-injected into all events.
        """
        self._queue: asyncio.Queue[SSEEvent] = asyncio.Queue()
        self._closed = False
        self._event_id = 0
        self._workflow_id = workflow_id
        self._session_id = session_id

    def _next_id(self) -> str:
        """Generate next event ID."""
        self._event_id += 1
        return str(self._event_id)

    async def _emit(self, event: str, data: dict[str, Any]) -> None:
        """Emit an SSE event.

        Automatically injects workflowId and sessionId if set.
        This ensures all events can be correlated back to the workflow.

        Args:
            event: Event type name
            data: Event data payload
        """
        if self._closed:
            return

        # Build payload with correlation IDs auto-injected
        payload = {
            **data,
            "timestamp": datetime.utcnow().isoformat(),
            "sequence": self._event_id,  # Monotonic sequence for ordering
        }

        # Auto-inject correlation IDs if set
        if self._workflow_id:
            payload["workflowId"] = self._workflow_id
        if self._session_id:
            payload["sessionId"] = self._session_id

        sse_event = SSEEvent(
            event=event,
            data=payload,
            id=self._next_id(),
        )
        await self._queue.put(sse_event)

    async def emit_status(
        self,
        state: str,
        message: str,
        **data: Any,
    ) -> None:
        """Emit a status update event.

        Args:
            state: Task state (working, input-required, completed, failed)
            message: Human-readable status message
            **data: Additional data to include in the event
        """
        await self._emit(
            "status-update",
            {
                "state": state,
                "message": message,
                **data,
            },
        )

    async def emit_progress(
        self,
        percent: float,
        message: Optional[str] = None,
        **data: Any,
    ) -> None:
        """Emit a progress update event.

        Args:
            percent: Progress percentage (0-100)
            message: Optional progress message
            **data: Additional data to include
        """
        payload: dict[str, Any] = {
            "state": "working",
            "progress": percent,
        }
        if message:
            payload["message"] = message
        payload.update(data)
        await self._emit("status-update", payload)

    async def emit_clarification(
        self,
        clarification: dict[str, Any],
    ) -> None:
        """Emit a clarification request event.

        This transitions the task to input-required state.

        Args:
            clarification: ClarificationNeeded data
        """
        await self._emit(
            "clarification_needed",
            {
                "state": "input-required",
                **clarification,
            },
        )

    async def emit_discovery(
        self,
        discovery: dict[str, Any],
    ) -> None:
        """Emit a discovery result event.

        Args:
            discovery: DiscoveryResult data
        """
        await self._emit(
            "discovery_result",
            {
                "state": "working",
                **discovery,
            },
        )

    async def emit_selection(
        self,
        selection: dict[str, Any],
    ) -> None:
        """Emit a selection request event.

        This transitions the task to input-required state.

        Args:
            selection: SelectionRequired data
        """
        await self._emit(
            "selection_required",
            {
                "state": "input-required",
                **selection,
            },
        )

    async def emit_preview(
        self,
        preview: dict[str, Any],
    ) -> None:
        """Emit a preview/plan event.

        This transitions the task to input-required state.

        Args:
            preview: SearchPlanPreview or PlanProposed data
        """
        await self._emit(
            "preview_ready",
            {
                "state": "input-required",
                **preview,
            },
        )

    async def emit_schedule_proposal(
        self,
        proposal: dict[str, Any],
    ) -> None:
        """Emit a schedule proposal event for user approval.

        This transitions the task to input-required state, prompting the user
        to confirm, edit, or cancel the proposed schedule.

        Args:
            proposal: ScheduleProposal.to_dict() data
        """
        await self._emit(
            "schedule_proposal",
            {
                "state": "input-required",
                **proposal,
            },
        )

    async def emit_result(
        self,
        message: A2AMessage,
        final: bool = True,
    ) -> None:
        """Emit a result message event.

        Args:
            message: A2A message with results
            final: Whether this is the final message
        """
        await self._emit(
            "message",
            {
                "state": "completed" if final else "working",
                "message": message.to_dict(),
                "final": final,
            },
        )

    async def emit_error(
        self,
        error_type: str,
        message: str,
        recoverable: bool = False,
        **data: Any,
    ) -> None:
        """Emit an error event.

        Args:
            error_type: Type of error
            message: Error message
            recoverable: Whether the error is recoverable
            **data: Additional error data
        """
        await self._emit(
            "error",
            {
                "state": "failed",
                "error_type": error_type,
                "message": message,
                "recoverable": recoverable,
                **data,
            },
        )

    async def events(self) -> AsyncGenerator[SSEEvent, None]:
        """Async generator yielding SSE events.

        Yields:
            SSEEvent objects as they are emitted
        """
        while not self._closed:
            try:
                event = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=30.0,  # Heartbeat timeout
                )
                yield event
            except asyncio.TimeoutError:
                # Send heartbeat comment
                yield SSEEvent(event="heartbeat", data={"type": "ping"})

    def close(self) -> None:
        """Close the stream."""
        self._closed = True

    async def __aenter__(self) -> "SSEStream":
        return self

    async def __aexit__(self, *args: Any) -> None:
        self.close()


def create_sse_response(stream: SSEStream) -> AsyncGenerator[str, None]:
    """Create an async generator of SSE-formatted strings.

    This can be used directly with FastAPI's StreamingResponse.

    Args:
        stream: SSEStream instance

    Returns:
        Async generator yielding SSE-formatted strings

    Example:
        from fastapi.responses import StreamingResponse

        stream = SSEStream()
        return StreamingResponse(
            create_sse_response(stream),
            media_type="text/event-stream"
        )
    """

    async def _generate() -> AsyncGenerator[str, None]:
        async for event in stream.events():
            yield event.encode()

    return _generate()
