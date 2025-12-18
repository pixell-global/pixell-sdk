"""Plan Mode Phases - Phase definitions and transition validation."""

from enum import Enum
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class Phase(str, Enum):
    """Plan mode workflow phases.

    Agents can opt into specific phases based on their workflow needs.
    Phases represent different stages of the plan mode workflow.
    """

    # Initial state
    IDLE = "idle"

    # Information gathering
    CLARIFICATION = "clarification"

    # Item discovery (search results, subreddits, hashtags, etc.)
    DISCOVERY = "discovery"

    # User selection from discovered items
    SELECTION = "selection"

    # Preview/confirmation before execution
    PREVIEW = "preview"

    # Active execution
    EXECUTING = "executing"

    # Terminal states
    COMPLETED = "completed"
    ERROR = "error"


# Valid phase transitions
# Key is current phase, value is list of valid next phases
VALID_TRANSITIONS: dict[Phase, list[Phase]] = {
    Phase.IDLE: [Phase.CLARIFICATION, Phase.DISCOVERY, Phase.EXECUTING, Phase.ERROR],
    Phase.CLARIFICATION: [Phase.DISCOVERY, Phase.SELECTION, Phase.PREVIEW, Phase.EXECUTING, Phase.CLARIFICATION, Phase.ERROR],
    Phase.DISCOVERY: [Phase.SELECTION, Phase.PREVIEW, Phase.EXECUTING, Phase.CLARIFICATION, Phase.ERROR],
    Phase.SELECTION: [Phase.PREVIEW, Phase.EXECUTING, Phase.SELECTION, Phase.CLARIFICATION, Phase.ERROR],
    Phase.PREVIEW: [Phase.EXECUTING, Phase.CLARIFICATION, Phase.ERROR],
    Phase.EXECUTING: [Phase.COMPLETED, Phase.ERROR],
    Phase.COMPLETED: [],  # Terminal
    Phase.ERROR: [Phase.IDLE],  # Can retry from error
}


def validate_transition(
    from_phase: Phase,
    to_phase: Phase,
    supported_phases: Optional[list[Phase]] = None,
) -> bool:
    """Validate a phase transition.

    This function checks if a transition is valid according to the
    transition rules and optionally checks if the target phase is
    supported by the agent.

    Note: Invalid transitions log a warning but don't raise exceptions
    (warning only, as per design decision).

    Args:
        from_phase: Current phase
        to_phase: Target phase
        supported_phases: Optional list of phases the agent supports

    Returns:
        True if transition is valid, False otherwise
    """
    # Check if transition is valid according to rules
    valid_next = VALID_TRANSITIONS.get(from_phase, [])
    if to_phase not in valid_next:
        logger.warning(
            f"Invalid phase transition: {from_phase.value} -> {to_phase.value}. "
            f"Valid transitions from {from_phase.value}: {[p.value for p in valid_next]}"
        )
        return False

    # Check if target phase is supported (if supported_phases provided)
    if supported_phases is not None:
        # Always allow terminal states and idle
        always_allowed = {Phase.IDLE, Phase.COMPLETED, Phase.ERROR, Phase.EXECUTING}
        if to_phase not in always_allowed and to_phase not in supported_phases:
            logger.warning(
                f"Phase {to_phase.value} is not in agent's supported phases: "
                f"{[p.value for p in supported_phases]}"
            )
            return False

    return True


def get_phase_order() -> list[Phase]:
    """Get phases in typical workflow order.

    Returns:
        List of phases in order (excluding error)
    """
    return [
        Phase.IDLE,
        Phase.CLARIFICATION,
        Phase.DISCOVERY,
        Phase.SELECTION,
        Phase.PREVIEW,
        Phase.EXECUTING,
        Phase.COMPLETED,
    ]


def phase_index(phase: Phase) -> int:
    """Get the index of a phase in the workflow order.

    Args:
        phase: Phase to get index for

    Returns:
        Index in workflow order, or -1 for ERROR
    """
    order = get_phase_order()
    try:
        return order.index(phase)
    except ValueError:
        return -1
