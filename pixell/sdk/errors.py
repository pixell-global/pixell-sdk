"""SDK exception hierarchy for pixell-sdk runtime."""

from typing import Any, Optional


class SDKError(Exception):
    """Base exception for all SDK errors.

    Attributes:
        code: Machine-readable error code.
        details: Additional error details.
        cause: Original exception that caused this error.
    """

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message)
        self.code = code or "SDK_ERROR"
        self.details = details or {}
        self.cause = cause

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for serialization."""
        return {
            "error": self.code,
            "message": str(self),
            "details": self.details,
        }


# Task Consumer Errors
class ConsumerError(SDKError):
    """Task consumer related errors."""

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(
            message,
            code=code or "CONSUMER_ERROR",
            details=details,
            cause=cause,
        )


class TaskTimeoutError(ConsumerError):
    """Task execution timed out."""

    def __init__(self, task_id: str, timeout: float) -> None:
        super().__init__(
            f"Task {task_id} timed out after {timeout}s",
            code="TASK_TIMEOUT",
            details={"task_id": task_id, "timeout": timeout},
        )


class TaskHandlerError(ConsumerError):
    """Error in task handler execution."""

    def __init__(
        self,
        message: str,
        *,
        task_id: Optional[str] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        details = {}
        if task_id:
            details["task_id"] = task_id
        super().__init__(
            message,
            code="TASK_HANDLER_ERROR",
            details=details,
            cause=cause,
        )


class QueueError(ConsumerError):
    """Error with task queue operations."""

    def __init__(
        self,
        message: str,
        *,
        queue_name: Optional[str] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        details = {}
        if queue_name:
            details["queue_name"] = queue_name
        super().__init__(
            message,
            code="QUEUE_ERROR",
            details=details,
            cause=cause,
        )


# HTTP Client Errors
class ClientError(SDKError):
    """HTTP client related errors."""

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(
            message,
            code=code or "CLIENT_ERROR",
            details=details,
            cause=cause,
        )


class AuthenticationError(ClientError):
    """Authentication failed."""

    def __init__(
        self,
        message: str = "Authentication failed",
        *,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(
            message,
            code="AUTH_FAILED",
            cause=cause,
        )


class RateLimitError(ClientError):
    """Rate limit exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        *,
        retry_after: Optional[int] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        details: dict[str, Any] = {}
        if retry_after is not None:
            details["retry_after"] = retry_after
        super().__init__(
            message,
            code="RATE_LIMITED",
            details=details,
            cause=cause,
        )


class APIError(ClientError):
    """API returned an error response."""

    def __init__(
        self,
        status_code: int,
        response_body: Optional[dict[str, Any]] = None,
        *,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(
            f"API error: HTTP {status_code}",
            code="API_ERROR",
            details={
                "status_code": status_code,
                "response": response_body or {},
            },
            cause=cause,
        )


class ConnectionError(ClientError):
    """Failed to connect to server."""

    def __init__(
        self,
        message: str = "Failed to connect to server",
        *,
        url: Optional[str] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        details: dict[str, Any] = {}
        if url:
            details["url"] = url
        super().__init__(
            message,
            code="CONNECTION_ERROR",
            details=details,
            cause=cause,
        )


# Context Errors
class ContextError(SDKError):
    """Context-related errors."""

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(
            message,
            code=code or "CONTEXT_ERROR",
            details=details,
            cause=cause,
        )


class ContextNotInitializedError(ContextError):
    """Context not properly initialized."""

    def __init__(
        self,
        message: str = "Context not initialized",
        *,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(
            message,
            code="CONTEXT_NOT_INITIALIZED",
            cause=cause,
        )


# Progress Reporting Errors
class ProgressError(SDKError):
    """Progress reporting errors."""

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(
            message,
            code=code or "PROGRESS_ERROR",
            details=details,
            cause=cause,
        )
