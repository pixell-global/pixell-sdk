"""A2A Client for agent-to-agent communication.

Provides a full-featured client for calling other agents via the A2A protocol.
Supports streaming, multi-turn sessions, clarification handling, and retries.

Example:
    # Simple: Send and wait for completion
    async with A2AClient(agent_url, jwt_token) as client:
        result = await client.send_message("Find unpaid registrations")
        print(result.data)

    # Advanced: Stream events in real-time
    async with A2AClient(agent_url, jwt_token) as client:
        async for event in client.stream_message("Find unpaid registrations"):
            if event.type == "complete":
                return event.data
            elif event.type == "status":
                print(f"Status: {event.message}")

    # Multi-turn session
    async with A2AClient(agent_url, jwt_token) as client:
        session = await client.start_session()
        result1 = await session.send("Attach the sheet")
        result2 = await session.send("Now find unpaid rows")
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Callable, Optional

import httpx

log = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================


class A2AError(Exception):
    """Base error for A2A operations."""

    def __init__(self, code: str, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"{code}: {message}")


class A2AConnectionError(A2AError):
    """Failed to connect to agent."""

    def __init__(self, message: str, cause: Exception | None = None):
        super().__init__("connection_error", message, {"cause": str(cause) if cause else None})
        self.__cause__ = cause


class A2ATimeoutError(A2AError):
    """Agent request timed out."""

    def __init__(self, timeout: float):
        super().__init__("timeout", f"Request timed out after {timeout}s")


class A2AClarificationNeeded(A2AError):
    """Agent needs clarification - caller must respond."""

    def __init__(self, session_id: str, questions: list[dict]):
        super().__init__(
            "clarification_needed",
            "Agent needs clarification",
            {"session_id": session_id, "questions": questions},
        )
        self.session_id = session_id
        self.questions = questions


# ============================================================================
# Event Types
# ============================================================================


@dataclass
class A2AEvent:
    """Event from A2A stream.

    Attributes:
        type: Event type (status, progress, clarification_needed, selection_needed,
              preview_ready, complete, error)
        raw: Raw event dict
        session_id: Session identifier
        message: Human-readable message
        status: Task status for status events
        percent: Progress percentage for progress events
        questions: Questions for clarification_needed events
        items: Items for selection_needed events
        preview: Preview data for preview_ready events
        data: Result data for complete events
        answer: Text answer for complete events
        code: Error code for error events
    """

    type: str
    raw: dict = field(repr=False)

    # Common fields
    session_id: str | None = None
    message: str | None = None

    # Type-specific fields
    status: str | None = None  # for status events
    percent: int | None = None  # for progress events
    questions: list[dict] | None = None  # for clarification_needed
    items: list[dict] | None = None  # for selection_needed
    preview: dict | None = None  # for preview_ready
    data: dict | None = None  # for complete
    answer: str | None = None  # for complete
    code: str | None = None  # for error

    @classmethod
    def from_dict(cls, d: dict) -> "A2AEvent":
        """Create A2AEvent from dict."""
        # Handle nested result structure (A2A protocol puts answer in result.answer)
        result = d.get("result", {}) if isinstance(d.get("result"), dict) else {}
        answer = d.get("answer") or result.get("answer")
        data = d.get("data") or result.get("data")

        # If data is not a dict but result is, use result as data
        if not isinstance(data, dict) and isinstance(result, dict) and result:
            data = result

        # Get event type - could be in "type", "event", or inferred from "state"
        event_type = d.get("type", d.get("event", "unknown"))

        # Normalize event type based on state for terminal events
        state = d.get("state") or d.get("status")
        if state == "completed" and event_type in ("unknown", "message", "status-update"):
            event_type = "complete"
        elif state == "failed" and event_type in ("unknown", "message", "status-update"):
            event_type = "error"

        return cls(
            type=event_type,
            raw=d,
            session_id=d.get("sessionId") or d.get("session_id"),
            message=d.get("message"),
            status=state,
            percent=d.get("percent") or d.get("progress"),
            questions=d.get("questions"),
            items=d.get("items"),
            preview=d.get("preview"),
            data=data if isinstance(data, dict) else None,
            answer=answer,
            code=d.get("code") or d.get("error_type"),
        )


# ============================================================================
# Agent Info
# ============================================================================


@dataclass
class AgentInfo:
    """Information about an agent from PAR discovery."""

    agent_id: str
    name: str
    url: str
    capabilities: list[str] = field(default_factory=list)
    version: str | None = None
    description: str | None = None


# ============================================================================
# Session
# ============================================================================


class A2ASession:
    """Multi-turn conversation session with an agent.

    Use sessions when you need to have a conversation with another agent
    where each message builds on the previous context.

    Example:
        session = await client.start_session()
        result1 = await session.send("Load the spreadsheet")
        result2 = await session.send("Now find rows where status='unpaid'")
        await session.close()
    """

    def __init__(
        self,
        client: "A2AClient",
        session_id: str,
    ):
        self._client = client
        self.session_id = session_id
        self._closed = False

    async def send(
        self,
        message: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> A2AEvent:
        """Send a message in this session.

        Args:
            message: Message text to send
            metadata: Additional metadata

        Returns:
            Final A2AEvent from the response

        Raises:
            A2AError: If session is closed or request fails
        """
        if self._closed:
            raise A2AError("session_closed", "Session has been closed")

        return await self._client.send_message(
            message,
            session_id=self.session_id,
            metadata=metadata,
        )

    async def stream(
        self,
        message: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> AsyncGenerator[A2AEvent, None]:
        """Stream a message in this session.

        Args:
            message: Message text to send
            metadata: Additional metadata

        Yields:
            A2AEvent objects as they arrive

        Raises:
            A2AError: If session is closed
        """
        if self._closed:
            raise A2AError("session_closed", "Session has been closed")

        async for event in self._client.stream_message(
            message,
            session_id=self.session_id,
            metadata=metadata,
        ):
            yield event

    async def respond(
        self,
        response_type: str,
        **response_data,
    ) -> A2AEvent:
        """Respond to a clarification/selection request.

        Args:
            response_type: Type of response (clarification, selection, preview, permission)
            **response_data: Response-specific data

        Returns:
            Final A2AEvent from the response
        """
        return await self._client.respond(
            session_id=self.session_id,
            response_type=response_type,
            **response_data,
        )

    async def close(self) -> None:
        """Close the session."""
        self._closed = True


# ============================================================================
# Client
# ============================================================================


class A2AClient:
    """Client for agent-to-agent communication via A2A protocol.

    Supports:
    - Single messages with streaming or blocking
    - Multi-turn sessions
    - Clarification/selection/preview responses
    - Retry with exponential backoff
    - Agent discovery via PAR

    Example:
        # Option 1: Direct agent URL (when you know the agent)
        async with A2AClient(
            agent_url="https://par.pixell.global/agents/{agent-id}",
            jwt_token=ctx.jwt_token,
        ) as client:
            result = await client.send_message("Find unpaid registrations")

        # Option 2: Discover agent by name/capability
        client = await A2AClient.from_discovery(
            par_url="https://par.pixell.global",
            agent_name="data-agent",
            jwt_token=ctx.jwt_token,
        )
    """

    def __init__(
        self,
        agent_url: str,
        jwt_token: str | None = None,
        *,
        timeout: float = 120.0,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ) -> None:
        """Initialize A2A client.

        Args:
            agent_url: Full URL of target agent (via PAR)
            jwt_token: JWT token for authentication
            timeout: Request timeout in seconds
            max_retries: Max retry attempts for transient errors
            retry_base_delay: Base delay for exponential backoff
        """
        self.agent_url = agent_url.rstrip("/")
        self.jwt_token = jwt_token
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self._client: httpx.AsyncClient | None = None

    # --- Class methods for discovery ---

    @classmethod
    async def from_discovery(
        cls,
        par_url: str,
        *,
        agent_name: str | None = None,
        agent_id: str | None = None,
        capability: str | None = None,
        jwt_token: str | None = None,
        **kwargs,
    ) -> "A2AClient":
        """Create client by discovering agent via PAR.

        Args:
            par_url: PAR base URL (e.g., https://par.pixell.global)
            agent_name: Find agent by name
            agent_id: Find agent by ID
            capability: Find agent by capability
            jwt_token: JWT token for authentication
            **kwargs: Additional args passed to A2AClient

        Returns:
            A2AClient configured for the discovered agent

        Raises:
            A2AError: If no matching agent found
        """
        agents = await cls.list_agents(par_url)

        for agent in agents:
            if agent_id and agent.agent_id == agent_id:
                return cls(agent.url, jwt_token, **kwargs)
            if agent_name and agent.name.lower() == agent_name.lower():
                return cls(agent.url, jwt_token, **kwargs)
            if capability and capability in agent.capabilities:
                return cls(agent.url, jwt_token, **kwargs)

        raise A2AError(
            "agent_not_found",
            f"No agent found matching: name={agent_name}, id={agent_id}, capability={capability}",
        )

    @classmethod
    async def list_agents(cls, par_url: str) -> list[AgentInfo]:
        """List all available agents from PAR.

        Args:
            par_url: PAR base URL

        Returns:
            List of AgentInfo objects
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{par_url.rstrip('/')}/agents")
            response.raise_for_status()
            data = response.json()

            # Handle both list and dict responses
            agents_list = data if isinstance(data, list) else data.get("agents", [])

            return [
                AgentInfo(
                    # PAR uses agent_app_id, other systems might use id or app_id
                    agent_id=a.get("agent_app_id", a.get("id", a.get("app_id", "unknown"))),
                    name=a.get("name", a.get("agent_app_id", "unknown")),
                    url=f"{par_url.rstrip('/')}/agents/{a.get('agent_app_id', a.get('id', a.get('app_id')))}",
                    capabilities=a.get("capabilities", []),
                    version=a.get("version"),
                    description=a.get("description"),
                )
                for a in agents_list
            ]

    # --- Instance methods ---

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout, connect=10.0)
            )
        return self._client

    async def get_agent_info(self) -> AgentInfo:
        """Get information about the target agent.

        Returns:
            AgentInfo with agent metadata
        """
        client = self._get_client()
        response = await client.get(f"{self.agent_url}/.well-known/agent.json")
        response.raise_for_status()
        data = response.json()

        return AgentInfo(
            agent_id=data.get("id", "unknown"),
            name=data.get("name", "unknown"),
            url=self.agent_url,
            capabilities=data.get("capabilities", []),
            version=data.get("version"),
            description=data.get("description"),
        )

    async def stream_message(
        self,
        message: str,
        *,
        session_id: str | None = None,
        workflow_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AsyncGenerator[A2AEvent, None]:
        """Send message and stream response events.

        Args:
            message: Message text to send
            session_id: Session ID for multi-turn conversations
            workflow_id: Workflow ID for correlation
            metadata: Additional metadata (user_id, pxui_base_url, etc.)

        Yields:
            A2AEvent objects as they arrive

        Raises:
            A2AConnectionError: Failed to connect
            A2ATimeoutError: Request timed out
            A2AError: Other errors
        """
        # Build metadata with JWT token
        full_metadata = metadata.copy() if metadata else {}
        if self.jwt_token:
            full_metadata["jwt_token"] = self.jwt_token

        # Build JSON-RPC request
        request_id = str(uuid.uuid4())
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "message/stream",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": message}],
                },
                "metadata": full_metadata,
            },
        }

        if session_id:
            request["params"]["sessionId"] = session_id
        if workflow_id:
            request["params"]["workflowId"] = workflow_id

        # Send with retry
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                async for event in self._stream_request(request):
                    yield event
                return  # Success
            except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_base_delay * (2**attempt)
                    log.warning(
                        f"A2A connection failed, retry {attempt + 1} in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
            except httpx.TimeoutException as e:
                raise A2ATimeoutError(self.timeout) from e

        raise A2AConnectionError("Failed to connect after retries", last_error)

    async def _stream_request(
        self,
        request: dict,
    ) -> AsyncGenerator[A2AEvent, None]:
        """Internal: Execute streaming request."""
        client = self._get_client()

        async with client.stream(
            "POST",
            self.agent_url,
            json=request,
            headers={"Accept": "text/event-stream"},
        ) as response:
            response.raise_for_status()

            # Track current event type from "event:" line
            current_event_type: str | None = None

            async for line in response.aiter_lines():
                if not line:
                    # Empty line signals end of an event
                    current_event_type = None
                    continue

                # Skip SSE comments (buffer flush padding)
                if line.startswith(":"):
                    continue

                # Parse "event: type" line
                if line.startswith("event:"):
                    current_event_type = line[6:].strip()
                    continue

                # Parse "id: N" line (ignore for now)
                if line.startswith("id:"):
                    continue

                # Parse "data: {...}" line
                if line.startswith("data: "):
                    data = line[6:].strip()
                elif line.startswith("data:"):
                    data = line[5:].strip()
                else:
                    continue

                if not data:
                    continue

                try:
                    event_dict = json.loads(data)

                    # Inject event type from "event:" line if present
                    if current_event_type and "type" not in event_dict:
                        event_dict["type"] = current_event_type

                    event = A2AEvent.from_dict(event_dict)
                    yield event

                    # Check for terminal events
                    if event.type == "error":
                        raise A2AError(
                            event.code or "unknown",
                            event.message or "Unknown error",
                            event.raw,
                        )

                except json.JSONDecodeError:
                    log.warning(f"Failed to parse SSE event: {data}")
                    continue

    async def send_message(
        self,
        message: str,
        *,
        session_id: str | None = None,
        workflow_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        handle_clarification: Callable[[A2AEvent], dict] | None = None,
    ) -> A2AEvent:
        """Send message and wait for completion.

        Args:
            message: Message text to send
            session_id: Session ID for multi-turn conversations
            workflow_id: Workflow ID for correlation
            metadata: Additional metadata
            handle_clarification: Optional callback to handle clarification requests.
                If not provided, raises A2AClarificationNeeded.

        Returns:
            Final A2AEvent (type=complete)

        Raises:
            A2AClarificationNeeded: If agent needs clarification and no handler
            A2AError: Other errors
        """
        result: A2AEvent | None = None
        current_session_id = session_id

        async for event in self.stream_message(
            message,
            session_id=current_session_id,
            workflow_id=workflow_id,
            metadata=metadata,
        ):
            # Track session ID from events
            if event.session_id:
                current_session_id = event.session_id

            if event.type == "complete" or event.type == "message":
                # "message" event with state=completed is the final result
                if event.status == "completed" or event.type == "complete":
                    result = event

            elif event.type == "clarification_needed":
                if handle_clarification:
                    # Use callback to get response
                    response_data = handle_clarification(event)
                    # Send response and continue
                    async for resp_event in self._respond_stream(
                        current_session_id or "",
                        "clarification",
                        response_data,
                    ):
                        if resp_event.type == "complete" or (
                            resp_event.type == "message"
                            and resp_event.status == "completed"
                        ):
                            result = resp_event
                else:
                    raise A2AClarificationNeeded(
                        event.session_id or "",
                        event.questions or [],
                    )

            elif event.type in ("selection_needed", "preview_ready"):
                # For now, raise error - caller should use stream_message
                raise A2AError(
                    event.type,
                    f"Agent requires {event.type}, use stream_message to handle",
                    event.raw,
                )

        if result is None:
            raise A2AError("no_result", "Agent did not return a result")

        return result

    async def respond(
        self,
        session_id: str,
        response_type: str,
        **response_data,
    ) -> A2AEvent:
        """Respond to a clarification/selection/preview request.

        Args:
            session_id: Session ID from the request event
            response_type: Type of response (clarification, selection, preview, permission)
            **response_data: Response-specific data:
                - clarification: answers={question_id: answer_value}
                - selection: selected_ids=[...]
                - preview: approved=True/False
                - permission: action="allow"|"deny"

        Returns:
            Final A2AEvent from the response
        """
        result: A2AEvent | None = None
        async for event in self._respond_stream(session_id, response_type, response_data):
            if event.type == "complete" or (
                event.type == "message" and event.status == "completed"
            ):
                result = event

        if result is None:
            raise A2AError("no_result", "Agent did not return a result after respond")

        return result

    async def _respond_stream(
        self,
        session_id: str,
        response_type: str,
        response_data: dict,
    ) -> AsyncGenerator[A2AEvent, None]:
        """Internal: Send response and stream events."""
        request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "respond",
            "params": {
                "sessionId": session_id,
                "responseType": response_type,
                **response_data,
            },
        }

        async for event in self._stream_request(request):
            yield event

    async def start_session(
        self,
        initial_message: str | None = None,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> A2ASession:
        """Start a multi-turn conversation session.

        Args:
            initial_message: Optional first message to send
            metadata: Metadata for the session

        Returns:
            A2ASession object for continuing the conversation
        """
        session_id = str(uuid.uuid4())

        if initial_message:
            async for event in self.stream_message(
                initial_message,
                session_id=session_id,
                metadata=metadata,
            ):
                if event.session_id:
                    session_id = event.session_id

        return A2ASession(self, session_id)

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "A2AClient":
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()
