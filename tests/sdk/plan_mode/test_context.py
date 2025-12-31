"""Tests for Plan Mode Context."""

import pytest
import asyncio
from pixell.sdk.plan_mode.context import PlanModeContext
from pixell.sdk.plan_mode.phases import Phase
from pixell.sdk.plan_mode.events import (
    Question,
    QuestionType,
    QuestionOption,
    DiscoveredItem,
    SearchPlanPreview,
    PlanProposed,
    PlanStep,
)
from pixell.sdk.a2a.streaming import SSEStream


class TestPlanModeContextCreation:
    """Tests for PlanModeContext initialization."""

    @pytest.fixture
    def stream(self):
        return SSEStream()

    def test_create_minimal(self, stream):
        ctx = PlanModeContext(stream=stream)
        assert ctx.phase == Phase.IDLE
        assert ctx.user_answers == {}
        assert ctx.discovered_items == []
        assert ctx.selected_ids == []
        assert ctx.supported_phases == []
        assert ctx.agent_id == ""

    def test_create_with_supported_phases(self, stream):
        supported = [Phase.CLARIFICATION, Phase.PREVIEW]
        ctx = PlanModeContext(
            stream=stream,
            supported_phases=supported,
            agent_id="test-agent",
        )
        assert ctx.supported_phases == supported
        assert ctx.agent_id == "test-agent"


class TestPlanModeContextTransitions:
    """Tests for phase transitions."""

    @pytest.fixture
    def stream(self):
        return SSEStream()

    @pytest.fixture
    def ctx(self, stream):
        return PlanModeContext(
            stream=stream,
            supported_phases=[
                Phase.CLARIFICATION,
                Phase.DISCOVERY,
                Phase.SELECTION,
                Phase.PREVIEW,
            ],
        )

    def test_initial_phase_is_idle(self, ctx):
        assert ctx.phase == Phase.IDLE

    def test_transition_to_clarification(self, ctx):
        result = ctx._transition_to(Phase.CLARIFICATION)
        assert result is True
        assert ctx.phase == Phase.CLARIFICATION

    def test_invalid_transition_still_happens_with_warning(self, ctx):
        # Force an invalid transition (completed can't go to clarification)
        ctx.phase = Phase.COMPLETED
        result = ctx._transition_to(Phase.CLARIFICATION)
        assert result is False
        # Transition still happens (warning only)
        assert ctx.phase == Phase.CLARIFICATION

    def test_transition_to_unsupported_phase_with_warning(self, ctx):
        # Discovery is in supported phases, but let's test with restricted
        ctx.supported_phases = [Phase.CLARIFICATION]  # Only clarification
        # Discovery not in supported phases
        result = ctx._transition_to(Phase.DISCOVERY)
        assert result is False
        # Transition still happens
        assert ctx.phase == Phase.DISCOVERY


class TestRequestClarification:
    """Tests for request_clarification method."""

    @pytest.fixture
    def stream(self):
        return SSEStream()

    @pytest.fixture
    def ctx(self, stream):
        return PlanModeContext(
            stream=stream,
            supported_phases=[Phase.CLARIFICATION],
            agent_id="test-agent",
        )

    @pytest.mark.asyncio
    async def test_request_clarification_basic(self, ctx):
        questions = [
            Question(
                id="topic",
                type=QuestionType.FREE_TEXT,
                question="What topic?",
            )
        ]

        clarification_id = await ctx.request_clarification(questions)

        assert clarification_id is not None
        assert ctx.phase == Phase.CLARIFICATION
        assert ctx._pending_clarification_id == clarification_id

    @pytest.mark.asyncio
    async def test_request_clarification_emits_event(self, ctx):
        questions = [Question(id="q1", type=QuestionType.YES_NO, question="Continue?")]

        await ctx.request_clarification(questions, message="Please confirm")

        event = await asyncio.wait_for(ctx.stream._queue.get(), timeout=1.0)
        assert event.event == "clarification_needed"
        assert event.data["state"] == "input-required"
        assert event.data["agentId"] == "test-agent"
        assert event.data["message"] == "Please confirm"

    @pytest.mark.asyncio
    async def test_request_clarification_with_context(self, ctx):
        questions = [Question(id="q1", type=QuestionType.FREE_TEXT, question="Q?")]

        await ctx.request_clarification(
            questions,
            context="Need more info to proceed",
            message="Please answer",
            timeout_ms=60000,
        )

        event = await asyncio.wait_for(ctx.stream._queue.get(), timeout=1.0)
        assert event.data["context"] == "Need more info to proceed"
        assert event.data["timeoutMs"] == 60000


