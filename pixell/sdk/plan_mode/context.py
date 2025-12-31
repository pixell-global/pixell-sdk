"""Plan Mode Context - In-memory state management for plan mode workflows."""

from typing import Any, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
import logging

from pixell.sdk.plan_mode.phases import Phase, validate_transition
from pixell.sdk.plan_mode.events import (
    Question,
    ClarificationNeeded,
    DiscoveredItem,
    DiscoveryResult,
    SelectionRequired,
    PlanProposed,
    SearchPlanPreview,
    IntervalSpec,
    ScheduleProposal,
    ScheduleResponse,
)

if TYPE_CHECKING:
    from pixell.sdk.a2a.streaming import SSEStream

logger = logging.getLogger(__name__)


@dataclass
class PlanModeContext:
    """In-memory plan mode state for current task.

    This context tracks the current phase, user answers, discovered items,
    and selections throughout the plan mode workflow.

    The context is tied to a single task/session and provides methods
    for transitioning between phases and emitting events.

    Example:
        ctx = PlanModeContext(stream=stream, supported_phases=[Phase.CLARIFICATION, Phase.PREVIEW])

        # Request clarification
        await ctx.request_clarification([
            Question(id="niche", type=QuestionType.FREE_TEXT, question="What niche?")
        ])

        # Later, after response received
        ctx.set_clarification_response({"niche": "gaming"})

        # Emit preview
        await ctx.emit_preview(SearchPlanPreview(...))
    """

    stream: "SSEStream"
    supported_phases: list[Phase] = field(default_factory=list)
    agent_id: str = ""

    # Current state
    phase: Phase = Phase.IDLE
    user_answers: dict[str, Any] = field(default_factory=dict)
    discovered_items: list[DiscoveredItem] = field(default_factory=list)
    selected_ids: list[str] = field(default_factory=list)

    # Pending requests (for tracking)
    _pending_clarification_id: Optional[str] = None
    _pending_selection_id: Optional[str] = None
    _pending_plan_id: Optional[str] = None
    _pending_schedule_proposal_id: Optional[str] = None

    def _transition_to(self, new_phase: Phase) -> bool:
        """Transition to a new phase.

        Args:
            new_phase: Target phase

        Returns:
            True if transition was valid
        """
        is_valid = validate_transition(
            self.phase, new_phase, self.supported_phases if self.supported_phases else None
        )

        old_phase = self.phase
        self.phase = new_phase

        if is_valid:
            logger.debug(f"Phase transition: {old_phase.value} -> {new_phase.value}")
        else:
            logger.warning(
                f"Proceeding with invalid transition: {old_phase.value} -> {new_phase.value}"
            )

        return is_valid

    async def request_clarification(
        self,
        questions: list[Question],
        *,
        context: Optional[str] = None,
        message: Optional[str] = None,
        timeout_ms: int = 300000,
    ) -> str:
        """Request clarification from the user.

        Emits a clarification_needed event and transitions to CLARIFICATION phase.

        Args:
            questions: List of questions to ask
            context: Why the agent is asking (internal)
            message: User-facing message
            timeout_ms: Timeout in milliseconds

        Returns:
            The clarification ID for tracking the response

        Example:
            clarification_id = await ctx.request_clarification([
                Question(
                    id="topic",
                    type=QuestionType.FREE_TEXT,
                    question="What topic are you interested in?",
                    header="Topic",
                )
            ])
        """
        self._transition_to(Phase.CLARIFICATION)

        clarification = ClarificationNeeded(
            questions=questions,
            agent_id=self.agent_id,
            context=context,
            message=message,
            timeout_ms=timeout_ms,
        )

        self._pending_clarification_id = clarification.clarification_id

        await self.stream.emit_clarification(clarification.to_dict())

        return clarification.clarification_id

    def set_clarification_response(
        self,
        answers: dict[str, Any],
        clarification_id: Optional[str] = None,
    ) -> None:
        """Set the clarification response.

        Call this when user responds to clarification request.

        Args:
            answers: Dictionary of question_id -> answer
            clarification_id: Optional ID to verify (logs warning if mismatch)
        """
        if clarification_id and clarification_id != self._pending_clarification_id:
            logger.warning(
                f"Clarification ID mismatch: expected {self._pending_clarification_id}, "
                f"got {clarification_id}"
            )

        self.user_answers.update(answers)
        self._pending_clarification_id = None
        logger.debug(f"Clarification response received: {list(answers.keys())}")

    async def emit_discovery(
        self,
        items: list[DiscoveredItem],
        discovery_type: str,
        *,
        message: Optional[str] = None,
    ) -> str:
        """Emit discovery results.

        Emits a discovery_result event and transitions to DISCOVERY phase.

        Args:
            items: List of discovered items
            discovery_type: Type of discovery (subreddits, hashtags, etc.)
            message: Optional message to display

        Returns:
            The discovery ID

        Example:
            await ctx.emit_discovery(
                items=[
                    DiscoveredItem(id="r/gaming", name="r/gaming", metadata={"subscribers": 1000000})
                ],
                discovery_type="subreddits",
            )
        """
        self._transition_to(Phase.DISCOVERY)

        discovery = DiscoveryResult(
            items=items,
            discovery_type=discovery_type,
            message=message,
        )

        self.discovered_items = items

        await self.stream.emit_discovery(discovery.to_dict())

        return discovery.discovery_id

    async def request_selection(
        self,
        items: Optional[list[DiscoveredItem]] = None,
        *,
        discovery_type: str = "",
        min_select: int = 1,
        max_select: Optional[int] = None,
        message: Optional[str] = None,
    ) -> str:
        """Request user selection from items.

        Emits a selection_required event and transitions to SELECTION phase.

        Args:
            items: Items to select from (defaults to discovered_items)
            discovery_type: Type for display purposes
            min_select: Minimum selections required
            max_select: Maximum selections allowed
            message: Optional message to display

        Returns:
            The selection ID for tracking the response

        Example:
            selection_id = await ctx.request_selection(
                min_select=1,
                max_select=5,
                message="Select the subreddits to monitor",
            )
        """
        self._transition_to(Phase.SELECTION)

        selection_items = items if items is not None else self.discovered_items

        selection = SelectionRequired(
            items=selection_items,
            discovery_type=discovery_type,
            min_select=min_select,
            max_select=max_select,
            message=message,
        )

        self._pending_selection_id = selection.selection_id

        await self.stream.emit_selection(selection.to_dict())

        return selection.selection_id

    def set_selection_response(
        self,
        selected_ids: list[str],
        selection_id: Optional[str] = None,
    ) -> None:
        """Set the selection response.

        Call this when user responds to selection request.

        Args:
            selected_ids: List of selected item IDs
            selection_id: Optional ID to verify (logs warning if mismatch)
        """
        if selection_id and selection_id != self._pending_selection_id:
            logger.warning(
                f"Selection ID mismatch: expected {self._pending_selection_id}, "
                f"got {selection_id}"
            )

        self.selected_ids = selected_ids
        self._pending_selection_id = None
        logger.debug(f"Selection response received: {len(selected_ids)} items selected")

    async def emit_preview(
        self,
        preview: SearchPlanPreview | PlanProposed,
    ) -> str:
        """Emit a preview/plan for user approval.

        Emits a preview_ready event and transitions to PREVIEW phase.

        Args:
            preview: SearchPlanPreview or PlanProposed object

        Returns:
            The plan ID for tracking the response

        Example:
            await ctx.emit_preview(SearchPlanPreview(
                user_intent="Find gaming content",
                search_keywords=["gaming", "streamer"],
                hashtags=["#gaming", "#streamer"],
            ))
        """
        self._transition_to(Phase.PREVIEW)

        self._pending_plan_id = preview.plan_id

        await self.stream.emit_preview(preview.to_dict())

        return preview.plan_id

    def set_plan_approval(
        self,
        approved: bool,
        plan_id: Optional[str] = None,
        modifications: Optional[dict[str, Any]] = None,
    ) -> None:
        """Set the plan approval response.

        Call this when user approves/rejects the plan.

        Args:
            approved: Whether the plan was approved
            plan_id: Optional ID to verify (logs warning if mismatch)
            modifications: Optional modifications requested by user
        """
        if plan_id and plan_id != self._pending_plan_id:
            logger.warning(f"Plan ID mismatch: expected {self._pending_plan_id}, " f"got {plan_id}")

        self._pending_plan_id = None

        if modifications:
            self.user_answers.update(modifications)

        logger.debug(f"Plan {'approved' if approved else 'rejected'}")

    async def start_execution(self, message: Optional[str] = None) -> None:
        """Transition to execution phase.

        Args:
            message: Optional status message
        """
        self._transition_to(Phase.EXECUTING)
        await self.stream.emit_status(
            "working",
            message or "Starting execution...",
        )

    async def complete(
        self,
        result: dict[str, Any],
        *,
        message: Optional[str] = None,
    ) -> None:
        """Complete the plan mode workflow.

        Emits a result message and transitions to COMPLETED phase.

        Args:
            result: Result data
            message: Optional result message
        """
        self._transition_to(Phase.COMPLETED)

        from pixell.sdk.a2a.protocol import A2AMessage

        msg = A2AMessage.agent_with_data(
            message or "Task completed successfully",
            result,
        )
        await self.stream.emit_result(msg, final=True)

    async def error(
        self,
        error_type: str,
        message: str,
        *,
        recoverable: bool = False,
    ) -> None:
        """Transition to error state.

        Args:
            error_type: Type of error
            message: Error message
            recoverable: Whether the error is recoverable
        """
        self._transition_to(Phase.ERROR)
        await self.stream.emit_error(error_type, message, recoverable=recoverable)

    def get_selected_items(self) -> list[DiscoveredItem]:
        """Get the discovered items that were selected.

        Returns:
            List of selected DiscoveredItem objects
        """
        return [item for item in self.discovered_items if item.id in self.selected_ids]

    async def emit_file_created(
        self,
        path: str,
        *,
        name: Optional[str] = None,
        format: Optional[str] = None,
        summary: Optional[str] = None,
        size: Optional[int] = None,
    ) -> None:
        """Emit a file_created event for orchestrator to upload to S3.

        This is the standard way for agents to notify the system that a file
        has been created and should be uploaded to user storage.

        Args:
            path: Path to the file (relative to agent's outputs_dir)
            name: Display name for the file (defaults to filename from path)
            format: File format/type (e.g., "html", "json", "csv")
            summary: Human-readable description of the file
            size: File size in bytes (optional)

        Example:
            await plan.emit_file_created(
                path="exports/report.html",
                name="Analysis Report",
                format="html",
                summary="Reddit research results for user query"
            )
        """
        from pathlib import Path as PathLib

        # Auto-detect name from path if not provided
        if not name:
            name = PathLib(path).name

        # Auto-detect format from extension if not provided
        if not format:
            suffix = PathLib(path).suffix.lower()
            format = suffix[1:] if suffix else "unknown"

        await self.stream.emit_status(
            "working",
            f"File created: {name}",
            step="file_created",
            path=path,
            name=name,
            format=format,
            summary=summary,
            size=size,
        )

    async def emit_schedule_proposal(
        self,
        name: str,
        prompt: str,
        schedule: str,
        schedule_display: str,
        schedule_type: str = "cron",
        *,
        description: Optional[str] = None,
        rationale: Optional[str] = None,
        timezone: str = "UTC",
        interval_value: Optional[int] = None,
        interval_unit: Optional[str] = None,
        next_runs_preview: Optional[list[str]] = None,
        # Execution plan fields (for plan mode integration)
        agent_name: Optional[str] = None,
        agent_description: Optional[str] = None,
        task_explanation: Optional[str] = None,
        expected_outputs: Optional[list[dict[str, Any]]] = None,
        execution_plan: Optional[dict[str, Any]] = None,
    ) -> str:
        """Propose a schedule to the user for approval.

        This emits a schedule_proposal event that will show a card in the UI
        allowing the user to confirm, edit, or cancel the proposed schedule.

        Args:
            name: Human-readable schedule name
            prompt: The task prompt to execute on schedule
            schedule: Cron expression, ISO datetime, or interval spec
            schedule_display: Human-readable schedule description
            schedule_type: Type of schedule ('cron', 'interval', 'one_time')
            description: Optional description
            rationale: Why the agent is proposing this schedule
            timezone: Timezone for schedule (default UTC)
            interval_value: For interval type, the numeric value
            interval_unit: For interval type, the unit ('minutes', 'hours', 'days', 'weeks')
            next_runs_preview: Optional list of next run times (ISO strings)
            agent_name: Human-readable agent name (for display)
            agent_description: Agent description (for display)
            task_explanation: Explanation of what the scheduled task will do
            expected_outputs: List of expected outputs (type, name, description)
            execution_plan: Full execution plan with task parameters from plan mode

        Returns:
            The proposal ID for tracking the response

        Example:
            proposal_id = await ctx.emit_schedule_proposal(
                name="Daily Report",
                prompt="Generate a summary of yesterday's metrics",
                schedule="0 9 * * *",
                schedule_display="Every day at 9:00 AM",
                schedule_type="cron",
                rationale="You asked for daily reports",
                timezone="America/New_York",
                task_explanation="I'll search r/gaming for trending posts",
                expected_outputs=[{"type": "html", "name": "Report"}],
                execution_plan={"taskType": "research", "parameters": {...}},
            )
        """
        # Build interval spec if provided
        interval = None
        if schedule_type == "interval" and interval_value and interval_unit:
            interval = IntervalSpec(value=interval_value, unit=interval_unit)

        proposal = ScheduleProposal(
            name=name,
            prompt=prompt,
            schedule_type=schedule_type,
            schedule_display=schedule_display,
            agent_id=self.agent_id,
            description=description,
            rationale=rationale,
            cron=schedule if schedule_type == "cron" else None,
            interval=interval,
            one_time_at=schedule if schedule_type == "one_time" else None,
            timezone=timezone,
            next_runs_preview=next_runs_preview,
            # Execution plan fields
            agent_name=agent_name,
            agent_description=agent_description,
            task_explanation=task_explanation,
            expected_outputs=expected_outputs,
            execution_plan=execution_plan,
        )

        self._pending_schedule_proposal_id = proposal.proposal_id

        await self.stream.emit_schedule_proposal(proposal.to_dict())

        return proposal.proposal_id

    def set_schedule_response(
        self,
        action: str,
        proposal_id: Optional[str] = None,
        modifications: Optional[dict[str, Any]] = None,
        cancel_reason: Optional[str] = None,
    ) -> ScheduleResponse:
        """Set the schedule response from the user.

        Call this when user responds to schedule proposal.

        Args:
            action: User action ('confirm', 'edit', 'cancel')
            proposal_id: Optional ID to verify (logs warning if mismatch)
            modifications: Optional modifications if action is 'edit'
            cancel_reason: Optional reason if action is 'cancel'

        Returns:
            The ScheduleResponse object
        """
        if proposal_id and proposal_id != self._pending_schedule_proposal_id:
            logger.warning(
                f"Schedule proposal ID mismatch: expected {self._pending_schedule_proposal_id}, "
                f"got {proposal_id}"
            )

        response = ScheduleResponse(
            proposal_id=proposal_id or self._pending_schedule_proposal_id or "",
            action=action,
            modifications=modifications,
            cancel_reason=cancel_reason,
        )

        self._pending_schedule_proposal_id = None

        logger.debug(f"Schedule response received: {action}")

        return response
