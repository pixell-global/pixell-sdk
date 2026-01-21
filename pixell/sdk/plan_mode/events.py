"""Plan Mode Events - Event types for plan mode communication."""

from enum import Enum
from typing import Any, Optional
from dataclasses import dataclass, field
import uuid


class QuestionType(str, Enum):
    """Types of questions for clarification."""

    SINGLE_CHOICE = "single_choice"  # Radio buttons
    MULTIPLE_CHOICE = "multiple_choice"  # Checkboxes
    FREE_TEXT = "free_text"  # Text input
    YES_NO = "yes_no"  # Yes/No confirmation
    NUMERIC_RANGE = "numeric_range"  # Slider or min/max


@dataclass
class QuestionOption:
    """Option for choice-based questions."""

    id: str
    label: str
    description: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        result = {"id": self.id, "label": self.label}
        if self.description:
            result["description"] = self.description
        return result


@dataclass
class Question:
    """Individual clarification question."""

    id: str
    type: QuestionType
    question: str
    header: Optional[str] = None  # Short label (max 12 chars)
    options: Optional[list[QuestionOption]] = None
    allow_free_text: bool = False
    default: Optional[str] = None
    placeholder: Optional[str] = None
    # For numeric_range type
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None
    # Structured preview data (e.g., change tables)
    preview: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "questionId": self.id,
            "questionType": self.type.value,
            "question": self.question,
            "allowFreeText": self.allow_free_text,
        }
        if self.header:
            result["header"] = self.header
        if self.options:
            result["options"] = [opt.to_dict() for opt in self.options]
        if self.default:
            result["default"] = self.default
        if self.placeholder:
            result["placeholder"] = self.placeholder
        if self.min is not None:
            result["min"] = self.min
        if self.max is not None:
            result["max"] = self.max
        if self.step is not None:
            result["step"] = self.step
        if self.preview:
            result["preview"] = self.preview
        return result


@dataclass
class ClarificationNeeded:
    """Agent request for user clarification."""

    questions: list[Question]
    agent_id: str = ""
    clarification_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    context: Optional[str] = None
    message: Optional[str] = None
    timeout_ms: int = 300000  # 5 minutes

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "type": "clarification_needed",
            "clarificationId": self.clarification_id,
            "agentId": self.agent_id,
            "questions": [q.to_dict() for q in self.questions],
            "timeoutMs": self.timeout_ms,
        }
        if self.context:
            result["context"] = self.context
        if self.message:
            result["message"] = self.message
        return result


@dataclass
class ClarificationResponse:
    """User response to clarification request."""

    clarification_id: str
    answers: dict[str, Any]  # question_id -> value

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClarificationResponse":
        return cls(
            clarification_id=data.get("clarificationId", ""),
            answers=data.get("answers", {}),
        )


@dataclass
class DiscoveredItem:
    """Item discovered during discovery phase."""

    id: str
    name: str
    description: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
        }
        if self.description:
            result["description"] = self.description
        if self.metadata:
            result["metadata"] = self.metadata
        return result


@dataclass
class DiscoveryResult:
    """Result of discovery phase."""

    discovery_type: str  # "subreddits", "hashtags", "channels", etc.
    items: list[DiscoveredItem]
    discovery_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "discovery_result",
            "discoveryId": self.discovery_id,
            "discoveryType": self.discovery_type,
            "items": [item.to_dict() for item in self.items],
            "message": self.message,
        }


@dataclass
class SelectionRequired:
    """Agent request for user to select from discovered items."""

    items: list[DiscoveredItem]
    selection_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    discovery_type: str = ""
    min_select: int = 1
    max_select: Optional[int] = None
    message: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "type": "selection_required",
            "selectionId": self.selection_id,
            "discoveryType": self.discovery_type,
            "items": [item.to_dict() for item in self.items],
            "minSelect": self.min_select,
        }
        if self.max_select:
            result["maxSelect"] = self.max_select
        if self.message:
            result["message"] = self.message
        return result


