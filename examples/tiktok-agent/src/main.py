"""TikTok Profile Analyzer Agent.

This example demonstrates how to build an agent using the PixellSDK runtime.
The agent analyzes TikTok profiles for engagement metrics and trends.
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Any

from pixell.sdk import UserContext, TaskConsumer


class TikTokAnalyzerAgent:
    """TikTok Profile Analyzer Agent.

    Analyzes TikTok profiles for engagement metrics and trends.
    Uses the PixellSDK to access user data and OAuth APIs.
    """

    async def execute(self, context: UserContext, payload: dict[str, Any]) -> dict[str, Any]:
        """Main execution method.

        Args:
            context: User context with data access methods
            payload: Task payload with prompt and options

        Returns:
            Analysis results
        """
        try:
            # Report starting
            await context.report_progress("starting", percent=0)

            # Get user's prompt from payload
            prompt = payload.get("prompt", "Analyze my TikTok profile")
            print(f"Processing prompt: {prompt}")

            # Step 1: Fetch TikTok profile
            await context.report_progress(
                "fetching_profile", percent=20, message="Fetching TikTok profile"
            )

            profile = await context.call_oauth_api(
                provider="tiktok",
                method="GET",
                path="/v2/user/info/",
                body={"fields": "display_name,follower_count,following_count,likes_count"},
            )

            # Step 2: Fetch user's files (if they uploaded comparison data)
            await context.report_progress(
                "checking_files", percent=40, message="Checking for uploaded data"
            )

            files = await context.get_files(filter={"type": "csv"}, limit=10)
            has_comparison_data = len(files) > 0

            # Step 3: Get historical data from previous runs
            await context.report_progress(
                "loading_history", percent=60, message="Loading historical data"
            )

            history = await context.get_task_history(agent_id="tiktok-analyzer", limit=5)

            # Step 4: Analyze metrics
            await context.report_progress("analyzing", percent=80, message="Analyzing metrics")

            metrics = self._analyze_profile(profile, history)

            # Step 5: Complete
            await context.report_progress("completed", percent=100, message="Analysis complete")

            return {
                "username": profile.get("data", {}).get("user", {}).get("display_name", "Unknown"),
                "metrics": metrics,
                "timestamp": datetime.utcnow().isoformat(),
                "has_comparison_data": has_comparison_data,
                "prompt": prompt,
            }

        except Exception as e:
            # Report error
            await context.report_error(
                error_type="ANALYSIS_FAILED",
                message=str(e),
                recoverable=False,
            )
            raise

    def _analyze_profile(
        self, profile: dict[str, Any], history: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Analyze TikTok profile data.

        Args:
            profile: TikTok profile data from API
            history: Previous analysis results

        Returns:
            Metrics dictionary with analysis results
        """
        user_data = profile.get("data", {}).get("user", {})

        followers = user_data.get("follower_count", 0)
        following = user_data.get("following_count", 0)
        likes = user_data.get("likes_count", 0)

        # Calculate engagement rate (simplified)
        engagement_rate = (likes / followers) if followers > 0 else 0

        # Determine trend by comparing with history
        trend = "stable"
        if history:
            try:
                latest_result = history[0].get("result", {})
                if isinstance(latest_result, str):
                    latest_result = json.loads(latest_result)

                prev_metrics = latest_result.get("metrics", {})
                prev_followers = prev_metrics.get("followers", followers)

                if followers > prev_followers * 1.1:
                    trend = "increasing"
                elif followers < prev_followers * 0.9:
                    trend = "decreasing"
            except (KeyError, json.JSONDecodeError, TypeError):
                pass

        return {
            "followers": followers,
            "following": following,
            "total_likes": likes,
            "engagement_rate": round(engagement_rate, 4),
            "trend": trend,
        }


# Create agent instance
agent = TikTokAnalyzerAgent()


async def handle_task(ctx: UserContext, payload: dict[str, Any]) -> dict[str, Any]:
    """Task handler function for the TaskConsumer.

    This is the entrypoint that TaskConsumer calls for each task.

    Args:
        ctx: User context with data access methods
        payload: Task payload

    Returns:
        Task result
    """
    return await agent.execute(ctx, payload)


async def main():
    """Entry point for TikTok Analyzer Agent."""
    # Get configuration from environment
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    pxui_base_url = os.environ.get("PXUI_BASE_URL", "https://api.pixell.global")

    # Create task consumer
    consumer = TaskConsumer(
        agent_id="tiktok-analyzer",
        redis_url=redis_url,
        pxui_base_url=pxui_base_url,
        handler=handle_task,
        concurrency=5,
        task_timeout=120.0,
    )

    print("TikTok Analyzer Agent started")
    print(f"Redis: {redis_url}")
    print(f"PXUI API: {pxui_base_url}")
    print("Waiting for tasks...")

    # Start consuming tasks
    async with consumer:
        await consumer.start()


if __name__ == "__main__":
    asyncio.run(main())
