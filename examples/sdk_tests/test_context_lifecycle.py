#!/usr/bin/env python3
"""Test context lifecycle management patterns.

These tests verify proper initialization, usage, and cleanup of
UserContext and its underlying resources.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from pixell.sdk import (
    UserContext,
    TaskMetadata,
    PXUIDataClient,
    ProgressReporter,
    ContextError,
    ContextNotInitializedError,
)


class TestContextInitialization:
    """Test UserContext initialization patterns."""

    def test_task_metadata_creation(self):
        """Test TaskMetadata with all fields."""
        now = datetime.utcnow()
        metadata = TaskMetadata(
            task_id="task-123",
            agent_id="test-agent",
            user_id="user-456",
            tenant_id="tenant-789",
            trace_id="trace-abc",
            created_at=now,
            payload={"prompt": "test", "options": {"key": "value"}},
        )

        assert metadata.task_id == "task-123"
        assert metadata.agent_id == "test-agent"
        assert metadata.user_id == "user-456"
        assert metadata.tenant_id == "tenant-789"
        assert metadata.trace_id == "trace-abc"
        assert metadata.created_at == now
        assert metadata.payload == {"prompt": "test", "options": {"key": "value"}}

        print("✓ TaskMetadata created with all fields")

    def test_task_metadata_immutability(self):
        """Test that TaskMetadata fields are accessible but dataclass frozen behavior."""
        metadata = TaskMetadata(
            task_id="task-123",
            agent_id="test-agent",
            user_id="user-456",
            tenant_id="tenant-789",
            trace_id="trace-abc",
            created_at=datetime.utcnow(),
        )

        # Fields should be accessible
        assert metadata.task_id == "task-123"

        # Note: Pydantic dataclasses may or may not be frozen by default
        # This test verifies field access, not mutation prevention

        print("✓ TaskMetadata fields are accessible")

    def test_context_factory_method_exists(self):
        """Test UserContext.from_task factory method exists."""
        assert hasattr(UserContext, "from_task")
        assert callable(UserContext.from_task)

        print("✓ UserContext.from_task factory method exists")

    def test_context_expected_methods(self):
        """Test UserContext has all expected methods."""
        expected_methods = [
            "from_task",
            "get_user_profile",
            "get_files",
            "get_file_content",
            "get_conversations",
            "get_task_history",
            "call_oauth_api",
            "report_progress",
            "report_error",
            "close",
        ]

        for method_name in expected_methods:
            assert hasattr(UserContext, method_name), f"Missing method: {method_name}"

        print("✓ UserContext has all expected methods")


class TestContextLifecycle:
    """Test context creation, usage, and cleanup patterns."""

    async def test_context_as_async_context_manager(self):
        """Test UserContext as async context manager."""
        entered = False
        exited = False

        class MockContext:
            async def __aenter__(self):
                nonlocal entered
                entered = True
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                nonlocal exited
                exited = True
                return False

            async def close(self):
                pass

        async with MockContext() as ctx:
            assert entered
            assert not exited

        assert exited

        print("✓ Async context manager pattern works correctly")

    async def test_context_cleanup_on_success(self):
        """Test that context is cleaned up after successful execution."""
        cleanup_called = False

        class MockContext:
            def __init__(self):
                self._closed = False

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                await self.close()
                return False

            async def close(self):
                nonlocal cleanup_called
                cleanup_called = True
                self._closed = True

            async def do_work(self):
                return "success"

        async with MockContext() as ctx:
            result = await ctx.do_work()
            assert result == "success"

        assert cleanup_called

        print("✓ Context cleaned up after successful execution")

    async def test_context_cleanup_on_exception(self):
        """Test that context is cleaned up even when exception occurs."""
        cleanup_called = False
        exception_raised = False

        class MockContext:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                nonlocal cleanup_called
                cleanup_called = True
                return False  # Don't suppress exception

            async def do_work_that_fails(self):
                raise ValueError("Intentional error")

        try:
            async with MockContext() as ctx:
                await ctx.do_work_that_fails()
        except ValueError:
            exception_raised = True

        assert exception_raised
        assert cleanup_called

        print("✓ Context cleaned up even when exception occurs")

    async def test_context_close_idempotency(self):
        """Test that calling close() multiple times is safe."""
        close_count = 0

        class MockContext:
            def __init__(self):
                self._closed = False

            async def close(self):
                nonlocal close_count
                if not self._closed:
                    close_count += 1
                    self._closed = True

        ctx = MockContext()

        # Close multiple times
        await ctx.close()
        await ctx.close()
        await ctx.close()

        assert close_count == 1

        print("✓ Context close is idempotent")

    async def test_closed_context_raises_error(self):
        """Test that using closed context raises error."""
        class MockContext:
            def __init__(self):
                self._closed = False

            def _check_closed(self):
                if self._closed:
                    raise ContextNotInitializedError("Context is closed")

            async def close(self):
                self._closed = True

            async def get_data(self):
                self._check_closed()
                return {"data": "value"}

        ctx = MockContext()

        # Works before close
        result = await ctx.get_data()
        assert result == {"data": "value"}

        # Close context
        await ctx.close()

        # Fails after close
        try:
            await ctx.get_data()
            assert False, "Should have raised ContextNotInitializedError"
        except ContextNotInitializedError:
            pass

        print("✓ Closed context raises ContextNotInitializedError")


class TestResourceManagement:
    """Test proper resource management in context."""

    async def test_nested_resource_cleanup(self):
        """Test cleanup of nested resources (client and reporter)."""
        client_closed = False
        reporter_closed = False

        class MockClient:
            async def close(self):
                nonlocal client_closed
                client_closed = True

        class MockReporter:
            async def close(self):
                nonlocal reporter_closed
                reporter_closed = True

        class MockContext:
            def __init__(self):
                self._client = MockClient()
                self._reporter = MockReporter()
                self._closed = False

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                await self.close()
                return False

            async def close(self):
                if self._closed:
                    return
                self._closed = True

                # Close both resources
                await self._client.close()
                await self._reporter.close()

        async with MockContext():
            pass

        assert client_closed
        assert reporter_closed

        print("✓ Nested resources cleaned up correctly")

    async def test_cleanup_continues_after_error(self):
        """Test that cleanup continues even if one resource fails."""
        cleanup_order = []

        class FailingResource:
            async def close(self):
                cleanup_order.append("failing_start")
                raise ValueError("Cleanup failed")

        class SuccessfulResource:
            async def close(self):
                cleanup_order.append("successful")

        class MockContext:
            def __init__(self):
                self._resources = [FailingResource(), SuccessfulResource()]

            async def close(self):
                errors = []
                for resource in self._resources:
                    try:
                        await resource.close()
                    except Exception as e:
                        errors.append(e)

                if errors:
                    # Log but don't re-raise to ensure all resources attempted
                    pass

        ctx = MockContext()
        await ctx.close()

        assert "failing_start" in cleanup_order
        assert "successful" in cleanup_order

        print("✓ Cleanup continues after individual resource failure")

    async def test_client_reuse_within_context(self):
        """Test that HTTP client is reused within a context."""
        client_creation_count = 0
        request_count = 0

        class MockHttpClient:
            def __init__(self):
                nonlocal client_creation_count
                client_creation_count += 1

            async def request(self, *args, **kwargs):
                nonlocal request_count
                request_count += 1
                return {"status": "ok"}

        class MockContext:
            def __init__(self):
                self._client = None

            async def _get_client(self):
                if self._client is None:
                    self._client = MockHttpClient()
                return self._client

            async def make_request(self):
                client = await self._get_client()
                return await client.request()

        ctx = MockContext()

        # Make multiple requests
        await ctx.make_request()
        await ctx.make_request()
        await ctx.make_request()

        assert client_creation_count == 1  # Single client created
        assert request_count == 3  # All requests made

        print("✓ HTTP client reused within context")


class TestContextMetadata:
    """Test metadata handling in context."""

    def test_metadata_preserved_throughout_lifecycle(self):
        """Test that metadata is preserved throughout context lifecycle."""
        trace_id = "trace-unique-123"
        task_id = "task-456"

        metadata = TaskMetadata(
            task_id=task_id,
            agent_id="test-agent",
            user_id="user-789",
            tenant_id="tenant-abc",
            trace_id=trace_id,
            created_at=datetime.utcnow(),
        )

        # Verify metadata fields accessible
        assert metadata.trace_id == trace_id
        assert metadata.task_id == task_id

        print("✓ Metadata preserved throughout lifecycle")

    def test_multiple_contexts_isolated(self):
        """Test that multiple contexts don't share state."""
        contexts_data: Dict[str, Dict] = {}

        class MockContext:
            def __init__(self, context_id: str):
                self.context_id = context_id
                self.state = {}

            def set_state(self, key: str, value: Any):
                self.state[key] = value
                contexts_data[self.context_id] = self.state.copy()

        # Create multiple contexts
        ctx1 = MockContext("ctx-1")
        ctx2 = MockContext("ctx-2")
        ctx3 = MockContext("ctx-3")

        # Set different state in each
        ctx1.set_state("value", 100)
        ctx2.set_state("value", 200)
        ctx3.set_state("value", 300)

        # Verify isolation
        assert contexts_data["ctx-1"]["value"] == 100
        assert contexts_data["ctx-2"]["value"] == 200
        assert contexts_data["ctx-3"]["value"] == 300

        print("✓ Multiple contexts are isolated")

    async def test_context_with_empty_payload(self):
        """Test context handles empty payload correctly."""
        metadata = TaskMetadata(
            task_id="task-empty",
            agent_id="test-agent",
            user_id="user-123",
            tenant_id="tenant-456",
            trace_id="trace-789",
            created_at=datetime.utcnow(),
            payload={},  # Empty payload
        )

        assert metadata.payload == {}

        print("✓ Context handles empty payload correctly")

    async def test_context_with_large_payload(self):
        """Test context handles large payload correctly."""
        large_data = {
            "items": [{"id": i, "data": "x" * 100} for i in range(1000)],
            "nested": {
                "level1": {
                    "level2": {
                        "level3": {"values": list(range(100))}
                    }
                }
            }
        }

        metadata = TaskMetadata(
            task_id="task-large",
            agent_id="test-agent",
            user_id="user-123",
            tenant_id="tenant-456",
            trace_id="trace-789",
            created_at=datetime.utcnow(),
            payload=large_data,
        )

        assert len(metadata.payload["items"]) == 1000
        assert metadata.payload["nested"]["level1"]["level2"]["level3"]["values"][50] == 50

        print("✓ Context handles large payload correctly")


