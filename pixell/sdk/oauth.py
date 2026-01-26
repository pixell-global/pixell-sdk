"""OAuth client for agents to get tokens from pixell-api.

This module provides a simple interface for agents to get OAuth access tokens
from pixell-api. Instead of proxying all API calls through pixell-api, agents
can get a token once and call external APIs directly.

Example:
    from pixell.sdk import PXUIDataClient
    from pixell.sdk.oauth import OAuthClient

    data_client = PXUIDataClient(base_url, jwt_token)
    oauth = OAuthClient(data_client)

    # Get a Google token
    token = await oauth.get_token("google")

    # Use it to call Gmail API directly
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            headers={"Authorization": f"Bearer {token.access_token}"},
        )
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pixell.sdk.data_client import PXUIDataClient


@dataclass
class OAuthToken:
    """OAuth access token with metadata.

    Attributes:
        access_token: The OAuth access token for API calls (bot token for Slack)
        user_token: User OAuth token for user actions (Slack only, xoxp- token)
        expires_at: When the token expires (UTC)
        provider: OAuth provider name (google, reddit, etc.)
        scopes: List of scopes granted to this token (if available)
    """

    access_token: str
    expires_at: datetime
    provider: str
    scopes: list[str] | None = None
    user_token: str | None = None  # User token for platforms that support it (e.g., Slack)

    @property
    def is_expired(self) -> bool:
        """Check if the token is expired.

        Includes a 60-second buffer to avoid using tokens that are about to expire.
        """
        buffer = timedelta(seconds=60)
        now = datetime.now(timezone.utc)
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return now >= (expires_at - buffer)

    @property
    def is_valid(self) -> bool:
        """Check if the token is still valid."""
        return not self.is_expired


class OAuthError(Exception):
    """Base error for OAuth operations."""

    def __init__(self, message: str, code: str = "OAUTH_ERROR", provider: str | None = None):
        self.message = message
        self.code = code
        self.provider = provider
        super().__init__(message)


class OAuthNotConnectedError(OAuthError):
    """OAuth provider not connected for this user."""

    def __init__(self, provider: str, message: str | None = None):
        super().__init__(
            message or f"{provider.title()} account not connected",
            "oauth_not_connected",
            provider,
        )


class OAuthTokenExpiredError(OAuthError):
    """OAuth token expired and refresh failed."""

    def __init__(self, provider: str, message: str | None = None):
        super().__init__(
            message or f"{provider.title()} token expired. Please reconnect.",
            "token_expired",
            provider,
        )


class OAuthClient:
    """Client for getting OAuth tokens from pixell-api.

    This client caches tokens in memory and automatically uses cached tokens
    when they're still valid. When a token expires, it fetches a fresh one
    from pixell-api (which handles the refresh automatically).

    Example:
        from pixell.sdk.data_client import PXUIDataClient
        from pixell.sdk.oauth import OAuthClient

        # Create clients
        data_client = PXUIDataClient(base_url, jwt_token)
        oauth = OAuthClient(data_client)

        # Get a token (fetches from API or returns cached)
        token = await oauth.get_token("google")

        # Use the token directly
        headers = {"Authorization": f"Bearer {token.access_token}"}
    """

    def __init__(self, api_client: "PXUIDataClient"):
        """Initialize the OAuth client.

        Args:
            api_client: PXUIDataClient instance for making API calls
        """
        self._api = api_client
        self._token_cache: dict[str, OAuthToken] = {}

    async def get_token(self, provider: str, force_refresh: bool = False) -> OAuthToken:
        """Get a valid OAuth token for a provider.

        This method:
        - Returns a cached token if still valid
        - Fetches a fresh token from pixell-api if expired or force_refresh=True
        - Raises OAuthNotConnectedError if the provider isn't connected
        - Raises OAuthTokenExpiredError if token refresh fails

        Args:
            provider: OAuth provider name ("google", "reddit", etc.)
            force_refresh: If True, always fetch a fresh token from API

        Returns:
            OAuthToken with valid access_token

        Raises:
            OAuthNotConnectedError: Provider not connected for this user
            OAuthTokenExpiredError: Token expired and refresh failed
            OAuthError: Other OAuth-related errors
        """
        # Check cache first (unless force refresh requested)
        if not force_refresh:
            cached = self._token_cache.get(provider)
            if cached and cached.is_valid:
                return cached

        # Fetch fresh token from pixell-api
        try:
            response = await self._api._request("GET", f"/api/v1/oauth/{provider}/token")
        except Exception as e:
            # Import here to avoid circular imports
            from pixell.sdk.errors import AuthenticationError, APIError

            # Check for authentication errors (JWT invalid/expired)
            if isinstance(e, AuthenticationError):
                raise OAuthError(
                    f"Invalid or expired JWT token. Please log in again.",
                    code="jwt_expired",
                    provider=provider,
                )

            # Check for API errors with status codes
            if isinstance(e, APIError):
                status_code = e.details.get("status_code")
                if status_code == 404:
                    raise OAuthNotConnectedError(provider)
                elif status_code == 401:
                    raise OAuthTokenExpiredError(provider)

            # Fall back to generic OAuth error
            raise OAuthError(str(e), provider=provider)

        # Parse response into OAuthToken
        expires_at_str = response.get("expires_at", "")
        try:
            # Handle ISO format with timezone
            if expires_at_str.endswith("Z"):
                expires_at_str = expires_at_str[:-1] + "+00:00"
            expires_at = datetime.fromisoformat(expires_at_str)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            # Fall back to 1 hour from now
            expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        token = OAuthToken(
            access_token=response["access_token"],
            expires_at=expires_at,
            provider=provider,
            scopes=response.get("scopes"),
            user_token=response.get("user_token"),  # User token for Slack
        )

        # Cache the token
        self._token_cache[provider] = token

        return token

    async def get_auth_headers(self, provider: str) -> dict[str, str]:
        """Get authorization headers for API calls.

        Convenience method that returns headers ready for use with httpx/requests.

        Args:
            provider: OAuth provider name

        Returns:
            Dict with Authorization header

        Example:
            headers = await oauth.get_auth_headers("google")
            response = await client.get(url, headers=headers)
        """
        token = await self.get_token(provider)
        return {"Authorization": f"Bearer {token.access_token}"}

    def clear_cache(self, provider: str | None = None) -> None:
        """Clear cached tokens.

        Args:
            provider: If specified, only clear cache for this provider.
                     If None, clear all cached tokens.
        """
        if provider:
            self._token_cache.pop(provider, None)
        else:
            self._token_cache.clear()

    def is_cached(self, provider: str) -> bool:
        """Check if a valid token is cached for the provider.

        Args:
            provider: OAuth provider name

        Returns:
            True if a valid (non-expired) token is cached
        """
        cached = self._token_cache.get(provider)
        return cached is not None and cached.is_valid