@dataclass
class SelectionResponse:
    """User response to selection request."""

    selection_id: str
    selected_ids: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SelectionResponse":
        return cls(
            selection_id=data.get("selectionId", ""),
            selected_ids=data.get("selectedIds", []),
        )


@dataclass
class PlanStep:
    """Step in a proposed plan."""

    id: str
    description: str
    status: str = "pending"  # pending, in_progress, completed, failed, skipped
    estimated_duration: Optional[str] = None
    tool_hint: Optional[str] = None
    dependencies: Optional[list[str]] = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id,
            "description": self.description,
            "status": self.status,
        }
        if self.estimated_duration:
            result["estimatedDuration"] = self.estimated_duration
        if self.tool_hint:
            result["toolHint"] = self.tool_hint
        if self.dependencies:
            result["dependencies"] = self.dependencies
        return result


@dataclass
class PlanProposed:
    """Agent-proposed execution plan."""

    title: str
    steps: list[PlanStep]
    agent_id: str = ""
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    auto_start_after_ms: Optional[int] = 5000
    requires_approval: bool = False
    message: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "type": "plan_proposed",
            "planId": self.plan_id,
            "agentId": self.agent_id,
            "title": self.title,
            "steps": [step.to_dict() for step in self.steps],
            "requiresApproval": self.requires_approval,
        }
        if self.auto_start_after_ms is not None:
            result["autoStartAfterMs"] = self.auto_start_after_ms
        if self.message:
            result["message"] = self.message
        return result


@dataclass
class PlanApproval:
    """User approval/rejection of proposed plan."""

    plan_id: str
    approved: bool
    modifications: Optional[dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlanApproval":
        return cls(
            plan_id=data.get("planId", ""),
            approved=data.get("approved", False),
            modifications=data.get("modifications"),
        )


@dataclass
class SearchPlanPreview:
    """Preview for tik-agent style search plans."""

    user_intent: str
    search_keywords: list[str]
    hashtags: list[str] = field(default_factory=list)
    subreddits: list[str] = field(default_factory=list)  # For Reddit agent
    follower_min: int = 1000
    follower_max: int = 100000
    location: Optional[str] = None
    min_engagement: float = 0.03
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    agent_url: Optional[str] = None
    user_answers: dict[str, Any] = field(default_factory=dict)
    message: str = "Here's my search plan based on your preferences"

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "search_plan",
            "planId": self.plan_id,
            "agentId": self.agent_id,
            "agentUrl": self.agent_url,
            "userIntent": self.user_intent,
            "userAnswers": self.user_answers,
            "searchKeywords": self.search_keywords,
            "hashtags": self.hashtags,
            "subreddits": self.subreddits,
            "followerMin": self.follower_min,
            "followerMax": self.follower_max,
            "location": self.location,
            "minEngagement": self.min_engagement,
            "message": self.message,
        }


@dataclass
class IntervalSpec:
    """Interval specification for scheduled tasks."""

    value: int
    unit: str  # 'minutes' | 'hours' | 'days' | 'weeks'

    def to_dict(self) -> dict[str, Any]:
        return {"value": self.value, "unit": self.unit}


