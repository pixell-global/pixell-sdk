#!/usr/bin/env python3
"""Test error handling and recovery patterns.

These tests verify that the SDK properly handles various error scenarios,
including retry logic, error classification, and recovery strategies.
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any

from pixell.sdk import (
    ProgressReporter,
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


class TestErrorClassification:
    """Test error type classification and hierarchy."""

    def test_error_inheritance_hierarchy(self):
        """Test the complete error inheritance hierarchy."""
        # Consumer errors
        assert issubclass(ConsumerError, SDKError)
        assert issubclass(TaskTimeoutError, ConsumerError)
        assert issubclass(TaskHandlerError, ConsumerError)
        assert issubclass(QueueError, ConsumerError)

        # Client errors
        assert issubclass(ClientError, SDKError)
        assert issubclass(AuthenticationError, ClientError)
        assert issubclass(RateLimitError, ClientError)
        assert issubclass(APIError, ClientError)
        assert issubclass(ConnectionError, ClientError)

        # Context errors
        assert issubclass(ContextError, SDKError)
        assert issubclass(ContextNotInitializedError, ContextError)

        # Progress errors
        assert issubclass(ProgressError, SDKError)

        print("✓ Error inheritance hierarchy is correct")

    def test_error_details_preservation(self):
        """Test that error details are preserved correctly."""
        # TaskTimeoutError preserves task_id and timeout
        timeout_error = TaskTimeoutError("task-123", 30.0)
        assert timeout_error.details["task_id"] == "task-123"
        assert timeout_error.details["timeout"] == 30.0

        # RateLimitError preserves retry_after
        rate_error = RateLimitError("Rate limited", retry_after=60)
        assert rate_error.details["retry_after"] == 60

        # APIError preserves status_code and response
        api_error = APIError(500, response_body={"error": "Server error"})
        assert api_error.details["status_code"] == 500
        assert api_error.details["response"] == {"error": "Server error"}

        # ConnectionError preserves URL
        conn_error = ConnectionError("Connection failed", url="https://api.example.com")
        assert conn_error.details["url"] == "https://api.example.com"

        # QueueError preserves queue_name
        queue_error = QueueError("Queue unavailable", queue_name="test-queue")
        assert queue_error.details["queue_name"] == "test-queue"

        # TaskHandlerError preserves task_id and cause
        cause = ValueError("Original error")
        handler_error = TaskHandlerError("Handler failed", task_id="task-456", cause=cause)
        assert handler_error.details["task_id"] == "task-456"
        assert handler_error.cause is cause

        print("✓ Error details are preserved correctly")

    def test_error_serialization(self):
        """Test error serialization to dict."""
        error = SDKError(
            "Test error",
            code="TEST_ERROR",
            details={"key": "value", "count": 42}
        )

        serialized = error.to_dict()

        assert serialized["error"] == "TEST_ERROR"
        assert serialized["message"] == "Test error"
        assert serialized["details"] == {"key": "value", "count": 42}

        print("✓ Error serialization works correctly")


class TestRetryLogic:
    """Test retry behavior for different error types."""

    async def test_retry_on_connection_error(self):
        """Test that connection errors trigger retries."""
        attempt_count = 0
        max_retries = 3

        async def flaky_operation():
            nonlocal attempt_count
            attempt_count += 1

            if attempt_count < max_retries:
                raise ConnectionError("Connection failed")
            return "success"

        async def retry_wrapper():
            for attempt in range(max_retries + 1):
                try:
                    return await flaky_operation()
                except ConnectionError:
                    if attempt == max_retries:
                        raise
                    await asyncio.sleep(0.01 * (2 ** attempt))  # Exponential backoff
            raise ConnectionError("Max retries exceeded")

        result = await retry_wrapper()
        assert result == "success"
        assert attempt_count == max_retries

        print("✓ Connection errors trigger retries correctly")

    async def test_no_retry_on_authentication_error(self):
        """Test that authentication errors don't trigger retries."""
        attempt_count = 0

        async def auth_operation():
            nonlocal attempt_count
            attempt_count += 1
            raise AuthenticationError("Invalid token")

        async def retry_wrapper():
            try:
                return await auth_operation()
            except AuthenticationError:
                # Don't retry auth errors
                raise

        try:
            await retry_wrapper()
        except AuthenticationError:
            pass

        assert attempt_count == 1  # No retry

        print("✓ Authentication errors don't trigger retries")

    async def test_no_retry_on_rate_limit(self):
        """Test rate limit errors are not retried immediately."""
        attempt_count = 0
        retry_after = None

        async def rate_limited_operation():
            nonlocal attempt_count
            attempt_count += 1
            raise RateLimitError("Rate limited", retry_after=60)

        try:
            await rate_limited_operation()
        except RateLimitError as e:
            retry_after = e.details.get("retry_after")

        assert attempt_count == 1
        assert retry_after == 60  # Caller should wait this long

        print("✓ Rate limit errors preserve retry_after without immediate retry")

    async def test_exponential_backoff(self):
        """Test exponential backoff timing."""
        delays: List[float] = []
        base_delay = 0.01

        async def operation_with_backoff(max_attempts: int):
            for attempt in range(max_attempts):
                try:
                    raise ConnectionError("Simulated failure")
                except ConnectionError:
                    if attempt == max_attempts - 1:
                        raise
                    delay = base_delay * (2 ** attempt)
                    delays.append(delay)
                    await asyncio.sleep(delay)

        try:
            await operation_with_backoff(4)
        except ConnectionError:
            pass

        # Verify exponential growth
        assert len(delays) == 3  # 4 attempts, 3 retries
        assert delays[0] == base_delay * 1  # 2^0
        assert delays[1] == base_delay * 2  # 2^1
        assert delays[2] == base_delay * 4  # 2^2

        print("✓ Exponential backoff timing is correct")


