"""Tests for Plan Mode Events."""

import pytest
import uuid
from pixell.sdk.plan_mode.events import (
    QuestionType,
    QuestionOption,
    Question,
    ClarificationNeeded,
    ClarificationResponse,
    DiscoveredItem,
    DiscoveryResult,
    SelectionRequired,
    SelectionResponse,
    PlanStep,
    PlanProposed,
    PlanApproval,
    SearchPlanPreview,
)


class TestQuestionType:
    """Tests for QuestionType enum."""

    def test_all_types_exist(self):
        assert QuestionType.SINGLE_CHOICE.value == "single_choice"
        assert QuestionType.MULTIPLE_CHOICE.value == "multiple_choice"
        assert QuestionType.FREE_TEXT.value == "free_text"
        assert QuestionType.YES_NO.value == "yes_no"
        assert QuestionType.NUMERIC_RANGE.value == "numeric_range"

    def test_type_is_string_enum(self):
        assert QuestionType.SINGLE_CHOICE == "single_choice"


class TestQuestionOption:
    """Tests for QuestionOption."""

    def test_create_option(self):
        opt = QuestionOption(id="opt-1", label="Option 1")
        assert opt.id == "opt-1"
        assert opt.label == "Option 1"
        assert opt.description is None

    def test_create_with_description(self):
        opt = QuestionOption(id="opt-2", label="Option 2", description="Details here")
        assert opt.description == "Details here"

    def test_to_dict_minimal(self):
        opt = QuestionOption(id="a", label="A")
        result = opt.to_dict()
        assert result == {"id": "a", "label": "A"}

    def test_to_dict_with_description(self):
        opt = QuestionOption(id="b", label="B", description="B desc")
        result = opt.to_dict()
        assert result == {"id": "b", "label": "B", "description": "B desc"}


class TestQuestion:
    """Tests for Question."""

    def test_create_free_text_question(self):
        q = Question(
            id="topic",
            type=QuestionType.FREE_TEXT,
            question="What topic?",
        )
        assert q.id == "topic"
        assert q.type == QuestionType.FREE_TEXT
        assert q.question == "What topic?"

    def test_create_with_all_fields(self):
        q = Question(
            id="depth",
            type=QuestionType.SINGLE_CHOICE,
            question="How deep?",
            header="Depth",
            options=[
                QuestionOption(id="quick", label="Quick"),
                QuestionOption(id="deep", label="Deep"),
            ],
            allow_free_text=True,
            default="quick",
            placeholder="Select depth",
        )
        assert q.header == "Depth"
        assert len(q.options) == 2
        assert q.allow_free_text is True
        assert q.default == "quick"
        assert q.placeholder == "Select depth"

    def test_create_numeric_range_question(self):
        q = Question(
            id="followers",
            type=QuestionType.NUMERIC_RANGE,
            question="Min followers?",
            min=100,
            max=1000000,
            step=100,
        )
        assert q.min == 100
        assert q.max == 1000000
        assert q.step == 100

    def test_to_dict_minimal(self):
        q = Question(
            id="test",
            type=QuestionType.FREE_TEXT,
            question="Test question?",
        )
        result = q.to_dict()
        assert result["questionId"] == "test"
        assert result["questionType"] == "free_text"
        assert result["question"] == "Test question?"
        assert result["allowFreeText"] is False

    def test_to_dict_with_options(self):
        q = Question(
            id="choice",
            type=QuestionType.SINGLE_CHOICE,
            question="Pick one?",
            options=[
                QuestionOption(id="a", label="A"),
                QuestionOption(id="b", label="B"),
            ],
        )
        result = q.to_dict()
        assert len(result["options"]) == 2
        assert result["options"][0]["id"] == "a"

    def test_to_dict_with_all_fields(self):
        q = Question(
            id="full",
            type=QuestionType.NUMERIC_RANGE,
            question="Select range?",
            header="Range",
            default="500",
            placeholder="Enter value",
            min=0,
            max=1000,
            step=10,
        )
        result = q.to_dict()
        assert result["header"] == "Range"
        assert result["default"] == "500"
        assert result["placeholder"] == "Enter value"
        assert result["min"] == 0
        assert result["max"] == 1000
        assert result["step"] == 10


