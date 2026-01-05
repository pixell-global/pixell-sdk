"""Unified AgentServer - FastAPI-style server for A2A agents.

This module provides a unified server class that handles:
- A2A JSON-RPC protocol (message/send, message/stream, respond)
- SSE streaming for real-time progress
- Plan mode context integration
- Translation context integration
- Agent card serving (.well-known/agent.json)

Example:
    from pixell.sdk import AgentServer, MessageContext

    server = AgentServer(
        agent_id="my-agent",
        port=9998,
    )

    @server.on_message
    async def handle_message(ctx: MessageContext):
        await ctx.emit_status("working", "Processing...")
        # ... agent logic
        await ctx.emit_result("Done!")

    server.run()
"""

import logging
import asyncio
import inspect
from typing import Any, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from pathlib import Path

from pixell.sdk.a2a.protocol import (
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCError,
)
from pixell.sdk.a2a.streaming import SSEStream
from pixell.sdk.a2a.handlers import (
    A2AHandler,
    MessageHandler,
    ResponseHandler,
)

if TYPE_CHECKING:
    from pixell.sdk.plan_mode import PlanModeContext
    from pixell.sdk.translation import Translator

logger = logging.getLogger(__name__)


@dataclass
class AgentCard:
    """Agent card for .well-known/agent.json."""

    name: str
    description: str = ""
    version: str = "1.0.0"
    url: str = ""
    capabilities: list[str] = field(default_factory=list)
    skills: list[dict[str, Any]] = field(default_factory=list)
    plan_mode: Optional[dict[str, Any]] = None
    translation: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "url": self.url,
            "capabilities": {
                "streaming": True,
                "pushNotifications": False,
                "stateTransitionHistory": False,
            },
            "skills": self.skills,
        }
        if self.plan_mode:
            result["planMode"] = self.plan_mode
        if self.translation:
            result["translation"] = self.translation
        return result


