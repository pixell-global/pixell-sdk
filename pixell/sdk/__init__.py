"""
PixellSDK Runtime - Import this in your agent code

This module provides runtime infrastructure for agent execution:
- AgentServer: Unified FastAPI server for A2A protocol
- UserContext: Execution context with access to user data and APIs
- TaskConsumer: Redis task queue consumer
- PXUIDataClient: HTTP client for PXUI API
- ProgressReporter: Real-time progress updates via Redis pub/sub

New A2A & Plan Mode Features:
- AgentServer: FastAPI-style server with decorator-based handlers
- Plan Mode: Multi-phase workflows (clarification, discovery, selection, preview)
- Translation: Interface for agent-owned i18n

Example (A2A Server):
    from pixell.sdk import AgentServer, MessageContext
    from pixell.sdk.plan_mode import Question, QuestionType

    server = AgentServer(
        agent_id="my-agent",
        port=9998,
        plan_mode_config={"phases": ["clarification", "preview"]},
    )

    @server.on_message
    async def handle_message(ctx: MessageContext):
        await ctx.emit_status("working", "Processing...")
        await ctx.plan_mode.request_clarification([
            Question(id="topic", type=QuestionType.FREE_TEXT, question="What topic?")
        ])

    @server.on_respond
    async def handle_respond(ctx):
        answers = ctx.answers
        await ctx.emit_result("Done!", {"answers": answers})

    server.run()

Example (TaskConsumer - legacy):
    from pixell.sdk import UserContext, TaskConsumer

    async def handle_task(ctx: UserContext, payload: dict) -> dict:
        await ctx.report_progress("starting", percent=0)
        profile = await ctx.get_user_profile()
        result = await ctx.call_oauth_api(
            provider="google",
            method="GET",
            path="/calendar/v3/calendars/primary/events"
        )
        await ctx.report_progress("completed", percent=100)
        return {"status": "success", "data": result}

    consumer = TaskConsumer(
        agent_id="my-agent",
        redis_url="redis://localhost:6379",
        pxui_base_url="https://api.pixell.global",
        handler=handle_task,
    )
    await consumer.start()
"""

# Core runtime components (backwards compatible)
from pixell.sdk.context import UserContext, TaskMetadata
from pixell.sdk.task_consumer import TaskConsumer
from pixell.sdk.data_client import PXUIDataClient
from pixell.sdk.progress import ProgressReporter
from pixell.sdk.errors import (
    SDKError,
    ConsumerError,
    TaskTimeoutError,
    TaskHandlerError,
    QueueError,
    ClientError,
    AuthenticationError,
    RateLimitError,
    APIError,
    ConnectionError,
    ContextError,
    ContextNotInitializedError,
    ProgressError,
)

# New A2A Server
from pixell.sdk.server import AgentServer

# A2A Protocol (contexts available at submodule level)
from pixell.sdk.a2a.handlers import MessageContext, ResponseContext

# Plan Mode - Core types exported directly for external developer convenience
# These are the primary types developers need for multi-phase workflows
from pixell.sdk.plan_mode import (
    PlanModeContext,
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
    Phase,
    # Schedule proposal types
    IntervalSpec,
    ScheduleProposal,
    ScheduleResponse,
    # PlanModeAgent base class and response types
    PlanModeAgent,
    Discovery,
    Clarification,
    Preview,
    Result,
    Error,
    Permission,
    AgentState,
    discovery,
    clarify,
    preview,
    result,
    error,
    permission,
)

__all__ = [
    # New A2A Server
    "AgentServer",
    "MessageContext",
    "ResponseContext",
    # Plan Mode - exported directly for convenience
    "PlanModeContext",
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
    "Phase",
    # Schedule proposal types
    "IntervalSpec",
    "ScheduleProposal",
    "ScheduleResponse",
    # PlanModeAgent base class and response types
    "PlanModeAgent",
    "Discovery",
    "Clarification",
    "Preview",
    "Result",
    "Error",
    "Permission",
    "AgentState",
    "discovery",
    "clarify",
    "preview",
    "result",
    "error",
    "permission",
    # Core components (backwards compatible)
    "UserContext",
    "TaskMetadata",
    "TaskConsumer",
    "PXUIDataClient",
    "ProgressReporter",
    # Errors
    "SDKError",
    "ConsumerError",
    "TaskTimeoutError",
    "TaskHandlerError",
    "QueueError",
    "ClientError",
    "AuthenticationError",
    "RateLimitError",
    "APIError",
    "ConnectionError",
    "ContextError",
    "ContextNotInitializedError",
    "ProgressError",
]
