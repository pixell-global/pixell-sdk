"""E2E tests for ToolBasedAgent lite mode workflow.

These tests verify that ToolBasedAgent correctly handles lite_mode_enabled
by auto-handling all interactive phases (Discovery, Clarification, Preview)
and completing the workflow without user interaction.
"""

import asyncio
import socket
import uuid
from contextlib import closing
from typing import AsyncGenerator

import httpx
import pytest

from pixell.sdk.tool_mode.agent import (
    ToolBasedAgent,
    Tool,
    ToolCall,
    tool,
)
from pixell.sdk.plan_mode.agent import (
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


class TestToolBasedAgentLiteModeHandlers:
    """Container for tracking lite mode test agent state."""

    def __init__(self):
        self.query_received = asyncio.Event()
        self.tool_executed = asyncio.Event()
        self.selection_received = asyncio.Event()
        self.execute_called = asyncio.Event()

        self.last_query: str = ""
        self.tool_name: str = ""
        self.selected_ids: list[str] = []
        self.execution_result: dict = {}

    def reset(self):
        self.query_received.clear()
        self.tool_executed.clear()
        self.selection_received.clear()
        self.execute_called.clear()
        self.last_query = ""
        self.tool_name = ""
        self.selected_ids = []
        self.execution_result = {}


class LiteModeToolBasedTestAgent(ToolBasedAgent):
    """Test ToolBasedAgent for lite mode E2E tests."""

    def __init__(self, port: int, handlers: TestToolBasedAgentLiteModeHandlers):
        super().__init__(
            agent_id="tool-based-lite-mode-test",
            name="Tool-Based Lite Mode Test Agent",
            description="Agent for testing ToolBasedAgent lite mode workflow",
            port=port,
            host="127.0.0.1",
        )
        self.handlers = handlers

    async def select_tools(self, query: str, tools: list[Tool]) -> list[ToolCall]:
        """Always select the deep_research tool for testing."""
        self.handlers.last_query = query
        self.handlers.query_received.set()

        return [ToolCall(name="deep_research", arguments={"query": query})]

    @tool(
        name="deep_research",
        description="Research with discovery flow",
        parameters={"query": {"type": "string", "description": "Search query"}},
    )
    async def deep_research(self, query: str) -> AgentResponse:
        """Simulate deep research - returns Discovery for selection."""
        self.handlers.tool_name = "deep_research"
        self.handlers.tool_executed.set()

        # Return discovery with items
        return Discovery(
            items=[
                {"id": "r/gaming", "name": "r/gaming", "description": "Gaming"},
                {"id": "r/pcgaming", "name": "r/pcgaming", "description": "PC Gaming"},
                {"id": "r/games", "name": "r/games", "description": "Quality gaming"},
            ],
            message="Found 3 subreddits",
            item_type="subreddits",
            min_select=1,
            max_select=5,
        )

    async def on_selection(self, selected: list[str]) -> AgentResponse:
        """Handle selection and return preview."""
        self.handlers.selected_ids = selected
        self.handlers.selection_received.set()

        return Preview(
            intent=f"Search {len(selected)} subreddits",
            plan={"targets": selected, "keywords": ["discussion"]},
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
def tool_based_handlers() -> TestToolBasedAgentLiteModeHandlers:
    """Create handlers for tracking test state."""
    return TestToolBasedAgentLiteModeHandlers()


@pytest.fixture
async def tool_based_server(
    tool_based_handlers: TestToolBasedAgentLiteModeHandlers,
) -> AsyncGenerator[tuple[LiteModeToolBasedTestAgent, str], None]:
    """Create a ToolBasedAgent server for lite mode testing."""
    port = find_free_port()
    agent = LiteModeToolBasedTestAgent(port=port, handlers=tool_based_handlers)

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


class TestToolBasedAgentLiteModeWorkflow:
    """Test that ToolBasedAgent lite mode skips interactive phases."""

    @pytest.mark.asyncio
    async def test_lite_mode_skips_all_interactive_phases(
        self,
        tool_based_server: tuple,
        tool_based_handlers: TestToolBasedAgentLiteModeHandlers,
    ):
        """With lite_mode=True, ToolBasedAgent should auto-handle all interactive phases.

        Expected flow:
        1. Send message with lite_mode_enabled=True
        2. select_tools returns deep_research tool call
        3. deep_research returns Discovery → SDK auto-selects and calls on_selection
        4. on_selection returns Preview → SDK auto-approves and calls on_execute
        5. on_execute returns Result → Workflow completes

        We should NOT receive:
        - discovery_result events (would require user selection)
        - selection_required events (would require user input)
        - preview_ready events (would require user approval)
        """
        agent, base_url = tool_based_server

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

        # Verify workflow completed
        assert "completed" in data_states, (
            f"Workflow should complete. Got states: {data_states}"
        )

        # Verify all phases were called internally
        assert tool_based_handlers.query_received.is_set()
        assert tool_based_handlers.tool_executed.is_set()
        assert tool_based_handlers.selection_received.is_set()
        assert tool_based_handlers.execute_called.is_set()

    @pytest.mark.asyncio
    async def test_normal_mode_emits_interactive_events(
        self,
        tool_based_server: tuple,
        tool_based_handlers: TestToolBasedAgentLiteModeHandlers,
    ):
        """Without lite_mode, ToolBasedAgent should emit interactive events."""
        agent, base_url = tool_based_server

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


class TestToolBasedAgentAutoSelection:
    """Test that lite mode auto-selects the correct items."""

    @pytest.mark.asyncio
    async def test_lite_mode_auto_selects_items(
        self,
        tool_based_server: tuple,
        tool_based_handlers: TestToolBasedAgentLiteModeHandlers,
    ):
        """Lite mode should auto-select items from discovery."""
        agent, base_url = tool_based_server

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
                _events = await collect_sse_until(
                    response,
                    lambda e: e.get("data", {}).get("state") == "completed",
                    max_events=50,
                )

        # Wait for handler to process
        await asyncio.wait_for(tool_based_handlers.execute_called.wait(), timeout=10.0)

        # The test agent emits 3 subreddits, so all 3 should be selected
        # (since 3 < max_select of 5)
        assert len(tool_based_handlers.selected_ids) == 3
        assert "r/gaming" in tool_based_handlers.selected_ids
        assert "r/pcgaming" in tool_based_handlers.selected_ids
        assert "r/games" in tool_based_handlers.selected_ids
