"""E2E tests for SSE buffer flush functionality.

These tests verify that the 2KB buffer flush padding is sent
correctly before real SSE events in both / and /respond endpoints.

Note: These tests require uvicorn and may have async timing issues in CI.
Consider running locally for comprehensive E2E testing.
"""

import asyncio
import os
import uuid

import httpx
import pytest

from tests.sdk.e2e.conftest import find_free_port
from pixell.sdk import AgentServer, MessageContext

# Skip E2E tests in CI environments
CI_SKIP = pytest.mark.skipif(
    os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true",
    reason="E2E tests with async servers are flaky in CI"
)


@CI_SKIP
class TestBufferFlushE2E:
    """E2E tests for buffer flush padding."""

    @pytest.fixture
    async def simple_server(self):
        """Create a simple server for buffer flush testing."""
        port = find_free_port()

        server = AgentServer(
            agent_id="buffer-test-agent",
            name="Buffer Test Agent",
            port=port,
            host="127.0.0.1",
            plan_mode_config={"phases": ["clarification"]},
        )

        @server.on_message
        async def handle_message(ctx: MessageContext):
            await ctx.emit_status("working", "Processing")
            await asyncio.sleep(0.05)
            await ctx.emit_status("completed", "Done")

        from uvicorn import Config, Server

        config = Config(
            app=server.app, host="127.0.0.1", port=port, log_level="warning"
        )
        server_instance = Server(config)
        server_task = asyncio.create_task(server_instance.serve())

        await asyncio.sleep(0.3)

        try:
            yield f"http://127.0.0.1:{port}"
        finally:
            server_instance.should_exit = True
            await asyncio.sleep(0.1)
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_buffer_flush_sent_first_on_root_endpoint(self, simple_server: str):
        """Test that 2KB padding is sent as first chunk on / endpoint."""
        base_url = simple_server

        request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/stream",
            "params": {
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "role": "user",
                    "parts": [{"text": "Test message"}],
                },
                "sessionId": str(uuid.uuid4()),
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                f"{base_url}/",
                json=request,
                headers={"Accept": "text/event-stream"},
            ) as response:
                assert response.status_code == 200

                chunks = []
                async for chunk in response.aiter_text():
                    chunks.append(chunk)
                    # Collect first few chunks
                    if len(chunks) >= 3:
                        break

                # First chunk should be the padding (starts with ":")
                first_chunk = chunks[0]
                assert first_chunk.startswith(
                    ":"
                ), f"First chunk should be SSE comment, got: {first_chunk[:100]}"
                assert (
                    len(first_chunk) >= 2048
                ), f"Padding should be >= 2KB, got {len(first_chunk)} bytes"

    @pytest.mark.asyncio
    async def test_buffer_flush_is_valid_sse_comment(self, simple_server: str):
        """Test that buffer flush is valid SSE format."""
        base_url = simple_server

        request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/stream",
            "params": {
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "role": "user",
                    "parts": [{"text": "Test"}],
                },
                "sessionId": str(uuid.uuid4()),
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                f"{base_url}/",
                json=request,
                headers={"Accept": "text/event-stream"},
            ) as response:
                first_chunk = ""
                async for chunk in response.aiter_text():
                    first_chunk = chunk
                    break

                # Should be a valid SSE comment line
                # Format: ": padding_chars\n\n"
                assert first_chunk.startswith(":")
                assert first_chunk.endswith("\n\n")

    @pytest.mark.asyncio
    async def test_real_events_flow_after_padding(self, simple_server: str):
        """Test that real events are received correctly after padding."""
        base_url = simple_server

        request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/stream",
            "params": {
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "role": "user",
                    "parts": [{"text": "Test"}],
                },
                "sessionId": str(uuid.uuid4()),
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                f"{base_url}/",
                json=request,
                headers={"Accept": "text/event-stream"},
            ) as response:
                full_response = ""
                async for chunk in response.aiter_text():
                    full_response += chunk

                # Should have padding at start
                assert full_response.startswith(":")

                # Should have real events after padding
                assert "event: status-update" in full_response
                # Check for completed state (may be formatted differently)
                assert '"state":' in full_response or '"state": ' in full_response

    @pytest.mark.asyncio
    async def test_padding_separates_from_events(self, simple_server: str):
        """Test that padding is a separate SSE message from real events."""
        base_url = simple_server

        request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/stream",
            "params": {
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "role": "user",
                    "parts": [{"text": "Test"}],
                },
                "sessionId": str(uuid.uuid4()),
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                f"{base_url}/",
                json=request,
                headers={"Accept": "text/event-stream"},
            ) as response:
                full_response = ""
                async for chunk in response.aiter_text():
                    full_response += chunk

                # Split by double newline (SSE message separator)
                messages = full_response.split("\n\n")

                # First message should be the padding comment
                first_message = messages[0].strip()
                assert first_message.startswith(
                    ":"
                ), f"First SSE message should be comment, got: {first_message[:50]}"

                # Should have at least one real event after padding
                real_events = [
                    m for m in messages[1:] if m.strip() and "event:" in m
                ]
                assert (
                    len(real_events) > 0
                ), "Should have at least one real event after padding"


