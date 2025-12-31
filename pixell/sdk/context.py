"""UserContext - Execution context for agent tasks."""

from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime

from pixell.sdk.data_client import PXUIDataClient
from pixell.sdk.progress import ProgressReporter
from pixell.sdk.errors import ContextNotInitializedError


@dataclass
class TaskMetadata:
    """Metadata for a task execution.

    Attributes:
        task_id: Unique identifier for this task
        agent_id: ID of the agent handling this task
        user_id: ID of the user who initiated the task
        tenant_id: ID of the tenant/organization
        trace_id: Distributed tracing ID
        created_at: When the task was created
        timeout_at: When the task will timeout (optional)
    """

    task_id: str
    agent_id: str
    user_id: str
    tenant_id: str
    trace_id: str
    created_at: datetime
    timeout_at: Optional[datetime] = None
    payload: dict[str, Any] = field(default_factory=dict)


class UserContext:
    """Execution context for agent tasks with access to user data and APIs.

    This context is created for each task and provides methods for:
    - Calling OAuth APIs on behalf of the user
    - Retrieving user profile and data
    - Accessing user files
    - Getting conversation history
    - Reporting progress

    Example:
        async with UserContext.from_task(task_data) as ctx:
            profile = await ctx.get_user_profile()
            await ctx.report_progress("processing", percent=50)
            result = await ctx.call_oauth_api(
                provider="google",
                method="GET",
                path="/calendar/v3/calendars/primary/events"
            )
    """

    def __init__(
        self,
        metadata: TaskMetadata,
        client: PXUIDataClient,
        reporter: ProgressReporter,
    ) -> None:
        """Initialize the user context.

        Args:
            metadata: Task metadata
            client: PXUI data client for API calls
            reporter: Progress reporter for status updates
        """
        self._metadata = metadata
        self._client = client
        self._reporter = reporter
        self._closed = False

    @classmethod
    def from_task(
        cls,
        task_data: dict[str, Any],
        *,
        pxui_base_url: str,
        redis_url: str,
    ) -> "UserContext":
        """Create a UserContext from task data.

        Args:
            task_data: Task data dictionary with required fields:
                - task_id: str
                - agent_id: str
                - user_id: str
                - tenant_id: str
                - trace_id: str
                - jwt_token: str
                - payload: dict (optional)
            pxui_base_url: Base URL of the PXUI API
            redis_url: Redis connection URL

        Returns:
            Configured UserContext instance
        """
        metadata = TaskMetadata(
            task_id=task_data["task_id"],
            agent_id=task_data["agent_id"],
            user_id=task_data["user_id"],
            tenant_id=task_data["tenant_id"],
            trace_id=task_data["trace_id"],
            created_at=datetime.utcnow(),
            payload=task_data.get("payload", {}),
        )

        client = PXUIDataClient(
            base_url=pxui_base_url,
            jwt_token=task_data["jwt_token"],
        )

        reporter = ProgressReporter(
            redis_url=redis_url,
            task_id=task_data["task_id"],
            user_id=task_data["user_id"],
        )

        return cls(metadata, client, reporter)

    def _check_closed(self) -> None:
        """Raise an error if context has been closed."""
        if self._closed:
            raise ContextNotInitializedError("Context has been closed")

    # Properties

    @property
    def task_id(self) -> str:
        """Get the task ID."""
        return self._metadata.task_id

    @property
    def agent_id(self) -> str:
        """Get the agent ID."""
        return self._metadata.agent_id

    @property
    def user_id(self) -> str:
        """Get the user ID."""
        return self._metadata.user_id

    @property
    def tenant_id(self) -> str:
        """Get the tenant ID."""
        return self._metadata.tenant_id

    @property
    def trace_id(self) -> str:
        """Get the trace ID for distributed tracing."""
        return self._metadata.trace_id

    @property
    def payload(self) -> dict[str, Any]:
        """Get the task payload."""
        return self._metadata.payload

    # OAuth API Methods

    async def call_oauth_api(
        self,
        provider: str,
        method: str,
        path: str,
        body: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """Make a proxied OAuth API call.

        Args:
            provider: OAuth provider (e.g., "google", "github", "tiktok")
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            path: API path for the provider's API
            body: Request body (optional)
            headers: Additional headers (optional)

        Returns:
            Response from the OAuth provider's API

        Example:
            events = await ctx.call_oauth_api(
                provider="google",
                method="GET",
                path="/calendar/v3/calendars/primary/events",
            )
        """
        self._check_closed()
        return await self._client.oauth_proxy_call(
            user_id=self._metadata.user_id,
            provider=provider,
            method=method,
            path=path,
            body=body,
            headers=headers,
        )

    # User Data Methods

    async def get_user_profile(self) -> dict[str, Any]:
        """Get the current user's profile.

        Returns:
            User profile data
        """
        self._check_closed()
        return await self._client.get_user_profile(self._metadata.user_id)

    async def get_files(
        self,
        *,
        filter: Optional[dict[str, Any]] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get files accessible to the user.

        Args:
            filter: Optional filter criteria
            limit: Maximum number of files to return

        Returns:
            List of file metadata
        """
        self._check_closed()
        return await self._client.list_files(
            user_id=self._metadata.user_id,
            filter=filter,
            limit=limit,
        )

    async def get_file_content(self, file_id: str) -> bytes:
        """Download file content.

        Args:
            file_id: The file ID

        Returns:
            File content as bytes
        """
        self._check_closed()
        return await self._client.get_file_content(
            user_id=self._metadata.user_id,
            file_id=file_id,
        )

    async def get_conversations(
        self,
        *,
        limit: int = 50,
        since: Optional[datetime] = None,
    ) -> list[dict[str, Any]]:
        """Get conversation history.

        Args:
            limit: Maximum number of conversations to return
            since: Only return conversations after this time

        Returns:
            List of conversation data
        """
        self._check_closed()
        return await self._client.list_conversations(
            user_id=self._metadata.user_id,
            limit=limit,
            since=since,
        )

    async def get_task_history(
        self,
        *,
        agent_id: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get task execution history.

        Args:
            agent_id: Optional filter by agent ID
            limit: Maximum number of tasks to return

        Returns:
            List of task history records
        """
        self._check_closed()
        return await self._client.list_task_history(
            user_id=self._metadata.user_id,
            agent_id=agent_id,
            limit=limit,
        )

    # Progress Reporting Methods

    async def report_progress(
        self,
        status: str,
        *,
        percent: Optional[float] = None,
        message: Optional[str] = None,
    ) -> None:
        """Report progress on the current task.

        Args:
            status: Current status (e.g., "starting", "processing", "analyzing")
            percent: Optional completion percentage (0-100)
            message: Optional human-readable message

        Example:
            await ctx.report_progress("processing", percent=50, message="Halfway done")
        """
        self._check_closed()
        await self._reporter.update(status, percent=percent, message=message)

    async def report_error(
        self,
        error_type: str,
        message: str,
        *,
        recoverable: bool = False,
    ) -> None:
        """Report an error on the current task.

        Args:
            error_type: Type of error (e.g., "API_ERROR", "VALIDATION_ERROR")
            message: Human-readable error message
            recoverable: Whether the task can be retried

        Example:
            await ctx.report_error(
                "API_ERROR",
                "External API returned 500",
                recoverable=True
            )
        """
        self._check_closed()
        await self._reporter.error(error_type, message, recoverable=recoverable)

    # Lifecycle Methods

    async def close(self) -> None:
        """Close the context and release resources."""
        if not self._closed:
            self._closed = True
            await self._client.close()
            await self._reporter.close()

    async def __aenter__(self) -> "UserContext":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()
