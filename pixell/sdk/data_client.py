"""PXUIDataClient - Async HTTP client for PXUI platform API."""

from typing import Any, Optional
from datetime import datetime

import httpx

from pixell.sdk.errors import (
    AuthenticationError,
    RateLimitError,
    APIError,
    ConnectionError,
)


class PXUIDataClient:
    """Async HTTP client for PXUI platform API.

    This client provides methods for:
    - OAuth proxy calls to external providers
    - User profile and data retrieval
    - File operations
    - Conversation history
    - Task history

    Example:
        async with PXUIDataClient(base_url, jwt_token) as client:
            profile = await client.get_user_profile(user_id)
            files = await client.list_files(user_id)
    """

    def __init__(
        self,
        base_url: str,
        jwt_token: str,
        *,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """Initialize the PXUI data client.

        Args:
            base_url: Base URL of the PXUI API (e.g., "https://api.pixell.global")
            jwt_token: JWT token for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self.base_url = base_url.rstrip("/")
        self.jwt_token = jwt_token
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
                headers={
                    "Authorization": f"Bearer {self.jwt_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._client

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Make an HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            path: API path (e.g., "/api/users/123/profile")
            json: JSON body for the request
            params: Query parameters

        Returns:
            Response data as dictionary

        Raises:
            AuthenticationError: If authentication fails (401)
            RateLimitError: If rate limited (429)
            APIError: For other API errors (4xx, 5xx)
            ConnectionError: If connection fails
        """
        client = await self._get_client()
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                response = await client.request(
                    method,
                    path,
                    json=json,
                    params=params,
                )

                # Handle error responses
                if response.status_code == 401:
                    raise AuthenticationError("Invalid or expired token")
                elif response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    raise RateLimitError(retry_after=int(retry_after) if retry_after else None)
                elif response.status_code >= 400:
                    try:
                        body = response.json()
                    except Exception:
                        body = {"raw": response.text}
                    raise APIError(response.status_code, body)

                # Success - return JSON response
                return response.json()

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    import asyncio

                    await asyncio.sleep(2**attempt)
                    continue
                raise ConnectionError(
                    f"Failed to connect after {self.max_retries} attempts",
                    url=f"{self.base_url}{path}",
                    cause=e,
                )
            except (AuthenticationError, RateLimitError, APIError):
                # Don't retry these errors
                raise

        # Should not reach here, but just in case
        raise ConnectionError(
            "Request failed",
            cause=last_error,
        )

    # OAuth Proxy Methods

    async def oauth_proxy_call(
        self,
        user_id: str,
        provider: str,
        method: str,
        path: str,
        body: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """Make a proxied OAuth API call on behalf of a user.

        Args:
            user_id: The user ID
            provider: OAuth provider name (e.g., "google", "github", "tiktok")
            method: HTTP method for the proxied request
            path: API path for the provider's API
            body: Request body for the proxied request
            headers: Additional headers for the proxied request

        Returns:
            Response from the OAuth provider's API
        """
        return await self._request(
            "POST",
            "/api/oauth/proxy",
            json={
                "user_id": user_id,
                "provider": provider,
                "method": method,
                "path": path,
                "body": body,
                "headers": headers,
            },
        )

    # User Methods

    async def get_user_profile(self, user_id: str) -> dict[str, Any]:
        """Get user profile information.

        Args:
            user_id: The user ID

        Returns:
            User profile data
        """
        return await self._request("GET", f"/api/users/{user_id}/profile")

    # File Methods

    async def register_file(
        self,
        *,
        name: str,
        url: str,
        mime_type: str,
        size: int,
        source: str = "agent",
        agent_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Register a file that was uploaded to S3.

        This method is used by agents that upload files directly to S3
        and need to register them with the platform so they appear in
        the user's Files panel.

        Args:
            name: Display name for the file (e.g., "Reddit Research: Tesla")
            url: S3 URL where file is stored
            mime_type: MIME type (e.g., "text/html", "application/pdf")
            size: File size in bytes
            source: Source identifier (e.g., "reddit-research-agent")
            agent_id: Agent identifier for grouping in Files panel (e.g., "reddit-agent")

        Returns:
            File metadata from API including:
            - id: File ID in the database
            - name: Display name
            - url: S3 URL
            - mime_type: MIME type
            - size: Size in bytes
            - source: Source identifier
            - agent_id: Agent identifier
            - created_at: Creation timestamp

        Example:
            await client.register_file(
                name="Reddit Research: Tesla",
                url="https://pixell-reports.s3.amazonaws.com/reports/tesla_20240115.html",
                mime_type="text/html",
                size=45678,
                source="reddit-research-agent",
                agent_id="reddit-agent",
            )
        """
        payload = {
            "name": name,
            "url": url,
            "mime_type": mime_type,
            "size": size,
            "source": source,
        }
        if agent_id:
            payload["agent_id"] = agent_id
        return await self._request(
            "POST",
            "/api/v1/files/register",
            json=payload,
        )

    async def list_files(
        self,
        user_id: str,
        *,
        filter: Optional[dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List files accessible to the user.

        Args:
            user_id: The user ID
            filter: Optional filter criteria
            limit: Maximum number of files to return
            offset: Offset for pagination

        Returns:
            List of file metadata
        """
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if filter:
            params["filter"] = filter

        response = await self._request(
            "GET",
            f"/api/users/{user_id}/files",
            params=params,
        )
        return response.get("files", [])

    async def get_file_content(self, user_id: str, file_id: str) -> bytes:
        """Download file content.

        Args:
            user_id: The user ID
            file_id: The file ID

        Returns:
            File content as bytes
        """
        client = await self._get_client()
        response = await client.get(f"/api/users/{user_id}/files/{file_id}/content")

        if response.status_code == 401:
            raise AuthenticationError("Invalid or expired token")
        elif response.status_code >= 400:
            raise APIError(response.status_code, {"file_id": file_id})

        return response.content

    # Conversation Methods

    async def list_conversations(
        self,
        user_id: str,
        *,
        limit: int = 50,
        since: Optional[datetime] = None,
    ) -> list[dict[str, Any]]:
        """Get conversation history for a user.

        Args:
            user_id: The user ID
            limit: Maximum number of conversations to return
            since: Only return conversations after this time

        Returns:
            List of conversation data
        """
        params: dict[str, Any] = {"limit": limit}
        if since:
            params["since"] = since.isoformat()

        response = await self._request(
            "GET",
            f"/api/users/{user_id}/conversations",
            params=params,
        )
        return response.get("conversations", [])

    # Task History Methods

    async def list_task_history(
        self,
        user_id: str,
        *,
        agent_id: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get task execution history.

        Args:
            user_id: The user ID
            agent_id: Optional filter by agent ID
            limit: Maximum number of tasks to return

        Returns:
            List of task history records
        """
        params: dict[str, Any] = {"limit": limit}
        if agent_id:
            params["agent_id"] = agent_id

        response = await self._request(
            "GET",
            f"/api/users/{user_id}/tasks",
            params=params,
        )
        return response.get("tasks", [])

    # Brand Methods

    async def get_brand(self) -> Optional[dict[str, Any]]:
        """Get the user's brand (from their primary organization).

        Returns:
            Brand data including competitors, or None if no brand exists
        """
        try:
            return await self._request("GET", "/api/v1/brands")
        except APIError as e:
            if e.status_code == 404:
                return None
            raise

    async def get_brand_by_id(self, brand_id: str) -> dict[str, Any]:
        """Get brand by ID.

        Args:
            brand_id: The brand ID

        Returns:
            Brand data including competitors
        """
        return await self._request("GET", f"/api/v1/brands/{brand_id}")

    async def get_brand_competitors(
        self,
        brand_id: str,
        *,
        confirmed_only: bool = True,
    ) -> list[dict[str, Any]]:
        """Get competitors for a brand.

        Args:
            brand_id: The brand ID
            confirmed_only: If True, only return confirmed competitors

        Returns:
            List of competitor data
        """
        response = await self._request(
            "GET",
            f"/api/v1/brands/{brand_id}/competitors",
            params={"confirmed_only": confirmed_only},
        )
        # Response is already a list
        return response if isinstance(response, list) else response.get("competitors", [])

    async def get_brand_context(self) -> Optional[dict[str, Any]]:
        """Get brand context for use in agents.

        This is a convenience method that fetches the user's brand
        and formats it for use in agent context.

        Returns:
            Brand context dict with:
            - brand_name: str
            - brand_id: str
            - industry: str | None
            - competitors: list[str]
            Or None if no brand exists
        """
        brand = await self.get_brand()
        if not brand:
            return None

        # Get confirmed competitors
        competitors = await self.get_brand_competitors(
            brand["id"],
            confirmed_only=True,
        )

        return {
            "brand_name": brand["name"],
            "brand_id": brand["id"],
            "industry": brand.get("industry"),
            "website": brand.get("website"),
            "competitors": [c["competitor_name"] for c in competitors],
        }

    async def add_competitor(
        self,
        brand_id: str,
        *,
        competitor_name: str,
        competitor_website: Optional[str] = None,
        discovery_source: str = "reddit_mentioned",
    ) -> dict[str, Any]:
        """Add a competitor to a brand.

        Args:
            brand_id: The brand ID to add competitor to
            competitor_name: Name of the competitor
            competitor_website: Optional website URL
            discovery_source: How competitor was discovered
                - 'manual': User added manually
                - 'tavily_auto': Auto-discovered via Tavily search
                - 'reddit_mentioned': Discovered from Reddit mentions

        Returns:
            The created competitor record including:
            - id: Competitor ID
            - competitor_name: Name
            - competitor_website: Website URL (if provided)
            - discovery_source: Source of discovery
            - is_confirmed: Whether user has confirmed this competitor
            - created_at: Creation timestamp

        Raises:
            APIError: If the API returns an error (e.g., 402 for limit reached)
        """
        return await self._request(
            "POST",
            f"/api/v1/brands/{brand_id}/competitors",
            json={
                "competitor_name": competitor_name,
                "competitor_website": competitor_website,
                "discovery_source": discovery_source,
            },
        )

    # ==================== Agent File Methods ====================

    async def list_agent_files(self, agent_id: str) -> list[dict[str, Any]]:
        """List files in an agent's folder for the current user.

        Args:
            agent_id: Agent identifier (e.g., "reddit-agent")

        Returns:
            List of file info dicts with:
            - id: File ID
            - name: Display name
            - agent_id: Agent identifier
            - size: Size in bytes
            - metadata: Dict with item_count, finding_type, etc.
            - created_at: Creation timestamp
        """
        response = await self._request("GET", f"/api/v1/files/agent/{agent_id}")
        return response.get("items", [])

    async def read_agent_file(self, agent_id: str, filename: str) -> dict[str, Any]:
        """Read JSON content from an agent file.

        Args:
            agent_id: Agent identifier
            filename: Name of the file (e.g., "engagement_opportunities.json")

        Returns:
            The parsed JSON content of the file.
        """
        response = await self._request(
            "GET", f"/api/v1/files/agent/{agent_id}/{filename}"
        )
        return response.get("content", {})

    async def write_agent_file(
        self,
        agent_id: str,
        filename: str,
        content: dict[str, Any],
        description: str = "",
    ) -> dict[str, Any]:
        """Create or update a file in the agent's folder.

        Args:
            agent_id: Agent identifier
            filename: Name of the file (e.g., "engagement_opportunities.json")
            content: JSON-serializable data to write
            description: Human-readable description for the Files panel

        Returns:
            File info with id, name, size, metadata, created_at
        """
        return await self._request(
            "PUT",
            f"/api/v1/files/agent/{agent_id}/{filename}",
            json={"content": content, "description": description},
        )

    async def delete_agent_file(self, agent_id: str, filename: str) -> bool:
        """Delete a file from the agent's folder.

        Args:
            agent_id: Agent identifier
            filename: Name of the file to delete

        Returns:
            True if deleted, False if not found.
        """
        try:
            response = await self._request(
                "DELETE", f"/api/v1/files/agent/{agent_id}/{filename}"
            )
            return response.get("deleted", False)
        except APIError as e:
            if e.status_code == 404:
                return False
            raise

    async def append_to_agent_file(
        self,
        agent_id: str,
        filename: str,
        items: list[dict[str, Any]],
        key: str = "items",
    ) -> dict[str, Any]:
        """Append items to an existing JSON file's array.

        Args:
            agent_id: Agent identifier
            filename: Name of the file
            items: Items to append
            key: The array key in the JSON (default: "items")

        Returns:
            Updated file info with id, name, size, metadata, created_at

        Notes:
            Creates the file if it doesn't exist.
        """
        return await self._request(
            "PATCH",
            f"/api/v1/files/agent/{agent_id}/{filename}/append",
            json={"items": items, "key": key},
        )

    # Conversation Context Methods

    async def get_conversation_context(
        self,
        conversation_id: str,
        *,
        token_budget: int = 8000,
        agent_id: Optional[str] = None,
        include_full_artifacts: bool = False,
    ) -> dict[str, Any]:
        """Get optimized conversation context for agent consumption.

        This method retrieves context including brand info, artifact summaries,
        and recent messages within the specified token budget.

        Args:
            conversation_id: The conversation ID
            token_budget: Maximum tokens to return (1000-32000, default 8000)
            agent_id: Optional filter artifacts by agent ID
            include_full_artifacts: Include full artifact content

        Returns:
            Context dict with:
            - conversation_id: str
            - token_count: int (estimated tokens in context)
            - system_context: dict with:
                - brand_context: dict with brand_name, competitors
                - artifact_summaries: list of recent artifacts
            - messages: list of recent messages
            - historical_summary: str | None (summary of older messages)
            - messages_summarized: int (count of summarized messages)
            - total_messages: int
            - messages_included: int
            - artifacts_included: int

        Example:
            context = await client.get_conversation_context(
                conversation_id="123",
                token_budget=8000,
                agent_id="reddit-agent",
            )
            # Use context.system_context.artifact_summaries to find
            # previously generated content for refinement flows
        """
        params: dict[str, Any] = {"token_budget": token_budget}
        if agent_id:
            params["agent_id"] = agent_id
        if include_full_artifacts:
            params["include_full_artifacts"] = include_full_artifacts

        return await self._request(
            "GET",
            f"/api/v1/conversations/{conversation_id}/context",
            params=params,
        )

    async def create_artifact(
        self,
        conversation_id: str,
        *,
        artifact_type: str,
        title: Optional[str] = None,
        summary: Optional[str] = None,
        content_json: Optional[dict[str, Any]] = None,
        agent_id: Optional[str] = None,
        entity_name: Optional[str] = None,
        message_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create an artifact in a conversation.

        Artifacts store structured outputs from agent responses, enabling
        context persistence for refinement flows like "make the title punchier".

        Args:
            conversation_id: The conversation ID
            artifact_type: Type of artifact:
                - 'research_report': Research findings
                - 'generated_content': Generated posts, emails, etc.
                - 'data_query_result': Query results from data agent
                - 'email_draft': Email draft
                - 'slack_message': Slack message draft
            title: Human-readable title
            summary: LLM-generated summary for context injection
            content_json: Full structured content
            agent_id: Agent that created this artifact
            entity_name: Brand/topic being discussed
            message_id: Optional associated message ID

        Returns:
            Created artifact with id, created_at, etc.

        Example:
            await client.create_artifact(
                conversation_id="123",
                artifact_type="generated_content",
                title="Post for r/longevity",
                summary="Generated 2 post variations about geroscience",
                content_json={"posts": [...]},
                agent_id="reddit-agent",
            )
        """
        payload = {"artifact_type": artifact_type}
        if title:
            payload["title"] = title
        if summary:
            payload["summary"] = summary
        if content_json:
            payload["content_json"] = content_json
        if agent_id:
            payload["agent_id"] = agent_id
        if entity_name:
            payload["entity_name"] = entity_name

        params = {}
        if message_id:
            params["message_id"] = message_id

        return await self._request(
            "POST",
            f"/api/v1/conversations/{conversation_id}/artifacts",
            json=payload,
            params=params if params else None,
        )

    async def list_artifacts(
        self,
        conversation_id: str,
        *,
        artifact_type: Optional[str] = None,
        agent_id: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> dict[str, Any]:
        """List artifacts in a conversation.

        Args:
            conversation_id: The conversation ID
            artifact_type: Optional filter by type
            agent_id: Optional filter by agent
            page: Page number (1-indexed)
            per_page: Items per page

        Returns:
            Paginated response with items, total, page, per_page, has_more
        """
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if artifact_type:
            params["artifact_type"] = artifact_type
        if agent_id:
            params["agent_id"] = agent_id

        return await self._request(
            "GET",
            f"/api/v1/conversations/{conversation_id}/artifacts",
            params=params,
        )

    # Lifecycle Methods

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "PXUIDataClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()
