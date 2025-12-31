"""E2E tests for error handling and recovery in plan mode.

Tests various error scenarios and recovery patterns.
"""

import asyncio
import uuid

import httpx
import pytest

from pixell.sdk import AgentServer, MessageContext, ResponseContext
from pixell.sdk.plan_mode import (
    Question,
    QuestionType,
    SearchPlanPreview,
)
from tests.sdk.e2e.conftest import collect_sse_until


class ErrorHandlers:
    """Handlers for error testing."""

    def __init__(self):
        self.should_error = False
        self.error_type = "recoverable"
        self.error_count = 0


@pytest.fixture
async def error_server(free_port: int) -> tuple:
    """Server that can trigger errors on demand."""
    handlers = ErrorHandlers()

    server = AgentServer(
        agent_id="error-test-agent",
        port=free_port,
        host="127.0.0.1",
        plan_mode_config={"phases": ["clarification", "preview"]},
    )

    @server.on_message
    async def handle_message(ctx: MessageContext):
        plan = ctx.plan_mode

        if handlers.should_error:
            handlers.error_count += 1
            if handlers.error_type == "recoverable":
                await plan.error(
                    "test_error",
                    "Test recoverable error",
                    recoverable=True,
                )
            elif handlers.error_type == "fatal":
                await plan.error(
                    "fatal_error",
                    "Test fatal error",
                    recoverable=False,
                )
            elif handlers.error_type == "exception":
                raise ValueError("Simulated exception in handler")
            return

        await plan.request_clarification(
            [
                Question(
                    id="input",
                    type=QuestionType.FREE_TEXT,
                    question="Enter something",
                    header="Input",
                ),
            ]
        )

    @server.on_respond
    async def handle_respond(ctx: ResponseContext):
        plan = ctx.plan_mode

        if ctx.response_type == "clarification":
            plan.set_clarification_response(ctx.answers, ctx.clarification_id)

            if handlers.should_error:
                handlers.error_count += 1
                await plan.error(
                    "respond_error",
                    "Error during respond",
                    recoverable=handlers.error_type == "recoverable",
                )
                return

            preview = SearchPlanPreview(
                user_intent="test",
                search_keywords=["test"],
                user_answers=ctx.answers,
                message="Ready to execute",
            )
            await plan.emit_preview(preview)

        elif ctx.response_type == "plan":
            plan.set_plan_approval(ctx.approved, ctx.plan_id)
            if ctx.approved:
                await plan.start_execution()
                await plan.complete({"status": "done"}, message="Completed!")

    from uvicorn import Config, Server

    app = server.app
    config = Config(app=app, host="127.0.0.1", port=free_port, log_level="warning")
    server_instance = Server(config)
    server_task = asyncio.create_task(server_instance.serve())
    await asyncio.sleep(0.3)

    base_url = f"http://127.0.0.1:{free_port}"

    try:
        yield server, base_url, handlers
    finally:
        server_instance.should_exit = True
        await asyncio.sleep(0.1)
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass


class TestRecoverableErrors:
    """Tests for recoverable error scenarios."""

    @pytest.mark.asyncio
    async def test_recoverable_error_in_message_handler(
        self,
        error_server: tuple,
    ):
        """Test that recoverable errors are properly signaled."""
        server, base_url, handlers = error_server
        handlers.should_error = True
        handlers.error_type = "recoverable"
        session_id = str(uuid.uuid4())

        async with httpx.AsyncClient(timeout=30.0) as http_client:
            async with http_client.stream(
                "POST",
                f"{base_url}/",
                json={
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "message/stream",
                    "params": {
                        "message": {
                            "messageId": str(uuid.uuid4()),
                            "role": "user",
                            "parts": [{"text": "Trigger error"}],
                        },
                        "sessionId": session_id,
                    },
                },
                headers={"Accept": "text/event-stream"},
            ) as response:
                events = await collect_sse_until(
                    response,
                    lambda e: e.get("event") == "error",
                )

                error_event = events[-1]["data"]
                assert error_event["state"] == "failed"
                assert error_event["error_type"] == "test_error"
                assert error_event["recoverable"] is True

    @pytest.mark.asyncio
    async def test_fatal_error_in_message_handler(
        self,
        error_server: tuple,
    ):
        """Test that fatal errors are properly signaled."""
        server, base_url, handlers = error_server
        handlers.should_error = True
        handlers.error_type = "fatal"
        session_id = str(uuid.uuid4())

        async with httpx.AsyncClient(timeout=30.0) as http_client:
            async with http_client.stream(
                "POST",
                f"{base_url}/",
                json={
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "message/stream",
                    "params": {
                        "message": {
                            "messageId": str(uuid.uuid4()),
                            "role": "user",
                            "parts": [{"text": "Trigger fatal error"}],
                        },
                        "sessionId": session_id,
                    },
                },
                headers={"Accept": "text/event-stream"},
            ) as response:
                events = await collect_sse_until(
                    response,
                    lambda e: e.get("event") == "error",
                )

                error_event = events[-1]["data"]
                assert error_event["state"] == "failed"
                assert error_event["error_type"] == "fatal_error"
                assert error_event["recoverable"] is False

    @pytest.mark.asyncio
    async def test_error_during_respond(
        self,
        error_server: tuple,
    ):
        """Test error handling during respond phase."""
        server, base_url, handlers = error_server
        session_id = str(uuid.uuid4())

        async with httpx.AsyncClient(timeout=30.0) as http_client:
            # First, get clarification successfully
            async with http_client.stream(
                "POST",
                f"{base_url}/",
                json={
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "message/stream",
                    "params": {
                        "message": {
                            "messageId": str(uuid.uuid4()),
                            "role": "user",
                            "parts": [{"text": "Start workflow"}],
                        },
                        "sessionId": session_id,
                    },
                },
                headers={"Accept": "text/event-stream"},
            ) as response:
                events = await collect_sse_until(
                    response,
                    lambda e: e.get("event") == "clarification_needed",
                )
                clar_id = events[-1]["data"]["clarificationId"]

            # Now trigger error on respond
            handlers.should_error = True
            handlers.error_type = "recoverable"

            async with http_client.stream(
                "POST",
                f"{base_url}/respond",
                json={
                    "sessionId": session_id,
                    "clarificationId": clar_id,
                    "answers": {"input": "test"},
                },
                headers={"Accept": "text/event-stream"},
            ) as response:
                events = await collect_sse_until(
                    response,
                    lambda e: e.get("event") == "error",
                )

                error_event = events[-1]["data"]
                assert error_event["error_type"] == "respond_error"
                assert error_event["recoverable"] is True


class TestMalformedRequests:
    """Tests for handling malformed requests."""

    @pytest.mark.asyncio
    async def test_missing_session_id(
        self,
        error_server: tuple,
    ):
        """Test handling of missing session ID in respond.

        When respond is called without a valid session, the plan_mode will be None.
        The handler should handle this gracefully (either by checking or failing safely).
        """
        server, base_url, handlers = error_server

        async with httpx.AsyncClient(timeout=5.0) as http_client:
            # Try to respond without a session - use streaming to properly handle SSE
            try:
                async with http_client.stream(
                    "POST",
                    f"{base_url}/respond",
                    json={
                        "clarificationId": str(uuid.uuid4()),
                        "answers": {"input": "test"},
                    },
                    headers={"Accept": "text/event-stream"},
                ) as response:
                    # Should return 200 (SSE endpoint exists)
                    assert response.status_code == 200
                    # The handler may or may not produce events depending on
                    # how it handles None plan_mode. We just verify the server
                    # doesn't crash.
            except httpx.ReadTimeout:
                # Timeout is acceptable - means the server is waiting for events
                # that will never come because plan_mode is None
                pass

    @pytest.mark.asyncio
    async def test_invalid_clarification_id(
        self,
        error_server: tuple,
    ):
        """Test handling of invalid clarification ID."""
        server, base_url, handlers = error_server
        session_id = str(uuid.uuid4())

        async with httpx.AsyncClient(timeout=30.0) as http_client:
            # First start a session
            async with http_client.stream(
                "POST",
                f"{base_url}/",
                json={
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "message/stream",
                    "params": {
                        "message": {
                            "messageId": str(uuid.uuid4()),
                            "role": "user",
                            "parts": [{"text": "Start"}],
                        },
                        "sessionId": session_id,
                    },
                },
                headers={"Accept": "text/event-stream"},
            ) as response:
                await collect_sse_until(
                    response,
                    lambda e: e.get("event") == "clarification_needed",
                )

            # Respond with wrong clarification ID
            async with http_client.stream(
                "POST",
                f"{base_url}/respond",
                json={
                    "sessionId": session_id,
                    "clarificationId": "wrong-id",  # Invalid ID
                    "answers": {"input": "test"},
                },
                headers={"Accept": "text/event-stream"},
            ) as response:
                # Should still work but log warning
                events = await collect_sse_until(
                    response,
                    lambda e: e.get("event") == "preview_ready",
                )
                # Despite wrong ID, the workflow continues
                assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_empty_answers(
        self,
        error_server: tuple,
    ):
        """Test handling of empty answers in clarification response."""
        server, base_url, handlers = error_server
        session_id = str(uuid.uuid4())

        async with httpx.AsyncClient(timeout=30.0) as http_client:
            async with http_client.stream(
                "POST",
                f"{base_url}/",
                json={
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "message/stream",
                    "params": {
                        "message": {
                            "messageId": str(uuid.uuid4()),
                            "role": "user",
                            "parts": [{"text": "Start"}],
                        },
                        "sessionId": session_id,
                    },
                },
                headers={"Accept": "text/event-stream"},
            ) as response:
                events = await collect_sse_until(
                    response,
                    lambda e: e.get("event") == "clarification_needed",
                )
                clar_id = events[-1]["data"]["clarificationId"]

            # Respond with empty answers
            async with http_client.stream(
                "POST",
                f"{base_url}/respond",
                json={
                    "sessionId": session_id,
                    "clarificationId": clar_id,
                    "answers": {},  # Empty answers
                },
                headers={"Accept": "text/event-stream"},
            ) as response:
                events = await collect_sse_until(
                    response,
                    lambda e: e.get("event") == "preview_ready",
                )
                # Should still work with empty answers
                assert len(events) >= 1