class TestSetClarificationResponse:
    """Tests for set_clarification_response method."""

    @pytest.fixture
    def stream(self):
        return SSEStream()

    @pytest.fixture
    def ctx(self, stream):
        return PlanModeContext(stream=stream)

    @pytest.mark.asyncio
    async def test_set_clarification_response(self, ctx):
        # First request clarification
        questions = [Question(id="topic", type=QuestionType.FREE_TEXT, question="Topic?")]
        clarification_id = await ctx.request_clarification(questions)

        # Then set response
        ctx.set_clarification_response({"topic": "gaming"}, clarification_id)

        assert ctx.user_answers["topic"] == "gaming"
        assert ctx._pending_clarification_id is None

    def test_set_clarification_response_updates_answers(self, ctx):
        ctx.user_answers = {"existing": "value"}
        ctx.set_clarification_response({"new": "answer"})
        assert ctx.user_answers == {"existing": "value", "new": "answer"}

    def test_set_clarification_response_mismatched_id_warning(self, ctx):
        ctx._pending_clarification_id = "expected-id"
        # Should log warning but still work
        ctx.set_clarification_response({"q": "a"}, "different-id")
        assert ctx.user_answers == {"q": "a"}


class TestEmitDiscovery:
    """Tests for emit_discovery method."""

    @pytest.fixture
    def stream(self):
        return SSEStream()

    @pytest.fixture
    def ctx(self, stream):
        return PlanModeContext(
            stream=stream,
            supported_phases=[Phase.DISCOVERY],
        )

    @pytest.mark.asyncio
    async def test_emit_discovery(self, ctx):
        items = [
            DiscoveredItem(id="r/gaming", name="r/gaming", description="Gaming sub"),
            DiscoveredItem(id="r/pcgaming", name="r/pcgaming"),
        ]

        discovery_id = await ctx.emit_discovery(items, "subreddits")

        assert discovery_id is not None
        assert ctx.phase == Phase.DISCOVERY
        assert ctx.discovered_items == items

    @pytest.mark.asyncio
    async def test_emit_discovery_emits_event(self, ctx):
        items = [DiscoveredItem(id="x", name="X")]

        await ctx.emit_discovery(items, "channels", message="Found 1 channel")

        event = await asyncio.wait_for(ctx.stream._queue.get(), timeout=1.0)
        assert event.event == "discovery_result"
        assert event.data["state"] == "working"
        assert event.data["discoveryType"] == "channels"
        assert event.data["message"] == "Found 1 channel"


class TestRequestSelection:
    """Tests for request_selection method."""

    @pytest.fixture
    def stream(self):
        return SSEStream()

    @pytest.fixture
    def ctx(self, stream):
        return PlanModeContext(
            stream=stream,
            supported_phases=[Phase.DISCOVERY, Phase.SELECTION],
        )

    @pytest.mark.asyncio
    async def test_request_selection(self, ctx):
        items = [
            DiscoveredItem(id="a", name="A"),
            DiscoveredItem(id="b", name="B"),
        ]
        ctx.discovered_items = items

        selection_id = await ctx.request_selection(min_select=1, max_select=5)

        assert selection_id is not None
        assert ctx.phase == Phase.SELECTION
        assert ctx._pending_selection_id == selection_id

    @pytest.mark.asyncio
    async def test_request_selection_with_explicit_items(self, ctx):
        explicit_items = [DiscoveredItem(id="x", name="X")]

        await ctx.request_selection(items=explicit_items)

        event = await asyncio.wait_for(ctx.stream._queue.get(), timeout=1.0)
        assert len(event.data["items"]) == 1
        assert event.data["items"][0]["id"] == "x"

    @pytest.mark.asyncio
    async def test_request_selection_emits_event(self, ctx):
        items = [DiscoveredItem(id="a", name="A")]
        ctx.discovered_items = items

        await ctx.request_selection(
            discovery_type="subreddits",
            min_select=1,
            max_select=10,
            message="Pick some",
        )

        event = await asyncio.wait_for(ctx.stream._queue.get(), timeout=1.0)
        assert event.event == "selection_required"
        assert event.data["state"] == "input-required"
        assert event.data["minSelect"] == 1
        assert event.data["maxSelect"] == 10
        assert event.data["message"] == "Pick some"