@CI_SKIP
class TestBufferFlushRespondEndpoint:
    """Tests for buffer flush on /respond endpoint."""

    @pytest.fixture
    async def plan_mode_server(self):
        """Create a server with plan mode for respond testing."""
        port = find_free_port()

        server = AgentServer(
            agent_id="plan-mode-test",
            name="Plan Mode Test",
            port=port,
            host="127.0.0.1",
            plan_mode_config={"phases": ["clarification"]},
        )

        clarification_sent = asyncio.Event()

        @server.on_message
        async def handle_message(ctx: MessageContext):
            await ctx.plan_mode.request_clarification(
                [
                    {
                        "id": "test_question",
                        "type": "free_text",
                        "question": "What do you want?",
                    }
                ]
            )
            clarification_sent.set()

        @server.on_respond
        async def handle_respond(ctx):
            await ctx.emit_status("working", "Processing response")
            await asyncio.sleep(0.05)
            await ctx.emit_status("completed", "Done")

        from uvicorn import Config, Server

        config = Config(
            app=server.app, host="127.0.0.1", port=port, log_level="warning"
        )
        server_instance = Server(config)
        server_task = asyncio.create_task(server_instance.serve())

        await asyncio.sleep(0.3)

        try:
            yield f"http://127.0.0.1:{port}", clarification_sent
        finally:
            server_instance.should_exit = True
            await asyncio.sleep(0.1)
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_buffer_flush_on_respond_endpoint(self, plan_mode_server):
        """Test that /respond endpoint also sends buffer flush padding."""
        base_url, clarification_sent = plan_mode_server
        session_id = str(uuid.uuid4())

        # First, send initial message to create session and get clarification
        request = {
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
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get clarification
            async with client.stream(
                "POST",
                f"{base_url}/",
                json=request,
                headers={"Accept": "text/event-stream"},
            ) as response:
                full_response = ""
                async for chunk in response.aiter_text():
                    full_response += chunk
                    if "clarification_needed" in full_response:
                        break

            # Now send respond request
            respond_body = {
                "sessionId": session_id,
                "response_type": "clarification",
                "answers": {"test_question": "my answer"},
            }

            async with client.stream(
                "POST",
                f"{base_url}/respond",
                json=respond_body,
                headers={"Accept": "text/event-stream"},
            ) as response:
                chunks = []
                async for chunk in response.aiter_text():
                    chunks.append(chunk)
                    if len(chunks) >= 3:
                        break

                # First chunk should be buffer flush padding
                if chunks:
                    first_chunk = chunks[0]
                    assert first_chunk.startswith(
                        ":"
                    ), f"Respond endpoint should also send padding, got: {first_chunk[:100]}"
                    assert len(first_chunk) >= 2048
