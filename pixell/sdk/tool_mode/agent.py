"""
ToolBasedAgent - LLM tool-calling based agent.

Unlike PlanModeAgent which enforces phases, ToolBasedAgent uses
LLM tool calling to let the model decide the workflow.

This follows the pattern used by OpenAI's ChatGPT and Anthropic's Claude:
1. User sends query
2. LLM decides which tool(s) to call based on query + tool descriptions
3. Tool executes and returns result
4. Result is sent back to user (or more tools are called)

Key insight: Tools ARE the "subagents". There's no separate supervisor -
the LLM IS the supervisor via tool selection.

Example:
    class RedditAgent(ToolBasedAgent):
        @tool(
            name="generate_content_ideas",
            description="Generate content ideas from Reddit. Use for content creators.",
        )
        async def content_ideas(self, topic: str) -> Result:
            # Fast path - no discovery, direct to result
            return result(answer="Here are content ideas...")

        @tool(
            name="deep_research",
            description="In-depth research with subreddit discovery.",
        )
        async def deep_research(self, query: str) -> Discovery:
            # Slow path - triggers discovery flow
            return discovery(items=subreddits, message="Select subreddits")

    RedditAgent(agent_id="reddit", port=9000).run()
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Union, TypeVar, get_type_hints
import logging
import functools
import inspect

from pixell.sdk.server import AgentServer
from pixell.sdk.a2a.handlers import MessageContext, ResponseContext
from pixell.sdk.plan_mode.context import PlanModeContext
from pixell.sdk.plan_mode.agent import (
    AgentState,
    AgentResponse,
    Discovery,
    Clarification,
    Preview,
    Result,
    Error,
    Permission,
    _workflow_states,
    _selection_to_workflow,
    _clarification_to_workflow,
    _plan_to_workflow,
    _permission_to_workflow,
)
from pixell.sdk.plan_mode.events import (
    DiscoveredItem,
    SearchPlanPreview,
    Question,
    QuestionType,
    QuestionOption,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


# =============================================================================
# Tool Definition
# =============================================================================


@dataclass
class Tool:
    """Tool definition in OpenAI function calling format.

    Each tool represents a capability that the LLM can invoke.
    The description is critical - it tells the LLM when to use this tool.
    """

    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    handler: Optional[Callable] = None  # Async function to execute

    def to_openai_schema(self) -> dict:
        """Convert to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": list(self.parameters.keys()),
                },
            },
        }

    def to_anthropic_schema(self) -> dict:
        """Convert to Anthropic tool use format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": self.parameters,
                "required": list(self.parameters.keys()),
            },
        }


@dataclass
class ToolCall:
    """Represents a tool call from the LLM."""

    name: str
    arguments: dict[str, Any]
    call_id: str = ""


@dataclass
class ToolResult:
    """Result from tool execution."""

    call_id: str
    output: Any
    error: Optional[str] = None


# =============================================================================
# Tool Decorator
# =============================================================================


def tool(
    name: str,
    description: str,
    parameters: Optional[dict[str, Any]] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to register a method as a tool.

    Args:
        name: Tool name (used by LLM to call it)
        description: Description for LLM (critical for tool selection)
        parameters: JSON Schema for parameters (optional, inferred from signature)

    Example:
        @tool(
            name="search_reddit",
            description="Search Reddit for discussions",
            parameters={
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "description": "Max results"},
            }
        )
        async def search(self, query: str, limit: int = 50) -> Result:
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Infer parameters from function signature if not provided
        inferred_params = parameters
        if inferred_params is None:
            inferred_params = _infer_parameters(func)

        # Store tool metadata on the function
        func._tool_metadata = Tool(
            name=name,
            description=description,
            parameters=inferred_params,
            handler=func,
        )
        return func

    return decorator


def _infer_parameters(func: Callable) -> dict[str, Any]:
    """Infer JSON Schema parameters from function signature."""
    sig = inspect.signature(func)
    hints = get_type_hints(func) if hasattr(func, "__annotations__") else {}

    params = {}
    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue

        # Map Python types to JSON Schema types
        param_type = hints.get(param_name, str)
        json_type = _python_to_json_type(param_type)

        params[param_name] = {
            "type": json_type,
            "description": f"The {param_name} parameter",
        }

        # Add default if present
        if param.default is not inspect.Parameter.empty:
            params[param_name]["default"] = param.default

    return params


def _python_to_json_type(python_type: type) -> str:
    """Map Python type to JSON Schema type."""
    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }
    return type_map.get(python_type, "string")


# =============================================================================
# ToolBasedAgent Base Class
# =============================================================================


class ToolBasedAgent(ABC):
    """
    Base class for tool-based agents.

    Unlike PlanModeAgent which has fixed phases, ToolBasedAgent lets the
    LLM decide which tools to call. Tools can return:
    - Result: Complete immediately (fast path)
    - Discovery: Trigger selection UI (slow path, for research tools)
    - Clarification: Ask user questions
    - Error: Fail with message

    Subclass and implement:
    - select_tools(query, tools): LLM-based tool selection
    - Define tool methods with @tool decorator

    Optionally override:
    - on_selection(selected): Handle selection (for tools returning Discovery)
    - on_clarification(answers): Handle clarification answers
    - on_execute(): Execute after selection/preview
    """

    def __init__(
        self,
        agent_id: str,
        name: str = "",
        description: str = "",
        port: int = 8000,
        host: str = "0.0.0.0",
        outputs_dir: Optional[str] = None,
    ):
        """
        Initialize the agent.

        Args:
            agent_id: Unique identifier for this agent
            name: Human-readable name
            description: Agent description
            port: Port to run on
            host: Host to bind to
            outputs_dir: Directory for output files
        """
        self._current_ctx: Optional[Union[MessageContext, ResponseContext]] = None
        self._current_workflow_id: Optional[str] = None
        self._registered_tools: dict[str, Tool] = {}

        # Auto-discover tools from decorated methods
        self._discover_tools()

        self._server = AgentServer(
            agent_id=agent_id,
            name=name or agent_id,
            description=description,
            port=port,
            host=host,
            plan_mode_config={
                "phases": ["clarification", "discovery", "selection", "preview"],
                "discoveryType": "items",
            },
            outputs_dir=outputs_dir,
        )

        # Register handlers
        self._server.on_message(self._handle_message)
        self._server.on_respond(self._handle_response)

    # -------------------------------------------------------------------------
    # Tool Registration
    # -------------------------------------------------------------------------

    def _discover_tools(self):
        """Auto-discover tools from decorated methods."""
        for attr_name in dir(self):
            attr = getattr(self, attr_name, None)
            if attr and hasattr(attr, "_tool_metadata"):
                tool_meta: Tool = attr._tool_metadata
                # Bind the handler to self
                tool_meta.handler = attr
                self._registered_tools[tool_meta.name] = tool_meta
                logger.info(f"Registered tool: {tool_meta.name}")

    def register_tool(self, tool_def: Tool):
        """Manually register a tool.

        Use this to add tools that aren't defined as methods on the class.

        Args:
            tool_def: Tool definition with handler
        """
        self._registered_tools[tool_def.name] = tool_def
        logger.info(f"Registered tool: {tool_def.name}")

    @property
    def tools(self) -> list[Tool]:
        """Get all registered tools."""
        return list(self._registered_tools.values())

    def get_tool_schemas(self, format: str = "openai") -> list[dict]:
        """Get tool schemas for LLM.

        Args:
            format: "openai" or "anthropic"

        Returns:
            List of tool schemas in the specified format
        """
        if format == "anthropic":
            return [t.to_anthropic_schema() for t in self.tools]
        return [t.to_openai_schema() for t in self.tools]

    # -------------------------------------------------------------------------
    # State Management (workflow-based, survives session changes)
    # -------------------------------------------------------------------------

    def _get_workflow_id(self, ctx: Union[MessageContext, ResponseContext]) -> str:
        """Extract workflow ID from context."""
        if hasattr(ctx, "stream") and ctx.stream:
            return getattr(ctx.stream, "workflow_id", None) or ctx.session_id
        return ctx.session_id

    @property
    def state(self) -> AgentState:
        """Current workflow state."""
        if self._current_workflow_id and self._current_workflow_id in _workflow_states:
            return _workflow_states[self._current_workflow_id]
        return AgentState()

    # -------------------------------------------------------------------------
    # Abstract Methods (implement these)
    # -------------------------------------------------------------------------

    @abstractmethod
    async def select_tools(
        self,
        query: str,
        tools: list[Tool],
    ) -> list[ToolCall]:
        """
        Use LLM to select which tools to call for the query.

        This is the core intelligence method - implement it using your
        preferred LLM provider (OpenAI, Anthropic, etc.).

        Args:
            query: User's query
            tools: Available tools (with schemas)

        Returns:
            List of ToolCalls the LLM decided to make.
            Return empty list if no tools should be called.

        Example using OpenAI:
            async def select_tools(self, query, tools):
                response = await openai.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": query}],
                    tools=[t.to_openai_schema() for t in tools],
                )
                return [
                    ToolCall(name=tc.name, arguments=tc.arguments)
                    for tc in response.tool_calls or []
                ]

        Example using Anthropic:
            async def select_tools(self, query, tools):
                response = await anthropic.messages.create(
                    model="claude-3-opus",
                    messages=[{"role": "user", "content": query}],
                    tools=[t.to_anthropic_schema() for t in tools],
                )
                # Parse tool_use blocks
                ...
        """
        pass

    # -------------------------------------------------------------------------
    # Optional Override Methods
    # -------------------------------------------------------------------------

    async def on_selection(self, selected: list[str]) -> AgentResponse:
        """
        Handle user selection (when a tool returns Discovery).

        Default: Execute with selected items.
        Override to customize behavior.

        Args:
            selected: List of selected item IDs

        Returns:
            Preview to show execution preview, or Error
        """
        # Default: go to preview
        return Preview(
            intent=f"Execute with {len(selected)} selected items",
            plan={"selected": selected},
        )

    async def on_execute(self) -> AgentResponse:
        """
        Execute the task after preview approval.

        Default: Not implemented (tools should return Result directly).
        Override if you have tools that return Discovery/Preview.

        Returns:
            Result with answer, or Error
        """
        return Error(message="on_execute not implemented")

    async def on_clarification(self, answers: dict) -> AgentResponse:
        """
        Handle clarification answers.

        Default: store answers and re-run with updated context.
        Override to customize behavior.

        Args:
            answers: Dict of question_id -> answer

        Returns:
            Next response (Result, Discovery, etc.)
        """
        self.state.context.update(answers)
        # Re-run the query with updated context
        return await self._process_query(self.state.query)

    # -------------------------------------------------------------------------
    # Helper Methods (use in tool implementations)
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
        """Notify that a file was created."""
        if self._current_ctx:
            await self._current_ctx.emit_file_created(path, name=name, summary=summary)

    # -------------------------------------------------------------------------
    # Internal Handlers
    # -------------------------------------------------------------------------

    async def _handle_message(self, ctx: MessageContext):
        """Handle new message - route to LLM for tool selection."""
        self._current_ctx = ctx
        self._current_workflow_id = self._get_workflow_id(ctx)

        # Initialize state for this workflow
        if self._current_workflow_id not in _workflow_states:
            _workflow_states[self._current_workflow_id] = AgentState()

        state = _workflow_states[self._current_workflow_id]
        state.clear()
        state.query = ctx.text
        state.metadata = ctx.metadata or {}

        logger.info(f"[ToolBasedAgent] New query: {ctx.text[:50]}...")

        try:
            response = await self._process_query(ctx.text)
            await self._emit_response(ctx.plan_mode, response)
        except Exception as e:
            logger.exception(f"Error processing query: {e}")
            await ctx.plan_mode.error("query_failed", str(e))

    async def _process_query(self, query: str) -> AgentResponse:
        """Process query using LLM tool selection."""
        # Let LLM select tools
        tool_calls = await self.select_tools(query, self.tools)

        if not tool_calls:
            # No tools selected - return generic response
            return Result(answer="I'm not sure how to help with that.")

        # Execute first tool call
        # (Future: could support parallel tool execution)
        tool_call = tool_calls[0]
        tool_def = self._registered_tools.get(tool_call.name)

        if not tool_def:
            return Error(message=f"Unknown tool: {tool_call.name}")

        if not tool_def.handler:
            return Error(message=f"Tool {tool_call.name} has no handler")

        # Execute the tool
        logger.info(f"[ToolBasedAgent] Executing tool: {tool_call.name}")
        await self.emit_progress(f"Running {tool_call.name}...")

        # Filter out internal keys (starting with _) before passing to handler
        filtered_args = {k: v for k, v in tool_call.arguments.items() if not k.startswith("_")}

        try:
            response = await tool_def.handler(**filtered_args)
            return response
        except Exception as e:
            logger.exception(f"Tool execution error: {e}")
            return Error(message=f"Tool error: {str(e)}")

    async def _handle_response(self, ctx: ResponseContext):
        """Handle responses (selection, clarification, plan approval)."""
        self._current_ctx = ctx
        plan = ctx.plan_mode

        # Look up original workflow
        original_workflow_id = None
        if ctx.response_type == "selection" and ctx.selection_id:
            original_workflow_id = _selection_to_workflow.get(ctx.selection_id)
        elif ctx.response_type == "clarification" and ctx.clarification_id:
            original_workflow_id = _clarification_to_workflow.get(ctx.clarification_id)
        elif ctx.response_type == "plan" and ctx.plan_id:
            original_workflow_id = _plan_to_workflow.get(ctx.plan_id)

        self._current_workflow_id = original_workflow_id or self._get_workflow_id(ctx)

        logger.info(
            f"[ToolBasedAgent] Response type={ctx.response_type} "
            f"(workflow={self._current_workflow_id})"
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

        except Exception as e:
            logger.exception(f"Error in handler: {e}")
            await plan.error("handler_failed", str(e))

    async def _emit_response(self, plan: PlanModeContext, response: AgentResponse):
        """Convert agent response to SDK calls.

        In lite mode, interactive responses (Discovery, Clarification, Preview)
        are auto-handled without waiting for user input.
        """
        lite_mode = self.state.metadata.get("lite_mode_enabled", False)

        if isinstance(response, Discovery):
            if lite_mode:
                # Auto-select top items and continue without user interaction
                items = response.items[:5]  # Top 5
                selected_ids = [
                    item.get("id", item.get("name", ""))
                    for item in items
                    if item.get("id") or item.get("name")
                ]
                logger.info(f"[Lite Mode] Auto-selecting {len(selected_ids)} items from discovery")
                self.state.discovered = response.items
                self.state.selected = selected_ids
                new_response = await self.on_selection(selected_ids)
                return await self._emit_response(plan, new_response)  # Recurse
            else:
                # Normal: emit discovery + request selection
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
                if self._current_workflow_id:
                    _selection_to_workflow[selection_id] = self._current_workflow_id

        elif isinstance(response, Clarification):
            if lite_mode:
                # Auto-answer with defaults and continue
                default_answers = self._get_default_clarification_answers(response)
                logger.info(f"[Lite Mode] Auto-answering clarification: {default_answers}")
                self.state.context.update(default_answers)
                new_response = await self.on_clarification(default_answers)
                return await self._emit_response(plan, new_response)  # Recurse
            else:
                # Normal: request clarification from user
                questions = self._to_questions(response)
                clarification_id = await plan.request_clarification(
                    questions, message=response.question
                )
                if self._current_workflow_id:
                    _clarification_to_workflow[clarification_id] = self._current_workflow_id

        elif isinstance(response, Preview):
            if lite_mode:
                # Auto-approve and execute
                logger.info("[Lite Mode] Auto-approving preview, starting execution")
                await plan.start_execution("Starting...")
                new_response = await self.on_execute()
                return await self._emit_response(plan, new_response)  # Recurse
            else:
                # Normal: emit preview and wait for approval
                preview_obj = SearchPlanPreview(
                    user_intent=response.intent,
                    subreddits=response.plan.get("targets", []),
                    search_keywords=response.plan.get("keywords", []),
                    message=response.message,
                )
                plan_id = await plan.emit_preview(preview_obj)
                if self._current_workflow_id:
                    _plan_to_workflow[plan_id] = self._current_workflow_id

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

    def _get_default_clarification_answers(self, clarification: Clarification) -> dict:
        """Generate default answers for lite mode clarification auto-response."""
        answers = {}
        questions = self._to_questions(clarification)
        for q in questions:
            if q.options:
                # Select first option
                answers[q.id] = q.options[0].id
            else:
                # Free text fallback
                answers[q.id] = "default"
        return answers

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