class TestSetSelectionResponse:
    """Tests for set_selection_response method."""

    @pytest.fixture
    def stream(self):
        return SSEStream()

    @pytest.fixture
    def ctx(self, stream):
        return PlanModeContext(stream=stream)

    @pytest.mark.asyncio
    async def test_set_selection_response(self, ctx):
        items = [
            DiscoveredItem(id="a", name="A"),
            DiscoveredItem(id="b", name="B"),
        ]
        ctx.discovered_items = items
        selection_id = await ctx.request_selection(items=items)

        ctx.set_selection_response(["a"], selection_id)

        assert ctx.selected_ids == ["a"]
        assert ctx._pending_selection_id is None

    def test_set_selection_response_multiple(self, ctx):
        ctx.set_selection_response(["item-1", "item-2", "item-3"])
        assert len(ctx.selected_ids) == 3


class TestEmitPreview:
    """Tests for emit_preview method."""

    @pytest.fixture
    def stream(self):
        return SSEStream()

    @pytest.fixture
    def ctx(self, stream):
        return PlanModeContext(
            stream=stream,
            supported_phases=[Phase.PREVIEW],
        )

    @pytest.mark.asyncio
    async def test_emit_preview_search_plan(self, ctx):
        preview = SearchPlanPreview(
            user_intent="Find gaming content",
            search_keywords=["gaming", "esports"],
            hashtags=["#gaming"],
        )

        plan_id = await ctx.emit_preview(preview)

        assert plan_id is not None
        assert ctx.phase == Phase.PREVIEW
        assert ctx._pending_plan_id == plan_id

    @pytest.mark.asyncio
    async def test_emit_preview_plan_proposed(self, ctx):
        plan = PlanProposed(
            title="Research Plan",
            steps=[
                PlanStep(id="s1", description="Step 1"),
                PlanStep(id="s2", description="Step 2"),
            ],
        )

        await ctx.emit_preview(plan)

        event = await asyncio.wait_for(ctx.stream._queue.get(), timeout=1.0)
        assert event.event == "preview_ready"
        assert event.data["state"] == "input-required"


class TestSetPlanApproval:
    """Tests for set_plan_approval method."""

    @pytest.fixture
    def stream(self):
        return SSEStream()

    @pytest.fixture
    def ctx(self, stream):
        return PlanModeContext(stream=stream)

    @pytest.mark.asyncio
    async def test_set_plan_approval_approved(self, ctx):
        preview = SearchPlanPreview(user_intent="Test", search_keywords=["test"])
        plan_id = await ctx.emit_preview(preview)

        ctx.set_plan_approval(True, plan_id)

        assert ctx._pending_plan_id is None

    @pytest.mark.asyncio
    async def test_set_plan_approval_rejected(self, ctx):
        preview = SearchPlanPreview(user_intent="Test", search_keywords=["test"])
        await ctx.emit_preview(preview)

        ctx.set_plan_approval(False)
        # Should work without raising

    def test_set_plan_approval_with_modifications(self, ctx):
        ctx.user_answers = {"original": "value"}
        ctx.set_plan_approval(True, modifications={"modified": "newvalue"})
        assert ctx.user_answers["modified"] == "newvalue"


