"""E2E tests for multi-round clarifications and phase transitions.

Tests complex workflows with multiple clarification rounds and phase rollbacks.
"""

import asyncio
import uuid

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
from tests.sdk.e2e.conftest import collect_sse_until


class MultiRoundHandlers:
    """Handlers for multi-round clarification tests."""

    def __init__(self):
        self.clarification_round = 0
        self.all_answers: dict = {}
        self.phase_history: list[str] = []


@pytest.fixture
async def multi_round_server(free_port: int) -> tuple:
    """Server that supports multiple clarification rounds."""
    handlers = MultiRoundHandlers()

    server = AgentServer(
        agent_id="multi-round-agent",
        name="Multi-Round Agent",
        port=free_port,
        host="127.0.0.1",
        plan_mode_config={
            "phases": ["clarification", "discovery", "selection", "preview"],
        },
    )

    @server.on_message
    async def handle_message(ctx: MessageContext):
        plan = ctx.plan_mode
        handlers.phase_history.append("initial_clarification")
        handlers.clarification_round = 1

        await plan.request_clarification(
            [
                Question(
                    id="topic",
                    type=QuestionType.FREE_TEXT,
                    question="What topic are you interested in?",
                    header="Topic",
                ),
                Question(
                    id="depth",
                    type=QuestionType.SINGLE_CHOICE,
                    question="How deep should we search?",
                    header="Depth",
                    options=[
                        QuestionOption(id="quick", label="Quick"),
                        QuestionOption(id="deep", label="Deep"),
                    ],
                ),
            ],
            message="First round: Basic info needed",
        )

    @server.on_respond
    async def handle_respond(ctx: ResponseContext):
        plan = ctx.plan_mode

        if ctx.response_type == "clarification":
            plan.set_clarification_response(ctx.answers, ctx.clarification_id)
            handlers.all_answers.update(ctx.answers)

            if handlers.clarification_round == 1:
                handlers.clarification_round = 2
                handlers.phase_history.append("second_clarification")

                await plan.request_clarification(
                    [
                        Question(
                            id="timeframe",
                            type=QuestionType.SINGLE_CHOICE,
                            question="What timeframe?",
                            header="Time",
                            options=[
                                QuestionOption(id="week", label="Past Week"),
                                QuestionOption(id="month", label="Past Month"),
                                QuestionOption(id="year", label="Past Year"),
                            ],
                        ),
                        Question(
                            id="include_comments",
                            type=QuestionType.YES_NO,
                            question="Include comments?",
                            header="Comments",
                        ),
                    ],
                    message="Second round: Additional details needed",
                )

            elif handlers.clarification_round == 2:
                handlers.clarification_round = 3
                handlers.phase_history.append("discovery")

                await plan.emit_discovery(
                    [
                        DiscoveredItem(
                            id="source_1",
                            name="Source 1",
                            description="First source",
                            metadata={"score": 95},
                        ),
                        DiscoveredItem(
                            id="source_2",
                            name="Source 2",
                            description="Second source",
                            metadata={"score": 85},
                        ),
                    ],
                    discovery_type="sources",
                    message="Found sources",
                )

                await plan.request_selection(
                    min_select=1,
                    max_select=2,
                    message="Select sources to analyze",
                )

            elif handlers.clarification_round == 3:
                handlers.clarification_round = 4
                handlers.phase_history.append("rollback_clarification")

                await plan.emit_discovery(
                    [
                        DiscoveredItem(
                            id="refined_1",
                            name="Refined 1",
                            description="Better match",
                        ),
                    ],
                    discovery_type="refined_sources",
                    message="Refined results",
                )

                await plan.request_selection(message="Select refined sources")

        elif ctx.response_type == "selection":
            plan.set_selection_response(ctx.selected_ids, ctx.selection_id)
            handlers.phase_history.append("preview")

            preview = SearchPlanPreview(
                user_intent=handlers.all_answers.get("topic", "research"),
                search_keywords=["test"],
                user_answers=handlers.all_answers,
                message=f"Research plan with {len(handlers.all_answers)} parameters",
            )
            await plan.emit_preview(preview)

        elif ctx.response_type == "plan":
            plan.set_plan_approval(ctx.approved, ctx.plan_id)
            if ctx.approved:
                handlers.phase_history.append("executing")
                await plan.start_execution()
                handlers.phase_history.append("completed")
                await plan.complete(
                    {"answers": handlers.all_answers},
                    message="Completed multi-round workflow!",
                )
            else:
                handlers.clarification_round = 3
                handlers.phase_history.append("rejection_rollback")

                await plan.request_clarification(
                    [
                        Question(
                            id="refinement",
                            type=QuestionType.FREE_TEXT,
                            question="What would you like to change?",
                            header="Changes",
                        ),
                    ],
                    message="Please tell us what to change",
                )

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


