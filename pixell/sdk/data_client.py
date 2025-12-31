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