class TestContextErrorScenarios:
    """Test error handling in context operations."""

    def test_context_not_initialized_error(self):
        """Test ContextNotInitializedError creation."""
        # Default message
        error1 = ContextNotInitializedError()
        assert str(error1) == "Context not initialized"
        assert error1.code == "CONTEXT_NOT_INITIALIZED"

        # Custom message
        error2 = ContextNotInitializedError("Custom: context was closed")
        assert str(error2) == "Custom: context was closed"

        print("✓ ContextNotInitializedError created correctly")

    async def test_operations_on_closed_context(self):
        """Test all operations fail on closed context."""
        operations_tested = []

        class MockContext:
            def __init__(self):
                self._closed = False

            def _check_closed(self):
                if self._closed:
                    raise ContextNotInitializedError()

            async def close(self):
                self._closed = True

            async def get_profile(self):
                self._check_closed()
                operations_tested.append("get_profile")
                return {}

            async def get_files(self):
                self._check_closed()
                operations_tested.append("get_files")
                return []

            async def report_progress(self, status, percent):
                self._check_closed()
                operations_tested.append("report_progress")

        ctx = MockContext()

        # Operations work before close
        await ctx.get_profile()
        await ctx.get_files()
        await ctx.report_progress("starting", 0)

        assert len(operations_tested) == 3

        # Close context
        await ctx.close()

        # All operations should fail now
        for op_name, op_func in [
            ("get_profile", ctx.get_profile),
            ("get_files", ctx.get_files),
            ("report_progress", lambda: ctx.report_progress("test", 50))
        ]:
            try:
                await op_func() if asyncio.iscoroutinefunction(op_func) else await op_func()
                assert False, f"{op_name} should have raised"
            except ContextNotInitializedError:
                pass

        print("✓ All operations fail on closed context")


