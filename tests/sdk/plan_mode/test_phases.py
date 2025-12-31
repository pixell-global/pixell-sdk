"""Tests for Plan Mode Phases."""

from pixell.sdk.plan_mode.phases import (
    Phase,
    VALID_TRANSITIONS,
    validate_transition,
    get_phase_order,
    phase_index,
)


class TestPhaseEnum:
    """Tests for Phase enum."""

    def test_all_phases_exist(self):
        assert Phase.IDLE.value == "idle"
        assert Phase.CLARIFICATION.value == "clarification"
        assert Phase.DISCOVERY.value == "discovery"
        assert Phase.SELECTION.value == "selection"
        assert Phase.PREVIEW.value == "preview"
        assert Phase.EXECUTING.value == "executing"
        assert Phase.COMPLETED.value == "completed"
        assert Phase.ERROR.value == "error"

    def test_phase_is_string_enum(self):
        assert isinstance(Phase.IDLE.value, str)
        assert Phase.IDLE == "idle"

    def test_all_phases_are_strings(self):
        for phase in Phase:
            assert isinstance(phase.value, str)

    def test_phase_count(self):
        assert len(Phase) == 8


class TestValidTransitions:
    """Tests for VALID_TRANSITIONS mapping."""

    def test_idle_transitions(self):
        valid = VALID_TRANSITIONS[Phase.IDLE]
        assert Phase.CLARIFICATION in valid
        assert Phase.DISCOVERY in valid
        assert Phase.EXECUTING in valid
        assert Phase.ERROR in valid
        assert Phase.COMPLETED not in valid

    def test_clarification_transitions(self):
        valid = VALID_TRANSITIONS[Phase.CLARIFICATION]
        assert Phase.DISCOVERY in valid
        assert Phase.SELECTION in valid
        assert Phase.PREVIEW in valid
        assert Phase.EXECUTING in valid
        assert Phase.CLARIFICATION in valid  # Can loop back
        assert Phase.ERROR in valid
        assert Phase.IDLE not in valid

    def test_discovery_transitions(self):
        valid = VALID_TRANSITIONS[Phase.DISCOVERY]
        assert Phase.SELECTION in valid
        assert Phase.PREVIEW in valid
        assert Phase.EXECUTING in valid
        assert Phase.CLARIFICATION in valid
        assert Phase.ERROR in valid

    def test_selection_transitions(self):
        valid = VALID_TRANSITIONS[Phase.SELECTION]
        assert Phase.PREVIEW in valid
        assert Phase.EXECUTING in valid
        assert Phase.SELECTION in valid  # Can loop back
        assert Phase.CLARIFICATION in valid
        assert Phase.ERROR in valid

    def test_preview_transitions(self):
        valid = VALID_TRANSITIONS[Phase.PREVIEW]
        assert Phase.EXECUTING in valid
        assert Phase.CLARIFICATION in valid  # Can go back for more clarification
        assert Phase.ERROR in valid
        assert Phase.COMPLETED not in valid

    def test_executing_transitions(self):
        valid = VALID_TRANSITIONS[Phase.EXECUTING]
        assert Phase.COMPLETED in valid
        assert Phase.ERROR in valid
        assert Phase.IDLE not in valid
        assert len(valid) == 2  # Only completed or error

    def test_completed_is_terminal(self):
        valid = VALID_TRANSITIONS[Phase.COMPLETED]
        assert len(valid) == 0

    def test_error_can_retry(self):
        valid = VALID_TRANSITIONS[Phase.ERROR]
        assert Phase.IDLE in valid
        assert len(valid) == 1

    def test_all_phases_have_transitions(self):
        for phase in Phase:
            assert phase in VALID_TRANSITIONS


