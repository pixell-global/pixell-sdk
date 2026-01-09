"""Unit tests for lite mode in PlanModeAgent."""

from pixell.sdk.plan_mode.agent import (
    AgentState,
    LiteModeConfig,
    Clarification,
    Discovery,
    Preview,
    Result,
)


class TestLiteModeConfig:
    """Tests for LiteModeConfig dataclass."""

    def test_default_config(self):
        """Default lite mode config has max_select=5 and auto_approve_plan=True."""
        config = LiteModeConfig()
        assert config.max_select == 5
        assert config.auto_approve_plan is True

    def test_custom_config(self):
        """LiteModeConfig can be customized."""
        config = LiteModeConfig(max_select=10, auto_approve_plan=False)
        assert config.max_select == 10
        assert config.auto_approve_plan is False


class TestAgentStateMetadata:
    """Tests for metadata storage in AgentState."""

    def test_metadata_stored_in_state(self):
        """AgentState should store request metadata."""
        state = AgentState()
        state.metadata = {"lite_mode_enabled": True, "user_id": "u123"}
        assert state.metadata.get("lite_mode_enabled") is True
        assert state.metadata.get("user_id") == "u123"

    def test_metadata_default_is_empty_dict(self):
        """AgentState metadata defaults to empty dict."""
        state = AgentState()
        assert state.metadata == {}

    def test_clear_resets_metadata(self):
        """AgentState.clear() should reset metadata to empty dict."""
        state = AgentState()
        state.metadata = {"lite_mode_enabled": True}
        state.query = "test query"
        state.context = {"key": "value"}

        state.clear()

        assert state.metadata == {}
        assert state.query == ""
        assert state.context == {}


class TestClarificationResponse:
    """Tests for Clarification response type."""

    def test_clarification_with_options(self):
        """Clarification can have options."""
        clarification = Clarification(
            question="What topic?",
            options=[
                {"id": "gaming", "label": "Gaming"},
                {"id": "fitness", "label": "Fitness"},
            ],
            header="Topic",
        )
        assert clarification.question == "What topic?"
        assert len(clarification.options) == 2
        assert clarification.options[0]["id"] == "gaming"

    def test_clarification_without_options(self):
        """Clarification can be free text (no options)."""
        clarification = Clarification(
            question="Describe your research goal",
            header="Goal",
        )
        assert clarification.question == "Describe your research goal"
        assert clarification.options is None


class TestDiscoveryResponse:
    """Tests for Discovery response type."""

    def test_discovery_with_items(self):
        """Discovery should contain items list."""
        discovery = Discovery(
            items=[
                {"id": "r/gaming", "name": "r/gaming", "description": "Gaming"},
                {"id": "r/pcgaming", "name": "r/pcgaming", "description": "PC Gaming"},
            ],
            message="Found 2 subreddits",
            item_type="subreddits",
            min_select=1,
            max_select=5,
        )
        assert len(discovery.items) == 2
        assert discovery.item_type == "subreddits"
        assert discovery.min_select == 1
        assert discovery.max_select == 5


class TestPreviewResponse:
    """Tests for Preview response type."""

    def test_preview_with_plan(self):
        """Preview should contain intent and plan."""
        preview = Preview(
            intent="Search gaming subreddits",
            plan={
                "targets": ["r/gaming", "r/pcgaming"],
                "keywords": ["discussion", "news"],
            },
            message="Ready to search",
        )
        assert preview.intent == "Search gaming subreddits"
        assert preview.plan["targets"] == ["r/gaming", "r/pcgaming"]


class TestResultResponse:
    """Tests for Result response type."""

    def test_result_with_data(self):
        """Result should contain answer and optional data."""
        result = Result(
            answer="Research completed successfully",
            data={
                "posts_analyzed": 150,
                "report_url": "https://example.com/report",
            },
        )
        assert result.answer == "Research completed successfully"
        assert result.data["posts_analyzed"] == 150