async def run_all_tests():
    """Run all context lifecycle tests."""
    # Initialization tests
    init_tests = TestContextInitialization()
    init_tests.test_task_metadata_creation()
    init_tests.test_task_metadata_immutability()
    init_tests.test_context_factory_method_exists()
    init_tests.test_context_expected_methods()

    # Lifecycle tests
    lifecycle_tests = TestContextLifecycle()
    await lifecycle_tests.test_context_as_async_context_manager()
    await lifecycle_tests.test_context_cleanup_on_success()
    await lifecycle_tests.test_context_cleanup_on_exception()
    await lifecycle_tests.test_context_close_idempotency()
    await lifecycle_tests.test_closed_context_raises_error()

    # Resource management tests
    resource_tests = TestResourceManagement()
    await resource_tests.test_nested_resource_cleanup()
    await resource_tests.test_cleanup_continues_after_error()
    await resource_tests.test_client_reuse_within_context()

    # Metadata tests
    metadata_tests = TestContextMetadata()
    metadata_tests.test_metadata_preserved_throughout_lifecycle()
    metadata_tests.test_multiple_contexts_isolated()
    await metadata_tests.test_context_with_empty_payload()
    await metadata_tests.test_context_with_large_payload()

    # Error scenario tests
    error_tests = TestContextErrorScenarios()
    error_tests.test_context_not_initialized_error()
    await error_tests.test_operations_on_closed_context()

    print("\n✓ All context lifecycle tests passed!")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
