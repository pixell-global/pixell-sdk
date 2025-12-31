"""ProgressReporter - Real-time progress updates via Redis pub/sub."""

import json
from typing import Any, Optional
from datetime import datetime

import redis.asyncio as redis

from pixell.sdk.errors import ProgressError


class ProgressReporter:
    """Reports task progress via Redis pub/sub.

    This class publishes progress updates to a Redis channel that clients
    can subscribe to for real-time task status updates.

    Channel format: pixell:tasks:{task_id}:progress

    Example:
        reporter = ProgressReporter(redis_url, task_id, user_id)
        await reporter.update("processing", percent=50, message="Halfway done")
        await reporter.error("API_ERROR", "External API failed", recoverable=True)
        await reporter.complete({"result": "data"})
    """

    def __init__(
        self,
        redis_url: str,
        task_id: str,
        user_id: str,
    ) -> None:
        """Initialize the progress reporter.

        Args:
            redis_url: Redis connection URL
            task_id: The task ID for progress reporting
            user_id: The user ID associated with this task
        """
        self.redis_url = redis_url
        self.task_id = task_id
        self.user_id = user_id
        self._client: Optional[redis.Redis] = None

    @property
    def channel(self) -> str:
        """Get the Redis channel name for this task."""
        return f"pixell:tasks:{self.task_id}:progress"

    async def _get_client(self) -> redis.Redis:
        """Get or create the Redis client."""
        if self._client is None:
            self._client = redis.from_url(
                self.redis_url,
                decode_responses=True,
            )
        return self._client

    async def _publish(self, data: dict[str, Any]) -> None:
        """Publish a message to the progress channel.

        Args:
            data: Message data to publish
        """
        try:
            client = await self._get_client()
            message = json.dumps({
                **data,
                "task_id": self.task_id,
                "user_id": self.user_id,
                "timestamp": datetime.utcnow().isoformat(),
            })
            await client.publish(self.channel, message)
        except Exception as e:
            raise ProgressError(
                f"Failed to publish progress update: {e}",
                code="PUBLISH_ERROR",
                cause=e,
            )

    async def update(
        self,
        status: str,
        *,
        percent: Optional[float] = None,
        message: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Report a progress update.

        Args:
            status: Current status (e.g., "starting", "processing", "completed")
            percent: Optional completion percentage (0-100)
            message: Optional human-readable message
            metadata: Optional additional metadata
        """
        data: dict[str, Any] = {
            "type": "progress",
            "status": status,
        }

        if percent is not None:
            if not 0 <= percent <= 100:
                raise ProgressError(
                    f"Percent must be between 0 and 100, got {percent}",
                    code="INVALID_PERCENT",
                )
            data["percent"] = percent

        if message:
            data["message"] = message

        if metadata:
            data["metadata"] = metadata

        await self._publish(data)

    async def error(
        self,
        error_type: str,
        message: str,
        *,
        recoverable: bool = False,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Report an error.

        Args:
            error_type: Type of error (e.g., "API_ERROR", "TIMEOUT")
            message: Human-readable error message
            recoverable: Whether the task can be retried
            details: Optional error details
        """
        data: dict[str, Any] = {
            "type": "error",
            "error_type": error_type,
            "message": message,
            "recoverable": recoverable,
        }

        if details:
            data["details"] = details

        await self._publish(data)

    async def complete(
        self,
        result: Optional[dict[str, Any]] = None,
    ) -> None:
        """Report task completion.

        Args:
            result: Optional result data
        """
        data: dict[str, Any] = {
            "type": "complete",
            "status": "completed",
        }

        if result:
            data["result"] = result

        await self._publish(data)

    async def close(self) -> None:
        """Close the Redis client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "ProgressReporter":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()
