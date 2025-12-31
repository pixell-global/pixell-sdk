"""Tests for UserContext."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from pixell.sdk.context import UserContext, TaskMetadata
from pixell.sdk.data_client import PXUIDataClient
from pixell.sdk.progress import ProgressReporter
from pixell.sdk.errors import ContextNotInitializedError


class TestTaskMetadata:
    """Tests for TaskMetadata dataclass."""

    def test_metadata_creation(self):
        """Test basic metadata creation."""
        metadata = TaskMetadata(
            task_id="task-123",
            agent_id="test-agent",
            user_id="user-456",
            tenant_id="tenant-789",
            trace_id="trace-abc",
            created_at=datetime.utcnow(),
        )
        assert metadata.task_id == "task-123"
        assert metadata.agent_id == "test-agent"
        assert metadata.user_id == "user-456"
        assert metadata.tenant_id == "tenant-789"
        assert metadata.trace_id == "trace-abc"
        assert metadata.timeout_at is None
        assert metadata.payload == {}

    def test_metadata_with_payload(self):
        """Test metadata with payload."""
        metadata = TaskMetadata(
            task_id="task-123",
            agent_id="test-agent",
            user_id="user-456",
            tenant_id="tenant-789",
            trace_id="trace-abc",
            created_at=datetime.utcnow(),
            payload={"prompt": "test prompt"},
        )
        assert metadata.payload == {"prompt": "test prompt"}


class TestUserContext:
    """Tests for UserContext class."""

    @pytest.fixture
    def mock_client(self):
        """Create mock PXUIDataClient."""
        client = MagicMock(spec=PXUIDataClient)
        client.close = AsyncMock()
        return client

    @pytest.fixture
    def mock_reporter(self):
        """Create mock ProgressReporter."""
        reporter = MagicMock(spec=ProgressReporter)
        reporter.update = AsyncMock()
        reporter.error = AsyncMock()
        reporter.close = AsyncMock()
        return reporter

    @pytest.fixture
    def metadata(self):
        """Create test metadata."""
        return TaskMetadata(
            task_id="task-123",
            agent_id="test-agent",
            user_id="user-456",
            tenant_id="tenant-789",
            trace_id="trace-abc",
            created_at=datetime.utcnow(),
            payload={"prompt": "test prompt"},
        )

    @pytest.fixture
    def context(self, metadata, mock_client, mock_reporter):
        """Create UserContext for testing."""
        return UserContext(metadata, mock_client, mock_reporter)

    def test_properties(self, context):
        """Test context properties."""
        assert context.task_id == "task-123"
        assert context.agent_id == "test-agent"
        assert context.user_id == "user-456"
        assert context.tenant_id == "tenant-789"
        assert context.trace_id == "trace-abc"
        assert context.payload == {"prompt": "test prompt"}

    @pytest.mark.asyncio
    async def test_call_oauth_api(self, context, mock_client):
        """Test OAuth API call."""
        mock_client.oauth_proxy_call = AsyncMock(return_value={"data": "result"})

        result = await context.call_oauth_api(
            provider="google",
            method="GET",
            path="/calendar/v3/calendars/primary/events",
        )

        assert result == {"data": "result"}
        mock_client.oauth_proxy_call.assert_called_once_with(
            user_id="user-456",
            provider="google",
            method="GET",
            path="/calendar/v3/calendars/primary/events",
            body=None,
            headers=None,
        )

    @pytest.mark.asyncio
    async def test_get_user_profile(self, context, mock_client):
        """Test get_user_profile method."""
        mock_client.get_user_profile = AsyncMock(
            return_value={"id": "user-456", "email": "test@example.com"}
        )

        result = await context.get_user_profile()

        assert result["id"] == "user-456"
        assert result["email"] == "test@example.com"
        mock_client.get_user_profile.assert_called_once_with("user-456")

    @pytest.mark.asyncio
    async def test_get_files(self, context, mock_client):
        """Test get_files method."""
        mock_client.list_files = AsyncMock(return_value=[{"id": "file-1", "name": "test.txt"}])

        result = await context.get_files(filter={"type": "txt"}, limit=50)

        assert len(result) == 1
        assert result[0]["id"] == "file-1"
        mock_client.list_files.assert_called_once_with(
            user_id="user-456",
            filter={"type": "txt"},
            limit=50,
        )

    @pytest.mark.asyncio
    async def test_get_file_content(self, context, mock_client):
        """Test get_file_content method."""
        mock_client.get_file_content = AsyncMock(return_value=b"file content")

        result = await context.get_file_content("file-123")

        assert result == b"file content"
        mock_client.get_file_content.assert_called_once_with(
            user_id="user-456",
            file_id="file-123",
        )

    @pytest.mark.asyncio
    async def test_get_conversations(self, context, mock_client):
        """Test get_conversations method."""
        mock_client.list_conversations = AsyncMock(
            return_value=[{"id": "conv-1", "title": "Test conversation"}]
        )

        result = await context.get_conversations(limit=10)

        assert len(result) == 1
        assert result[0]["id"] == "conv-1"
        mock_client.list_conversations.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_task_history(self, context, mock_client):
        """Test get_task_history method."""
        mock_client.list_task_history = AsyncMock(
            return_value=[{"task_id": "task-old", "status": "completed"}]
        )

        result = await context.get_task_history(agent_id="test-agent", limit=5)

        assert len(result) == 1
        assert result[0]["task_id"] == "task-old"
        mock_client.list_task_history.assert_called_once_with(
            user_id="user-456",
            agent_id="test-agent",
            limit=5,
        )

    @pytest.mark.asyncio
    async def test_report_progress(self, context, mock_reporter):
        """Test report_progress method."""
        await context.report_progress("processing", percent=50, message="Halfway done")

        mock_reporter.update.assert_called_once_with(
            "processing",
            percent=50,
            message="Halfway done",
        )

    @pytest.mark.asyncio
    async def test_report_error(self, context, mock_reporter):
        """Test report_error method."""
        await context.report_error("API_ERROR", "External API failed", recoverable=True)

        mock_reporter.error.assert_called_once_with(
            "API_ERROR",
            "External API failed",
            recoverable=True,
        )

    @pytest.mark.asyncio
    async def test_close(self, context, mock_client, mock_reporter):
        """Test context close."""
        await context.close()

        mock_client.close.assert_called_once()
        mock_reporter.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(self, context, mock_client, mock_reporter):
        """Test async context manager."""
        async with context:
            pass

        mock_client.close.assert_called_once()
        mock_reporter.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_closed_raises(self, context):
        """Test that methods raise after context is closed."""
        await context.close()

        with pytest.raises(ContextNotInitializedError):
            await context.get_user_profile()

        with pytest.raises(ContextNotInitializedError):
            await context.report_progress("test")


class TestUserContextFromTask:
    """Tests for UserContext.from_task factory method."""

    def test_from_task(self):
        """Test creating context from task data."""
        task_data = {
            "task_id": "task-123",
            "agent_id": "test-agent",
            "user_id": "user-456",
            "tenant_id": "tenant-789",
            "trace_id": "trace-abc",
            "jwt_token": "token-xyz",
            "payload": {"prompt": "test prompt"},
        }

        with patch.object(PXUIDataClient, "__init__", return_value=None):
            with patch.object(ProgressReporter, "__init__", return_value=None):
                context = UserContext.from_task(
                    task_data,
                    pxui_base_url="https://api.example.com",
                    redis_url="redis://localhost:6379",
                )

        assert context.task_id == "task-123"
        assert context.agent_id == "test-agent"
        assert context.user_id == "user-456"
        assert context.tenant_id == "tenant-789"
        assert context.trace_id == "trace-abc"
        assert context.payload == {"prompt": "test prompt"}