class AgentServer:
    """Unified server for A2A agents.

    Handles HTTP requests using FastAPI and provides a decorator-based API
    for registering message and respond handlers.

    Args:
        agent_id: Unique identifier for this agent
        name: Human-readable name for the agent
        description: Agent description
        port: Port to run the server on
        host: Host to bind to
        translator: Optional Translator implementation for i18n
        plan_mode_config: Optional plan mode configuration

    Example:
        server = AgentServer(
            agent_id="tik-agent",
            name="TikTok Research Agent",
            port=9998,
        )

        @server.on_message
        async def handle_message(ctx: MessageContext):
            plan = ctx.plan_mode
            await ctx.emit_status("working", "Analyzing...")
            await plan.request_clarification([...])

        server.run()
    """

    def __init__(
        self,
        agent_id: str,
        name: Optional[str] = None,
        description: str = "",
        port: int = 8000,
        host: str = "0.0.0.0",
        translator: Optional["Translator"] = None,
        plan_mode_config: Optional[dict[str, Any]] = None,
        outputs_dir: Optional[str] = None,
    ) -> None:
        self.agent_id = agent_id
        self.name = name or agent_id
        self.description = description
        self.port = port
        self.host = host
        self.translator = translator
        self.plan_mode_config = plan_mode_config or {}

        self._handler = A2AHandler()
        self._app: Any = None  # FastAPI app instance
        self._sessions: dict[str, "PlanModeContext"] = {}

        # Resolve outputs_dir to absolute path relative to caller's file
        self._outputs_dir: Optional[Path] = None
        self._outputs_dir_name: Optional[str] = None
        if outputs_dir:
            self._outputs_dir_name = outputs_dir
            # Find the caller's file to resolve relative path
            caller_frame = inspect.stack()[1]
            caller_file = Path(caller_frame.filename)
            self._outputs_dir = (caller_file.parent / outputs_dir).resolve()
            logger.info(f"Outputs directory configured: {self._outputs_dir}")

    @property
    def card(self) -> AgentCard:
        """Get the agent card."""
        plan_mode = None
        if self.plan_mode_config:
            plan_mode = {
                "supported": True,
                **self.plan_mode_config,
            }

        translation = None
        if self.translator:
            translation = {
                "supported": True,
            }

        return AgentCard(
            name=self.name,
            description=self.description,
            url=f"http://{self.host}:{self.port}",
            plan_mode=plan_mode,
            translation=translation,
        )

    def on_message(self, func: MessageHandler) -> MessageHandler:
        """Decorator to register message handler.

        Args:
            func: Async function that takes MessageContext

        Returns:
            The registered function

        Example:
            @server.on_message
            async def handle_message(ctx: MessageContext):
                await ctx.emit_status("working", "Processing...")
        """
        return self._handler.on_message(func)

    def on_respond(self, func: ResponseHandler) -> ResponseHandler:
        """Decorator to register respond handler.

        Args:
            func: Async function that takes ResponseContext

        Returns:
            The registered function

        Example:
            @server.on_respond
            async def handle_respond(ctx: ResponseContext):
                if ctx.response_type == "clarification":
                    # Handle clarification response
                    pass
        """
        return self._handler.on_respond(func)

    def _create_app(self) -> Any:
        """Create the FastAPI application."""
        try:
            from fastapi import FastAPI, Request
            from fastapi.responses import StreamingResponse, JSONResponse
            from fastapi.middleware.cors import CORSMiddleware
        except ImportError:
            raise ImportError(
                "FastAPI is required for AgentServer. Install it with: pip install fastapi uvicorn"
            )

        app = FastAPI(
            title=self.name,
            description=self.description,
        )

        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @app.get("/.well-known/agent.json")
        async def get_agent_card() -> dict[str, Any]:
            """Serve the agent card."""
            return self.card.to_dict()

        @app.get("/health")
        async def health_check() -> dict[str, Any]:
            """Health check endpoint."""
            return {"status": "healthy", "agent_id": self.agent_id}

        # Auto-create file download endpoint if outputs_dir is configured
        if self._outputs_dir:
            from starlette.responses import FileResponse

            @app.get("/files/download")
            async def download_file(path: str = "") -> Any:
                """Download files from agent's outputs directory.

                This endpoint is auto-created by pixell-sdk when outputs_dir is configured.
                The orchestrator calls this to fetch agent-generated files for S3 upload.
                """
                if not path:
                    return JSONResponse({"error": "Missing path parameter"}, status_code=400)

                # Strip outputs_dir prefix if present (path might be "exports/file.html" or just "file.html")
                if self._outputs_dir_name and path.startswith(f"{self._outputs_dir_name}/"):
                    path = path[len(self._outputs_dir_name) + 1 :]

                full_path = self._outputs_dir / path

                # Security: prevent directory traversal attacks
                try:
                    if not full_path.resolve().is_relative_to(self._outputs_dir.resolve()):
                        logger.warning(f"Path traversal attempt blocked: {path}")
                        return JSONResponse({"error": "Invalid path"}, status_code=400)
                except ValueError:
                    return JSONResponse({"error": "Invalid path"}, status_code=400)

                if not full_path.exists():
                    logger.warning(f"File not found: {full_path}")
                    return JSONResponse({"error": "File not found"}, status_code=404)

                # Determine media type based on extension
                media_type = "application/octet-stream"
                suffix = full_path.suffix.lower()
                if suffix == ".html":
                    media_type = "text/html"
                elif suffix == ".json":
                    media_type = "application/json"
                elif suffix == ".csv":
                    media_type = "text/csv"
                elif suffix == ".txt":
                    media_type = "text/plain"
                elif suffix == ".pdf":
                    media_type = "application/pdf"

                logger.info(f"Serving file: {full_path}")
                return FileResponse(full_path, media_type=media_type, filename=full_path.name)

        @app.post("/", response_model=None)
        async def handle_jsonrpc(request: Request) -> StreamingResponse | JSONResponse:
            """Handle JSON-RPC requests."""
            try:
                body = await request.json()
                rpc_request = JSONRPCRequest.from_dict(body)

                # Extract correlation IDs from request params
                params = body.get("params", {})
                workflow_id = params.get("workflowId")
                session_id = params.get("sessionId")

                # Create SSE stream with correlation IDs
                # These will be auto-injected into every event
                stream = SSEStream(
                    workflow_id=workflow_id,
                    session_id=session_id,
                )

                # Create plan mode context if configured
                plan_mode = None
                if self.plan_mode_config:
                    from pixell.sdk.plan_mode import PlanModeContext

                    session_id = body.get("params", {}).get("sessionId")
                    if session_id and session_id in self._sessions:
                        plan_mode = self._sessions[session_id]
                    else:
                        plan_mode = PlanModeContext(
                            stream=stream,
                            supported_phases=self.plan_mode_config.get("phases", []),
                        )

                # Create translation context if translator provided
                translation = None
                if self.translator:
                    from pixell.sdk.translation import TranslationContext

                    metadata = body.get("params", {}).get("metadata", {})
                    translation = TranslationContext(
                        translator=self.translator,
                        user_language=metadata.get("language", "en"),
                    )

                # Check if streaming is requested
                method = rpc_request.method
                if method == "message/stream":
                    # Store session immediately for streaming requests
                    session_id = body.get("params", {}).get("sessionId")
                    logger.info(
                        f"[message/stream] Attempting to store session: {session_id}, plan_mode exists: {plan_mode is not None}"
                    )
                    if session_id and plan_mode:
                        self._sessions[session_id] = plan_mode
                        logger.info(
                            f"[message/stream] Session stored! Total sessions: {len(self._sessions)}, Keys: {list(self._sessions.keys())}"
                        )

                    # Return SSE stream
                    async def handle_and_stream():
                        # Yield 2KB padding first to flush proxy buffers
                        from pixell.sdk.a2a.streaming import buffer_flush_padding

                        yield buffer_flush_padding()

                        # Start handler in background
                        asyncio.create_task(
                            self._handler.handle_request(
                                rpc_request, stream, plan_mode, translation
                            )
                        )
                        # Stream events
                        async for event in stream.events():
                            yield event.encode()
                            # Break on terminal states or when input is required
                            state = event.data.get("state")
                            if state in ("completed", "failed", "input-required"):
                                break
                        stream.close()

                    return StreamingResponse(
                        handle_and_stream(),
                        media_type="text/event-stream",
                        headers={
                            "Cache-Control": "no-cache",
                            "Connection": "keep-alive",
                            "X-Accel-Buffering": "no",
                        },
                    )
                else:
                    # Non-streaming - handle and return response
                    response = await self._handler.handle_request(
                        rpc_request, stream, plan_mode, translation
                    )

                    # Store session if plan mode is active
                    if plan_mode and response.result:
                        session_id = response.result.get("sessionId")
                        if session_id:
                            self._sessions[session_id] = plan_mode

                    return JSONResponse(response.to_dict())

            except Exception as e:
                logger.exception("Error handling request")
                error_response = JSONRPCResponse.failure(
                    body.get("id", "unknown"),
                    JSONRPCError(
                        code=JSONRPCError.INTERNAL_ERROR,
                        message=str(e),
                    ),
                )
                return JSONResponse(
                    error_response.to_dict(),
                    status_code=500,
                )

        @app.post("/respond", response_model=None)
        async def handle_respond(request: Request) -> StreamingResponse:
            """Handle respond requests (alternative endpoint)."""
            try:
                body = await request.json()

                # Wrap in JSON-RPC format
                rpc_request = JSONRPCRequest(
                    method="respond",
                    params=body,
                )

                # Extract correlation IDs
                workflow_id = body.get("workflowId")
                session_id = body.get("sessionId")

                # Create SSE stream with correlation IDs
                stream = SSEStream(
                    workflow_id=workflow_id,
                    session_id=session_id,
                )

                # Get existing plan mode context from session
                plan_mode = None
                session_id = body.get("sessionId")

                # Debug logging for session lookup
                logger.info(f"[/respond] Looking up session: {session_id}")
                logger.info(f"[/respond] Available sessions: {list(self._sessions.keys())}")

                if session_id and session_id in self._sessions:
                    plan_mode = self._sessions[session_id]
                    plan_mode.stream = stream
                    logger.info(
                        f"[/respond] Found session! Phase: {plan_mode.phase if hasattr(plan_mode, 'phase') else 'unknown'}"
                    )
                    logger.info(
                        f"[/respond] Pending IDs - clarification: {getattr(plan_mode, '_pending_clarification_id', None)}, selection: {getattr(plan_mode, '_pending_selection_id', None)}"
                    )
                else:
                    logger.warning(f"[/respond] Session NOT FOUND: {session_id}")

                translation = None
                if self.translator:
                    from pixell.sdk.translation import TranslationContext

                    translation = TranslationContext(
                        translator=self.translator,
                        user_language=body.get("language", "en"),
                    )

                async def handle_and_stream():
                    # Yield 2KB padding first to flush proxy buffers
                    from pixell.sdk.a2a.streaming import buffer_flush_padding

                    yield buffer_flush_padding()

                    asyncio.create_task(
                        self._handler.handle_request(rpc_request, stream, plan_mode, translation)
                    )
                    async for event in stream.events():
                        yield event.encode()
                        # Break on terminal states or when input is required
                        state = event.data.get("state")
                        if state in ("completed", "failed", "input-required"):
                            break
                    stream.close()

                return StreamingResponse(
                    handle_and_stream(),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Accel-Buffering": "no",
                    },
                )

            except Exception:
                logger.exception("Error handling respond")
                raise

        return app

    def run(self, **kwargs: Any) -> None:
        """Run the server.

        Args:
            **kwargs: Additional arguments passed to uvicorn.run()
        """
        try:
            import uvicorn
        except ImportError:
            raise ImportError(
                "Uvicorn is required for AgentServer. Install it with: pip install uvicorn"
            )

        if self._app is None:
            self._app = self._create_app()

        logger.info(f"Starting {self.name} on {self.host}:{self.port}")
        uvicorn.run(
            self._app,
            host=self.host,
            port=self.port,
            **kwargs,
        )

    async def run_async(self, **kwargs: Any) -> None:
        """Run the server asynchronously.

        Args:
            **kwargs: Additional arguments passed to uvicorn
        """
        try:
            import uvicorn
        except ImportError:
            raise ImportError(
                "Uvicorn is required for AgentServer. Install it with: pip install uvicorn"
            )

        if self._app is None:
            self._app = self._create_app()

        config = uvicorn.Config(
            self._app,
            host=self.host,
            port=self.port,
            **kwargs,
        )
        server = uvicorn.Server(config)
        await server.serve()

    @property
    def app(self) -> Any:
        """Get the FastAPI application instance.

        Useful for testing or adding additional routes.
        """
        if self._app is None:
            self._app = self._create_app()
        return self._app
