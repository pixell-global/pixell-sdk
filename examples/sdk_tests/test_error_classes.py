#!/usr/bin/env python3
"""Test error class instantiation and attributes."""

from pixell.sdk import (
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


def test_sdk_error():
    """Test SDKError base class."""
    error = SDKError("Test error", code="TEST_CODE", details={"key": "value"})
    assert error.code == "TEST_CODE"
    assert error.details == {"key": "value"}
    assert str(error) == "Test error"
    print("✓ SDKError works correctly")


def test_task_timeout_error():
    """Test TaskTimeoutError with task_id and timeout."""
    error = TaskTimeoutError("task-123", 30.0)
    assert "task-123" in str(error)
    assert error.details["task_id"] == "task-123"
    assert error.details["timeout"] == 30.0
    print("✓ TaskTimeoutError works correctly")


def test_task_handler_error():
    """Test TaskHandlerError with cause."""
    cause = ValueError("Original error")
    error = TaskHandlerError("Handler failed", task_id="task-123", cause=cause)
    assert error.details["task_id"] == "task-123"
    assert error.cause is cause
    print("✓ TaskHandlerError works correctly")


def test_queue_error():
    """Test QueueError with queue name."""
    error = QueueError("Queue unavailable", queue_name="test-queue")
    assert error.details["queue_name"] == "test-queue"
    print("✓ QueueError works correctly")


def test_rate_limit_error():
    """Test RateLimitError with retry_after."""
    error = RateLimitError("Rate limited", retry_after=60)
    assert error.details["retry_after"] == 60
    print("✓ RateLimitError works correctly")


def test_api_error():
    """Test APIError with status code and response."""
    error = APIError(500, response_body={"error": "Internal error"})
    assert error.details["status_code"] == 500
    assert error.details["response"] == {"error": "Internal error"}
    print("✓ APIError works correctly")


def test_authentication_error():
    """Test AuthenticationError."""
    error = AuthenticationError("Invalid token")
    assert str(error) == "Invalid token"
    # Test default message
    error_default = AuthenticationError()
    assert str(error_default) == "Authentication failed"
    print("✓ AuthenticationError works correctly")


def test_connection_error():
    """Test ConnectionError with URL."""
    error = ConnectionError("Connection failed", url="https://api.example.com")
    assert error.details["url"] == "https://api.example.com"
    print("✓ ConnectionError works correctly")


def test_context_errors():
    """Test context-related errors."""
    error = ContextError("Context error")
    assert error.code == "CONTEXT_ERROR"

    not_init_error = ContextNotInitializedError()
    assert str(not_init_error) == "Context not initialized"
    print("✓ Context errors work correctly")


def test_progress_error():
    """Test ProgressError."""
    error = ProgressError("Progress update failed")
    assert error.code == "PROGRESS_ERROR"
    print("✓ ProgressError works correctly")


def test_error_inheritance():
    """Verify error inheritance hierarchy."""
    assert issubclass(ConsumerError, SDKError)
    assert issubclass(TaskTimeoutError, ConsumerError)
    assert issubclass(TaskHandlerError, ConsumerError)
    assert issubclass(QueueError, ConsumerError)
    assert issubclass(ClientError, SDKError)
    assert issubclass(AuthenticationError, ClientError)
    assert issubclass(RateLimitError, ClientError)
    assert issubclass(APIError, ClientError)
    assert issubclass(ConnectionError, ClientError)
    assert issubclass(ContextError, SDKError)
    assert issubclass(ContextNotInitializedError, ContextError)
    assert issubclass(ProgressError, SDKError)
    print("✓ Error inheritance hierarchy is correct")


def test_error_to_dict():
    """Test error serialization."""
    error = SDKError("Test error", code="TEST_CODE", details={"key": "value"})
    result = error.to_dict()
    assert result["error"] == "TEST_CODE"
    assert result["message"] == "Test error"
    assert result["details"] == {"key": "value"}
    print("✓ Error serialization works correctly")


if __name__ == "__main__":
    test_sdk_error()
    test_task_timeout_error()
    test_task_handler_error()
    test_queue_error()
    test_rate_limit_error()
    test_api_error()
    test_authentication_error()
    test_connection_error()
    test_context_errors()
    test_progress_error()
    test_error_inheritance()
    test_error_to_dict()
    print("\n✓ All error class tests passed!")