class TestClarificationNeeded:
    """Tests for ClarificationNeeded."""

    def test_create_clarification(self):
        questions = [
            Question(id="q1", type=QuestionType.FREE_TEXT, question="Q1?"),
            Question(id="q2", type=QuestionType.YES_NO, question="Q2?"),
        ]
        clarify = ClarificationNeeded(questions=questions, agent_id="test-agent")
        assert len(clarify.questions) == 2
        assert clarify.agent_id == "test-agent"
        assert clarify.clarification_id is not None
        # Should be valid UUID
        uuid.UUID(clarify.clarification_id)

    def test_auto_generated_id(self):
        c1 = ClarificationNeeded(questions=[])
        c2 = ClarificationNeeded(questions=[])
        assert c1.clarification_id != c2.clarification_id

    def test_to_dict(self):
        questions = [
            Question(id="topic", type=QuestionType.FREE_TEXT, question="Topic?"),
        ]
        clarify = ClarificationNeeded(
            questions=questions,
            agent_id="agent-123",
            context="Need more info",
            message="Please answer these questions",
            timeout_ms=60000,
        )
        result = clarify.to_dict()
        assert result["type"] == "clarification_needed"
        assert result["clarificationId"] == clarify.clarification_id
        assert result["agentId"] == "agent-123"
        assert len(result["questions"]) == 1
        assert result["context"] == "Need more info"
        assert result["message"] == "Please answer these questions"
        assert result["timeoutMs"] == 60000


class TestClarificationResponse:
    """Tests for ClarificationResponse."""

    def test_from_dict(self):
        data = {
            "clarificationId": "c-123",
            "answers": {"topic": "gaming", "depth": "moderate"},
        }
        response = ClarificationResponse.from_dict(data)
        assert response.clarification_id == "c-123"
        assert response.answers["topic"] == "gaming"
        assert response.answers["depth"] == "moderate"

    def test_from_dict_empty_answers(self):
        data = {"clarificationId": "c-456", "answers": {}}
        response = ClarificationResponse.from_dict(data)
        assert response.answers == {}

    def test_from_dict_missing_fields(self):
        response = ClarificationResponse.from_dict({})
        assert response.clarification_id == ""
        assert response.answers == {}


class TestDiscoveredItem:
    """Tests for DiscoveredItem."""

    def test_create_minimal(self):
        item = DiscoveredItem(id="r/gaming", name="r/gaming")
        assert item.id == "r/gaming"
        assert item.name == "r/gaming"
        assert item.description is None
        assert item.metadata is None

    def test_create_full(self):
        item = DiscoveredItem(
            id="r/gaming",
            name="r/gaming",
            description="Gaming subreddit",
            metadata={"subscribers": 35000000, "posts_per_day": 500},
        )
        assert item.description == "Gaming subreddit"
        assert item.metadata["subscribers"] == 35000000

    def test_to_dict_minimal(self):
        item = DiscoveredItem(id="x", name="X")
        result = item.to_dict()
        assert result == {"id": "x", "name": "X"}

    def test_to_dict_full(self):
        item = DiscoveredItem(
            id="channel-1",
            name="Channel 1",
            description="A channel",
            metadata={"followers": 10000},
        )
        result = item.to_dict()
        assert result["id"] == "channel-1"
        assert result["name"] == "Channel 1"
        assert result["description"] == "A channel"
        assert result["metadata"]["followers"] == 10000