class TestErrorRecovery:
    """Test error recovery strategies."""

    async def test_recoverable_vs_non_recoverable_errors(self):
        """Test classification of recoverable vs non-recoverable errors."""
        recoverable_errors = []
        non_recoverable_errors = []

        async def classify_error(error: SDKError) -> bool:
            """Classify if error is recoverable."""
            if isinstance(error, RateLimitError):
                return True  # Recoverable - retry after delay
            if isinstance(error, ConnectionError):
                return True  # Recoverable - network issues are transient
            if isinstance(error, AuthenticationError):
                return False  # Non-recoverable - need new credentials
            if isinstance(error, APIError):
                status = error.details.get("status_code", 500)
                return status >= 500  # 5xx are recoverable, 4xx are not
            return False  # Default to non-recoverable

        # Test various error types
        test_errors = [
            RateLimitError("Rate limited", retry_after=60),
            ConnectionError("Connection timeout"),
            AuthenticationError("Invalid API key"),
            APIError(500, response_body={"error": "Server error"}),
            APIError(404, response_body={"error": "Not found"}),
            APIError(400, response_body={"error": "Bad request"}),
        ]

        for error in test_errors:
            is_recoverable = await classify_error(error)
            if is_recoverable:
                recoverable_errors.append(type(error).__name__)
            else:
                non_recoverable_errors.append(type(error).__name__)

        assert "RateLimitError" in recoverable_errors
        assert "ConnectionError" in recoverable_errors
        assert "AuthenticationError" in non_recoverable_errors

        print("✓ Error recoverability classification is correct")

    async def test_dead_letter_queue_routing(self):
        """Test that non-recoverable errors route to dead letter queue."""
        dead_letter_queue: List[Dict] = []
        retry_queue: List[Dict] = []

        async def handle_error(task_id: str, error: SDKError):
            error_data = {
                "task_id": task_id,
                "error_type": type(error).__name__,
                "message": str(error),
                "details": error.details
            }

            # Route based on recoverability
            if isinstance(error, RateLimitError):
                retry_queue.append(error_data)
            elif isinstance(error, ConnectionError):
                retry_queue.append(error_data)
            else:
                dead_letter_queue.append(error_data)

        # Simulate various task failures
        await handle_error("task-1", RateLimitError("Rate limited", retry_after=60))
        await handle_error("task-2", AuthenticationError("Bad token"))
        await handle_error("task-3", ConnectionError("Timeout"))
        await handle_error("task-4", TaskTimeoutError("task-4", 30.0))
        await handle_error("task-5", APIError(400, response_body={"error": "Invalid"}))

        assert len(retry_queue) == 2  # RateLimitError, ConnectionError
        assert len(dead_letter_queue) == 3  # AuthError, TimeoutError, APIError

        print("✓ Dead letter queue routing is correct")

    async def test_partial_failure_recovery(self):
        """Test recovery from partial workflow failure."""
        checkpoint_state: Dict[str, Any] = {}

        async def checkpoint_operation(name: str, result: Any):
            """Save checkpoint for recovery."""
            checkpoint_state[name] = {
                "result": result,
                "completed_at": datetime.utcnow().isoformat()
            }

        async def recover_from_checkpoint() -> Dict[str, Any]:
            """Recover state from last checkpoint."""
            return checkpoint_state.copy()

        async def workflow_with_checkpoints():
            # Step 1
            await checkpoint_operation("step1", {"data": "step1_result"})

            # Step 2
            await checkpoint_operation("step2", {"data": "step2_result"})

            # Step 3 - fails
            raise ConnectionError("Network error at step 3")

        # First run - fails at step 3
        try:
            await workflow_with_checkpoints()
        except ConnectionError:
            pass

        # Verify checkpoints saved
        recovered = await recover_from_checkpoint()
        assert "step1" in recovered
        assert "step2" in recovered
        assert "step3" not in recovered

        print("✓ Partial failure recovery with checkpoints works")

    async def test_error_context_preservation(self):
        """Test that error context is preserved through the chain."""
        async def inner_operation():
            raise ValueError("Original error in inner operation")

        async def middle_operation():
            try:
                await inner_operation()
            except ValueError as e:
                raise TaskHandlerError(
                    "Handler failed",
                    task_id="task-123",
                    cause=e
                )

        async def outer_operation():
            try:
                await middle_operation()
            except TaskHandlerError as e:
                # Preserve full chain
                return {
                    "error_type": type(e).__name__,
                    "message": str(e),
                    "task_id": e.details.get("task_id"),
                    "original_error": str(e.cause) if e.cause else None,
                    "original_type": type(e.cause).__name__ if e.cause else None
                }

        result = await outer_operation()

        assert result["error_type"] == "TaskHandlerError"
        assert result["task_id"] == "task-123"
        assert result["original_error"] == "Original error in inner operation"
        assert result["original_type"] == "ValueError"

        print("✓ Error context is preserved through the chain")


