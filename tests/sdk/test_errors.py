"""Tests for SDK error classes."""

import pytest
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


class TestSDKError:
    """Tests for base SDKError."""

    def test_basic_error(self):
        """Test basic error creation."""
        error = SDKError("Test error")
        assert str(error) == "Test error"
        assert error.code == "SDK_ERROR"
        assert error.details == {}

    def test_error_with_code(self):
        """Test error with custom code."""
        error = SDKError("Test error", code="CUSTOM_CODE")
        assert error.code == "CUSTOM_CODE"

    def test_error_with_details(self):
        """Test error with details."""
        error = SDKError("Test error", details={"key": "value"})
        assert error.details == {"key": "value"}

    def test_error_with_cause(self):
        """Test error with cause."""
        cause = ValueError("Original error")
        error = SDKError("Wrapper error", cause=cause)
        assert error.cause is cause

    def test_to_dict(self):
        """Test error serialization."""
        error = SDKError("Test error", code="TEST_CODE", details={"key": "value"})
        result = error.to_dict()
        assert result["error"] == "TEST_CODE"
        assert result["message"] == "Test error"
        assert result["details"] == {"key": "value"}


class TestConsumerErrors:
    """Tests for consumer-related errors."""

    def test_consumer_error(self):
        """Test ConsumerError."""
        error = ConsumerError("Consumer failed")
        assert str(error) == "Consumer failed"
        assert error.code == "CONSUMER_ERROR"

    def test_task_timeout_error(self):
        """Test TaskTimeoutError."""
        error = TaskTimeoutError("task-123", 30.0)
        assert "task-123" in str(error)
        assert "30.0" in str(error)
        assert error.code == "TASK_TIMEOUT"
        assert error.details["task_id"] == "task-123"
        assert error.details["timeout"] == 30.0

    def test_task_handler_error(self):
        """Test TaskHandlerError."""
        cause = ValueError("Handler failed")
        error = TaskHandlerError("Handler error", task_id="task-123", cause=cause)
        assert "Handler error" in str(error)
        assert error.code == "TASK_HANDLER_ERROR"
        assert error.details["task_id"] == "task-123"
        assert error.cause is cause

    def test_queue_error(self):
        """Test QueueError."""
        error = QueueError("Queue unavailable")
        assert str(error) == "Queue unavailable"
        assert error.code == "QUEUE_ERROR"

    def test_queue_error_with_name(self):
        """Test QueueError with queue name."""
        error = QueueError("Queue unavailable", queue_name="test-queue")
        assert error.details["queue_name"] == "test-queue"


class TestClientErrors:
    """Tests for HTTP client errors."""

    def test_client_error(self):
        """Test ClientError."""
        error = ClientError("Request failed")
        assert str(error) == "Request failed"
        assert error.code == "CLIENT_ERROR"

    def test_authentication_error(self):
        """Test AuthenticationError."""
        error = AuthenticationError("Invalid token")
        assert str(error) == "Invalid token"
        assert error.code == "AUTH_FAILED"

    def test_authentication_error_default_message(self):
        """Test AuthenticationError with default message."""
        error = AuthenticationError()
        assert str(error) == "Authentication failed"

    def test_rate_limit_error(self):
        """Test RateLimitError."""
        error = RateLimitError("Rate limited", retry_after=60)
        assert "Rate limited" in str(error)
        assert error.code == "RATE_LIMITED"
        assert error.details["retry_after"] == 60

    def test_rate_limit_error_without_retry(self):
        """Test RateLimitError without retry_after."""
        error = RateLimitError("Rate limited")
        assert error.details == {}

    def test_api_error(self):
        """Test APIError."""
        error = APIError(500, response_body={"error": "Internal error"})
        assert "500" in str(error)
        assert error.code == "API_ERROR"
        assert error.details["status_code"] == 500
        assert error.details["response"] == {"error": "Internal error"}

    def test_api_error_without_body(self):
        """Test APIError without response body."""
        error = APIError(404)
        assert error.details["status_code"] == 404
        assert error.details["response"] == {}

    def test_connection_error(self):
        """Test ConnectionError."""
        error = ConnectionError("Connection failed", url="https://api.example.com")
        assert "Connection failed" in str(error)
        assert error.code == "CONNECTION_ERROR"
        assert error.details["url"] == "https://api.example.com"

    def test_connection_error_default_message(self):
        """Test ConnectionError with default message."""
        error = ConnectionError()
        assert str(error) == "Failed to connect to server"


class TestContextErrors:
    """Tests for context errors."""

    def test_context_error(self):
        """Test ContextError."""
        error = ContextError("Context error")
        assert str(error) == "Context error"
        assert error.code == "CONTEXT_ERROR"

    def test_context_not_initialized_error(self):
        """Test ContextNotInitializedError."""
        error = ContextNotInitializedError("Not initialized")
        assert str(error) == "Not initialized"
        assert error.code == "CONTEXT_NOT_INITIALIZED"

    def test_context_not_initialized_default_message(self):
        """Test ContextNotInitializedError with default message."""
        error = ContextNotInitializedError()
        assert str(error) == "Context not initialized"


class TestProgressError:
    """Tests for progress errors."""

    def test_progress_error(self):
        """Test ProgressError."""
        error = ProgressError("Progress update failed")
        assert str(error) == "Progress update failed"
        assert error.code == "PROGRESS_ERROR"

    def test_progress_error_with_cause(self):
        """Test ProgressError with cause."""
        cause = OSError("Redis connection failed")
        error = ProgressError("Progress update failed", cause=cause)
        assert error.cause is cause

    def test_progress_error_with_custom_code(self):
        """Test ProgressError with custom code."""
        error = ProgressError("Invalid percent", code="INVALID_PERCENT")
        assert error.code == "INVALID_PERCENT"
