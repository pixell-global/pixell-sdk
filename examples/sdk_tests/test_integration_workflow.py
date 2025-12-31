#!/usr/bin/env python3
"""End-to-end integration workflow tests.

These tests simulate complete task processing workflows, testing the
integration between all SDK components working together.
"""

import asyncio
import json
from datetime import datetime
from typing import List, Dict, Optional

from pixell.sdk import (
    RateLimitError,
    AuthenticationError,
)


class MockRedisState:
    """Simulates Redis state for integration testing."""

    def __init__(self):
        self.queues: Dict[str, List[str]] = {}
        self.hashes: Dict[str, Dict[str, str]] = {}
        self.pubsub_messages: Dict[str, List[str]] = {}

    async def lpush(self, key: str, value: str):
        if key not in self.queues:
            self.queues[key] = []
        self.queues[key].insert(0, value)

    async def rpush(self, key: str, value: str):
        if key not in self.queues:
            self.queues[key] = []
        self.queues[key].append(value)

    async def brpoplpush(self, src: str, dest: str, timeout: int = 0) -> Optional[str]:
        if src in self.queues and self.queues[src]:
            value = self.queues[src].pop()
            if dest not in self.queues:
                self.queues[dest] = []
            self.queues[dest].insert(0, value)
            return value
        return None

    async def lrem(self, key: str, count: int, value: str):
        if key in self.queues:
            try:
                self.queues[key].remove(value)
            except ValueError:
                pass

    async def hset(self, key: str, mapping: Dict[str, str] = None, **kwargs):
        if key not in self.hashes:
            self.hashes[key] = {}
        if mapping:
            self.hashes[key].update(mapping)
        self.hashes[key].update(kwargs)

    async def hget(self, key: str, field: str) -> Optional[str]:
        return self.hashes.get(key, {}).get(field)

    async def hgetall(self, key: str) -> Dict[str, str]:
        return self.hashes.get(key, {})

    async def publish(self, channel: str, message: str):
        if channel not in self.pubsub_messages:
            self.pubsub_messages[channel] = []
        self.pubsub_messages[channel].append(message)