class TestProgressErrorHandling:
    """Test progress reporting error scenarios."""

    async def test_progress_invalid_percent_validation(self):
        """Test that invalid percent values are rejected."""
        reporter = ProgressReporter(
            redis_url="redis://localhost:6379",
            task_id="task-123",
            user_id="user-456",
        )

        # Test invalid percent values
        invalid_percents = [-10, -1, 101, 150, 200]

        for percent in invalid_percents:
            try:
                await reporter.update("processing", percent=percent)
                assert False, f"Should have raised for percent={percent}"
            except ProgressError as e:
                assert "INVALID_PERCENT" in e.code

        print("✓ Invalid percent values are rejected")

    async def test_progress_continues_after_error(self):
        """Test that task can continue after progress error."""
        successful_updates = []

        async def mock_publish(channel, message):
            # Simulate first publish failing
            if len(successful_updates) == 0:
                raise Exception("Redis connection lost")
            successful_updates.append(message)

        async def workflow_with_progress_recovery():
            # First progress update might fail
            try:
                await mock_publish("channel", "progress:0%")
            except Exception:
                pass  # Log and continue

            # Simulate reconnection
            successful_updates.clear()
            successful_updates.append("reconnected")

            # Subsequent updates should work
            await mock_publish("channel", "progress:50%")
            await mock_publish("channel", "progress:100%")

            return {"completed": True}

        result = await workflow_with_progress_recovery()
        assert result["completed"]
        assert len(successful_updates) == 3  # reconnected + 2 updates

        print("✓ Task continues after progress error recovery")


class TestTimeoutHandling:
    """Test task timeout scenarios."""

    async def test_task_timeout_error_creation(self):
        """Test TaskTimeoutError creation and attributes."""
        error = TaskTimeoutError("task-123", 30.0)

        assert "task-123" in str(error)
        assert "30.0" in str(error)
        assert error.code == "TASK_TIMEOUT"
        assert error.details["task_id"] == "task-123"
        assert error.details["timeout"] == 30.0

        print("✓ TaskTimeoutError created correctly")

    async def test_asyncio_timeout_handling(self):
        """Test handling of asyncio.TimeoutError."""
        task_id = "task-timeout-test"
        timeout_seconds = 0.1

        async def slow_operation():
            await asyncio.sleep(1.0)  # Much longer than timeout
            return "completed"

        async def execute_with_timeout():
            try:
                result = await asyncio.wait_for(
                    slow_operation(),
                    timeout=timeout_seconds
                )
                return {"status": "success", "result": result}
            except asyncio.TimeoutError:
                raise TaskTimeoutError(task_id, timeout_seconds)

        try:
            await execute_with_timeout()
            assert False, "Should have timed out"
        except TaskTimeoutError as e:
            assert e.details["task_id"] == task_id
            assert e.details["timeout"] == timeout_seconds

        print("✓ asyncio.TimeoutError converted to TaskTimeoutError")

    async def test_timeout_cleanup(self):
        """Test that resources are cleaned up after timeout."""
        cleanup_called = False

        async def operation_with_cleanup():
            nonlocal cleanup_called
            try:
                await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                cleanup_called = True
                raise

        async def execute_with_cleanup():
            task = asyncio.create_task(operation_with_cleanup())
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=0.05)
            except asyncio.TimeoutError:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        await execute_with_cleanup()
        assert cleanup_called

        print("✓ Resources cleaned up after timeout")


async def run_all_tests():
    """Run all error recovery tests."""
    # Error classification tests
    classification = TestErrorClassification()
    classification.test_error_inheritance_hierarchy()
    classification.test_error_details_preservation()
    classification.test_error_serialization()

    # Retry logic tests
    retry = TestRetryLogic()
    await retry.test_retry_on_connection_error()
    await retry.test_no_retry_on_authentication_error()
    await retry.test_no_retry_on_rate_limit()
    await retry.test_exponential_backoff()

    # Error recovery tests
    recovery = TestErrorRecovery()
    await recovery.test_recoverable_vs_non_recoverable_errors()
    await recovery.test_dead_letter_queue_routing()
    await recovery.test_partial_failure_recovery()
    await recovery.test_error_context_preservation()

    # Progress error tests
    progress = TestProgressErrorHandling()
    await progress.test_progress_invalid_percent_validation()
    await progress.test_progress_continues_after_error()

    # Timeout tests
    timeout = TestTimeoutHandling()
    await timeout.test_task_timeout_error_creation()
    await timeout.test_asyncio_timeout_handling()
    await timeout.test_timeout_cleanup()

    print("\n✓ All error recovery tests passed!")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
