"""
PlanModeAgent - Clean base class for plan mode agents.

Provides automatic:
- Workflow-based state persistence (survives session ID changes)
- Response type routing (clarification/selection/plan → methods)
- Format conversions (dict → DiscoveredItem, etc.)
- Error handling with recoverable states

Example:
    from pixell.sdk import PlanModeAgent, discovery, preview, result

    class RedditAgent(PlanModeAgent):
        async def on_query(self, query: str):
            return discovery(items=subreddits, message="Found subreddits")

        async def on_selection(self, selected: list[str]):
            return preview(
                intent=f"Search {len(selected)} subreddits",
                plan={"targets": selected, "keywords": ["gaming"]}
            )

        async def on_execute(self):
            return result(answer=report.summary)

    RedditAgent(agent_id="reddit", port=9000).run()
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Union
import logging

from pixell.sdk.server import AgentServer
from pixell.sdk.a2a.handlers import MessageContext, ResponseContext
from pixell.sdk.plan_mode.context import PlanModeContext
from pixell.sdk.plan_mode.events import (
    DiscoveredItem,
    SearchPlanPreview,
    Question,
    QuestionType,
    QuestionOption,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Response Types (returned by agent methods)
# =============================================================================


@dataclass
class Discovery:
    """Return from on_query to show items for selection."""

    items: list[dict]
    message: str = ""
    item_type: str = "items"
    min_select: int = 1
    max_select: Optional[int] = None


@dataclass
class Clarification:
    """Return from on_query to ask user questions."""

    question: str
    options: Optional[list[dict]] = None
    header: str = "Question"
    preview: Optional[dict] = None  # Structured preview data (e.g., change tables)


@dataclass
class Preview:
    """Return from on_query or on_selection to show execution preview."""

    intent: str
    plan: dict = field(default_factory=dict)
    message: str = ""


@dataclass
class Result:
    """Return from on_execute when task completes."""

    answer: str
    data: dict = field(default_factory=dict)
    recommended_actions: list[dict] = field(default_factory=list)
    # Each dict: {"objective": "Compare competitors", "prompt": "Compare Nike vs Adidas"}


@dataclass
class Error:
    """Return from any method to indicate failure."""

    message: str
    recoverable: bool = True


@dataclass
class Permission:
    """Return to request user permission before performing an action.

    This is used when an agent needs explicit user approval before proceeding
    with an action (e.g., adding a competitor, deleting data, posting content).

    The permission will be shown as a card in the chat UI with Approve/Deny buttons.
    """

    action: str  # Action type (e.g., "add_competitor", "delete_file")
    description: str  # Human-readable description of the action
    details: dict = field(default_factory=dict)  # Action-specific details
    message: str = ""  # Optional message explaining why permission is needed


# Helper functions for cleaner syntax
def discovery(
    items: list[dict],
    message: str = "",
    item_type: str = "items",
    min_select: int = 1,
    max_select: Optional[int] = None,
) -> Discovery:
    """Create a Discovery response."""
    return Discovery(
        items=items,
        message=message,
        item_type=item_type,
        min_select=min_select,
        max_select=max_select,
    )


def clarify(
    question: str,
    options: Optional[list[dict]] = None,
    header: str = "Question",
) -> Clarification:
    """Create a Clarification response."""
    return Clarification(question=question, options=options, header=header)


def preview(
    intent: str,
    plan: Optional[dict] = None,
    message: str = "",
) -> Preview:
    """Create a Preview response."""
    return Preview(intent=intent, plan=plan or {}, message=message)


def result(
    answer: str,
    data: Optional[dict] = None,
    recommended_actions: Optional[list[dict]] = None,
) -> Result:
    """Create a Result response.

    Args:
        answer: The main response text
        data: Additional data to include in the result
        recommended_actions: List of follow-up suggestions, each with:
            - objective: What the user can accomplish (e.g., "Compare with competitors")
            - prompt: The suggested query to send (e.g., "Compare Nike vs Adidas")
    """
    return Result(
        answer=answer,
        data=data or {},
        recommended_actions=recommended_actions or [],
    )


def error(message: str, recoverable: bool = True) -> Error:
    """Create an Error response."""
    return Error(message=message, recoverable=recoverable)


def permission(
    action: str,
    description: str,
    details: Optional[dict] = None,
    message: str = "",
) -> Permission:
    """Create a Permission response to request user approval.

    Args:
        action: The action type (e.g., "add_competitor", "delete_file")
        description: Human-readable description of the action
        details: Action-specific details to pass back when approved
        message: Optional message explaining why permission is needed

    Example:
        return permission(
            action="add_competitor",
            description="Add 'Nike' as a competitor",
            details={"competitor_name": "Nike", "website": "nike.com"},
            message="I noticed Nike is frequently mentioned in discussions."
        )
    """
    return Permission(
        action=action,
        description=description,
        details=details or {},
        message=message,
    )


# Type alias for response types
AgentResponse = Union[Discovery, Clarification, Preview, Result, Error, Permission]


# =============================================================================
# Agent State (persisted by workflow ID)
# =============================================================================


@dataclass
class LiteModeConfig:
    """Configuration for lite mode behavior.

    Lite mode automatically handles interactive phases without user input:
    - Clarification: Auto-select first option for each question
    - Discovery/Selection: Auto-select top N items by relevance
    - Preview: Auto-approve and proceed to execution
    """

    max_select: int = 5  # Max items to auto-select from discovery
    auto_approve_plan: bool = True  # Auto-approve preview


@dataclass
class AgentState:
    """State for a single workflow. Persisted across session changes."""

    query: str = ""
    context: dict = field(default_factory=dict)
    discovered: list[dict] = field(default_factory=list)
    selected: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)  # Request metadata (includes lite_mode_enabled)

    # PlanModeContext state (also needs to persist across requests)
    phase: str = "idle"
    pending_selection_id: Optional[str] = None
    pending_clarification_id: Optional[str] = None
    pending_plan_id: Optional[str] = None
    pending_permission_id: Optional[str] = None

    def clear(self):
        """Reset state for new workflow."""
        self.query = ""
        self.context = {}
        self.discovered = []
        self.selected = []
        self.metadata = {}
        self.phase = "idle"
        self.pending_selection_id = None
        self.pending_clarification_id = None
        self.pending_plan_id = None
        self.pending_permission_id = None


# Workflow-based state store (key = workflow_id)
_workflow_states: dict[str, AgentState] = {}

# Mapping from interaction IDs to workflow IDs (for session correlation)
# When the frontend sends a response with selection_id/clarification_id/plan_id/permission_id,
# we use these mappings to find the original workflow state
_selection_to_workflow: dict[str, str] = {}
_clarification_to_workflow: dict[str, str] = {}
_plan_to_workflow: dict[str, str] = {}
_permission_to_workflow: dict[str, str] = {}


# =============================================================================
# PlanModeAgent Base Class
# =============================================================================


class PlanModeAgent(ABC):
    """
    Base class for plan mode agents.

    Subclass and implement 3 methods:
    - on_query(query) → Discovery | Clarification | Preview | Error
    - on_selection(selected) → Preview | Error
    - on_execute() → Result | Error

    Optionally override:
    - on_clarification(answers) → Discovery | Clarification | Preview | Error
    """

    def __init__(
        self,
        agent_id: str,
        name: str = "",
        description: str = "",
        port: int = 8000,
        host: str = "0.0.0.0",
        discovery_type: str = "items",
        outputs_dir: Optional[str] = None,
        lite_mode_config: Optional[LiteModeConfig] = None,
    ):
        """
        Initialize the agent.

        Args:
            agent_id: Unique identifier for this agent
            name: Human-readable name
            description: Agent description
            port: Port to run on
            host: Host to bind to
            discovery_type: Type of items discovered (e.g., "subreddits", "hashtags")
            outputs_dir: Directory for output files
            lite_mode_config: Configuration for lite mode behavior (auto-responses)
        """
        self._discovery_type = discovery_type
        self._current_ctx: Optional[Union[MessageContext, ResponseContext]] = None
        self._current_workflow_id: Optional[str] = None
        self._lite_mode_config = lite_mode_config or LiteModeConfig()

        self._server = AgentServer(
            agent_id=agent_id,
            name=name or agent_id,
            description=description,
            port=port,
            host=host,
            plan_mode_config={
                "phases": ["clarification", "discovery", "selection", "preview"],
                "discoveryType": discovery_type,
            },
            outputs_dir=outputs_dir,
        )

        # Register handlers
        self._server.on_message(self._handle_message)
        self._server.on_respond(self._handle_response)

    # -------------------------------------------------------------------------
    # State Management (workflow-based, survives session changes)
    # -------------------------------------------------------------------------

    def _get_workflow_id(self, ctx: Union[MessageContext, ResponseContext]) -> str:
        """Extract workflow ID from context (stable across session changes)."""
        if hasattr(ctx, "stream") and ctx.stream:
            return getattr(ctx.stream, "workflow_id", None) or ctx.session_id
        return ctx.session_id

    @property
    def state(self) -> AgentState:
        """Current workflow state."""
        if self._current_workflow_id and self._current_workflow_id in _workflow_states:
            return _workflow_states[self._current_workflow_id]
        return AgentState()

    def _restore_plan_mode_context(self, plan: PlanModeContext) -> None:
        """Restore PlanModeContext state from persisted AgentState.

        This is needed because PlanModeContext is recreated fresh for each HTTP request,
        but we need to maintain phase and pending IDs across requests.
        """
        state = self.state
        if state.phase != "idle":
            # Import Phase enum for setting phase
            from pixell.sdk.plan_mode.phases import Phase
            try:
                plan.phase = Phase(state.phase)
            except ValueError:
                pass  # Keep default if invalid

        plan._pending_selection_id = state.pending_selection_id
        plan._pending_clarification_id = state.pending_clarification_id
        plan._pending_plan_id = state.pending_plan_id
        plan._pending_permission_id = state.pending_permission_id

        logger.debug(
            f"Restored PlanModeContext: phase={state.phase}, "
            f"selection_id={state.pending_selection_id}, "
            f"plan_id={state.pending_plan_id}, "
            f"permission_id={state.pending_permission_id}"
        )

    def _save_plan_mode_context(self, plan: PlanModeContext) -> None:
        """Save PlanModeContext state to AgentState for persistence."""
        state = self.state
        state.phase = plan.phase.value if hasattr(plan.phase, 'value') else str(plan.phase)
        state.pending_selection_id = plan._pending_selection_id
        state.pending_clarification_id = plan._pending_clarification_id
        state.pending_plan_id = plan._pending_plan_id
        state.pending_permission_id = plan._pending_permission_id

        logger.debug(
            f"Saved PlanModeContext: phase={state.phase}, "
            f"selection_id={state.pending_selection_id}, "
            f"plan_id={state.pending_plan_id}, "
            f"permission_id={state.pending_permission_id}"
        )

    # -------------------------------------------------------------------------
    # Helper Methods (use in agent implementations)
    # -------------------------------------------------------------------------

    async def emit_progress(self, message: str):
        """Emit progress update to client."""
        if self._current_ctx:
            await self._current_ctx.emit_status("working", message)

    async def emit_file(
        self,
        path: str,
        name: Optional[str] = None,
        summary: Optional[str] = None,
    ):
        """Notify that a file was created (for S3 upload by orchestrator)."""
        if self._current_ctx:
            await self._current_ctx.emit_file_created(path, name=name, summary=summary)

    # -------------------------------------------------------------------------
    # Abstract Methods (implement these)
    # -------------------------------------------------------------------------

    @abstractmethod
    async def on_query(self, query: str) -> AgentResponse:
        """
        Handle new query.

        Return one of:
        - Discovery: Show items for user selection
        - Clarification: Ask user questions
        - Preview: Skip to execution preview
        - Result: Complete immediately
        - Error: Fail with message
        """
        pass

    @abstractmethod
    async def on_selection(self, selected: list[str]) -> Union[Preview, Error]:
        """
        Handle user selection.

        Args:
            selected: List of selected item IDs

        Return:
        - Preview: Show execution preview
        - Error: Fail with message
        """
        pass

    @abstractmethod
    async def on_execute(self) -> Union[Result, Error]:
        """
        Execute the task.

        Return:
        - Result: Success with answer and data
        - Error: Fail with message
        """
        pass

    async def on_clarification(self, answers: dict) -> AgentResponse:
        """
        Handle clarification answers.

        Default: store answers in context and re-run on_query.
        Override to customize behavior or ask follow-up questions.

        Args:
            answers: Dict of question_id → answer

        Return: Same as on_query
        """
        self.state.context.update(answers)
        return await self.on_query(self.state.query)

    async def on_permission(
        self,
        approved: bool,
        action: str,
        details: dict,
    ) -> AgentResponse:
        """
        Handle permission response from user.

        Override this method to perform the action when permission is granted,
        or to handle denial gracefully.

        Args:
            approved: Whether the user approved the action
            action: The action type (e.g., "add_competitor")
            details: Action-specific details passed to the permission request

        Return:
        - Result: If action was performed (or denied with a message)
        - Error: If something went wrong

        Example:
            async def on_permission(self, approved, action, details):
                if action == "add_competitor" and approved:
                    await self.add_competitor(details["competitor_name"])
                    return result(answer=f"Added '{details['competitor_name']}' as a competitor.")
                elif not approved:
                    return result(answer="No problem, I won't add the competitor.")
                return error(f"Unknown action: {action}")
        """
        # Default implementation: just acknowledge the response
        if approved:
            return result(answer=f"Permission granted for {action}.")
        else:
            return result(answer=f"Permission denied for {action}.")

    # -------------------------------------------------------------------------
    # Internal Handlers (route SDK events to agent methods)
    # -------------------------------------------------------------------------

    async def _handle_message(self, ctx: MessageContext):
        """Route new messages to on_query."""
        self._current_ctx = ctx
        self._current_workflow_id = self._get_workflow_id(ctx)

        # Initialize state for this workflow
        if self._current_workflow_id not in _workflow_states:
            _workflow_states[self._current_workflow_id] = AgentState()

        state = _workflow_states[self._current_workflow_id]
        state.clear()
        state.query = ctx.text
        state.metadata = ctx.metadata or {}  # Store request metadata (includes lite_mode_enabled)

        lite_mode = state.metadata.get("lite_mode_enabled", False)
        logger.info(
            f"[PlanModeAgent] New query: {ctx.text[:50]}... "
            f"(workflow={self._current_workflow_id}, lite_mode={lite_mode})"
        )

        try:
            response = await self.on_query(ctx.text)
            await self._emit_response(ctx.plan_mode, response)
        except Exception as e:
            logger.exception(f"Error in on_query: {e}")
            await ctx.plan_mode.error("query_failed", str(e))

    async def _handle_response(self, ctx: ResponseContext):
        """Route responses to appropriate handler."""
        self._current_ctx = ctx
        plan = ctx.plan_mode

        # Look up the original workflow ID from the interaction ID
        # (session_id changes between requests, but interaction IDs are stable)
        original_workflow_id = None
        if ctx.response_type == "selection" and ctx.selection_id:
            original_workflow_id = _selection_to_workflow.get(ctx.selection_id)
        elif ctx.response_type == "clarification" and ctx.clarification_id:
            original_workflow_id = _clarification_to_workflow.get(ctx.clarification_id)
        elif ctx.response_type == "plan" and ctx.plan_id:
            original_workflow_id = _plan_to_workflow.get(ctx.plan_id)
        elif ctx.response_type == "permission" and ctx.permission_id:
            original_workflow_id = _permission_to_workflow.get(ctx.permission_id)

        # Use the original workflow ID if found, otherwise fall back to session ID
        self._current_workflow_id = original_workflow_id or self._get_workflow_id(ctx)

        logger.info(
            f"[PlanModeAgent] Response type={ctx.response_type} "
            f"(workflow={self._current_workflow_id}, "
            f"resolved_from={'interaction_id' if original_workflow_id else 'session_id'})"
        )

        try:
            if ctx.response_type == "clarification":
                if ctx.answers:
                    plan.set_clarification_response(ctx.answers, ctx.clarification_id)
                response = await self.on_clarification(ctx.answers or {})
                await self._emit_response(plan, response)

            elif ctx.response_type == "selection":
                selected = ctx.selected_ids or []
                plan.set_selection_response(selected, ctx.selection_id)
                self.state.selected = selected
                response = await self.on_selection(selected)
                await self._emit_response(plan, response)

            elif ctx.response_type == "plan":
                plan.set_plan_approval(ctx.approved or False, ctx.plan_id)
                if not ctx.approved:
                    await plan.error("cancelled", "Cancelled by user", recoverable=True)
                    return

                await plan.start_execution("Starting...")
                response = await self.on_execute()
                await self._emit_response(plan, response)

            elif ctx.response_type == "permission":
                plan.set_permission_response(ctx.approved or False, ctx.permission_id)
                response = await self.on_permission(
                    approved=ctx.approved or False,
                    action=ctx.permission_action or "",
                    details=ctx.permission_details or {},
                )
                await self._emit_response(plan, response)

        except Exception as e:
            logger.exception(f"Error in handler: {e}")
            await plan.error("handler_failed", str(e))

    async def _emit_response(self, plan: PlanModeContext, response: AgentResponse):
        """Convert agent response to SDK calls, with lite mode handling.

        In lite mode (metadata.lite_mode_enabled=True), interactive phases are
        automatically handled without requiring user input:
        - Clarification: Auto-select first option for each question, re-run on_query
        - Discovery: Auto-select top N items, call on_selection
        - Preview: Auto-approve, call on_execute
        """
        lite_mode = self.state.metadata.get("lite_mode_enabled", False)
        logger.info(
            f"[PlanModeAgent] _emit_response called with {type(response).__name__} "
            f"(lite_mode={lite_mode})"
        )

        # =====================================================================
        # LITE MODE: Skip clarification - use defaults and re-run on_query
        # =====================================================================
        if isinstance(response, Clarification) and lite_mode:
            logger.info("[PlanModeAgent] Lite mode: Skipping clarification, using defaults")
            default_answers = self._get_default_clarification_answers(response)
            self.state.context.update(default_answers)
            # Re-run on_query with the context updated
            new_response = await self.on_query(self.state.query)
            return await self._emit_response(plan, new_response)  # Recurse

        # =====================================================================
        # LITE MODE: Auto-select from discovery
        # =====================================================================
        if isinstance(response, Discovery) and lite_mode:
            logger.info("[PlanModeAgent] Lite mode: Auto-selecting items from discovery")
            self.state.discovered = response.items
            items = self._to_discovered_items(response.items)

            # Auto-select top N items (respecting max_select constraint)
            max_select = min(
                self._lite_mode_config.max_select,
                response.max_select or len(items),
            )
            selected_ids = [item.id for item in items[:max_select]]
            self.state.selected = selected_ids

            logger.info(
                f"[PlanModeAgent] Lite mode: Auto-selected {len(selected_ids)} items: "
                f"{selected_ids[:3]}{'...' if len(selected_ids) > 3 else ''}"
            )

            # Call on_selection with auto-selected items
            new_response = await self.on_selection(selected_ids)
            return await self._emit_response(plan, new_response)  # Recurse

        # =====================================================================
        # LITE MODE: Auto-approve preview
        # =====================================================================
        if isinstance(response, Preview) and lite_mode and self._lite_mode_config.auto_approve_plan:
            logger.info("[PlanModeAgent] Lite mode: Auto-approving plan, starting execution")
            await plan.start_execution("Starting (lite mode)...")
            new_response = await self.on_execute()
            return await self._emit_response(plan, new_response)  # Recurse

        # =====================================================================
        # NORMAL MODE: Emit interactive events as usual
        # =====================================================================
        if isinstance(response, Discovery):
            items = self._to_discovered_items(response.items)
            self.state.discovered = response.items
            await plan.emit_discovery(items, response.item_type)
            selection_id = await plan.request_selection(
                items=items,
                discovery_type=response.item_type,
                min_select=response.min_select,
                max_select=response.max_select,
                message=response.message,
            )
            # Store mapping: selection_id → workflow_id
            if self._current_workflow_id:
                _selection_to_workflow[selection_id] = self._current_workflow_id
                logger.debug(f"Stored mapping: selection {selection_id} → workflow {self._current_workflow_id}")

        elif isinstance(response, Clarification):
            questions = self._to_questions(response)
            clarification_id = await plan.request_clarification(questions, message=response.question)
            # Store mapping: clarification_id → workflow_id
            if self._current_workflow_id:
                _clarification_to_workflow[clarification_id] = self._current_workflow_id
                logger.debug(f"Stored mapping: clarification {clarification_id} → workflow {self._current_workflow_id}")

        elif isinstance(response, Preview):
            # Build SearchPlanPreview from generic plan dict
            logger.info(f"[PlanModeAgent] Emitting preview: intent={response.intent}")
            preview_obj = SearchPlanPreview(
                user_intent=response.intent,
                subreddits=response.plan.get("targets", []),
                search_keywords=response.plan.get("keywords", []),
                message=response.message,
            )
            plan_id = await plan.emit_preview(preview_obj)
            logger.info(f"[PlanModeAgent] Preview emitted with plan_id={plan_id}")
            # Store mapping: plan_id → workflow_id
            if self._current_workflow_id:
                _plan_to_workflow[plan_id] = self._current_workflow_id
                logger.debug(f"Stored mapping: plan {plan_id} → workflow {self._current_workflow_id}")

        elif isinstance(response, Result):
            await plan.complete(
                result={
                    "answer": response.answer,
                    "recommended_actions": response.recommended_actions,
                    **response.data,
                },
                message=response.answer,
            )

        elif isinstance(response, Error):
            await plan.error(
                "agent_error", response.message, recoverable=response.recoverable
            )

        elif isinstance(response, Permission):
            # Request permission from user
            permission_id = await plan.request_permission(
                action=response.action,
                description=response.description,
                details=response.details,
                message=response.message,
            )
            # Store mapping: permission_id → workflow_id
            if self._current_workflow_id:
                _permission_to_workflow[permission_id] = self._current_workflow_id
                logger.debug(f"Stored mapping: permission {permission_id} → workflow {self._current_workflow_id}")

    def _get_default_clarification_answers(self, clarification: Clarification) -> dict:
        """Generate default answers for clarification in lite mode.

        Priority:
        1. First option if options are available
        2. 'default' for free text questions
        """
        answers = {}
        questions = self._to_questions(clarification)

        for q in questions:
            if q.options:
                # Select first option
                answers[q.id] = q.options[0].id
                logger.debug(f"[LiteMode] Question '{q.id}': selected first option '{q.options[0].id}'")
            else:
                # Free text: use 'default'
                answers[q.id] = "default"
                logger.debug(f"[LiteMode] Question '{q.id}': using 'default' for free text")

        return answers

    # -------------------------------------------------------------------------
    # Converters
    # -------------------------------------------------------------------------

    def _to_discovered_items(self, items: list[dict]) -> list[DiscoveredItem]:
        """Convert dicts to DiscoveredItem objects."""
        return [
            DiscoveredItem(
                id=item.get("id", item.get("name", "")),
                name=item.get("name", ""),
                description=(item.get("description") or "")[:200],
                metadata=item.get("metadata", {}),
            )
            for item in items
        ]

    def _to_questions(self, clarification: Clarification) -> list[Question]:
        """Convert Clarification to Question list."""
        q_type = QuestionType.FREE_TEXT
        options = None

        if clarification.options:
            q_type = QuestionType.SINGLE_CHOICE
            options = [
                QuestionOption(
                    id=opt.get("id", ""),
                    label=opt.get("label", ""),
                    description=opt.get("description", ""),
                )
                for opt in clarification.options
            ]

        return [
            Question(
                id="q1",
                type=q_type,
                question=clarification.question,
                header=clarification.header,
                options=options,
                preview=clarification.preview,
            )
        ]

    # -------------------------------------------------------------------------
    # Run
    # -------------------------------------------------------------------------

    def run(self, **kwargs):
        """Start the agent server."""
        self._server.run(**kwargs)

    @property
    def app(self):
        """FastAPI app for ASGI deployment."""
        return self._server.app
