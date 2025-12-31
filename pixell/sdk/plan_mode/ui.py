"""Plan Mode UI Helpers - Pre-built UI component generators."""

from typing import Any, Optional

from pixell.sdk.plan_mode.events import (
    Question,
    DiscoveredItem,
    SearchPlanPreview,
    PlanProposed,
)


def clarification_card(
    questions: list[Question],
    *,
    message: Optional[str] = None,
    context: Optional[str] = None,
) -> dict[str, Any]:
    """Generate UISpec for a clarification card.

    Creates a structured UI specification for rendering clarification
    questions in the frontend.

    Args:
        questions: List of Question objects
        message: Optional friendly message to display
        context: Optional context explaining why questions are being asked

    Returns:
        UISpec dictionary for clarification card

    Example:
        spec = clarification_card(
            questions=[
                Question(
                    id="niche",
                    type=QuestionType.FREE_TEXT,
                    question="What niche are you targeting?",
                    header="Niche",
                    placeholder="e.g., fitness, cooking, tech"
                )
            ],
            message="Let me understand your requirements better"
        )
    """
    return {
        "type": "clarification_card",
        "questions": [q.to_dict() for q in questions],
        "message": message,
        "context": context,
        "style": {
            "maxWidth": "lg",
            "borderColor": "purple-200",
            "gradient": "purple-50",
        },
    }


def discovery_list(
    items: list[DiscoveredItem],
    discovery_type: str,
    *,
    message: Optional[str] = None,
    show_metadata: bool = True,
) -> dict[str, Any]:
    """Generate UISpec for a discovery result list.

    Creates a structured UI specification for displaying discovered items.

    Args:
        items: List of DiscoveredItem objects
        discovery_type: Type of discovery (subreddits, hashtags, etc.)
        message: Optional message to display
        show_metadata: Whether to show item metadata

    Returns:
        UISpec dictionary for discovery list

    Example:
        spec = discovery_list(
            items=[
                DiscoveredItem(
                    id="r/gaming",
                    name="r/gaming",
                    description="Gaming discussions",
                    metadata={"subscribers": 35000000}
                )
            ],
            discovery_type="subreddits",
            message="Found 10 relevant subreddits"
        )
    """
    return {
        "type": "discovery_list",
        "discoveryType": discovery_type,
        "items": [item.to_dict() for item in items],
        "message": message,
        "showMetadata": show_metadata,
        "style": {
            "maxHeight": "400px",
            "overflow": "auto",
        },
    }


def selection_grid(
    items: list[DiscoveredItem],
    discovery_type: str = "",
    *,
    min_select: int = 1,
    max_select: Optional[int] = None,
    message: Optional[str] = None,
    show_search: bool = True,
) -> dict[str, Any]:
    """Generate UISpec for a selection grid.

    Creates a structured UI specification for item selection interface.

    Args:
        items: List of DiscoveredItem objects to select from
        discovery_type: Type for display purposes
        min_select: Minimum required selections
        max_select: Maximum allowed selections
        message: Optional message to display
        show_search: Whether to show search/filter input

    Returns:
        UISpec dictionary for selection grid

    Example:
        spec = selection_grid(
            items=discovered_subreddits,
            discovery_type="subreddits",
            min_select=1,
            max_select=5,
            message="Select subreddits to monitor"
        )
    """
    return {
        "type": "selection_grid",
        "discoveryType": discovery_type,
        "items": [item.to_dict() for item in items],
        "minSelect": min_select,
        "maxSelect": max_select,
        "message": message,
        "showSearch": show_search,
        "style": {
            "maxWidth": "lg",
            "maxHeight": "60vh",
            "borderColor": "blue-200",
            "gradient": "blue-50",
        },
    }


def preview_card(
    preview: SearchPlanPreview | PlanProposed,
    *,
    editable: bool = True,
    auto_approve_ms: Optional[int] = None,
) -> dict[str, Any]:
    """Generate UISpec for a preview/plan card.

    Creates a structured UI specification for plan preview and approval.

    Args:
        preview: SearchPlanPreview or PlanProposed object
        editable: Whether the preview parameters can be edited
        auto_approve_ms: Auto-approve after this many milliseconds

    Returns:
        UISpec dictionary for preview card

    Example:
        spec = preview_card(
            SearchPlanPreview(
                user_intent="Find gaming influencers",
                search_keywords=["gaming", "streamer"],
                hashtags=["#gaming"],
                follower_min=10000,
                follower_max=100000,
            ),
            editable=True,
            auto_approve_ms=5000,
        )
    """
    preview_data = preview.to_dict()

    if isinstance(preview, SearchPlanPreview):
        return {
            "type": "search_plan_preview",
            "data": preview_data,
            "editable": editable,
            "autoApproveMs": auto_approve_ms,
            "style": {
                "maxWidth": "lg",
                "borderColor": "amber-200",
                "gradient": "amber-50",
            },
            "fields": [
                {
                    "key": "searchKeywords",
                    "label": "Keywords",
                    "type": "tags",
                    "editable": editable,
                },
                {"key": "hashtags", "label": "Hashtags", "type": "tags", "editable": editable},
                {
                    "key": "followerMin",
                    "label": "Min Followers",
                    "type": "number",
                    "editable": editable,
                },
                {
                    "key": "followerMax",
                    "label": "Max Followers",
                    "type": "number",
                    "editable": editable,
                },
                {
                    "key": "minEngagement",
                    "label": "Min Engagement",
                    "type": "percent",
                    "editable": editable,
                },
                {"key": "location", "label": "Location", "type": "text", "editable": editable},
            ],
        }
    else:
        return {
            "type": "plan_preview",
            "data": preview_data,
            "editable": editable,
            "autoApproveMs": auto_approve_ms,
            "style": {
                "maxWidth": "lg",
                "borderColor": "green-200",
                "gradient": "green-50",
            },
        }


def progress_indicator(
    current_phase: str,
    supported_phases: list[str],
    *,
    agent_name: Optional[str] = None,
) -> dict[str, Any]:
    """Generate UISpec for a phase progress indicator.

    Creates a structured UI specification for displaying workflow progress.

    Args:
        current_phase: Current phase name
        supported_phases: List of supported phase names
        agent_name: Optional agent name to display

    Returns:
        UISpec dictionary for progress indicator

    Example:
        spec = progress_indicator(
            current_phase="clarification",
            supported_phases=["clarification", "discovery", "selection", "preview"],
            agent_name="Reddit Agent"
        )
    """
    return {
        "type": "phase_indicator",
        "currentPhase": current_phase,
        "supportedPhases": supported_phases,
        "agentName": agent_name,
        "style": {
            "compact": False,
        },
    }