class TestMultiRoundClarification:
    """Tests for multi-round clarification workflows."""

    @pytest.mark.asyncio
    async def test_two_round_clarification_then_discovery(
        self,
        multi_round_server: tuple,
    ):
        """Test workflow with two rounds of clarification before discovery."""
        server, base_url, handlers = multi_round_server
        session_id = str(uuid.uuid4())

        async with httpx.AsyncClient(timeout=30.0) as http_client:
            # Round 1: Initial message
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
                            "parts": [{"text": "Start multi-round workflow"}],
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
                clarification_1 = events[-1]["data"]
                assert len(clarification_1["questions"]) == 2
                clarification_id_1 = clarification_1["clarificationId"]

            # Round 1: Respond with basic answers
            async with http_client.stream(
                "POST",
                f"{base_url}/respond",
                json={
                    "sessionId": session_id,
                    "clarificationId": clarification_id_1,
                    "answers": {"topic": "gaming", "depth": "deep"},
                },
                headers={"Accept": "text/event-stream"},
            ) as response:
                events = await collect_sse_until(
                    response,
                    lambda e: e.get("event") == "clarification_needed",
                )
                clarification_2 = events[-1]["data"]
                assert len(clarification_2["questions"]) == 2
                question_ids = [q["questionId"] for q in clarification_2["questions"]]
                assert "timeframe" in question_ids
                assert "include_comments" in question_ids
                clarification_id_2 = clarification_2["clarificationId"]

            # Round 2: Respond with follow-up answers
            async with http_client.stream(
                "POST",
                f"{base_url}/respond",
                json={
                    "sessionId": session_id,
                    "clarificationId": clarification_id_2,
                    "answers": {"timeframe": "month", "include_comments": True},
                },
                headers={"Accept": "text/event-stream"},
            ) as response:
                events = await collect_sse_until(
                    response,
                    lambda e: e.get("event") == "selection_required",
                )
                discovery_events = [e for e in events if e.get("event") == "discovery_result"]
                assert len(discovery_events) >= 1
                selection = events[-1]["data"]
                assert "selectionId" in selection

            assert handlers.all_answers == {
                "topic": "gaming",
                "depth": "deep",
                "timeframe": "month",
                "include_comments": True,
            }
            assert "initial_clarification" in handlers.phase_history
            assert "second_clarification" in handlers.phase_history
            assert "discovery" in handlers.phase_history

    @pytest.mark.asyncio
    async def test_complete_multi_round_workflow_to_completion(
        self,
        multi_round_server: tuple,
    ):
        """Test complete workflow: 2 clarifications -> discovery -> selection -> preview -> complete."""
        server, base_url, handlers = multi_round_server
        session_id = str(uuid.uuid4())

        async with httpx.AsyncClient(timeout=30.0) as http_client:
            # Initial message
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
                            "parts": [{"text": "Complete workflow test"}],
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
                clar_id_1 = events[-1]["data"]["clarificationId"]

            # First clarification response
            async with http_client.stream(
                "POST",
                f"{base_url}/respond",
                json={
                    "sessionId": session_id,
                    "clarificationId": clar_id_1,
                    "answers": {"topic": "AI research", "depth": "quick"},
                },
                headers={"Accept": "text/event-stream"},
            ) as response:
                events = await collect_sse_until(
                    response,
                    lambda e: e.get("event") == "clarification_needed",
                )
                clar_id_2 = events[-1]["data"]["clarificationId"]

            # Second clarification response
            async with http_client.stream(
                "POST",
                f"{base_url}/respond",
                json={
                    "sessionId": session_id,
                    "clarificationId": clar_id_2,
                    "answers": {"timeframe": "week", "include_comments": False},
                },
                headers={"Accept": "text/event-stream"},
            ) as response:
                events = await collect_sse_until(
                    response,
                    lambda e: e.get("event") == "selection_required",
                )
                selection_id = events[-1]["data"]["selectionId"]

            # Selection response
            async with http_client.stream(
                "POST",
                f"{base_url}/respond",
                json={
                    "sessionId": session_id,
                    "selectionId": selection_id,
                    "selectedIds": ["source_1"],
                },
                headers={"Accept": "text/event-stream"},
            ) as response:
                events = await collect_sse_until(
                    response,
                    lambda e: e.get("event") == "preview_ready",
                )
                preview = events[-1]["data"]
                assert preview["userAnswers"]["topic"] == "AI research"
                assert preview["userAnswers"]["timeframe"] == "week"
                plan_id = preview["planId"]

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

            assert handlers.phase_history == [
                "initial_clarification",
                "second_clarification",
                "discovery",
                "preview",
                "executing",
                "completed",
            ]

    @pytest.mark.asyncio
    async def test_plan_rejection_triggers_clarification_rollback(
        self,
        multi_round_server: tuple,
    ):
        """Test that rejecting a plan can trigger a rollback to clarification."""
        server, base_url, handlers = multi_round_server
        session_id = str(uuid.uuid4())

        async with httpx.AsyncClient(timeout=30.0) as http_client:
            # Initial message
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
                            "parts": [{"text": "Test rejection"}],
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
                clar_id_1 = events[-1]["data"]["clarificationId"]

            async with http_client.stream(
                "POST",
                f"{base_url}/respond",
                json={
                    "sessionId": session_id,
                    "clarificationId": clar_id_1,
                    "answers": {"topic": "test", "depth": "quick"},
                },
                headers={"Accept": "text/event-stream"},
            ) as response:
                events = await collect_sse_until(
                    response,
                    lambda e: e.get("event") == "clarification_needed",
                )
                clar_id_2 = events[-1]["data"]["clarificationId"]

            async with http_client.stream(
                "POST",
                f"{base_url}/respond",
                json={
                    "sessionId": session_id,
                    "clarificationId": clar_id_2,
                    "answers": {"timeframe": "year", "include_comments": True},
                },
                headers={"Accept": "text/event-stream"},
            ) as response:
                events = await collect_sse_until(
                    response,
                    lambda e: e.get("event") == "selection_required",
                )
                selection_id = events[-1]["data"]["selectionId"]

            async with http_client.stream(
                "POST",
                f"{base_url}/respond",
                json={
                    "sessionId": session_id,
                    "selectionId": selection_id,
                    "selectedIds": ["source_1", "source_2"],
                },
                headers={"Accept": "text/event-stream"},
            ) as response:
                events = await collect_sse_until(
                    response,
                    lambda e: e.get("event") == "preview_ready",
                )
                plan_id = events[-1]["data"]["planId"]

            # REJECT the plan
            async with http_client.stream(
                "POST",
                f"{base_url}/respond",
                json={
                    "sessionId": session_id,
                    "planId": plan_id,
                    "approved": False,
                },
                headers={"Accept": "text/event-stream"},
            ) as response:
                events = await collect_sse_until(
                    response,
                    lambda e: e.get("event") == "clarification_needed",
                )
                new_clarification = events[-1]["data"]
                assert "refinement" in [q["questionId"] for q in new_clarification["questions"]]

            assert "rejection_rollback" in handlers.phase_history