class TestStartExecution:
    """Tests for start_execution method."""

    @pytest.fixture
    def stream(self):
        return SSEStream()

    @pytest.fixture
    def ctx(self, stream):
        return PlanModeContext(stream=stream)

    @pytest.mark.asyncio
    async def test_start_execution(self, ctx):
        await ctx.start_execution()

        assert ctx.phase == Phase.EXECUTING

    @pytest.mark.asyncio
    async def test_start_execution_emits_status(self, ctx):
        await ctx.start_execution("Beginning task...")

        event = await asyncio.wait_for(ctx.stream._queue.get(), timeout=1.0)
        assert event.event == "status-update"
        assert event.data["state"] == "working"
        assert event.data["message"] == "Beginning task..."

    @pytest.mark.asyncio
    async def test_start_execution_default_message(self, ctx):
        await ctx.start_execution()

        event = await asyncio.wait_for(ctx.stream._queue.get(), timeout=1.0)
        assert event.data["message"] == "Starting execution..."


class TestComplete:
    """Tests for complete method."""

    @pytest.fixture
    def stream(self):
        return SSEStream()

    @pytest.fixture
    def ctx(self, stream):
        return PlanModeContext(stream=stream)

    @pytest.mark.asyncio
    async def test_complete(self, ctx):
        result = {"items_found": 10, "status": "success"}

        await ctx.complete(result)

        assert ctx.phase == Phase.COMPLETED

    @pytest.mark.asyncio
    async def test_complete_emits_result(self, ctx):
        result = {"count": 5}

        await ctx.complete(result, message="Found 5 items!")

        event = await asyncio.wait_for(ctx.stream._queue.get(), timeout=1.0)
        assert event.event == "message"
        assert event.data["state"] == "completed"
        assert event.data["final"] is True
        assert event.data["message"]["parts"][0]["text"] == "Found 5 items!"
        assert event.data["message"]["parts"][1]["data"]["count"] == 5


class TestError:
    """Tests for error method."""

    @pytest.fixture
    def stream(self):
        return SSEStream()

    @pytest.fixture
    def ctx(self, stream):
        return PlanModeContext(stream=stream)

    @pytest.mark.asyncio
    async def test_error(self, ctx):
        await ctx.error("api_error", "Rate limited")

        assert ctx.phase == Phase.ERROR

    @pytest.mark.asyncio
    async def test_error_emits_event(self, ctx):
        await ctx.error("validation_error", "Invalid input", recoverable=True)

        event = await asyncio.wait_for(ctx.stream._queue.get(), timeout=1.0)
        assert event.event == "error"
        assert event.data["state"] == "failed"
        assert event.data["error_type"] == "validation_error"
        assert event.data["message"] == "Invalid input"
        assert event.data["recoverable"] is True


class TestGetSelectedItems:
    """Tests for get_selected_items method."""

    @pytest.fixture
    def stream(self):
        return SSEStream()

    @pytest.fixture
    def ctx(self, stream):
        return PlanModeContext(stream=stream)

    def test_get_selected_items(self, ctx):
        ctx.discovered_items = [
            DiscoveredItem(id="a", name="A"),
            DiscoveredItem(id="b", name="B"),
            DiscoveredItem(id="c", name="C"),
        ]
        ctx.selected_ids = ["a", "c"]

        selected = ctx.get_selected_items()

        assert len(selected) == 2
        assert selected[0].id == "a"
        assert selected[1].id == "c"

    def test_get_selected_items_empty(self, ctx):
        ctx.discovered_items = [DiscoveredItem(id="a", name="A")]
        ctx.selected_ids = []

        selected = ctx.get_selected_items()
        assert selected == []

    def test_get_selected_items_all(self, ctx):
        ctx.discovered_items = [
            DiscoveredItem(id="a", name="A"),
            DiscoveredItem(id="b", name="B"),
        ]
        ctx.selected_ids = ["a", "b"]

        selected = ctx.get_selected_items()
        assert len(selected) == 2


