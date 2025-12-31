"""TaskConsumer - Redis task queue consumer for agent execution."""

import json
import asyncio
from typing import Any, Optional, Callable, Awaitable
from datetime import datetime

import redis.asyncio as redis

from pixell.sdk.context import UserContext
from pixell.sdk.errors import (
    ConsumerError,
    TaskTimeoutError,
    TaskHandlerError,
    QueueError,
)


# Type alias for task handler function
TaskHandler = Callable[[UserContext, dict[str, Any]], Awaitable[dict[str, Any]]]


class TaskConsumer:
    """Consumes tasks from Redis queue and processes with UserContext.

    The consumer polls a Redis list for tasks, creates a UserContext for each,
    and invokes the provided handler function.

    Queue format: pixell:agents:{agent_id}:tasks
    Status key: pixell:agents:{agent_id}:status

    Example:
        async def handle_task(ctx: UserContext, payload: dict) -> dict:
            await ctx.report_progress("processing", percent=0)
            result = await ctx.call_oauth_api(...)
            return {"status": "success", "data": result}

        consumer = TaskConsumer(
            agent_id="my-agent",
            redis_url="redis://localhost:6379",
            pxui_base_url="https://api.pixell.global",
            handler=handle_task,
        )
        await consumer.start()
    """

    def __init__(
        self,
        agent_id: str,
        redis_url: str,
        pxui_base_url: str,
        handler: TaskHandler,
        *,
        concurrency: int = 10,
        poll_interval: float = 1.0,
        task_timeout: float = 300.0,
    ) -> None:
        """Initialize the task consumer.

        Args:
            agent_id: The agent ID for queue identification
            redis_url: Redis connection URL
            pxui_base_url: Base URL of the PXUI API
            handler: Async function to handle each task
            concurrency: Maximum concurrent task processing
            poll_interval: Interval between queue polls in seconds
            task_timeout: Timeout for task execution in seconds
        """
        self.agent_id = agent_id
        self.redis_url = redis_url
        self.pxui_base_url = pxui_base_url
        self.handler = handler
        self.concurrency = concurrency
        self.poll_interval = poll_interval
        self.task_timeout = task_timeout

        self._client: Optional[redis.Redis] = None
        self._running = False
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._tasks: set[asyncio.Task] = set()

    @property
    def queue_key(self) -> str:
        """Get the Redis key for the task queue."""
        return f"pixell:agents:{self.agent_id}:tasks"

    @property
    def processing_key(self) -> str:
        """Get the Redis key for tasks being processed."""
        return f"pixell:agents:{self.agent_id}:processing"

    @property
    def status_key(self) -> str:
        """Get the Redis key for agent status."""
        return f"pixell:agents:{self.agent_id}:status"

    @property
    def dead_letter_key(self) -> str:
        """Get the Redis key for dead letter queue."""
        return f"pixell:agents:{self.agent_id}:dead_letter"

    async def _get_client(self) -> redis.Redis:
        """Get or create the Redis client."""
        if self._client is None:
            self._client = redis.from_url(
                self.redis_url,
                decode_responses=True,
            )
        return self._client

    async def _update_status(
        self,
        task_id: str,
        status: str,
        result: Optional[dict[str, Any]] = None,
    ) -> None:
        """Update task status in Redis.

        Args:
            task_id: The task ID
            status: New status
            result: Optional result data
        """
        client = await self._get_client()
        status_data = {
            "task_id": task_id,
            "agent_id": self.agent_id,
            "status": status,
            "updated_at": datetime.utcnow().isoformat(),
        }
        if result:
            status_data["result"] = result

        await client.hset(
            f"pixell:tasks:{task_id}:status",
            mapping={k: json.dumps(v) if isinstance(v, dict) else str(v) for k, v in status_data.items()},
        )

    async def _handle_error(
        self,
        task_id: str,
        error: Exception,
        recoverable: bool,
    ) -> None:
        """Handle task error with proper reporting.

        Args:
            task_id: The task ID
            error: The error that occurred
            recoverable: Whether the task can be retried
        """
        from pixell.sdk.errors import SDKError

        error_data: dict[str, Any] = {
            "error_type": type(error).__name__,
            "message": str(error),
            "recoverable": recoverable,
        }

        if isinstance(error, SDKError):
            error_data["code"] = error.code
            error_data["details"] = error.details

        await self._update_status(task_id, "failed", error_data)

        # Move to dead letter queue if not recoverable
        if not recoverable:
            client = await self._get_client()
            await client.lpush(
                self.dead_letter_key,
                json.dumps({"task_id": task_id, "error": error_data}),
            )

    async def _process_task(self, task_data_str: str) -> None:
        """Process a single task.

        Args:
            task_data_str: JSON string of task data
        """
        task_data = json.loads(task_data_str)
        task_id = task_data.get("task_id", "unknown")

        try:
            await self._update_status(task_id, "processing")

            # Create context for this task
            ctx = UserContext.from_task(
                task_data,
                pxui_base_url=self.pxui_base_url,
                redis_url=self.redis_url,
            )

            async with ctx:
                # Execute handler with timeout
                result = await asyncio.wait_for(
                    self.handler(ctx, task_data.get("payload", {})),
                    timeout=self.task_timeout,
                )

                # Mark as completed
                await self._update_status(task_id, "completed", result)

        except asyncio.TimeoutError:
            error = TaskTimeoutError(task_id, self.task_timeout)
            await self._handle_error(task_id, error, recoverable=False)

        except Exception as e:
            from pixell.sdk.errors import ClientError, RateLimitError

            # Client errors may be retryable
            if isinstance(e, RateLimitError):
                await self._handle_error(task_id, e, recoverable=True)
            elif isinstance(e, ClientError):
                await self._handle_error(task_id, e, recoverable=False)
            else:
                # Unexpected errors
                wrapped = TaskHandlerError(
                    f"Unexpected error in task handler: {e}",
                    task_id=task_id,
                    cause=e,
                )
                await self._handle_error(task_id, wrapped, recoverable=False)

        finally:
            # Remove from processing list
            client = await self._get_client()
            await client.lrem(self.processing_key, 1, task_data_str)

    async def _process_with_semaphore(self, task_data: str) -> None:
        """Process task with semaphore for concurrency control.

        Args:
            task_data: JSON string of task data
        """
        if self._semaphore is None:
            raise ConsumerError("Consumer not started")

        async with self._semaphore:
            await self._process_task(task_data)

    async def _poll_and_process(self) -> None:
        """Poll for tasks and process them."""
        client = await self._get_client()

        # Use BRPOPLPUSH for reliable queue processing
        # Moves task from queue to processing list atomically
        task_data = await client.brpoplpush(
            self.queue_key,
            self.processing_key,
            timeout=1,  # 1 second timeout for responsive shutdown
        )

        if task_data:
            # Create task with semaphore control
            task = asyncio.create_task(self._process_with_semaphore(task_data))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    async def start(self) -> None:
        """Start consuming tasks. Runs until stop() is called or cancelled.

        This method will block and continuously poll the queue for tasks.
        Use stop() to gracefully shut down.
        """
        self._running = True
        self._semaphore = asyncio.Semaphore(self.concurrency)
        self._tasks = set()

        try:
            # Update agent status
            client = await self._get_client()
            await client.hset(
                self.status_key,
                mapping={
                    "status": "running",
                    "started_at": datetime.utcnow().isoformat(),
                    "concurrency": str(self.concurrency),
                },
            )

            while self._running:
                try:
                    await self._poll_and_process()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    # Log error but continue processing
                    print(f"Error polling queue: {e}")
                    await asyncio.sleep(self.poll_interval)

        finally:
            # Wait for in-flight tasks to complete
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)

            # Update agent status
            client = await self._get_client()
            await client.hset(
                self.status_key,
                mapping={
                    "status": "stopped",
                    "stopped_at": datetime.utcnow().isoformat(),
                },
            )

    async def stop(self, graceful: bool = True) -> None:
        """Stop the consumer.

        Args:
            graceful: If True, wait for in-flight tasks to complete
        """
        self._running = False

        if not graceful:
            # Cancel all in-flight tasks
            for task in self._tasks:
                task.cancel()

    async def close(self) -> None:
        """Close the Redis client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "TaskConsumer":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.stop()
        await self.close()
