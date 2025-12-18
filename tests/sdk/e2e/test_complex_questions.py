"""E2E tests for complex question types and multi-question clarifications.

Tests all 5 question types and complex multi-question workflows.
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
from tests.sdk.e2e.conftest import collect_sse_until, find_free_port


class ComplexQuestionHandlers:
    """Handlers for testing complex question types."""

    def __init__(self):
        self.received_answers: dict = {}
        self.clarification_count = 0


@pytest.fixture
async def complex_questions_server(
    free_port: int,
) -> tuple:
    """Server with all question types."""
    handlers = ComplexQuestionHandlers()

    server = AgentServer(
        agent_id="complex-questions-agent",
        name="Complex Questions Agent",
        port=free_port,
        host="127.0.0.1",
        plan_mode_config={
            "phases": ["clarification", "preview"],
        },
    )

    @server.on_message
    async def handle_message(ctx: MessageContext):
        plan = ctx.plan_mode
        handlers.clarification_count += 1

        # Ask all 5 question types in one clarification
        await plan.request_clarification([
            # 1. Free text
            Question(
                id="free_text_q",
                type=QuestionType.FREE_TEXT,
                question="What is your research topic?",
                header="Topic",
                placeholder="Enter topic here...",
            ),
            # 2. Single choice
            Question(
                id="single_choice_q",
                type=QuestionType.SINGLE_CHOICE,
                question="Select research depth",
                header="Depth",
                options=[
                    QuestionOption(id="shallow", label="Shallow", description="Quick scan"),
                    QuestionOption(id="medium", label="Medium", description="Moderate depth"),
                    QuestionOption(id="deep", label="Deep", description="Thorough analysis"),
                ],
            ),
            # 3. Multiple choice
            Question(
                id="multiple_choice_q",
                type=QuestionType.MULTIPLE_CHOICE,
                question="Select data sources",
                header="Sources",
                options=[
                    QuestionOption(id="reddit", label="Reddit"),
                    QuestionOption(id="twitter", label="Twitter"),
                    QuestionOption(id="youtube", label="YouTube"),
                    QuestionOption(id="tiktok", label="TikTok"),
                ],
            ),
            # 4. Yes/No
            Question(
                id="yes_no_q",
                type=QuestionType.YES_NO,
                question="Include NSFW content?",
                header="NSFW",
            ),
            # 5. Numeric range
            Question(
                id="numeric_range_q",
                type=QuestionType.NUMERIC_RANGE,
                question="Minimum follower count",
                header="Followers",
                min=1000,
                max=10000000,
                step=1000,
            ),
        ], message="Please answer all questions to configure your research.")

    @server.on_respond
    async def handle_respond(ctx: ResponseContext):
        plan = ctx.plan_mode

        if ctx.response_type == "clarification":
            plan.set_clarification_response(ctx.answers, ctx.clarification_id)
            handlers.received_answers = ctx.answers

            # Emit preview with user answers
            preview = SearchPlanPreview(
                user_intent=ctx.answers.get("free_text_q", "research"),
                search_keywords=["test"],
                user_answers=ctx.answers,
                message="Research plan based on your answers",
            )
            await plan.emit_preview(preview)

        elif ctx.response_type == "plan":
            plan.set_plan_approval(ctx.approved, ctx.plan_id)
            if ctx.approved:
                await plan.start_execution()
                await plan.complete(
                    {"answers_received": handlers.received_answers},
                    message="Completed with all question types!",
                )

    # Start server
    import uvicorn
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


class TestAllQuestionTypes:
    """Tests for all 5 question types."""

    @pytest.mark.asyncio
    async def test_all_question_types_in_single_clarification(
        self,
        complex_questions_server: tuple,
        http_client: httpx.AsyncClient,
    ):
        """Test all 5 question types in a single clarification request."""
        server, base_url, handlers = complex_questions_server
        session_id = str(uuid.uuid4())

        # Send initial message
        message_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/stream",
            "params": {
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "role": "user",
                    "parts": [{"text": "Test all question types"}],
                },
                "sessionId": session_id,
            },
        }

        async with http_client.stream(
            "POST", f"{base_url}/", json=message_request,
            headers={"Accept": "text/event-stream"},
        ) as response:
            events = await collect_sse_until(
                response,
                lambda e: e.get("event") == "clarification_needed",
            )

            clarification = events[-1]["data"]
            questions = clarification["questions"]

            # Verify all 5 question types are present
            assert len(questions) == 5

            question_types = {q["questionId"]: q["questionType"] for q in questions}
            assert question_types["free_text_q"] == "free_text"
            assert question_types["single_choice_q"] == "single_choice"
            assert question_types["multiple_choice_q"] == "multiple_choice"
            assert question_types["yes_no_q"] == "yes_no"
            assert question_types["numeric_range_q"] == "numeric_range"

            # Verify single_choice has options
            single_choice = next(q for q in questions if q["questionId"] == "single_choice_q")
            assert len(single_choice["options"]) == 3
            assert single_choice["options"][0]["id"] == "shallow"

            # Verify multiple_choice has options
            multiple_choice = next(q for q in questions if q["questionId"] == "multiple_choice_q")
            assert len(multiple_choice["options"]) == 4

            # Verify numeric_range has min/max/step
            numeric = next(q for q in questions if q["questionId"] == "numeric_range_q")
            assert numeric["min"] == 1000
            assert numeric["max"] == 10000000
            assert numeric["step"] == 1000

            clarification_id = clarification["clarificationId"]

        # Respond with all answer types
        complex_answers = {
            "free_text_q": "AI research in social media",
            "single_choice_q": "deep",
            "multiple_choice_q": ["reddit", "twitter", "youtube"],  # Multiple selections
            "yes_no_q": False,
            "numeric_range_q": 50000,
        }

        async with http_client.stream(
            "POST", f"{base_url}/respond",
            json={
                "sessionId": session_id,
                "clarificationId": clarification_id,
                "answers": complex_answers,
            },
            headers={"Accept": "text/event-stream"},
        ) as response:
            events = await collect_sse_until(
                response,
                lambda e: e.get("event") == "preview_ready",
            )

            preview = events[-1]["data"]
            # Verify user answers are in preview
            assert preview["userAnswers"]["free_text_q"] == "AI research in social media"
            assert preview["userAnswers"]["single_choice_q"] == "deep"
            assert preview["userAnswers"]["multiple_choice_q"] == ["reddit", "twitter", "youtube"]
            assert preview["userAnswers"]["yes_no_q"] is False
            assert preview["userAnswers"]["numeric_range_q"] == 50000

            plan_id = preview["planId"]

        # Approve and complete
        async with http_client.stream(
            "POST", f"{base_url}/respond",
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

        # Verify all answers were received
        assert handlers.received_answers == complex_answers

    @pytest.mark.asyncio
    async def test_free_text_with_special_characters(
        self,
        complex_questions_server: tuple,
        http_client: httpx.AsyncClient,
    ):
        """Test free text answers with special characters, unicode, and long text."""
        server, base_url, handlers = complex_questions_server
        session_id = str(uuid.uuid4())

        # Get clarification
        message_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/stream",
            "params": {
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "role": "user",
                    "parts": [{"text": "Test special characters"}],
                },
                "sessionId": session_id,
            },
        }

        async with http_client.stream(
            "POST", f"{base_url}/", json=message_request,
            headers={"Accept": "text/event-stream"},
        ) as response:
            events = await collect_sse_until(
                response,
                lambda e: e.get("event") == "clarification_needed",
            )
            clarification_id = events[-1]["data"]["clarificationId"]

        # Answer with special characters and unicode
        special_text = """
        研究主題: AI & Machine Learning 🤖
        Keywords: "deep learning", 'neural networks'
        Special chars: <script>alert('test')</script>
        Newlines and tabs:	test
        Emoji: 🎉🚀💻
        """

        answers = {
            "free_text_q": special_text,
            "single_choice_q": "medium",
            "multiple_choice_q": ["reddit"],
            "yes_no_q": True,
            "numeric_range_q": 10000,
        }

        async with http_client.stream(
            "POST", f"{base_url}/respond",
            json={
                "sessionId": session_id,
                "clarificationId": clarification_id,
                "answers": answers,
            },
            headers={"Accept": "text/event-stream"},
        ) as response:
            events = await collect_sse_until(
                response,
                lambda e: e.get("event") == "preview_ready",
            )

            preview = events[-1]["data"]
            # Verify special characters are preserved
            assert "研究主題" in preview["userAnswers"]["free_text_q"]
            assert "🤖" in preview["userAnswers"]["free_text_q"]

    @pytest.mark.asyncio
    async def test_empty_multiple_choice_selection(
        self,
        complex_questions_server: tuple,
        http_client: httpx.AsyncClient,
    ):
        """Test with empty multiple choice selection (edge case)."""
        server, base_url, handlers = complex_questions_server
        session_id = str(uuid.uuid4())

        # Get clarification
        message_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/stream",
            "params": {
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "role": "user",
                    "parts": [{"text": "Test empty selection"}],
                },
                "sessionId": session_id,
            },
        }

        async with http_client.stream(
            "POST", f"{base_url}/", json=message_request,
            headers={"Accept": "text/event-stream"},
        ) as response:
            events = await collect_sse_until(
                response,
                lambda e: e.get("event") == "clarification_needed",
            )
            clarification_id = events[-1]["data"]["clarificationId"]

        # Answer with empty multiple choice
        answers = {
            "free_text_q": "test",
            "single_choice_q": "shallow",
            "multiple_choice_q": [],  # Empty selection
            "yes_no_q": False,
            "numeric_range_q": 1000,
        }

        async with http_client.stream(
            "POST", f"{base_url}/respond",
            json={
                "sessionId": session_id,
                "clarificationId": clarification_id,
                "answers": answers,
            },
            headers={"Accept": "text/event-stream"},
        ) as response:
            events = await collect_sse_until(
                response,
                lambda e: e.get("event") == "preview_ready",
            )

            preview = events[-1]["data"]
            assert preview["userAnswers"]["multiple_choice_q"] == []

    @pytest.mark.asyncio
    async def test_numeric_range_boundary_values(
        self,
        complex_questions_server: tuple,
        http_client: httpx.AsyncClient,
    ):
        """Test numeric range with boundary values (min, max)."""
        server, base_url, handlers = complex_questions_server

        for test_value in [1000, 10000000, 5000000]:  # min, max, middle
            session_id = str(uuid.uuid4())

            message_request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "message/stream",
                "params": {
                    "message": {
                        "messageId": str(uuid.uuid4()),
                        "role": "user",
                        "parts": [{"text": f"Test numeric {test_value}"}],
                    },
                    "sessionId": session_id,
                },
            }

            async with http_client.stream(
                "POST", f"{base_url}/", json=message_request,
                headers={"Accept": "text/event-stream"},
            ) as response:
                events = await collect_sse_until(
                    response,
                    lambda e: e.get("event") == "clarification_needed",
                )
                clarification_id = events[-1]["data"]["clarificationId"]

            answers = {
                "free_text_q": "test",
                "single_choice_q": "shallow",
                "multiple_choice_q": ["reddit"],
                "yes_no_q": True,
                "numeric_range_q": test_value,
            }

            async with http_client.stream(
                "POST", f"{base_url}/respond",
                json={
                    "sessionId": session_id,
                    "clarificationId": clarification_id,
                    "answers": answers,
                },
                headers={"Accept": "text/event-stream"},
            ) as response:
                events = await collect_sse_until(
                    response,
                    lambda e: e.get("event") == "preview_ready",
                )

                preview = events[-1]["data"]
                assert preview["userAnswers"]["numeric_range_q"] == test_value
