"""E2E tests for lite mode workflow.

These tests verify that lite mode correctly skips interactive phases
(clarification, selection, preview) and auto-completes the workflow.
"""

import asyncio
import socket
import uuid
from contextlib import closing
from typing import AsyncGenerator, Union

import httpx
import pytest

from pixell.sdk.plan_mode.agent import (
    PlanModeAgent,
    Discovery,
    Preview,
    Result,
    AgentResponse,
)
from tests.sdk.e2e.conftest import collect_sse_until


def find_free_port() -> int:
    """Find a free port on localhost."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


class TestLiteModeWorkflowHandlers:
    """Container for tracking lite mode test agent state."""

    def __init__(self):
        self.query_received = asyncio.Event()
        self.selection_received = asyncio.Event()
        self.execute_called = asyncio.Event()
        self.completed = asyncio.Event()

        self.last_query: str = ""
        self.selected_ids: list[str] = []
        self.execution_result: dict = {}

    def reset(self):
        self.query_received.clear()
        self.selection_received.clear()
        self.execute_called.clear()
        self.completed.clear()
        self.last_query = ""
        self.selected_ids = []
        self.execution_result = {}


class LiteModeTestAgent(PlanModeAgent):
    """Test agent for lite mode E2E tests."""

    def __init__(self, port: int, handlers: TestLiteModeWorkflowHandlers):
        super().__init__(
            agent_id="lite-mode-test-agent",
            name="Lite Mode Test Agent",
            description="Agent for testing lite mode workflow",
            port=port,
            host="127.0.0.1",
            discovery_type="subreddits",
        )
        self.handlers = handlers

    async def on_query(self, query: str) -> AgentResponse:
        """Return discovery items for selection."""
        self.handlers.last_query = query
        self.handlers.query_received.set()

        # Return discovery with 3 items
        return Discovery(
            items=[
                {"id": "r/gaming", "name": "r/gaming", "description": "Gaming community"},
                {"id": "r/pcgaming", "name": "r/pcgaming", "description": "PC Gaming"},
                {"id": "r/games", "name": "r/games", "description": "Quality gaming"},
            ],
            message="Found 3 subreddits",
            item_type="subreddits",
            min_select=1,
            max_select=5,
        )

    async def on_selection(self, selected: list[str]) -> Union[Preview, Result]:
        """Handle selection and return preview."""
        self.handlers.selected_ids = selected
        self.handlers.selection_received.set()

        return Preview(
            intent=f"Search {len(selected)} subreddits",
            plan={
                "targets": selected,
                "keywords": ["discussion", "news"],
            },
            message="Ready to search",
        )

    async def on_execute(self) -> Result:
        """Execute and return result."""
        self.handlers.execute_called.set()

        result_data = {
            "subreddits_analyzed": len(self.handlers.selected_ids),
            "posts_found": 150,
            "report_url": "https://example.com/report",
        }
        self.handlers.execution_result = result_data

        return Result(
            answer="Research completed successfully",
            data=result_data,
        )


@pytest.fixture
def lite_mode_handlers() -> TestLiteModeWorkflowHandlers:
    """Create handlers for tracking test state."""
    return TestLiteModeWorkflowHandlers()


@pytest.fixture
async def lite_mode_server(
    lite_mode_handlers: TestLiteModeWorkflowHandlers,
) -> AsyncGenerator[tuple[LiteModeTestAgent, str], None]:
    """Create a PlanModeAgent server for lite mode testing."""
    port = find_free_port()
    agent = LiteModeTestAgent(port=port, handlers=lite_mode_handlers)

    base_url = f"http://127.0.0.1:{port}"

    # Run server in background
    from uvicorn import Config, Server

    config = Config(app=agent.app, host="127.0.0.1", port=port, log_level="warning")
    server_instance = Server(config)
    server_task = asyncio.create_task(server_instance.serve())

    # Wait for server to start
    await asyncio.sleep(0.3)

    try:
        yield agent, base_url
    finally:
        server_instance.should_exit = True
        await asyncio.sleep(0.1)
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass


class TestLiteModeWorkflow:
    """Test that lite mode skips interactive phases."""

    @pytest.mark.asyncio
    async def test_lite_mode_skips_all_interactive_phases(
        self,
        lite_mode_server: tuple,
        lite_mode_handlers: TestLiteModeWorkflowHandlers,
    ):
        """With lite_mode=True, all interactive phases should be auto-handled.

        Expected flow:
        1. Send message with lite_mode_enabled=True
        2. Agent returns discovery → SDK auto-selects and calls on_selection
        3. Agent returns preview → SDK auto-approves and calls on_execute
        4. Agent returns result → Workflow completes

        We should receive ONLY:
        - status-update events (working)
        - completed event

        We should NOT receive:
        - discovery_result events (would require user selection)
        - selection_required events (would require user input)
        - preview_ready events (would require user approval)
        """
        agent, base_url = lite_mode_server

        request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/stream",
            "params": {
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "role": "user",
                    "parts": [{"text": "Find gaming content"}],
                },
                "sessionId": str(uuid.uuid4()),
                "metadata": {"lite_mode_enabled": True},  # LITE MODE
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

                events = await collect_sse_until(
                    response,
                    lambda e: e.get("data", {}).get("state") == "completed",
                    max_events=50,
                )

        # Collect event types
        event_types = [e.get("event") for e in events if e.get("event")]
        data_states = [e.get("data", {}).get("state") for e in events]

        # Verify NO interactive events were emitted
        assert "selection_required" not in event_types, (
            f"Lite mode should skip selection. Got events: {event_types}"
        )
        assert "preview_ready" not in event_types, (
            f"Lite mode should skip preview. Got events: {event_types}"
        )

        # Verify NO input-required states
        assert "input-required" not in data_states, (
            f"Lite mode should never require input. Got states: {data_states}"
        )

        # Verify workflow completed
        assert "completed" in data_states, (
            f"Workflow should complete. Got states: {data_states}"
        )

        # Verify all phases were called internally
        assert lite_mode_handlers.query_received.is_set()
        assert lite_mode_handlers.selection_received.is_set()
        assert lite_mode_handlers.execute_called.is_set()

    @pytest.mark.asyncio
    async def test_normal_mode_emits_interactive_events(
        self,
        lite_mode_server: tuple,
        lite_mode_handlers: TestLiteModeWorkflowHandlers,
    ):
        """Without lite_mode, interactive phases should emit events."""
        agent, base_url = lite_mode_server

        request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/stream",
            "params": {
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "role": "user",
                    "parts": [{"text": "Find gaming content"}],
                },
                "sessionId": str(uuid.uuid4()),
                # NO lite_mode_enabled - should trigger interactive phases
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

                # Collect events until we get selection_required (interactive phase)
                events = await collect_sse_until(
                    response,
                    lambda e: e.get("event") == "selection_required",
                    max_events=20,
                )

        # Verify we got the interactive event
        event_types = [e.get("event") for e in events if e.get("event")]
        assert "selection_required" in event_types, (
            f"Normal mode should emit selection_required. Got: {event_types}"
        )


class TestLiteModeAutoSelection:
    """Test that lite mode auto-selects the correct number of items."""

    @pytest.mark.asyncio
    async def test_lite_mode_auto_selects_all_items(
        self,
        lite_mode_server: tuple,
        lite_mode_handlers: TestLiteModeWorkflowHandlers,
    ):
        """Lite mode should auto-select items (up to max_select=5)."""
        agent, base_url = lite_mode_server

        request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/stream",
            "params": {
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "role": "user",
                    "parts": [{"text": "Test auto-selection"}],
                },
                "sessionId": str(uuid.uuid4()),
                "metadata": {"lite_mode_enabled": True},
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                f"{base_url}/",
                json=request,
                headers={"Accept": "text/event-stream"},
            ) as response:
                events = await collect_sse_until(
                    response,
                    lambda e: e.get("data", {}).get("state") == "completed",
                    max_events=50,
                )

        # Wait for handler to process
        await asyncio.wait_for(lite_mode_handlers.execute_called.wait(), timeout=10.0)

        # The test agent emits 3 subreddits, so all 3 should be selected
        # (since 3 < max_select of 5)
        assert len(lite_mode_handlers.selected_ids) == 3
        assert "r/gaming" in lite_mode_handlers.selected_ids
        assert "r/pcgaming" in lite_mode_handlers.selected_ids
        assert "r/games" in lite_mode_handlers.selected_ids
