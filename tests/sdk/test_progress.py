"""Tests for ProgressReporter."""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock

from pixell.sdk.progress import ProgressReporter
from pixell.sdk.errors import ProgressError


class TestProgressReporter:
    """Tests for ProgressReporter class."""

    @pytest.fixture
    def reporter(self):
        """Create ProgressReporter for testing."""
        return ProgressReporter(
            redis_url="redis://localhost:6379",
            task_id="task-123",
            user_id="user-456",
        )

    def test_channel_property(self, reporter):
        """Test channel property."""
        assert reporter.channel == "pixell:tasks:task-123:progress"

    @pytest.mark.asyncio
    async def test_update(self, reporter):
        """Test progress update."""
        with patch.object(reporter, "_get_client") as mock_get_client:
            mock_redis = AsyncMock()
            mock_get_client.return_value = mock_redis

            await reporter.update("processing", percent=50, message="Halfway done")

            mock_redis.publish.assert_called_once()
            call_args = mock_redis.publish.call_args
            channel = call_args[0][0]
            message = json.loads(call_args[0][1])

            assert channel == "pixell:tasks:task-123:progress"
            assert message["type"] == "progress"
            assert message["status"] == "processing"
            assert message["percent"] == 50
            assert message["message"] == "Halfway done"
            assert message["task_id"] == "task-123"
            assert message["user_id"] == "user-456"
            assert "timestamp" in message

    @pytest.mark.asyncio
    async def test_update_without_percent(self, reporter):
        """Test progress update without percent."""
        with patch.object(reporter, "_get_client") as mock_get_client:
            mock_redis = AsyncMock()
            mock_get_client.return_value = mock_redis

            await reporter.update("starting")

            call_args = mock_redis.publish.call_args
            message = json.loads(call_args[0][1])

            assert message["status"] == "starting"
            assert "percent" not in message

    @pytest.mark.asyncio
    async def test_update_with_metadata(self, reporter):
        """Test progress update with metadata."""
        with patch.object(reporter, "_get_client") as mock_get_client:
            mock_redis = AsyncMock()
            mock_get_client.return_value = mock_redis

            await reporter.update(
                "processing",
                percent=50,
                metadata={"items_processed": 100},
            )

            call_args = mock_redis.publish.call_args
            message = json.loads(call_args[0][1])

            assert message["metadata"] == {"items_processed": 100}

    @pytest.mark.asyncio
    async def test_update_invalid_percent(self, reporter):
        """Test progress update with invalid percent raises error."""
        with pytest.raises(ProgressError) as exc_info:
            await reporter.update("processing", percent=150)

        assert "INVALID_PERCENT" in str(exc_info.value.code)

    @pytest.mark.asyncio
    async def test_update_negative_percent(self, reporter):
        """Test progress update with negative percent raises error."""
        with pytest.raises(ProgressError) as exc_info:
            await reporter.update("processing", percent=-10)

        assert "INVALID_PERCENT" in str(exc_info.value.code)

    @pytest.mark.asyncio
    async def test_error(self, reporter):
        """Test error reporting."""
        with patch.object(reporter, "_get_client") as mock_get_client:
            mock_redis = AsyncMock()
            mock_get_client.return_value = mock_redis

            await reporter.error(
                "API_ERROR",
                "External API failed",
                recoverable=True,
                details={"status_code": 500},
            )

            call_args = mock_redis.publish.call_args
            message = json.loads(call_args[0][1])

            assert message["type"] == "error"
            assert message["error_type"] == "API_ERROR"
            assert message["message"] == "External API failed"
            assert message["recoverable"] is True
            assert message["details"] == {"status_code": 500}

    @pytest.mark.asyncio
    async def test_complete(self, reporter):
        """Test completion reporting."""
        with patch.object(reporter, "_get_client") as mock_get_client:
            mock_redis = AsyncMock()
            mock_get_client.return_value = mock_redis

            await reporter.complete({"result": "success"})

            call_args = mock_redis.publish.call_args
            message = json.loads(call_args[0][1])

            assert message["type"] == "complete"
            assert message["status"] == "completed"
            assert message["result"] == {"result": "success"}

    @pytest.mark.asyncio
    async def test_complete_without_result(self, reporter):
        """Test completion without result."""
        with patch.object(reporter, "_get_client") as mock_get_client:
            mock_redis = AsyncMock()
            mock_get_client.return_value = mock_redis

            await reporter.complete()

            call_args = mock_redis.publish.call_args
            message = json.loads(call_args[0][1])

            assert message["type"] == "complete"
            assert message["status"] == "completed"
            assert "result" not in message

    @pytest.mark.asyncio
    async def test_publish_error_handling(self, reporter):
        """Test error handling during publish."""
        with patch.object(reporter, "_get_client") as mock_get_client:
            mock_redis = AsyncMock()
            mock_redis.publish.side_effect = Exception("Redis error")
            mock_get_client.return_value = mock_redis

            with pytest.raises(ProgressError) as exc_info:
                await reporter.update("processing")

            assert "PUBLISH_ERROR" in str(exc_info.value.code)


class TestProgressReporterLifecycle:
    """Tests for reporter lifecycle methods."""

    @pytest.mark.asyncio
    async def test_close(self):
        """Test reporter close."""
        reporter = ProgressReporter(
            redis_url="redis://localhost:6379",
            task_id="task-123",
            user_id="user-456",
        )

        with patch("redis.asyncio.from_url") as mock_from_url:
            mock_redis = AsyncMock()
            mock_from_url.return_value = mock_redis

            # Get client to initialize it
            await reporter._get_client()

            # Close
            await reporter.close()

            mock_redis.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        reporter = ProgressReporter(
            redis_url="redis://localhost:6379",
            task_id="task-123",
            user_id="user-456",
        )

        with patch("redis.asyncio.from_url") as mock_from_url:
            mock_redis = AsyncMock()
            mock_from_url.return_value = mock_redis

            async with reporter:
                await reporter._get_client()

            mock_redis.aclose.assert_called_once()