class TestAnswerAccumulation:
    """Tests for answer accumulation across clarification rounds."""

    @pytest.mark.asyncio
    async def test_answers_accumulate_across_rounds(
        self,
        multi_round_server: tuple,
    ):
        """Test that answers from all rounds are accumulated and available."""
        server, base_url, handlers = multi_round_server
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
                            "parts": [{"text": "Test accumulation"}],
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
                clar_id_1 = events[-1]["data"]["clarificationId"]

            async with http_client.stream(
                "POST",
                f"{base_url}/respond",
                json={
                    "sessionId": session_id,
                    "clarificationId": clar_id_1,
                    "answers": {"topic": "unique_topic_123", "depth": "deep"},
                },
                headers={"Accept": "text/event-stream"},
            ) as response:
                events = await collect_sse_until(
                    response,
                    lambda e: e.get("event") == "clarification_needed",
                )
                clar_id_2 = events[-1]["data"]["clarificationId"]

            async with http_client.stream(
                "POST",
                f"{base_url}/respond",
                json={
                    "sessionId": session_id,
                    "clarificationId": clar_id_2,
                    "answers": {"timeframe": "special_timeframe", "include_comments": False},
                },
                headers={"Accept": "text/event-stream"},
            ) as response:
                await collect_sse_until(
                    response,
                    lambda e: e.get("event") == "selection_required",
                )

            assert handlers.all_answers == {
                "topic": "unique_topic_123",
                "depth": "deep",
                "timeframe": "special_timeframe",
                "include_comments": False,
            }

    @pytest.mark.asyncio
    async def test_later_answers_override_earlier_same_keys(
        self,
        free_port: int,
    ):
        """Test that if same question ID appears in multiple rounds, later overrides earlier."""
        handlers_data = {"all_answers": {}}

        server = AgentServer(
            agent_id="override-test-agent",
            port=free_port,
            host="127.0.0.1",
            plan_mode_config={"phases": ["clarification", "preview"]},
        )

        @server.on_message
        async def handle_message(ctx: MessageContext):
            await ctx.plan_mode.request_clarification(
                [
                    Question(
                        id="shared_question",
                        type=QuestionType.FREE_TEXT,
                        question="Enter value",
                        header="Value",
                    ),
                ]
            )

        round_count = [0]

        @server.on_respond
        async def handle_respond(ctx: ResponseContext):
            plan = ctx.plan_mode

            if ctx.response_type == "clarification":
                plan.set_clarification_response(ctx.answers, ctx.clarification_id)
                handlers_data["all_answers"].update(ctx.answers)
                round_count[0] += 1

                if round_count[0] == 1:
                    await plan.request_clarification(
                        [
                            Question(
                                id="shared_question",
                                type=QuestionType.FREE_TEXT,
                                question="Enter value again",
                                header="Value",
                            ),
                        ]
                    )
                else:
                    preview = SearchPlanPreview(
                        user_intent="test",
                        search_keywords=["test"],
                        user_answers=handlers_data["all_answers"],
                        message="Done",
                    )
                    await plan.emit_preview(preview)

            elif ctx.response_type == "plan":
                plan.set_plan_approval(ctx.approved, ctx.plan_id)
                if ctx.approved:
                    await plan.start_execution()
                    await plan.complete({}, message="Done")

        from uvicorn import Config, Server

        app = server.app
        config = Config(app=app, host="127.0.0.1", port=free_port, log_level="warning")
        server_instance = Server(config)
        server_task = asyncio.create_task(server_instance.serve())
        await asyncio.sleep(0.3)

        base_url = f"http://127.0.0.1:{free_port}"
        session_id = str(uuid.uuid4())

        try:
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
                                "parts": [{"text": "Override test"}],
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
                    clar_id_1 = events[-1]["data"]["clarificationId"]

                async with http_client.stream(
                    "POST",
                    f"{base_url}/respond",
                    json={
                        "sessionId": session_id,
                        "clarificationId": clar_id_1,
                        "answers": {"shared_question": "FIRST_VALUE"},
                    },
                    headers={"Accept": "text/event-stream"},
                ) as response:
                    events = await collect_sse_until(
                        response,
                        lambda e: e.get("event") == "clarification_needed",
                    )
                    clar_id_2 = events[-1]["data"]["clarificationId"]

                async with http_client.stream(
                    "POST",
                    f"{base_url}/respond",
                    json={
                        "sessionId": session_id,
                        "clarificationId": clar_id_2,
                        "answers": {"shared_question": "SECOND_VALUE"},
                    },
                    headers={"Accept": "text/event-stream"},
                ) as response:
                    events = await collect_sse_until(
                        response,
                        lambda e: e.get("event") == "preview_ready",
                    )
                    preview = events[-1]["data"]
                    assert preview["userAnswers"]["shared_question"] == "SECOND_VALUE"

        finally:
            server_instance.should_exit = True
            await asyncio.sleep(0.1)
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass
