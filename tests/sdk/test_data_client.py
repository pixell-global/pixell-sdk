"""Tests for PXUIDataClient."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

import httpx

from pixell.sdk.data_client import PXUIDataClient
from pixell.sdk.errors import (
    AuthenticationError,
    RateLimitError,
    APIError,
    ConnectionError,
)


class TestPXUIDataClient:
    """Tests for PXUIDataClient class."""

    @pytest.fixture
    def client(self):
        """Create PXUIDataClient for testing."""
        return PXUIDataClient(
            base_url="https://api.example.com",
            jwt_token="test-token",
        )

    @pytest.fixture
    def mock_response_200(self):
        """Create mock 200 response."""
        response = MagicMock(spec=httpx.Response)
        response.status_code = 200
        response.json.return_value = {"data": "result"}
        response.raise_for_status = MagicMock()
        return response

    @pytest.mark.asyncio
    async def test_oauth_proxy_call(self, client, mock_response_200):
        """Test OAuth proxy call."""
        mock_response_200.json.return_value = {"data": "result"}

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.request.return_value = mock_response_200
            mock_get_client.return_value = mock_http_client

            result = await client.oauth_proxy_call(
                user_id="user-123",
                provider="google",
                method="GET",
                path="/calendar/v3/calendars/primary/events",
            )

            assert result == {"data": "result"}
            mock_http_client.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_profile(self, client, mock_response_200):
        """Test get_user_profile method."""
        mock_response_200.json.return_value = {"id": "user-123", "email": "test@example.com"}

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.request.return_value = mock_response_200
            mock_get_client.return_value = mock_http_client

            result = await client.get_user_profile("user-123")

            assert result["id"] == "user-123"
            assert result["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_list_files(self, client, mock_response_200):
        """Test list_files method."""
        # The method expects {"files": [...]} structure
        mock_response_200.json.return_value = {"files": [{"id": "file-1", "name": "test.txt"}]}

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.request.return_value = mock_response_200
            mock_get_client.return_value = mock_http_client

            result = await client.list_files(
                user_id="user-123",
                filter={"type": "txt"},
                limit=50,
            )

            assert len(result) == 1
            assert result[0]["id"] == "file-1"

    @pytest.mark.asyncio
    async def test_get_file_content(self, client):
        """Test get_file_content method."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.content = b"file content"

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.get.return_value = mock_response
            mock_get_client.return_value = mock_http_client

            result = await client.get_file_content(
                user_id="user-123",
                file_id="file-456",
            )

            assert result == b"file content"

    @pytest.mark.asyncio
    async def test_list_conversations(self, client, mock_response_200):
        """Test list_conversations method."""
        # The method expects {"conversations": [...]} structure
        mock_response_200.json.return_value = {"conversations": [{"id": "conv-1", "title": "Test"}]}

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.request.return_value = mock_response_200
            mock_get_client.return_value = mock_http_client

            result = await client.list_conversations(
                user_id="user-123",
                limit=10,
            )

            assert len(result) == 1
            assert result[0]["id"] == "conv-1"

    @pytest.mark.asyncio
    async def test_list_task_history(self, client, mock_response_200):
        """Test list_task_history method."""
        # The method expects {"tasks": [...]} structure
        mock_response_200.json.return_value = {"tasks": [{"task_id": "task-1", "status": "completed"}]}

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.request.return_value = mock_response_200
            mock_get_client.return_value = mock_http_client

            result = await client.list_task_history(
                user_id="user-123",
                agent_id="test-agent",
                limit=5,
            )

            assert len(result) == 1
            assert result[0]["task_id"] == "task-1"


class TestPXUIDataClientErrors:
    """Tests for error handling in PXUIDataClient."""

    @pytest.fixture
    def client(self):
        """Create PXUIDataClient for testing."""
        return PXUIDataClient(
            base_url="https://api.example.com",
            jwt_token="test-token",
        )

    @pytest.mark.asyncio
    async def test_authentication_error(self, client):
        """Test 401 response raises AuthenticationError."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Unauthorized"}

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.request.return_value = mock_response
            mock_get_client.return_value = mock_http_client

            with pytest.raises(AuthenticationError):
                await client.get_user_profile("user-123")

    @pytest.mark.asyncio
    async def test_rate_limit_error(self, client):
        """Test 429 response raises RateLimitError."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": "Rate limited"}
        mock_response.headers = {"Retry-After": "60"}

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.request.return_value = mock_response
            mock_get_client.return_value = mock_http_client

            with pytest.raises(RateLimitError) as exc_info:
                await client.get_user_profile("user-123")

            assert exc_info.value.details["retry_after"] == 60

    @pytest.mark.asyncio
    async def test_api_error(self, client):
        """Test 500 response raises APIError."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal server error"}

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.request.return_value = mock_response
            mock_get_client.return_value = mock_http_client

            with pytest.raises(APIError) as exc_info:
                await client.get_user_profile("user-123")

            assert exc_info.value.details["status_code"] == 500

    @pytest.mark.asyncio
    async def test_connection_error(self, client):
        """Test connection error handling."""
        # Set max_retries to 1 to speed up test
        client.max_retries = 1

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.request.side_effect = httpx.ConnectError("Connection failed")
            mock_get_client.return_value = mock_http_client

            with pytest.raises(ConnectionError):
                await client.get_user_profile("user-123")


class TestPXUIDataClientLifecycle:
    """Tests for client lifecycle methods."""

    @pytest.mark.asyncio
    async def test_close(self):
        """Test client close."""
        client = PXUIDataClient(
            base_url="https://api.example.com",
            jwt_token="test-token",
        )

        # Create a mock client that is not closed
        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.is_closed = False
        mock_http_client.aclose = AsyncMock()
        client._client = mock_http_client

        await client.close()

        mock_http_client.aclose.assert_called_once()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_close_without_client(self):
        """Test close when no client exists."""
        client = PXUIDataClient(
            base_url="https://api.example.com",
            jwt_token="test-token",
        )

        # Should not raise even with no client
        await client.close()

    @pytest.mark.asyncio
    async def test_close_already_closed(self):
        """Test close when client is already closed."""
        client = PXUIDataClient(
            base_url="https://api.example.com",
            jwt_token="test-token",
        )

        # Create a mock client that is already closed
        mock_http_client = MagicMock(spec=httpx.AsyncClient)
        mock_http_client.is_closed = True
        client._client = mock_http_client

        await client.close()
        # Should not call aclose on already closed client

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        client = PXUIDataClient(
            base_url="https://api.example.com",
            jwt_token="test-token",
        )

        # Create a mock client that is not closed
        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.is_closed = False
        mock_http_client.aclose = AsyncMock()
        client._client = mock_http_client

        async with client:
            pass

        mock_http_client.aclose.assert_called_once()
