"""
PixellSDK Runtime - Import this in your agent code

This module provides runtime infrastructure for agent execution:
- UserContext: Execution context with access to user data and APIs
- TaskConsumer: Redis task queue consumer
- PXUIDataClient: HTTP client for PXUI API
- ProgressReporter: Real-time progress updates via Redis pub/sub

Example:
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

__all__ = [
    # Core components
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