class TestValidateTransition:
    """Tests for validate_transition function."""

    def test_valid_idle_to_clarification(self):
        assert validate_transition(Phase.IDLE, Phase.CLARIFICATION) is True

    def test_valid_idle_to_discovery(self):
        assert validate_transition(Phase.IDLE, Phase.DISCOVERY) is True

    def test_valid_clarification_to_selection(self):
        assert validate_transition(Phase.CLARIFICATION, Phase.SELECTION) is True

    def test_valid_selection_to_preview(self):
        assert validate_transition(Phase.SELECTION, Phase.PREVIEW) is True

    def test_valid_preview_to_executing(self):
        assert validate_transition(Phase.PREVIEW, Phase.EXECUTING) is True

    def test_valid_executing_to_completed(self):
        assert validate_transition(Phase.EXECUTING, Phase.COMPLETED) is True

    def test_invalid_idle_to_completed(self):
        # Can't skip to completed from idle
        assert validate_transition(Phase.IDLE, Phase.COMPLETED) is False

    def test_invalid_completed_to_anything(self):
        for phase in Phase:
            if phase != Phase.COMPLETED:
                assert validate_transition(Phase.COMPLETED, phase) is False

    def test_invalid_preview_to_discovery(self):
        # Can't go back to discovery from preview
        assert validate_transition(Phase.PREVIEW, Phase.DISCOVERY) is False

    def test_error_to_idle_is_valid(self):
        assert validate_transition(Phase.ERROR, Phase.IDLE) is True

    def test_any_to_error_is_valid(self):
        for phase in Phase:
            # ERROR -> ERROR is not valid, and COMPLETED can't transition
            if phase not in (Phase.COMPLETED, Phase.ERROR):
                assert validate_transition(phase, Phase.ERROR) is True

    def test_clarification_loop_is_valid(self):
        # Can loop back to clarification
        assert validate_transition(Phase.CLARIFICATION, Phase.CLARIFICATION) is True

    def test_selection_loop_is_valid(self):
        # Can loop back to selection
        assert validate_transition(Phase.SELECTION, Phase.SELECTION) is True


class TestValidateTransitionWithSupportedPhases:
    """Tests for validate_transition with supported_phases."""

    def test_supported_phase_is_valid(self):
        supported = [Phase.CLARIFICATION, Phase.PREVIEW]
        assert validate_transition(Phase.IDLE, Phase.CLARIFICATION, supported) is True

    def test_unsupported_phase_is_invalid(self):
        supported = [Phase.CLARIFICATION, Phase.PREVIEW]
        # Discovery not in supported phases
        assert validate_transition(Phase.IDLE, Phase.DISCOVERY, supported) is False

    def test_terminal_states_always_allowed(self):
        supported = [Phase.CLARIFICATION]  # Minimal supported
        # Terminal states should always be allowed
        assert validate_transition(Phase.CLARIFICATION, Phase.ERROR, supported) is True

    def test_executing_always_allowed(self):
        supported = [Phase.CLARIFICATION, Phase.PREVIEW]
        assert validate_transition(Phase.PREVIEW, Phase.EXECUTING, supported) is True

    def test_completed_always_allowed(self):
        supported = [Phase.CLARIFICATION]
        assert validate_transition(Phase.EXECUTING, Phase.COMPLETED, supported) is True

    def test_none_supported_phases_allows_all(self):
        # When supported_phases is None, all transitions are checked only against rules
        assert validate_transition(Phase.IDLE, Phase.DISCOVERY, None) is True

    def test_empty_supported_phases_restricts_phases(self):
        # Empty list only allows always-allowed phases
        supported: list[Phase] = []
        # Clarification is not in empty list, but transition rules check fails for empty
        assert validate_transition(Phase.IDLE, Phase.CLARIFICATION, supported) is False


class TestGetPhaseOrder:
    """Tests for get_phase_order function."""

    def test_returns_correct_order(self):
        order = get_phase_order()
        assert order[0] == Phase.IDLE
        assert order[1] == Phase.CLARIFICATION
        assert order[2] == Phase.DISCOVERY
        assert order[3] == Phase.SELECTION
        assert order[4] == Phase.PREVIEW
        assert order[5] == Phase.EXECUTING
        assert order[6] == Phase.COMPLETED

    def test_error_not_in_order(self):
        order = get_phase_order()
        assert Phase.ERROR not in order

    def test_order_length(self):
        order = get_phase_order()
        assert len(order) == 7  # All phases except ERROR


