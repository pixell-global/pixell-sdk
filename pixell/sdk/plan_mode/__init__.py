"""Plan Mode Module - Phase management for agent workflows."""

from pixell.sdk.plan_mode.phases import (
    Phase,
    VALID_TRANSITIONS,
    validate_transition,
)
from pixell.sdk.plan_mode.context import PlanModeContext
from pixell.sdk.plan_mode.events import (
    Question,
    QuestionType,
    QuestionOption,
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
    IntervalSpec,
    ScheduleProposal,
    ScheduleResponse,
)
from pixell.sdk.plan_mode.ui import (
    clarification_card,
    discovery_list,
    selection_grid,
    preview_card,
)

__all__ = [
    # Phases
    "Phase",
    "VALID_TRANSITIONS",
    "validate_transition",
    # Context
    "PlanModeContext",
    # Event types
    "Question",
    "QuestionType",
    "QuestionOption",
    "ClarificationNeeded",
    "ClarificationResponse",
    "DiscoveredItem",
    "DiscoveryResult",
    "SelectionRequired",
    "SelectionResponse",
    "PlanStep",
    "PlanProposed",
    "PlanApproval",
    "SearchPlanPreview",
    # Schedule proposal types
    "IntervalSpec",
    "ScheduleProposal",
    "ScheduleResponse",
    # UI helpers
    "clarification_card",
    "discovery_list",
    "selection_grid",
    "preview_card",
]