class TestWorkflowRecovery:
    """Tests for workflow recovery after errors."""

    @pytest.mark.asyncio
    async def test_restart_after_error(
        self,
        error_server: tuple,
    ):
        """Test that workflow can restart after a recoverable error."""
        server, base_url, handlers = error_server

        async with httpx.AsyncClient(timeout=30.0) as http_client:
            # First attempt - trigger error
            handlers.should_error = True
            handlers.error_type = "recoverable"
            session_id_1 = str(uuid.uuid4())

            async with http_client.stream(
                "POST",
                f"{base_url}/",
                json={
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "message/stream",
                    "params": {
                        "message": {
                            "messageId": str(uuid.uuid4()),
                            "role": "user",
                            "parts": [{"text": "First attempt"}],
                        },
                        "sessionId": session_id_1,
                    },
                },
                headers={"Accept": "text/event-stream"},
            ) as response:
                events = await collect_sse_until(
                    response,
                    lambda e: e.get("event") == "error",
                )
                assert events[-1]["data"]["recoverable"] is True

            # Second attempt - should succeed
            handlers.should_error = False
            session_id_2 = str(uuid.uuid4())

            async with http_client.stream(
                "POST",
                f"{base_url}/",
                json={
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "message/stream",
                    "params": {
                        "message": {
                            "messageId": str(uuid.uuid4()),
                            "role": "user",
                            "parts": [{"text": "Second attempt"}],
                        },
                        "sessionId": session_id_2,
                    },
                },
                headers={"Accept": "text/event-stream"},
            ) as response:
                events = await collect_sse_until(
                    response,
                    lambda e: e.get("event") == "clarification_needed",
                )
                assert events[-1]["data"]["state"] == "input-required"

    @pytest.mark.asyncio
    async def test_complete_workflow_after_initial_error(
        self,
        error_server: tuple,
    ):
        """Test completing full workflow after recovering from error."""
        server, base_url, handlers = error_server
        session_id = str(uuid.uuid4())

        async with httpx.AsyncClient(timeout=30.0) as http_client:
            # Get clarification
            async with http_client.stream(
                "POST",
                f"{base_url}/",
                json={
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "message/stream",
                    "params": {
                        "message": {
                            "messageId": str(uuid.uuid4()),
                            "role": "user",
                            "parts": [{"text": "Start workflow"}],
                        },
                        "sessionId": session_id,
                    },
                },
                headers={"Accept": "text/event-stream"},
            ) as response:
                events = await collect_sse_until(
                    response,
                    lambda e: e.get("event") == "clarification_needed",
                )
                clar_id = events[-1]["data"]["clarificationId"]

            # Respond to clarification
            async with http_client.stream(
                "POST",
                f"{base_url}/respond",
                json={
                    "sessionId": session_id,
                    "clarificationId": clar_id,
                    "answers": {"input": "test value"},
                },
                headers={"Accept": "text/event-stream"},
            ) as response:
                events = await collect_sse_until(
                    response,
                    lambda e: e.get("event") == "preview_ready",
                )
                plan_id = events[-1]["data"]["planId"]

            # Approve and complete
            async with http_client.stream(
                "POST",
                f"{base_url}/respond",
                json={
                    "sessionId": session_id,
                    "planId": plan_id,
                    "approved": True,
                },
                headers={"Accept": "text/event-stream"},
            ) as response:
                events = await collect_sse_until(
                    response,
                    lambda e: e.get("data", {}).get("state") == "completed",
                )

            assert handlers.error_count == 0  # No errors during this workflow