class TestDiscoveryResult:
    """Tests for DiscoveryResult."""

    def test_create(self):
        items = [
            DiscoveredItem(id="a", name="A"),
            DiscoveredItem(id="b", name="B"),
        ]
        result = DiscoveryResult(discovery_type="subreddits", items=items)
        assert result.discovery_type == "subreddits"
        assert len(result.items) == 2
        assert result.discovery_id is not None

    def test_auto_generated_id(self):
        r1 = DiscoveryResult(discovery_type="test", items=[])
        r2 = DiscoveryResult(discovery_type="test", items=[])
        assert r1.discovery_id != r2.discovery_id

    def test_to_dict(self):
        items = [DiscoveredItem(id="x", name="X")]
        result = DiscoveryResult(
            discovery_type="hashtags",
            items=items,
            message="Found 1 result",
        )
        output = result.to_dict()
        assert output["type"] == "discovery_result"
        assert output["discoveryType"] == "hashtags"
        assert len(output["items"]) == 1
        assert output["message"] == "Found 1 result"


class TestSelectionRequired:
    """Tests for SelectionRequired."""

    def test_create_minimal(self):
        items = [DiscoveredItem(id="a", name="A")]
        sel = SelectionRequired(items=items)
        assert len(sel.items) == 1
        assert sel.selection_id is not None
        assert sel.min_select == 1
        assert sel.max_select is None

    def test_create_with_constraints(self):
        items = [
            DiscoveredItem(id="a", name="A"),
            DiscoveredItem(id="b", name="B"),
            DiscoveredItem(id="c", name="C"),
        ]
        sel = SelectionRequired(
            items=items,
            discovery_type="channels",
            min_select=1,
            max_select=5,
            message="Select channels to monitor",
        )
        assert sel.discovery_type == "channels"
        assert sel.min_select == 1
        assert sel.max_select == 5
        assert sel.message == "Select channels to monitor"

    def test_to_dict(self):
        items = [DiscoveredItem(id="x", name="X")]
        sel = SelectionRequired(
            items=items,
            discovery_type="subreddits",
            min_select=2,
            max_select=10,
            message="Pick some",
        )
        result = sel.to_dict()
        assert result["type"] == "selection_required"
        assert result["selectionId"] == sel.selection_id
        assert result["discoveryType"] == "subreddits"
        assert result["minSelect"] == 2
        assert result["maxSelect"] == 10
        assert result["message"] == "Pick some"


class TestSelectionResponse:
    """Tests for SelectionResponse."""

    def test_from_dict(self):
        data = {
            "selectionId": "sel-123",
            "selectedIds": ["item-1", "item-2", "item-3"],
        }
        response = SelectionResponse.from_dict(data)
        assert response.selection_id == "sel-123"
        assert len(response.selected_ids) == 3
        assert "item-2" in response.selected_ids

    def test_from_dict_empty(self):
        response = SelectionResponse.from_dict({})
        assert response.selection_id == ""
        assert response.selected_ids == []


class TestPlanStep:
    """Tests for PlanStep."""

    def test_create_minimal(self):
        step = PlanStep(id="step-1", description="Do something")
        assert step.id == "step-1"
        assert step.description == "Do something"
        assert step.status == "pending"

    def test_create_full(self):
        step = PlanStep(
            id="step-2",
            description="Search for content",
            status="in_progress",
            estimated_duration="2 minutes",
            tool_hint="search_api",
            dependencies=["step-1"],
        )
        assert step.estimated_duration == "2 minutes"
        assert step.tool_hint == "search_api"
        assert step.dependencies == ["step-1"]

    def test_to_dict_minimal(self):
        step = PlanStep(id="s1", description="Step 1")
        result = step.to_dict()
        assert result == {"id": "s1", "description": "Step 1", "status": "pending"}

    def test_to_dict_full(self):
        step = PlanStep(
            id="s2",
            description="Step 2",
            status="completed",
            estimated_duration="1 minute",
            tool_hint="api_call",
            dependencies=["s1"],
        )
        result = step.to_dict()
        assert result["estimatedDuration"] == "1 minute"
        assert result["toolHint"] == "api_call"
        assert result["dependencies"] == ["s1"]