class TestFullWorkflow:
    """Integration tests for complete plan mode workflows."""

    @pytest.mark.asyncio
    async def test_complete_clarification_to_execution_workflow(self):
        stream = SSEStream()
        ctx = PlanModeContext(
            stream=stream,
            supported_phases=[Phase.CLARIFICATION, Phase.DISCOVERY, Phase.SELECTION, Phase.PREVIEW],
            agent_id="test-agent",
        )

        # Phase 1: Clarification
        clarification_id = await ctx.request_clarification(
            [
                Question(id="topic", type=QuestionType.FREE_TEXT, question="Topic?"),
                Question(
                    id="depth",
                    type=QuestionType.SINGLE_CHOICE,
                    question="Depth?",
                    options=[
                        QuestionOption(id="quick", label="Quick"),
                        QuestionOption(id="deep", label="Deep"),
                    ],
                ),
            ]
        )
        assert ctx.phase == Phase.CLARIFICATION

        # User responds
        ctx.set_clarification_response({"topic": "gaming", "depth": "deep"}, clarification_id)
        assert ctx.user_answers["topic"] == "gaming"

        # Phase 2: Discovery
        items = [
            DiscoveredItem(id="r/gaming", name="r/gaming", metadata={"subs": 35000000}),
            DiscoveredItem(id="r/pcgaming", name="r/pcgaming", metadata={"subs": 5000000}),
        ]
        await ctx.emit_discovery(items, "subreddits", message="Found 2 subreddits")
        assert ctx.phase == Phase.DISCOVERY
        assert len(ctx.discovered_items) == 2

        # Phase 3: Selection
        selection_id = await ctx.request_selection(min_select=1, max_select=5)
        assert ctx.phase == Phase.SELECTION

        # User selects
        ctx.set_selection_response(["r/gaming"], selection_id)
        assert ctx.selected_ids == ["r/gaming"]

        # Phase 4: Preview
        preview = SearchPlanPreview(
            user_intent="Research gaming subreddits",
            search_keywords=["gaming", "esports"],
            user_answers=ctx.user_answers,
        )
        plan_id = await ctx.emit_preview(preview)
        assert ctx.phase == Phase.PREVIEW

        # User approves
        ctx.set_plan_approval(True, plan_id)

        # Phase 5: Execution
        await ctx.start_execution("Starting research...")
        assert ctx.phase == Phase.EXECUTING

        # Complete
        await ctx.complete(
            {"items_researched": 1, "posts_analyzed": 100},
            message="Research complete!",
        )
        assert ctx.phase == Phase.COMPLETED

        # Verify selected items
        selected = ctx.get_selected_items()
        assert len(selected) == 1
        assert selected[0].id == "r/gaming"

    @pytest.mark.asyncio
    async def test_minimal_workflow(self):
        """Test minimal workflow skipping optional phases."""
        stream = SSEStream()
        ctx = PlanModeContext(stream=stream, supported_phases=[])

        # Skip directly to execution
        await ctx.start_execution("Running task...")
        assert ctx.phase == Phase.EXECUTING

        await ctx.complete({"result": "done"})
        assert ctx.phase == Phase.COMPLETED

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self):
        """Test workflow that encounters and recovers from error."""
        stream = SSEStream()
        ctx = PlanModeContext(
            stream=stream,
            supported_phases=[Phase.CLARIFICATION],
        )

        # Start clarification
        await ctx.request_clarification(
            [Question(id="q", type=QuestionType.FREE_TEXT, question="Q?")]
        )

        # Error occurs
        await ctx.error("api_error", "External service unavailable", recoverable=True)
        assert ctx.phase == Phase.ERROR

        # Can restart from idle (per transition rules)
        ctx._transition_to(Phase.IDLE)
        assert ctx.phase == Phase.IDLE

        # Retry
        await ctx.request_clarification(
            [Question(id="q", type=QuestionType.FREE_TEXT, question="Q?")]
        )
        assert ctx.phase == Phase.CLARIFICATION