@dataclass
class ScheduleProposal:
    """Agent-proposed schedule for recurring task execution.

    This is used when an agent wants to propose a scheduled/recurring task
    to the user for approval. The proposal will be shown as a card in the UI.

    Example:
        proposal = ScheduleProposal(
            name="Daily Report",
            prompt="Generate a summary of yesterday's metrics",
            schedule_type="cron",
            schedule_display="Every day at 9:00 AM",
            cron="0 9 * * *",
            timezone="America/New_York",
            rationale="You asked for daily reports, so I'm proposing this schedule",
        )
    """

    name: str
    prompt: str
    schedule_type: str  # 'cron' | 'interval' | 'one_time'
    schedule_display: str  # Human-readable (e.g., "Every Monday at 9am")

    # Optional fields
    agent_id: str = ""
    proposal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: Optional[str] = None
    rationale: Optional[str] = None
    message: Optional[str] = None

    # Schedule-specific fields (one of these based on schedule_type)
    cron: Optional[str] = None  # e.g., "0 9 * * 1"
    interval: Optional[IntervalSpec] = None
    one_time_at: Optional[str] = None  # ISO datetime

    timezone: str = "UTC"
    next_runs_preview: Optional[list[str]] = None  # Preview of next 5 runs
    timeout_ms: int = 300000  # 5 minutes for user response

    # Execution plan fields (for plan mode integration)
    agent_name: Optional[str] = None
    agent_description: Optional[str] = None
    task_explanation: Optional[str] = None
    expected_outputs: Optional[list[dict[str, Any]]] = None
    execution_plan: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "proposalId": self.proposal_id,
            "agentId": self.agent_id,
            "name": self.name,
            "prompt": self.prompt,
            "scheduleType": self.schedule_type,
            "scheduleDisplay": self.schedule_display,
            "timezone": self.timezone,
            "timeoutMs": self.timeout_ms,
        }
        if self.description:
            result["description"] = self.description
        if self.rationale:
            result["rationale"] = self.rationale
        if self.message:
            result["message"] = self.message
        if self.cron:
            result["cron"] = self.cron
        if self.interval:
            result["interval"] = self.interval.to_dict()
        if self.one_time_at:
            result["oneTimeAt"] = self.one_time_at
        if self.next_runs_preview:
            result["nextRunsPreview"] = self.next_runs_preview
        # Execution plan fields
        if self.agent_name:
            result["agentName"] = self.agent_name
        if self.agent_description:
            result["agentDescription"] = self.agent_description
        if self.task_explanation:
            result["taskExplanation"] = self.task_explanation
        if self.expected_outputs:
            result["expectedOutputs"] = self.expected_outputs
        if self.execution_plan:
            result["executionPlan"] = self.execution_plan
        return result


@dataclass
class ScheduleResponse:
    """User response to a schedule proposal."""

    proposal_id: str
    action: str  # 'confirm' | 'edit' | 'cancel'
    modifications: Optional[dict[str, Any]] = None
    cancel_reason: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScheduleResponse":
        return cls(
            proposal_id=data.get("proposalId", ""),
            action=data.get("action", ""),
            modifications=data.get("modifications"),
            cancel_reason=data.get("cancelReason"),
        )


@dataclass
class PermissionRequest:
    """Agent request for user permission to perform an action.

    This is a generic permission request that can be used for various agent actions
    that require user approval before proceeding (e.g., adding competitors, deleting data,
    posting comments, etc.).

    Example:
        permission = PermissionRequest(
            action="add_competitor",
            description="Add 'Nike' as a competitor",
            details={"competitor_name": "Nike", "competitor_website": "nike.com"},
            message="I noticed Nike is frequently mentioned. Add as competitor?",
        )
    """

    action: str  # Action type (e.g., "add_competitor", "delete_file", "post_comment")
    description: str  # Human-readable description of the action
    details: dict[str, Any] = field(default_factory=dict)  # Action-specific details
    message: str = ""  # Optional message explaining why permission is needed
    agent_id: str = ""
    permission_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timeout_ms: int = 300000  # 5 minutes

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "permission_request",
            "permissionId": self.permission_id,
            "agentId": self.agent_id,
            "action": self.action,
            "description": self.description,
            "details": self.details,
            "message": self.message,
            "timeoutMs": self.timeout_ms,
        }


@dataclass
class PermissionResponse:
    """User response to a permission request."""

    permission_id: str
    approved: bool
    reason: Optional[str] = None  # Optional reason for denial

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PermissionResponse":
        return cls(
            permission_id=data.get("permissionId", ""),
            approved=data.get("approved", False),
            reason=data.get("reason"),
        )
