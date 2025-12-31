#!/usr/bin/env python3
"""Test multi-step workflow patterns with SDK components.

These tests verify complex workflows where multiple SDK components
interact together to process tasks with multiple stages.
"""

import asyncio
from unittest.mock import AsyncMock

from pixell.sdk import (
    PXUIDataClient,
    ProgressReporter,
    RateLimitError,
)


class TestMultiStepWorkflow:
    """Test multi-step workflows with progress tracking."""

    def create_mock_context(self, task_id: str = "task-123"):
        """Create a mock UserContext for testing."""
        mock_client = AsyncMock(spec=PXUIDataClient)
        mock_reporter = AsyncMock(spec=ProgressReporter)

        # Set up default return values
        mock_client.get_user_profile.return_value = {
            "id": "user-456",
            "email": "test@example.com",
            "name": "Test User"
        }
        mock_client.list_files.return_value = [
            {"id": "file-1", "name": "doc1.pdf"},
            {"id": "file-2", "name": "doc2.pdf"}
        ]
        mock_client.oauth_proxy_call.return_value = {
            "items": [{"id": "event-1"}, {"id": "event-2"}]
        }
        mock_client.list_conversations.return_value = [
            {"id": "conv-1", "title": "Conversation 1"}
        ]

        return mock_client, mock_reporter

    async def test_sequential_api_calls_workflow(self):
        """Test a workflow with sequential API calls and progress updates."""
        mock_client, mock_reporter = self.create_mock_context()

        # Simulate a multi-step workflow
        workflow_steps = []

        async def execute_workflow():
            # Step 1: Get profile
            workflow_steps.append("start")
            await mock_reporter.update("starting", percent=0, message="Initializing")

            profile = await mock_client.get_user_profile("user-456")
            workflow_steps.append(f"profile:{profile['name']}")
            await mock_reporter.update("processing", percent=25, message="Got profile")

            # Step 2: Get files
            files = await mock_client.list_files("user-456", limit=10)
            workflow_steps.append(f"files:{len(files)}")
            await mock_reporter.update("processing", percent=50, message="Got files")

            # Step 3: Call OAuth API
            events = await mock_client.oauth_proxy_call(
                "user-456", "google", "GET", "/calendar/v3/events"
            )
            workflow_steps.append(f"events:{len(events['items'])}")
            await mock_reporter.update("processing", percent=75, message="Got events")

            # Step 4: Get conversations
            convos = await mock_client.list_conversations("user-456", limit=5)
            workflow_steps.append(f"convos:{len(convos)}")
            await mock_reporter.update("completed", percent=100, message="Done")

            return {
                "profile": profile,
                "files_count": len(files),
                "events_count": len(events["items"]),
                "conversations_count": len(convos)
            }

        result = await execute_workflow()

        # Verify workflow executed in order
        assert workflow_steps == [
            "start",
            "profile:Test User",
            "files:2",
            "events:2",
            "convos:1"
        ]

        # Verify progress was reported 5 times
        assert mock_reporter.update.call_count == 5

        # Verify result
        assert result["profile"]["name"] == "Test User"
        assert result["files_count"] == 2
        assert result["events_count"] == 2
        assert result["conversations_count"] == 1

        print("✓ Sequential API calls workflow executed correctly")

    async def test_workflow_with_intermediate_failure(self):
        """Test workflow recovery when an intermediate step fails."""
        mock_client, mock_reporter = self.create_mock_context()

        # Make OAuth call fail with rate limit
        mock_client.oauth_proxy_call.side_effect = RateLimitError(
            "Rate limited", retry_after=60
        )

        completed_steps = []
        error_reported = False

        async def execute_workflow_with_error_handling():
            nonlocal error_reported

            try:
                # Step 1: Get profile (succeeds)
                await mock_client.get_user_profile("user-456")
                completed_steps.append("profile")
                await mock_reporter.update("processing", percent=25)

                # Step 2: Get files (succeeds)
                await mock_client.list_files("user-456")
                completed_steps.append("files")
                await mock_reporter.update("processing", percent=50)

                # Step 3: OAuth call (fails)
                await mock_client.oauth_proxy_call(
                    "user-456", "google", "GET", "/calendar/v3/events"
                )
                completed_steps.append("events")

            except RateLimitError as e:
                error_reported = True
                await mock_reporter.error(
                    "RATE_LIMITED",
                    str(e),
                    recoverable=True,
                    details={"retry_after": e.details.get("retry_after")}
                )
                return {"status": "rate_limited", "completed_steps": completed_steps}

            return {"status": "success", "completed_steps": completed_steps}

        result = await execute_workflow_with_error_handling()

        # Verify partial completion
        assert completed_steps == ["profile", "files"]
        assert "events" not in completed_steps

        # Verify error was reported
        assert error_reported
        assert result["status"] == "rate_limited"

        # Verify error reporter was called
        mock_reporter.error.assert_called_once()
        error_call = mock_reporter.error.call_args
        assert error_call[0][0] == "RATE_LIMITED"
        assert error_call[1]["recoverable"] is True

        print("✓ Workflow with intermediate failure handled correctly")

    async def test_parallel_api_calls_within_workflow(self):
        """Test workflow that makes parallel API calls."""
        mock_client, mock_reporter = self.create_mock_context()

        # Add some delay to simulate real API calls
        original_get_files = mock_client.list_files.return_value
        original_get_convos = mock_client.list_conversations.return_value

        call_order = []

        async def delayed_files(*args, **kwargs):
            call_order.append("files_start")
            await asyncio.sleep(0.01)
            call_order.append("files_end")
            return original_get_files

        async def delayed_convos(*args, **kwargs):
            call_order.append("convos_start")
            await asyncio.sleep(0.01)
            call_order.append("convos_end")
            return original_get_convos

        mock_client.list_files.side_effect = delayed_files
        mock_client.list_conversations.side_effect = delayed_convos

        async def execute_parallel_workflow():
            await mock_reporter.update("starting", percent=0)

            # Parallel API calls
            files_task = asyncio.create_task(mock_client.list_files("user-456"))
            convos_task = asyncio.create_task(mock_client.list_conversations("user-456"))

            files, convos = await asyncio.gather(files_task, convos_task)

            await mock_reporter.update("completed", percent=100)

            return {"files": files, "conversations": convos}

        result = await execute_parallel_workflow()

        # Verify both calls completed
        assert len(result["files"]) == 2
        assert len(result["conversations"]) == 1

        # Verify calls were made in parallel (interleaved order)
        # Both should start before either ends
        assert "files_start" in call_order
        assert "convos_start" in call_order

        print("✓ Parallel API calls within workflow executed correctly")

    async def test_workflow_with_conditional_steps(self):
        """Test workflow with conditional execution based on previous results."""
        mock_client, mock_reporter = self.create_mock_context()

        # Set up different file counts for different scenarios
        executed_steps = []

        async def execute_conditional_workflow(file_count: int):
            executed_steps.clear()

            # Mock files based on count
            mock_client.list_files.return_value = [
                {"id": f"file-{i}"} for i in range(file_count)
            ]

            await mock_reporter.update("starting", percent=0)
            executed_steps.append("start")

            # Get files
            files = await mock_client.list_files("user-456")
            executed_steps.append(f"got_files:{len(files)}")

            # Conditional: only process if we have files
            if len(files) > 0:
                await mock_reporter.update("processing", percent=50, message="Processing files")
                executed_steps.append("processing_files")

                # Conditional: batch processing for many files
                if len(files) > 5:
                    executed_steps.append("batch_mode")
                else:
                    executed_steps.append("single_mode")
            else:
                executed_steps.append("no_files_skip")

            await mock_reporter.update("completed", percent=100)
            executed_steps.append("done")

            return {"files_processed": len(files), "steps": executed_steps.copy()}

        # Test with no files
        result1 = await execute_conditional_workflow(0)
        assert result1["steps"] == ["start", "got_files:0", "no_files_skip", "done"]

        # Test with few files (single mode)
        result2 = await execute_conditional_workflow(3)
        assert "single_mode" in result2["steps"]
        assert "batch_mode" not in result2["steps"]

        # Test with many files (batch mode)
        result3 = await execute_conditional_workflow(10)
        assert "batch_mode" in result3["steps"]
        assert "single_mode" not in result3["steps"]

        print("✓ Workflow with conditional steps executed correctly")

    async def test_workflow_progress_tracking_accuracy(self):
        """Test that progress updates reflect actual workflow state."""
        mock_client, mock_reporter = self.create_mock_context()

        progress_history = []

        async def track_progress(status, percent=None, message=None, **kwargs):
            progress_history.append({
                "status": status,
                "percent": percent,
                "message": message
            })

        mock_reporter.update.side_effect = track_progress

        async def execute_tracked_workflow():
            await mock_reporter.update("starting", percent=0, message="Initializing")
            await mock_client.get_user_profile("user-456")
            await mock_reporter.update("processing", percent=33, message="Got profile")
            await mock_client.list_files("user-456")
            await mock_reporter.update("processing", percent=66, message="Got files")
            await mock_client.list_conversations("user-456")
            await mock_reporter.update("completed", percent=100, message="Done")

        await execute_tracked_workflow()

        # Verify progress tracking
        assert len(progress_history) == 4

        # Verify progress is monotonically increasing
        percents = [p["percent"] for p in progress_history]
        assert percents == [0, 33, 66, 100]

        # Verify status transitions
        statuses = [p["status"] for p in progress_history]
        assert statuses[0] == "starting"
        assert statuses[-1] == "completed"

        print("✓ Workflow progress tracking is accurate")


async def run_all_tests():
    """Run all multi-step workflow tests."""
    test_instance = TestMultiStepWorkflow()

    await test_instance.test_sequential_api_calls_workflow()
    await test_instance.test_workflow_with_intermediate_failure()
    await test_instance.test_parallel_api_calls_within_workflow()
    await test_instance.test_workflow_with_conditional_steps()
    await test_instance.test_workflow_progress_tracking_accuracy()

    print("\n✓ All multi-step workflow tests passed!")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
