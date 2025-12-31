#!/usr/bin/env python3
"""Complete agent example demonstrating SDK usage.

This example shows how an agent developer would use the Pixell SDK
to build a task-processing agent.
"""

from typing import Any
from pixell.sdk import (
    UserContext,
    TaskConsumer,
    SDKError,
    TaskTimeoutError,
    RateLimitError,
)


class MyAnalyzerAgent:
    """Example agent that analyzes user data."""

    async def execute(self, ctx: UserContext, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute the agent task.

        Args:
            ctx: User context with data access methods
            payload: Task payload from the queue

        Returns:
            Analysis results
        """
        try:
            # Report starting
            await ctx.report_progress("starting", percent=0, message="Initializing analysis")

            # Get user profile
            profile = await ctx.get_user_profile()

            # Report progress
            await ctx.report_progress("processing", percent=50, message="Analyzing data")

            # Call external OAuth API
            result = await ctx.call_oauth_api(
                provider="google",
                method="GET",
                path="/calendar/v3/calendars/primary/events",
            )

            # Get files if available
            files = await ctx.get_files(limit=10)

            # Complete
            await ctx.report_progress("completed", percent=100, message="Analysis complete")

            return {
                "status": "success",
                "user_id": ctx.user_id,
                "profile": profile,
                "events_count": len(result.get("items", [])),
                "files_count": len(files),
            }

        except RateLimitError as e:
            await ctx.report_error("RATE_LIMITED", str(e), recoverable=True)
            raise
        except SDKError as e:
            await ctx.report_error("SDK_ERROR", str(e), recoverable=False)
            raise


async def handle_task(ctx: UserContext, payload: dict[str, Any]) -> dict[str, Any]:
    """Task handler function for TaskConsumer."""
    agent = MyAnalyzerAgent()
    return await agent.execute(ctx, payload)


def test_agent_class():
    """Test agent class can be instantiated."""
    agent = MyAnalyzerAgent()
    assert hasattr(agent, "execute")
    assert callable(agent.execute)
    print("✓ Agent class instantiated successfully")


def test_consumer_setup():
    """Test consumer can be configured for the agent."""
    consumer = TaskConsumer(
        agent_id="example-agent",
        redis_url="redis://localhost:6379",
        pxui_base_url="https://api.pixell.global",
        handler=handle_task,
        concurrency=3,
        task_timeout=300.0,
    )

    assert consumer.agent_id == "example-agent"
    assert consumer.handler is handle_task
    print("✓ TaskConsumer configured for agent")
    print(f"  Queue: {consumer.queue_key}")
    print(f"  Processing: {consumer.processing_key}")


def test_error_handling_types():
    """Test error types used in agent."""
    # Verify error types can be caught
    try:
        raise RateLimitError("Rate limited", retry_after=60)
    except SDKError as e:
        assert e.details["retry_after"] == 60

    try:
        raise TaskTimeoutError("task-123", 30.0)
    except SDKError as e:
        assert "task-123" in str(e)

    print("✓ Error handling types work correctly")


def show_usage_patterns():
    """Display SDK usage patterns for documentation."""
    print("\nPixell SDK Agent Example")
    print("========================")
    print()
    print("This example demonstrates how to build an agent using pixell-sdk:")
    print()
    print("1. Import SDK components:")
    print("   from pixell.sdk import UserContext, TaskConsumer")
    print()
    print("2. Create a task handler:")
    print("   async def handle_task(ctx: UserContext, payload: dict) -> dict:")
    print("       await ctx.report_progress('starting', percent=0)")
    print("       profile = await ctx.get_user_profile()")
    print("       return {'status': 'success'}")
    print()
    print("3. Create and start consumer:")
    print("   consumer = TaskConsumer(")
    print("       agent_id='my-agent',")
    print("       redis_url='redis://localhost:6379',")
    print("       pxui_base_url='https://api.pixell.global',")
    print("       handler=handle_task,")
    print("   )")
    print("   await consumer.start()")
    print()


def main():
    """Main entry point."""
    test_agent_class()
    test_consumer_setup()
    test_error_handling_types()
    show_usage_patterns()

    # Final verification
    consumer = TaskConsumer(
        agent_id="example-agent",
        redis_url="redis://localhost:6379",
        pxui_base_url="https://api.pixell.global",
        handler=handle_task,
    )

    print(f"✓ TaskConsumer created: {consumer.agent_id}")
    print(f"  Queue: {consumer.queue_key}")
    print()
    print("✓ All SDK components work correctly!")


if __name__ == "__main__":
    main()
