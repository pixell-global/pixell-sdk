"""E2E test fixtures for plan mode server testing.

This module provides fixtures for spinning up real AgentServer instances
and testing with actual HTTP requests.
"""

import asyncio
import json
import socket
from contextlib import closing
from typing import AsyncGenerator, Callable, Any

import httpx
import pytest

from pixell.sdk import AgentServer, MessageContext, ResponseContext
from pixell.sdk.plan_mode import (
    Question,
    QuestionType,
    QuestionOption,
    DiscoveredItem,
    SearchPlanPreview,
)


def find_free_port() -> int:
    """Find a free port on localhost."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


@pytest.fixture
def free_port() -> int:
    """Get a free port for the test server."""
    return find_free_port()


@pytest.fixture
def base_url(free_port: int) -> str:
    """Get the base URL for the test server."""
    return f"http://127.0.0.1:{free_port}"


class TestAgentHandlers:
    """Container for test agent handlers.

    This class manages the state and handlers for a test agent.
    """

    def __init__(self):
        self.clarification_requested = asyncio.Event()
        self.discovery_emitted = asyncio.Event()
        self.selection_requested = asyncio.Event()
        self.preview_emitted = asyncio.Event()
        self.execution_started = asyncio.Event()
        self.completed = asyncio.Event()

        self.last_clarification_id: str | None = None
        self.last_selection_id: str | None = None
        self.last_plan_id: str | None = None
        self.user_answers: dict[str, Any] = {}
        self.selected_ids: list[str] = []
        self.approved: bool = False

    def reset(self):
        """Reset all state."""
        self.clarification_requested.clear()
        self.discovery_emitted.clear()
        self.selection_requested.clear()
        self.preview_emitted.clear()
        self.execution_started.clear()
        self.completed.clear()
        self.last_clarification_id = None
        self.last_selection_id = None
        self.last_plan_id = None
        self.user_answers = {}
        self.selected_ids = []
        self.approved = False


@pytest.fixture
def test_handlers() -> TestAgentHandlers:
    """Create test agent handlers."""
    return TestAgentHandlers()


@pytest.fixture
async def plan_mode_server(
    free_port: int,
    test_handlers: TestAgentHandlers,
) -> AsyncGenerator[tuple[AgentServer, str], None]:
    """Create and run a test AgentServer with plan mode enabled.

    Yields:
        Tuple of (server, base_url)
    """
    server = AgentServer(
        agent_id="e2e-test-agent",
        name="E2E Test Agent",
        description="Agent for E2E testing plan mode",
        port=free_port,
        host="127.0.0.1",
        plan_mode_config={
            "phases": ["clarification", "discovery", "selection", "preview"],
            "discovery_type": "subreddits",
        },
    )

    @server.on_message
    async def handle_message(ctx: MessageContext):
        """Handle incoming messages."""
        plan = ctx.plan_mode

        await ctx.emit_status("working", "Starting plan mode workflow...")

        # Request clarification
        test_handlers.last_clarification_id = await plan.request_clarification(
            [
                Question(
                    id="topic",
                    type=QuestionType.FREE_TEXT,
                    question="What topic are you researching?",
                    header="Topic",
                    placeholder="e.g., gaming, fitness",
                ),
                Question(
                    id="depth",
                    type=QuestionType.SINGLE_CHOICE,
                    question="How thorough should the search be?",
                    header="Depth",
                    options=[
                        QuestionOption(id="quick", label="Quick", description="Top 5 results"),
                        QuestionOption(id="deep", label="Deep", description="Top 20 results"),
                    ],
                ),
            ],
            message="I need some information to help you.",
        )

        test_handlers.clarification_requested.set()

    @server.on_respond
    async def handle_respond(ctx: ResponseContext):
        """Handle user responses."""
        plan = ctx.plan_mode

        if ctx.response_type == "clarification":
            # Store answers
            plan.set_clarification_response(ctx.answers, ctx.clarification_id)
            test_handlers.user_answers = ctx.answers

            await ctx.emit_status("working", "Discovering relevant subreddits...")

            # Emit discovery
            discovered_items = [
                DiscoveredItem(
                    id="r/gaming",
                    name="r/gaming",
                    description="Gaming discussions",
                    metadata={"subscribers": 35000000, "posts_per_day": 500},
                ),
                DiscoveredItem(
                    id="r/pcgaming",
                    name="r/pcgaming",
                    description="PC Gaming community",
                    metadata={"subscribers": 5000000, "posts_per_day": 200},
                ),
                DiscoveredItem(
                    id="r/games",
                    name="r/games",
                    description="Quality gaming content",
                    metadata={"subscribers": 3000000, "posts_per_day": 150},
                ),
            ]

            await plan.emit_discovery(discovered_items, "subreddits", message="Found 3 subreddits")
            test_handlers.discovery_emitted.set()

            # Request selection
            test_handlers.last_selection_id = await plan.request_selection(
                min_select=1,
                max_select=5,
                message="Select the subreddits you want to analyze",
            )
            test_handlers.selection_requested.set()

        elif ctx.response_type == "selection":
            plan.set_selection_response(ctx.selected_ids, ctx.selection_id)
            test_handlers.selected_ids = ctx.selected_ids

            await ctx.emit_status("working", "Preparing search plan...")

            # Emit preview
            preview = SearchPlanPreview(
                user_intent=plan.user_answers.get("topic", "research"),
                search_keywords=["discussion", "news", "analysis"],
                hashtags=[],
                follower_min=0,
                follower_max=0,
                user_answers=plan.user_answers,
                message="Here's the research plan. Review and approve to start.",
            )

            test_handlers.last_plan_id = await plan.emit_preview(preview)
            test_handlers.preview_emitted.set()

        elif ctx.response_type == "plan":
            plan.set_plan_approval(ctx.approved, ctx.plan_id)
            test_handlers.approved = ctx.approved

            if ctx.approved:
                await plan.start_execution("Executing research plan...")
                test_handlers.execution_started.set()

                # Simulate work
                await asyncio.sleep(0.1)

                result = {
                    "subreddits_analyzed": len(plan.selected_ids),
                    "posts_found": 150,
                    "top_topics": ["topic1", "topic2"],
                }

                await plan.complete(result, message="Research completed!")
                test_handlers.completed.set()
            else:
                await ctx.emit_status("working", "Plan cancelled.")

    # Start server in background
    base_url = f"http://127.0.0.1:{free_port}"

    # Create the app but don't start uvicorn (use TestClient pattern)
    app = server.app

    # For real server tests, we need to actually run the server
    from uvicorn import Config, Server

    config = Config(app=app, host="127.0.0.1", port=free_port, log_level="warning")
    server_instance = Server(config)

    # Run server in background task
    server_task = asyncio.create_task(server_instance.serve())

    # Wait for server to be ready
    await asyncio.sleep(0.3)

    try:
        yield server, base_url
    finally:
        # Shutdown server
        server_instance.should_exit = True
        await asyncio.sleep(0.1)
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass


@pytest.fixture
async def http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create an async HTTP client."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


async def parse_sse_events(response: httpx.Response) -> list[dict[str, Any]]:
    """Parse SSE events from a streaming response.

    Args:
        response: httpx streaming response

    Returns:
        List of parsed event data dictionaries
    """
    events = []
    buffer = ""

    async for chunk in response.aiter_text():
        buffer += chunk

        while "\n\n" in buffer:
            event_str, buffer = buffer.split("\n\n", 1)

            event_data = {}
            for line in event_str.split("\n"):
                if line.startswith("event:"):
                    event_data["event"] = line[6:].strip()
                elif line.startswith("data:"):
                    try:
                        event_data["data"] = json.loads(line[5:].strip())
                    except json.JSONDecodeError:
                        event_data["data"] = line[5:].strip()
                elif line.startswith("id:"):
                    event_data["id"] = line[3:].strip()

            if event_data:
                events.append(event_data)

    return events


async def collect_sse_until(
    response: httpx.Response,
    condition: Callable[[dict[str, Any]], bool],
    max_events: int = 100,
) -> list[dict[str, Any]]:
    """Collect SSE events until a condition is met.

    Args:
        response: httpx streaming response
        condition: Function that returns True when collection should stop
        max_events: Maximum events to collect before giving up

    Returns:
        List of collected events
    """
    events = []
    buffer = ""

    async for chunk in response.aiter_text():
        buffer += chunk

        while "\n\n" in buffer:
            event_str, buffer = buffer.split("\n\n", 1)

            event_data = {}
            for line in event_str.split("\n"):
                if line.startswith("event:"):
                    event_data["event"] = line[6:].strip()
                elif line.startswith("data:"):
                    try:
                        event_data["data"] = json.loads(line[5:].strip())
                    except json.JSONDecodeError:
                        event_data["data"] = line[5:].strip()
                elif line.startswith("id:"):
                    event_data["id"] = line[3:].strip()

            if event_data:
                events.append(event_data)

                if condition(event_data):
                    return events

                if len(events) >= max_events:
                    return events

    return events