class TestPhaseIndex:
    """Tests for phase_index function."""

    def test_idle_index(self):
        assert phase_index(Phase.IDLE) == 0

    def test_clarification_index(self):
        assert phase_index(Phase.CLARIFICATION) == 1

    def test_discovery_index(self):
        assert phase_index(Phase.DISCOVERY) == 2

    def test_selection_index(self):
        assert phase_index(Phase.SELECTION) == 3

    def test_preview_index(self):
        assert phase_index(Phase.PREVIEW) == 4

    def test_executing_index(self):
        assert phase_index(Phase.EXECUTING) == 5

    def test_completed_index(self):
        assert phase_index(Phase.COMPLETED) == 6

    def test_error_returns_negative(self):
        assert phase_index(Phase.ERROR) == -1

    def test_phase_progression(self):
        # Each phase should have higher index than the previous
        order = get_phase_order()
        for i in range(len(order) - 1):
            assert phase_index(order[i]) < phase_index(order[i + 1])


class TestPhaseWorkflow:
    """Integration tests for typical phase workflows."""

    def test_minimal_workflow(self):
        """Test minimal workflow: idle -> executing -> completed."""
        assert validate_transition(Phase.IDLE, Phase.EXECUTING) is True
        assert validate_transition(Phase.EXECUTING, Phase.COMPLETED) is True

    def test_clarification_only_workflow(self):
        """Test workflow with only clarification."""
        supported = [Phase.CLARIFICATION]
        assert validate_transition(Phase.IDLE, Phase.CLARIFICATION, supported) is True
        assert validate_transition(Phase.CLARIFICATION, Phase.EXECUTING, supported) is True
        assert validate_transition(Phase.EXECUTING, Phase.COMPLETED, supported) is True

    def test_full_workflow(self):
        """Test complete workflow through all phases."""
        supported = [Phase.CLARIFICATION, Phase.DISCOVERY, Phase.SELECTION, Phase.PREVIEW]

        transitions = [
            (Phase.IDLE, Phase.CLARIFICATION),
            (Phase.CLARIFICATION, Phase.DISCOVERY),
            (Phase.DISCOVERY, Phase.SELECTION),
            (Phase.SELECTION, Phase.PREVIEW),
            (Phase.PREVIEW, Phase.EXECUTING),
            (Phase.EXECUTING, Phase.COMPLETED),
        ]

        for from_phase, to_phase in transitions:
            assert (
                validate_transition(from_phase, to_phase, supported) is True
            ), f"Transition {from_phase.value} -> {to_phase.value} should be valid"

    def test_workflow_with_clarification_loop(self):
        """Test workflow that loops back for more clarification."""
        supported = [Phase.CLARIFICATION, Phase.DISCOVERY, Phase.SELECTION, Phase.PREVIEW]

        # Initial clarification
        assert validate_transition(Phase.IDLE, Phase.CLARIFICATION, supported) is True
        # Discovery
        assert validate_transition(Phase.CLARIFICATION, Phase.DISCOVERY, supported) is True
        # Selection
        assert validate_transition(Phase.DISCOVERY, Phase.SELECTION, supported) is True
        # Back to clarification for more info
        assert validate_transition(Phase.SELECTION, Phase.CLARIFICATION, supported) is True
        # Continue to preview
        assert validate_transition(Phase.CLARIFICATION, Phase.PREVIEW, supported) is True

    def test_error_recovery_workflow(self):
        """Test workflow that recovers from error."""
        # Start workflow
        assert validate_transition(Phase.IDLE, Phase.CLARIFICATION) is True
        # Error occurs
        assert validate_transition(Phase.CLARIFICATION, Phase.ERROR) is True
        # Recover
        assert validate_transition(Phase.ERROR, Phase.IDLE) is True
        # Retry
        assert validate_transition(Phase.IDLE, Phase.CLARIFICATION) is True
