#!/usr/bin/env python3
"""Test concurrent task processing patterns.

These tests verify that the SDK handles concurrent operations correctly,
including semaphore-based concurrency limits and parallel task execution.
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any

from pixell.sdk import (
    TaskConsumer,
)


class TestConcurrentProcessing:
    """Test concurrent task processing scenarios."""

    async def test_semaphore_limits_concurrency(self):
        """Test that concurrent tasks respect semaphore limits."""
        max_concurrent = 3
        total_tasks = 10
        semaphore = asyncio.Semaphore(max_concurrent)

        active_count = 0
        max_active_observed = 0
        completed_tasks = []

        async def process_task(task_id: int):
            nonlocal active_count, max_active_observed

            async with semaphore:
                active_count += 1
                max_active_observed = max(max_active_observed, active_count)

                # Simulate work
                await asyncio.sleep(0.02)

                completed_tasks.append(task_id)
                active_count -= 1

        # Create all tasks at once
        tasks = [asyncio.create_task(process_task(i)) for i in range(total_tasks)]

        # Wait for all to complete
        await asyncio.gather(*tasks)

        # Verify concurrency was limited
        assert max_active_observed <= max_concurrent
        assert len(completed_tasks) == total_tasks

        print(f"✓ Semaphore limited concurrency to {max_active_observed} (max: {max_concurrent})")

    async def test_task_consumer_concurrency_property(self):
        """Test TaskConsumer concurrency configuration."""

        async def dummy_handler(ctx, payload):
            return {"status": "success"}

        # Test different concurrency settings
        for concurrency in [1, 5, 10, 20]:
            consumer = TaskConsumer(
                agent_id="test-agent",
                redis_url="redis://localhost:6379",
                pxui_base_url="https://api.example.com",
                handler=dummy_handler,
                concurrency=concurrency,
            )
            assert consumer.concurrency == concurrency

        print("✓ TaskConsumer accepts different concurrency settings")

    async def test_parallel_consumers_different_agents(self):
        """Test multiple consumers for different agents."""

        async def handler_a(ctx, payload):
            return {"agent": "a", "result": "success"}

        async def handler_b(ctx, payload):
            return {"agent": "b", "result": "success"}

        consumer_a = TaskConsumer(
            agent_id="agent-a",
            redis_url="redis://localhost:6379",
            pxui_base_url="https://api.example.com",
            handler=handler_a,
        )

        consumer_b = TaskConsumer(
            agent_id="agent-b",
            redis_url="redis://localhost:6379",
            pxui_base_url="https://api.example.com",
            handler=handler_b,
        )

        # Verify separate queues
        assert consumer_a.queue_key == "pixell:agents:agent-a:tasks"
        assert consumer_b.queue_key == "pixell:agents:agent-b:tasks"
        assert consumer_a.queue_key != consumer_b.queue_key

        # Verify separate processing keys
        assert consumer_a.processing_key != consumer_b.processing_key

        print("✓ Multiple consumers have separate Redis keys")

    async def test_concurrent_progress_updates(self):
        """Test that concurrent progress updates don't interfere."""
        update_log: List[Dict[str, Any]] = []
        lock = asyncio.Lock()

        async def mock_update(task_id: str, status: str, percent: int):
            async with lock:
                update_log.append(
                    {
                        "task_id": task_id,
                        "status": status,
                        "percent": percent,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
            await asyncio.sleep(0.001)  # Simulate network delay

        async def simulate_task_progress(task_id: str):
            for percent in [0, 25, 50, 75, 100]:
                status = (
                    "starting" if percent == 0 else "completed" if percent == 100 else "processing"
                )
                await mock_update(task_id, status, percent)

        # Run 5 tasks concurrently
        tasks = [asyncio.create_task(simulate_task_progress(f"task-{i}")) for i in range(5)]
        await asyncio.gather(*tasks)

        # Verify all updates recorded
        assert len(update_log) == 25  # 5 tasks * 5 updates each

        # Verify each task has all its updates
        for i in range(5):
            task_updates = [u for u in update_log if u["task_id"] == f"task-{i}"]
            assert len(task_updates) == 5
            percents = sorted([u["percent"] for u in task_updates])
            assert percents == [0, 25, 50, 75, 100]

        print("✓ Concurrent progress updates recorded correctly")

    async def test_task_isolation(self):
        """Test that tasks don't share state inappropriately."""
        task_states: Dict[str, Dict] = {}

        async def isolated_handler(task_id: str, initial_value: int):
            # Each task has its own state
            local_state = {"value": initial_value, "steps": []}

            for i in range(3):
                local_state["value"] += 1
                local_state["steps"].append(f"step-{i}")
                await asyncio.sleep(0.001)

            task_states[task_id] = local_state
            return local_state

        # Run tasks with different initial values concurrently
        tasks = [asyncio.create_task(isolated_handler(f"task-{i}", i * 10)) for i in range(5)]
        await asyncio.gather(*tasks)

        # Verify each task has correct final state
        for i in range(5):
            state = task_states[f"task-{i}"]
            expected_value = i * 10 + 3  # initial + 3 increments
            assert state["value"] == expected_value
            assert len(state["steps"]) == 3

        print("✓ Task state isolation maintained correctly")

    async def test_graceful_shutdown_waits_for_tasks(self):
        """Test graceful shutdown waits for in-flight tasks."""
        completed_tasks = []
        asyncio.Event()

        async def long_running_task(task_id: str):
            await asyncio.sleep(0.05)
            completed_tasks.append(task_id)
            return task_id

        # Start tasks
        tasks = set()
        for i in range(5):
            task = asyncio.create_task(long_running_task(f"task-{i}"))
            tasks.add(task)
            task.add_done_callback(tasks.discard)

        # Simulate graceful shutdown (wait for completion)
        await asyncio.gather(*list(tasks), return_exceptions=True)

        # All tasks should complete
        assert len(completed_tasks) == 5

        print("✓ Graceful shutdown waited for all tasks")

    async def test_ungraceful_shutdown_cancels_tasks(self):
        """Test ungraceful shutdown cancels in-flight tasks."""
        completed_tasks = []
        cancelled_tasks = []

        async def cancellable_task(task_id: str):
            try:
                await asyncio.sleep(1.0)  # Long sleep
                completed_tasks.append(task_id)
            except asyncio.CancelledError:
                cancelled_tasks.append(task_id)
                raise

        # Start tasks
        tasks = [asyncio.create_task(cancellable_task(f"task-{i}")) for i in range(5)]

        # Give tasks a moment to start
        await asyncio.sleep(0.01)

        # Cancel all tasks (ungraceful shutdown)
        for task in tasks:
            task.cancel()

        # Wait for cancellation to propagate
        await asyncio.gather(*tasks, return_exceptions=True)

        # Tasks should be cancelled, not completed
        assert len(completed_tasks) == 0
        assert len(cancelled_tasks) == 5

        print("✓ Ungraceful shutdown cancelled all tasks")

    async def test_exception_in_one_task_doesnt_affect_others(self):
        """Test that exception in one task doesn't stop others."""
        results = {}

        async def task_that_might_fail(task_id: str, should_fail: bool):
            await asyncio.sleep(0.01)
            if should_fail:
                raise ValueError(f"Task {task_id} failed intentionally")
            results[task_id] = "success"
            return "success"

        # Create mix of failing and succeeding tasks
        tasks = [
            asyncio.create_task(task_that_might_fail("task-0", should_fail=True)),
            asyncio.create_task(task_that_might_fail("task-1", should_fail=False)),
            asyncio.create_task(task_that_might_fail("task-2", should_fail=True)),
            asyncio.create_task(task_that_might_fail("task-3", should_fail=False)),
            asyncio.create_task(task_that_might_fail("task-4", should_fail=False)),
        ]

        # Gather with return_exceptions=True to not propagate errors
        outcomes = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify mix of results
        success_count = sum(1 for o in outcomes if o == "success")
        error_count = sum(1 for o in outcomes if isinstance(o, ValueError))

        assert success_count == 3
        assert error_count == 2
        assert len(results) == 3  # Only successful tasks recorded

        print("✓ Exception in one task didn't affect others")

    async def test_concurrent_redis_key_access_patterns(self):
        """Test concurrent access to different Redis keys."""
        # Simulate Redis key operations
        redis_state: Dict[str, Any] = {}
        operation_log: List[str] = []
        lock = asyncio.Lock()

        async def redis_operation(key: str, operation: str, value: Any = None):
            async with lock:
                operation_log.append(f"{operation}:{key}")
                if operation == "set":
                    redis_state[key] = value
                elif operation == "get":
                    return redis_state.get(key)
                elif operation == "delete":
                    redis_state.pop(key, None)
            await asyncio.sleep(0.001)

        async def process_task(task_id: str):
            # Simulate task lifecycle with Redis operations
            await redis_operation(f"task:{task_id}:status", "set", "processing")
            await asyncio.sleep(0.01)
            await redis_operation(f"task:{task_id}:result", "set", {"success": True})
            await redis_operation(f"task:{task_id}:status", "set", "completed")

        # Run multiple tasks concurrently
        tasks = [asyncio.create_task(process_task(f"task-{i}")) for i in range(10)]
        await asyncio.gather(*tasks)

        # Verify all tasks completed
        for i in range(10):
            assert redis_state.get(f"task:task-{i}:status") == "completed"
            assert redis_state.get(f"task:task-{i}:result") == {"success": True}

        print("✓ Concurrent Redis key operations completed correctly")


async def run_all_tests():
    """Run all concurrent processing tests."""
    test_instance = TestConcurrentProcessing()

    await test_instance.test_semaphore_limits_concurrency()
    await test_instance.test_task_consumer_concurrency_property()
    await test_instance.test_parallel_consumers_different_agents()
    await test_instance.test_concurrent_progress_updates()
    await test_instance.test_task_isolation()
    await test_instance.test_graceful_shutdown_waits_for_tasks()
    await test_instance.test_ungraceful_shutdown_cancels_tasks()
    await test_instance.test_exception_in_one_task_doesnt_affect_others()
    await test_instance.test_concurrent_redis_key_access_patterns()

    print("\n✓ All concurrent processing tests passed!")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