class TestPlanProposed:
    """Tests for PlanProposed."""

    def test_create_minimal(self):
        steps = [PlanStep(id="s1", description="Step 1")]
        plan = PlanProposed(title="Test Plan", steps=steps)
        assert plan.title == "Test Plan"
        assert len(plan.steps) == 1
        assert plan.plan_id is not None
        assert plan.auto_start_after_ms == 5000
        assert plan.requires_approval is False

    def test_create_with_approval(self):
        steps = [
            PlanStep(id="s1", description="Collect data"),
            PlanStep(id="s2", description="Analyze data", dependencies=["s1"]),
        ]
        plan = PlanProposed(
            title="Data Analysis Plan",
            steps=steps,
            agent_id="analyst-agent",
            requires_approval=True,
            auto_start_after_ms=None,
            message="Please review this plan",
        )
        assert plan.requires_approval is True
        assert plan.auto_start_after_ms is None
        assert plan.message == "Please review this plan"

    def test_to_dict(self):
        steps = [PlanStep(id="s1", description="Do it")]
        plan = PlanProposed(
            title="Simple Plan",
            steps=steps,
            agent_id="agent-1",
            requires_approval=True,
            auto_start_after_ms=10000,
            message="Review please",
        )
        result = plan.to_dict()
        assert result["type"] == "plan_proposed"
        assert result["planId"] == plan.plan_id
        assert result["agentId"] == "agent-1"
        assert result["title"] == "Simple Plan"
        assert len(result["steps"]) == 1
        assert result["requiresApproval"] is True
        assert result["autoStartAfterMs"] == 10000
        assert result["message"] == "Review please"


class TestPlanApproval:
    """Tests for PlanApproval."""

    def test_from_dict_approved(self):
        data = {"planId": "plan-123", "approved": True}
        approval = PlanApproval.from_dict(data)
        assert approval.plan_id == "plan-123"
        assert approval.approved is True
        assert approval.modifications is None

    def test_from_dict_rejected(self):
        data = {"planId": "plan-456", "approved": False}
        approval = PlanApproval.from_dict(data)
        assert approval.approved is False

    def test_from_dict_with_modifications(self):
        data = {
            "planId": "plan-789",
            "approved": True,
            "modifications": {"keywords": ["new", "modified"]},
        }
        approval = PlanApproval.from_dict(data)
        assert approval.modifications["keywords"] == ["new", "modified"]


class TestSearchPlanPreview:
    """Tests for SearchPlanPreview."""

    def test_create_minimal(self):
        preview = SearchPlanPreview(
            user_intent="Find gaming content",
            search_keywords=["gaming", "esports"],
        )
        assert preview.user_intent == "Find gaming content"
        assert preview.search_keywords == ["gaming", "esports"]
        assert preview.hashtags == []
        assert preview.follower_min == 1000
        assert preview.follower_max == 100000
        assert preview.min_engagement == 0.03
        assert preview.plan_id is not None

    def test_create_full(self):
        preview = SearchPlanPreview(
            user_intent="Find fitness influencers in Korea",
            search_keywords=["fitness", "workout"],
            hashtags=["#fitness", "#workout"],
            follower_min=5000,
            follower_max=50000,
            location="Korea",
            min_engagement=0.05,
            agent_id="tik-agent",
            agent_url="http://localhost:9998",
            user_answers={"topic": "fitness", "region": "Korea"},
            message="Search plan for Korean fitness content",
        )
        assert preview.location == "Korea"
        assert preview.follower_min == 5000
        assert preview.agent_url == "http://localhost:9998"
        assert preview.user_answers["region"] == "Korea"

    def test_auto_generated_id(self):
        p1 = SearchPlanPreview(user_intent="A", search_keywords=["a"])
        p2 = SearchPlanPreview(user_intent="B", search_keywords=["b"])
        assert p1.plan_id != p2.plan_id

    def test_to_dict(self):
        preview = SearchPlanPreview(
            user_intent="Find tech content",
            search_keywords=["tech", "coding"],
            hashtags=["#tech", "#coding"],
            follower_min=10000,
            follower_max=500000,
            location="US",
            min_engagement=0.04,
            agent_id="search-agent",
            agent_url="http://agent.local",
            user_answers={"niche": "tech"},
            message="Here's the search plan",
        )
        result = preview.to_dict()
        assert result["type"] == "search_plan"
        assert result["planId"] == preview.plan_id
        assert result["agentId"] == "search-agent"
        assert result["agentUrl"] == "http://agent.local"
        assert result["userIntent"] == "Find tech content"
        assert result["userAnswers"] == {"niche": "tech"}
        assert result["searchKeywords"] == ["tech", "coding"]
        assert result["hashtags"] == ["#tech", "#coding"]
        assert result["followerMin"] == 10000
        assert result["followerMax"] == 500000
        assert result["location"] == "US"
        assert result["minEngagement"] == 0.04
        assert result["message"] == "Here's the search plan"


class TestEventSerialization:
    """Integration tests for event serialization roundtrips."""

    def test_complex_clarification_serialization(self):
        """Test complex clarification with all question types."""
        questions = [
            Question(
                id="niche",
                type=QuestionType.FREE_TEXT,
                question="What niche?",
                header="Niche",
                placeholder="e.g., gaming, fitness",
            ),
            Question(
                id="depth",
                type=QuestionType.SINGLE_CHOICE,
                question="How deep?",
                header="Depth",
                options=[
                    QuestionOption(id="quick", label="Quick", description="Fast scan"),
                    QuestionOption(id="deep", label="Deep", description="Thorough"),
                ],
            ),
            Question(
                id="features",
                type=QuestionType.MULTIPLE_CHOICE,
                question="Which features?",
                header="Features",
                options=[
                    QuestionOption(id="analytics", label="Analytics"),
                    QuestionOption(id="export", label="Export"),
                ],
            ),
            Question(
                id="followers",
                type=QuestionType.NUMERIC_RANGE,
                question="Min followers?",
                min=1000,
                max=1000000,
                step=1000,
            ),
        ]

        clarification = ClarificationNeeded(
            questions=questions,
            agent_id="complex-agent",
            context="Gathering requirements",
            message="Please answer these questions to continue",
        )

        result = clarification.to_dict()

        # Verify structure
        assert len(result["questions"]) == 4
        assert result["questions"][0]["questionType"] == "free_text"
        assert result["questions"][1]["questionType"] == "single_choice"
        assert len(result["questions"][1]["options"]) == 2
        assert result["questions"][2]["questionType"] == "multiple_choice"
        assert result["questions"][3]["questionType"] == "numeric_range"
        assert result["questions"][3]["min"] == 1000

    def test_discovery_to_selection_flow(self):
        """Test discovery items flowing to selection."""
        # Create discovered items
        items = [
            DiscoveredItem(
                id="r/gaming",
                name="r/gaming",
                description="Gaming discussions",
                metadata={"subscribers": 35000000},
            ),
            DiscoveredItem(
                id="r/pcgaming",
                name="r/pcgaming",
                description="PC Gaming",
                metadata={"subscribers": 5000000},
            ),
        ]

        # Create discovery result
        discovery = DiscoveryResult(
            discovery_type="subreddits",
            items=items,
            message="Found 2 subreddits",
        )

        # Serialize and verify
        discovery_dict = discovery.to_dict()
        assert len(discovery_dict["items"]) == 2
        assert discovery_dict["items"][0]["metadata"]["subscribers"] == 35000000

        # Use same items for selection
        selection = SelectionRequired(
            items=items,
            discovery_type="subreddits",
            min_select=1,
            max_select=5,
            message="Select subreddits to monitor",
        )

        selection_dict = selection.to_dict()
        assert selection_dict["items"] == discovery_dict["items"]
