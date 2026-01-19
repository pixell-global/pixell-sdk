"""Unit tests for lite mode in ToolBasedAgent.

These tests verify that ToolBasedAgent._emit_response correctly handles
lite_mode_enabled by auto-handling interactive responses (Discovery,
Clarification, Preview) without waiting for user input.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from pixell.sdk.plan_mode.agent import (
    AgentState,
    Discovery,
    Clarification,
    Preview,
    Result,
    Error,
)
from pixell.sdk.tool_mode.agent import ToolBasedAgent, Tool, ToolCall


class MockToolBasedAgent(ToolBasedAgent):
    """Mock ToolBasedAgent for testing."""

    def __init__(self):
        # Skip parent __init__ to avoid server setup
        self._current_ctx = None
        self._current_workflow_id = "test-workflow-123"
        self._registered_tools = {}
        self._server = MagicMock()

        # Create a mock state
        self._mock_state = AgentState()

    @property
    def state(self) -> AgentState:
        return self._mock_state

    async def select_tools(self, query: str, tools: list[Tool]) -> list[ToolCall]:
        return []

    async def on_selection(self, selected: list[str]):
        return Preview(
            intent=f"Execute with {len(selected)} items",
            plan={"targets": selected},
        )

    async def on_execute(self):
        return Result(answer="Execution complete", data={"success": True})

    async def on_clarification(self, answers: dict):
        return Result(answer="Got answers", data=answers)


class TestToolBasedAgentLiteModeDiscovery:
    """Test lite mode handling of Discovery responses."""

    @pytest.fixture
    def agent(self):
        return MockToolBasedAgent()

    @pytest.fixture
    def mock_plan_context(self):
        plan = MagicMock()
        plan.emit_discovery = AsyncMock()
        plan.request_selection = AsyncMock(return_value="sel-123")
        plan.start_execution = AsyncMock()
        plan.complete = AsyncMock()
        plan.error = AsyncMock()
        return plan

    @pytest.mark.asyncio
    async def test_lite_mode_auto_selects_discovery_items(
        self, agent, mock_plan_context
    ):
        """In lite mode, Discovery should auto-select items and continue."""
        agent._mock_state.metadata = {"lite_mode_enabled": True}

        discovery = Discovery(
            items=[
                {"id": "item1", "name": "Item 1"},
                {"id": "item2", "name": "Item 2"},
                {"id": "item3", "name": "Item 3"},
            ],
            message="Select items",
            item_type="items",
        )

        await agent._emit_response(mock_plan_context, discovery)

        # Should NOT emit discovery or request selection
        mock_plan_context.emit_discovery.assert_not_called()
        mock_plan_context.request_selection.assert_not_called()

        # Should have auto-selected items
        assert len(agent.state.selected) == 3
        assert "item1" in agent.state.selected
        assert "item2" in agent.state.selected
        assert "item3" in agent.state.selected

    @pytest.mark.asyncio
    async def test_lite_mode_limits_auto_selection_to_5(
        self, agent, mock_plan_context
    ):
        """In lite mode, auto-selection should limit to 5 items."""
        agent._mock_state.metadata = {"lite_mode_enabled": True}

        discovery = Discovery(
            items=[
                {"id": f"item{i}", "name": f"Item {i}"}
                for i in range(10)  # 10 items
            ],
            message="Select items",
            item_type="items",
        )

        await agent._emit_response(mock_plan_context, discovery)

        # Should only select top 5
        assert len(agent.state.selected) == 5
        assert "item0" in agent.state.selected
        assert "item4" in agent.state.selected
        assert "item5" not in agent.state.selected  # 6th should be excluded

    @pytest.mark.asyncio
    async def test_normal_mode_emits_discovery_events(
        self, agent, mock_plan_context
    ):
        """Without lite mode, Discovery should emit events for user interaction."""
        agent._mock_state.metadata = {}  # No lite mode

        discovery = Discovery(
            items=[{"id": "item1", "name": "Item 1"}],
            message="Select items",
            item_type="items",
        )

        await agent._emit_response(mock_plan_context, discovery)

        # Should emit discovery and request selection
        mock_plan_context.emit_discovery.assert_called_once()
        mock_plan_context.request_selection.assert_called_once()


class TestToolBasedAgentLiteModeClarification:
    """Test lite mode handling of Clarification responses."""

    @pytest.fixture
    def agent(self):
        return MockToolBasedAgent()

    @pytest.fixture
    def mock_plan_context(self):
        plan = MagicMock()
        plan.request_clarification = AsyncMock(return_value="clar-123")
        plan.complete = AsyncMock()
        return plan

    @pytest.mark.asyncio
    async def test_lite_mode_auto_answers_clarification(
        self, agent, mock_plan_context
    ):
        """In lite mode, Clarification should auto-answer with defaults."""
        agent._mock_state.metadata = {"lite_mode_enabled": True}

        clarification = Clarification(
            question="What topic?",
            header="Topic",
            options=[
                {"id": "gaming", "label": "Gaming"},
                {"id": "fitness", "label": "Fitness"},
            ],
        )

        await agent._emit_response(mock_plan_context, clarification)

        # Should NOT request clarification from user
        mock_plan_context.request_clarification.assert_not_called()

        # Should have completed (after auto-answering)
        mock_plan_context.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_normal_mode_requests_clarification(
        self, agent, mock_plan_context
    ):
        """Without lite mode, Clarification should request user input."""
        agent._mock_state.metadata = {}  # No lite mode

        clarification = Clarification(
            question="What topic?",
            header="Topic",
        )

        await agent._emit_response(mock_plan_context, clarification)

        # Should request clarification
        mock_plan_context.request_clarification.assert_called_once()


class TestToolBasedAgentLiteModePreview:
    """Test lite mode handling of Preview responses."""

    @pytest.fixture
    def agent(self):
        return MockToolBasedAgent()

    @pytest.fixture
    def mock_plan_context(self):
        plan = MagicMock()
        plan.emit_preview = AsyncMock(return_value="plan-123")
        plan.start_execution = AsyncMock()
        plan.complete = AsyncMock()
        return plan

    @pytest.mark.asyncio
    async def test_lite_mode_auto_approves_preview(
        self, agent, mock_plan_context
    ):
        """In lite mode, Preview should auto-approve and execute."""
        agent._mock_state.metadata = {"lite_mode_enabled": True}

        preview = Preview(
            intent="Search subreddits",
            plan={"targets": ["r/gaming"], "keywords": ["news"]},
        )

        await agent._emit_response(mock_plan_context, preview)

        # Should NOT emit preview for user approval
        mock_plan_context.emit_preview.assert_not_called()

        # Should start execution and complete
        mock_plan_context.start_execution.assert_called_once()
        mock_plan_context.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_normal_mode_emits_preview(
        self, agent, mock_plan_context
    ):
        """Without lite mode, Preview should emit for user approval."""
        agent._mock_state.metadata = {}  # No lite mode

        preview = Preview(
            intent="Search subreddits",
            plan={"targets": ["r/gaming"]},
        )

        await agent._emit_response(mock_plan_context, preview)

        # Should emit preview
        mock_plan_context.emit_preview.assert_called_once()


class TestGetDefaultClarificationAnswers:
    """Test the _get_default_clarification_answers helper method."""

    @pytest.fixture
    def agent(self):
        return MockToolBasedAgent()

    def test_selects_first_option_when_available(self, agent):
        """Should select first option for each question."""
        clarification = Clarification(
            question="What topic?",
            header="Topic",
            options=[
                {"id": "gaming", "label": "Gaming"},
                {"id": "fitness", "label": "Fitness"},
            ],
        )

        answers = agent._get_default_clarification_answers(clarification)

        assert answers.get("q1") == "gaming"  # First option

    def test_uses_default_for_free_text(self, agent):
        """Should use 'default' for free text questions."""
        clarification = Clarification(
            question="Describe your goal",
            header="Goal",
            # No options = free text
        )

        answers = agent._get_default_clarification_answers(clarification)

        assert answers.get("q1") == "default"


class TestLiteModeFullWorkflow:
    """Test the full workflow through Discovery → Preview → Result."""

    @pytest.fixture
    def agent(self):
        agent = MockToolBasedAgent()
        # Track execution order
        agent.execution_order = []
        original_on_selection = agent.on_selection
        original_on_execute = agent.on_execute

        async def tracked_on_selection(selected):
            agent.execution_order.append(("on_selection", selected))
            return await original_on_selection(selected)

        async def tracked_on_execute():
            agent.execution_order.append(("on_execute",))
            return await original_on_execute()

        agent.on_selection = tracked_on_selection
        agent.on_execute = tracked_on_execute
        return agent

    @pytest.fixture
    def mock_plan_context(self):
        plan = MagicMock()
        plan.start_execution = AsyncMock()
        plan.complete = AsyncMock()
        return plan

    @pytest.mark.asyncio
    async def test_lite_mode_flows_discovery_to_result(
        self, agent, mock_plan_context
    ):
        """Lite mode should auto-flow: Discovery → on_selection → Preview → on_execute → Result."""
        agent._mock_state.metadata = {"lite_mode_enabled": True}

        discovery = Discovery(
            items=[
                {"id": "r/gaming", "name": "r/gaming"},
                {"id": "r/pcgaming", "name": "r/pcgaming"},
            ],
            message="Select subreddits",
            item_type="subreddits",
        )

        await agent._emit_response(mock_plan_context, discovery)

        # Verify execution order
        assert len(agent.execution_order) >= 2
        assert agent.execution_order[0][0] == "on_selection"
        assert agent.execution_order[1][0] == "on_execute"

        # Verify completion
        mock_plan_context.complete.assert_called_once()