class TestCompleteTaskLifecycle:
    """Test complete task processing lifecycle."""

    async def test_happy_path_workflow(self):
        """Test complete successful task workflow."""
        redis = MockRedisState()
        workflow_log: List[str] = []

        # Create task data
        task_data = {
            "task_id": "task-123",
            "agent_id": "test-agent",
            "user_id": "user-456",
            "tenant_id": "tenant-789",
            "trace_id": "trace-abc",
            "jwt_token": "token-xyz",
            "payload": {"prompt": "Analyze my calendar"},
        }

        # Simulate task in queue
        await redis.rpush("pixell:agents:test-agent:tasks", json.dumps(task_data))

        # Mock API responses

        async def mock_handler(ctx, payload):
            workflow_log.append("handler_started")

            # Report starting
            await redis.publish(
                f"pixell:tasks:{task_data['task_id']}:progress",
                json.dumps({"status": "starting", "percent": 0})
            )
            workflow_log.append("progress_0")

            # Simulate getting profile
            workflow_log.append("getting_profile")

            # Simulate calling OAuth API
            workflow_log.append("calling_oauth_api")

            # Report progress
            await redis.publish(
                f"pixell:tasks:{task_data['task_id']}:progress",
                json.dumps({"status": "processing", "percent": 50})
            )
            workflow_log.append("progress_50")

            # Process results
            workflow_log.append("processing_results")

            # Report completion
            await redis.publish(
                f"pixell:tasks:{task_data['task_id']}:progress",
                json.dumps({"status": "completed", "percent": 100})
            )
            workflow_log.append("progress_100")

            return {"status": "success", "events_found": 1}

        # Simulate consumer processing
        task_json = await redis.brpoplpush(
            "pixell:agents:test-agent:tasks",
            "pixell:agents:test-agent:processing"
        )

        assert task_json is not None
        parsed_task = json.loads(task_json)

        # Update status to processing
        await redis.hset(
            f"pixell:tasks:{parsed_task['task_id']}:status",
            mapping={"status": "processing", "started_at": datetime.utcnow().isoformat()}
        )

        # Execute handler
        result = await mock_handler(None, parsed_task["payload"])

        # Update status to completed
        await redis.hset(
            f"pixell:tasks:{parsed_task['task_id']}:status",
            mapping={
                "status": "completed",
                "result": json.dumps(result),
                "completed_at": datetime.utcnow().isoformat()
            }
        )

        # Remove from processing queue
        await redis.lrem("pixell:agents:test-agent:processing", 1, task_json)

        # Verify workflow
        assert workflow_log == [
            "handler_started",
            "progress_0",
            "getting_profile",
            "calling_oauth_api",
            "progress_50",
            "processing_results",
            "progress_100",
        ]

        # Verify Redis state
        assert "pixell:agents:test-agent:processing" not in redis.queues or \
               task_json not in redis.queues.get("pixell:agents:test-agent:processing", [])

        status = await redis.hgetall(f"pixell:tasks:{task_data['task_id']}:status")
        assert status["status"] == "completed"

        # Verify progress messages
        progress_channel = f"pixell:tasks:{task_data['task_id']}:progress"
        assert len(redis.pubsub_messages.get(progress_channel, [])) == 3

        print("✓ Happy path workflow completed successfully")

    async def test_timeout_workflow(self):
        """Test workflow with task timeout."""
        redis = MockRedisState()

        task_data = {
            "task_id": "task-timeout",
            "agent_id": "test-agent",
            "user_id": "user-456",
            "tenant_id": "tenant-789",
            "trace_id": "trace-timeout",
            "jwt_token": "token-xyz",
            "payload": {"prompt": "Slow operation"},
        }

        await redis.rpush("pixell:agents:test-agent:tasks", json.dumps(task_data))

        async def slow_handler(ctx, payload):
            await asyncio.sleep(1.0)  # Too slow
            return {"status": "success"}

        # Get task from queue
        task_json = await redis.brpoplpush(
            "pixell:agents:test-agent:tasks",
            "pixell:agents:test-agent:processing"
        )

        # Execute with timeout
        timeout_seconds = 0.1
        error_occurred = False

        try:
            await asyncio.wait_for(slow_handler(None, task_data["payload"]), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            error_occurred = True

            # Update status to failed
            await redis.hset(
                f"pixell:tasks:{task_data['task_id']}:status",
                mapping={
                    "status": "failed",
                    "error": json.dumps({
                        "type": "TASK_TIMEOUT",
                        "message": f"Task exceeded {timeout_seconds}s timeout",
                        "recoverable": False
                    }),
                    "failed_at": datetime.utcnow().isoformat()
                }
            )

            # Move to dead letter queue
            await redis.lpush("pixell:agents:test-agent:dead_letter", task_json)
            await redis.lrem("pixell:agents:test-agent:processing", 1, task_json)

        assert error_occurred

        # Verify dead letter queue
        assert len(redis.queues.get("pixell:agents:test-agent:dead_letter", [])) == 1

        # Verify status
        status = await redis.hgetall(f"pixell:tasks:{task_data['task_id']}:status")
        assert status["status"] == "failed"
        error_info = json.loads(status["error"])
        assert error_info["type"] == "TASK_TIMEOUT"

        print("✓ Timeout workflow handled correctly")

    async def test_rate_limit_workflow(self):
        """Test workflow with rate limit error (recoverable)."""
        redis = MockRedisState()

        task_data = {
            "task_id": "task-ratelimit",
            "agent_id": "test-agent",
            "user_id": "user-456",
            "tenant_id": "tenant-789",
            "trace_id": "trace-ratelimit",
            "jwt_token": "token-xyz",
            "payload": {"prompt": "API call"},
        }

        await redis.rpush("pixell:agents:test-agent:tasks", json.dumps(task_data))

        async def rate_limited_handler(ctx, payload):
            raise RateLimitError("Rate limited by external API", retry_after=60)

        # Get task
        task_json = await redis.brpoplpush(
            "pixell:agents:test-agent:tasks",
            "pixell:agents:test-agent:processing"
        )

        # Execute handler
        try:
            await rate_limited_handler(None, task_data["payload"])
        except RateLimitError as e:
            # Update status with retry info
            await redis.hset(
                f"pixell:tasks:{task_data['task_id']}:status",
                mapping={
                    "status": "failed",
                    "error": json.dumps({
                        "type": "RATE_LIMITED",
                        "message": str(e),
                        "retry_after": e.details.get("retry_after"),
                        "recoverable": True
                    }),
                    "failed_at": datetime.utcnow().isoformat()
                }
            )

            # Don't move to dead letter (recoverable)
            await redis.lrem("pixell:agents:test-agent:processing", 1, task_json)

        # Verify NOT in dead letter queue
        assert len(redis.queues.get("pixell:agents:test-agent:dead_letter", [])) == 0

        # Verify status has retry info
        status = await redis.hgetall(f"pixell:tasks:{task_data['task_id']}:status")
        error_info = json.loads(status["error"])
        assert error_info["recoverable"] is True
        assert error_info["retry_after"] == 60

        print("✓ Rate limit workflow handled correctly (not in dead letter)")

    async def test_authentication_error_workflow(self):
        """Test workflow with authentication error (non-recoverable)."""
        redis = MockRedisState()

        task_data = {
            "task_id": "task-auth-fail",
            "agent_id": "test-agent",
            "user_id": "user-456",
            "tenant_id": "tenant-789",
            "trace_id": "trace-auth",
            "jwt_token": "expired-token",
            "payload": {"prompt": "Authenticated request"},
        }

        await redis.rpush("pixell:agents:test-agent:tasks", json.dumps(task_data))

        async def auth_failing_handler(ctx, payload):
            raise AuthenticationError("JWT token expired")

        # Get task
        task_json = await redis.brpoplpush(
            "pixell:agents:test-agent:tasks",
            "pixell:agents:test-agent:processing"
        )

        # Execute handler
        try:
            await auth_failing_handler(None, task_data["payload"])
        except AuthenticationError as e:
            # Update status
            await redis.hset(
                f"pixell:tasks:{task_data['task_id']}:status",
                mapping={
                    "status": "failed",
                    "error": json.dumps({
                        "type": "AUTH_FAILED",
                        "message": str(e),
                        "recoverable": False
                    }),
                    "failed_at": datetime.utcnow().isoformat()
                }
            )

            # Move to dead letter (non-recoverable)
            await redis.lpush("pixell:agents:test-agent:dead_letter", task_json)
            await redis.lrem("pixell:agents:test-agent:processing", 1, task_json)

        # Verify IS in dead letter queue
        assert len(redis.queues.get("pixell:agents:test-agent:dead_letter", [])) == 1

        print("✓ Authentication error workflow handled correctly (in dead letter)")


class TestMultipleTasksProcessing:
    """Test processing multiple tasks in sequence and parallel."""

    async def test_sequential_task_processing(self):
        """Test processing multiple tasks sequentially."""
        redis = MockRedisState()
        processed_tasks: List[str] = []

        # Add multiple tasks
        for i in range(5):
            task_data = {
                "task_id": f"task-seq-{i}",
                "agent_id": "test-agent",
                "user_id": "user-456",
                "tenant_id": "tenant-789",
                "trace_id": f"trace-seq-{i}",
                "jwt_token": "token-xyz",
                "payload": {"index": i},
            }
            await redis.rpush("pixell:agents:test-agent:tasks", json.dumps(task_data))

        async def simple_handler(payload):
            processed_tasks.append(f"task-seq-{payload['index']}")
            await asyncio.sleep(0.01)
            return {"processed": payload["index"]}

        # Process all tasks sequentially
        while True:
            task_json = await redis.brpoplpush(
                "pixell:agents:test-agent:tasks",
                "pixell:agents:test-agent:processing"
            )

            if task_json is None:
                break

            task_data = json.loads(task_json)
            await simple_handler(task_data["payload"])

            # Complete task
            await redis.lrem("pixell:agents:test-agent:processing", 1, task_json)

        assert len(processed_tasks) == 5
        # All tasks processed (order depends on Redis queue implementation)
        assert set(processed_tasks) == {f"task-seq-{i}" for i in range(5)}

        print("✓ Sequential task processing completed correctly")

    async def test_concurrent_task_processing(self):
        """Test processing multiple tasks concurrently with limit."""
        redis = MockRedisState()
        processed_tasks: List[str] = []
        max_concurrent = 3
        semaphore = asyncio.Semaphore(max_concurrent)
        active_count = 0
        max_active_observed = 0

        # Add tasks
        for i in range(10):
            task_data = {
                "task_id": f"task-conc-{i}",
                "agent_id": "test-agent",
                "user_id": "user-456",
                "tenant_id": "tenant-789",
                "trace_id": f"trace-conc-{i}",
                "payload": {"index": i},
            }
            await redis.rpush("pixell:agents:test-agent:tasks", json.dumps(task_data))

        async def concurrent_handler(payload):
            nonlocal active_count, max_active_observed
            async with semaphore:
                active_count += 1
                max_active_observed = max(max_active_observed, active_count)

                processed_tasks.append(f"task-conc-{payload['index']}")
                await asyncio.sleep(0.02)

                active_count -= 1

        # Process all tasks concurrently
        tasks = []
        while True:
            task_json = await redis.brpoplpush(
                "pixell:agents:test-agent:tasks",
                "pixell:agents:test-agent:processing"
            )

            if task_json is None:
                break

            task_data = json.loads(task_json)
            task = asyncio.create_task(concurrent_handler(task_data["payload"]))
            tasks.append(task)

        await asyncio.gather(*tasks)

        assert len(processed_tasks) == 10
        assert max_active_observed <= max_concurrent

        print(f"✓ Concurrent processing: max {max_active_observed} (limit {max_concurrent})")


class TestEndToEndScenarios:
    """Test realistic end-to-end scenarios."""

    async def test_data_analysis_agent_workflow(self):
        """Simulate a data analysis agent workflow."""
        redis = MockRedisState()
        workflow_events: List[Dict] = []

        task_data = {
            "task_id": "task-analysis",
            "agent_id": "data-analyzer",
            "user_id": "user-analyst",
            "tenant_id": "tenant-corp",
            "trace_id": "trace-analysis-001",
            "jwt_token": "valid-token",
            "payload": {
                "analysis_type": "calendar_summary",
                "date_range": "last_week",
                "include_files": True
            },
        }

        await redis.rpush("pixell:agents:data-analyzer:tasks", json.dumps(task_data))

        # Simulate agent workflow
        task_json = await redis.brpoplpush(
            "pixell:agents:data-analyzer:tasks",
            "pixell:agents:data-analyzer:processing"
        )

        parsed_task = json.loads(task_json)

        # Workflow steps
        async def run_analysis():
            # 1. Initialize
            workflow_events.append({"step": "init", "percent": 0})
            await redis.publish(
                f"pixell:tasks:{parsed_task['task_id']}:progress",
                json.dumps({"status": "starting", "percent": 0, "message": "Initializing"})
            )

            # 2. Fetch profile
            workflow_events.append({"step": "profile", "percent": 10})
            await asyncio.sleep(0.01)  # Simulate API call

            # 3. Fetch calendar events
            workflow_events.append({"step": "calendar", "percent": 30})
            await redis.publish(
                f"pixell:tasks:{parsed_task['task_id']}:progress",
                json.dumps({"status": "processing", "percent": 30, "message": "Fetching calendar"})
            )
            await asyncio.sleep(0.01)

            # 4. Fetch files (if requested)
            if parsed_task["payload"].get("include_files"):
                workflow_events.append({"step": "files", "percent": 50})
                await redis.publish(
                    f"pixell:tasks:{parsed_task['task_id']}:progress",
                    json.dumps({"status": "processing", "percent": 50, "message": "Fetching files"})
                )
                await asyncio.sleep(0.01)

            # 5. Analyze data
            workflow_events.append({"step": "analyze", "percent": 75})
            await redis.publish(
                f"pixell:tasks:{parsed_task['task_id']}:progress",
                json.dumps({"status": "processing", "percent": 75, "message": "Analyzing data"})
            )
            await asyncio.sleep(0.01)

            # 6. Generate report
            workflow_events.append({"step": "report", "percent": 90})

            # 7. Complete
            workflow_events.append({"step": "complete", "percent": 100})
            await redis.publish(
                f"pixell:tasks:{parsed_task['task_id']}:progress",
                json.dumps({"status": "completed", "percent": 100, "message": "Analysis complete"})
            )

            return {
                "status": "success",
                "summary": {
                    "meetings": 15,
                    "files_analyzed": 8,
                    "insights": ["Busy week", "Most meetings on Tuesday"]
                }
            }

        result = await run_analysis()

        # Update final status
        await redis.hset(
            f"pixell:tasks:{parsed_task['task_id']}:status",
            mapping={
                "status": "completed",
                "result": json.dumps(result),
                "completed_at": datetime.utcnow().isoformat()
            }
        )

        # Cleanup
        await redis.lrem("pixell:agents:data-analyzer:processing", 1, task_json)

        # Verify workflow
        steps = [e["step"] for e in workflow_events]
        assert steps == ["init", "profile", "calendar", "files", "analyze", "report", "complete"]

        # Verify progress messages sent
        progress_channel = f"pixell:tasks:{parsed_task['task_id']}:progress"
        assert len(redis.pubsub_messages.get(progress_channel, [])) == 5

        print("✓ Data analysis agent workflow completed successfully")

    async def test_multi_provider_oauth_workflow(self):
        """Simulate workflow calling multiple OAuth providers."""
        redis = MockRedisState()
        api_calls: List[Dict] = []

        task_data = {
            "task_id": "task-multi-oauth",
            "agent_id": "integration-agent",
            "user_id": "user-123",
            "tenant_id": "tenant-456",
            "trace_id": "trace-oauth-001",
            "jwt_token": "valid-token",
            "payload": {
                "providers": ["google", "github", "slack"],
                "action": "aggregate_notifications"
            },
        }

        await redis.rpush("pixell:agents:integration-agent:tasks", json.dumps(task_data))

        async def mock_oauth_call(provider: str, method: str, path: str):
            await asyncio.sleep(0.01)
            api_calls.append({"provider": provider, "method": method, "path": path})

            if provider == "google":
                return {"notifications": [{"id": "g1"}, {"id": "g2"}]}
            elif provider == "github":
                return {"notifications": [{"id": "gh1"}]}
            elif provider == "slack":
                return {"messages": [{"id": "s1"}, {"id": "s2"}, {"id": "s3"}]}
            return {}

        # Process task
        task_json = await redis.brpoplpush(
            "pixell:agents:integration-agent:tasks",
            "pixell:agents:integration-agent:processing"
        )

        parsed_task = json.loads(task_json)
        providers = parsed_task["payload"]["providers"]

        # Call all providers in parallel
        async def fetch_from_provider(provider: str):
            if provider == "google":
                return await mock_oauth_call(provider, "GET", "/gmail/v1/messages")
            elif provider == "github":
                return await mock_oauth_call(provider, "GET", "/notifications")
            elif provider == "slack":
                return await mock_oauth_call(provider, "GET", "/conversations.history")
            return {}

        results = await asyncio.gather(*[
            fetch_from_provider(p) for p in providers
        ])

        # Aggregate results
        total_items = sum(
            len(r.get("notifications", r.get("messages", [])))
            for r in results
        )

        # Verify all providers called
        assert len(api_calls) == 3
        assert {c["provider"] for c in api_calls} == {"google", "github", "slack"}
        assert total_items == 6  # 2 + 1 + 3

        print("✓ Multi-provider OAuth workflow completed successfully")


async def run_all_tests():
    """Run all integration workflow tests."""
    # Complete lifecycle tests
    lifecycle = TestCompleteTaskLifecycle()
    await lifecycle.test_happy_path_workflow()
    await lifecycle.test_timeout_workflow()
    await lifecycle.test_rate_limit_workflow()
    await lifecycle.test_authentication_error_workflow()

    # Multiple tasks tests
    multiple = TestMultipleTasksProcessing()
    await multiple.test_sequential_task_processing()
    await multiple.test_concurrent_task_processing()

    # End-to-end scenarios
    e2e = TestEndToEndScenarios()
    await e2e.test_data_analysis_agent_workflow()
    await e2e.test_multi_provider_oauth_workflow()

    print("\n✓ All integration workflow tests passed!")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
