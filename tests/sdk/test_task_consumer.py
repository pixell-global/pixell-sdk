"""Tests for TaskConsumer."""

import pytest
import json
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from pixell.sdk.task_consumer import TaskConsumer
from pixell.sdk.context import UserContext
from pixell.sdk.errors import (
    ConsumerError,
    TaskTimeoutError,
    TaskHandlerError,
    RateLimitError,
    ClientError,
)


class TestTaskConsumer:
    """Tests for TaskConsumer class."""

    @pytest.fixture
    def handler(self):
        """Create mock task handler."""
        return AsyncMock(return_value={"result": "success"})

    @pytest.fixture
    def consumer(self, handler):
        """Create TaskConsumer for testing."""
        return TaskConsumer(
            agent_id="test-agent",
            redis_url="redis://localhost:6379",
            pxui_base_url="https://api.example.com",
            handler=handler,
            concurrency=5,
            task_timeout=30.0,
        )

    def test_initialization(self, consumer, handler):
        """Test consumer initialization."""
        assert consumer.agent_id == "test-agent"
        assert consumer.redis_url == "redis://localhost:6379"
        assert consumer.pxui_base_url == "https://api.example.com"
        assert consumer.handler is handler
        assert consumer.concurrency == 5
        assert consumer.task_timeout == 30.0

    def test_queue_key(self, consumer):
        """Test queue key property."""
        assert consumer.queue_key == "pixell:agents:test-agent:tasks"

    def test_processing_key(self, consumer):
        """Test processing key property."""
        assert consumer.processing_key == "pixell:agents:test-agent:processing"

    def test_status_key(self, consumer):
        """Test status key property."""
        assert consumer.status_key == "pixell:agents:test-agent:status"

    def test_dead_letter_key(self, consumer):
        """Test dead letter key property."""
        assert consumer.dead_letter_key == "pixell:agents:test-agent:dead_letter"


class TestTaskConsumerProcessing:
    """Tests for task processing."""

    @pytest.fixture
    def handler(self):
        """Create mock task handler."""
        return AsyncMock(return_value={"result": "success"})

    @pytest.fixture
    def consumer(self, handler):
        """Create TaskConsumer for testing."""
        return TaskConsumer(
            agent_id="test-agent",
            redis_url="redis://localhost:6379",
            pxui_base_url="https://api.example.com",
            handler=handler,
        )

    @pytest.fixture
    def task_data(self):
        """Create test task data."""
        return {
            "task_id": "task-123",
            "agent_id": "test-agent",
            "user_id": "user-456",
            "tenant_id": "tenant-789",
            "trace_id": "trace-abc",
            "jwt_token": "token-xyz",
            "payload": {"prompt": "test prompt"},
        }

    @pytest.mark.asyncio
    async def test_process_task_success(self, consumer, handler, task_data):
        """Test successful task processing."""
        with patch.object(consumer, "_get_client") as mock_get_client:
            mock_redis = AsyncMock()
            mock_get_client.return_value = mock_redis

            # Mock UserContext.from_task
            with patch("pixell.sdk.task_consumer.UserContext") as mock_context_class:
                mock_context = AsyncMock()
                mock_context.__aenter__ = AsyncMock(return_value=mock_context)
                mock_context.__aexit__ = AsyncMock(return_value=None)
                mock_context_class.from_task.return_value = mock_context

                await consumer._process_task(json.dumps(task_data))

                # Verify handler was called
                handler.assert_called_once()
                call_args = handler.call_args[0]
                assert call_args[0] is mock_context
                assert call_args[1] == {"prompt": "test prompt"}

    @pytest.mark.asyncio
    async def test_process_task_timeout(self, consumer, task_data):
        """Test task timeout handling."""
        # Create a handler that takes too long
        async def slow_handler(ctx, payload):
            await asyncio.sleep(10)
            return {"result": "success"}

        consumer.handler = slow_handler
        consumer.task_timeout = 0.1  # Very short timeout

        with patch.object(consumer, "_get_client") as mock_get_client:
            mock_redis = AsyncMock()
            mock_get_client.return_value = mock_redis

            with patch("pixell.sdk.task_consumer.UserContext") as mock_context_class:
                mock_context = AsyncMock()
                mock_context.__aenter__ = AsyncMock(return_value=mock_context)
                mock_context.__aexit__ = AsyncMock(return_value=None)
                mock_context_class.from_task.return_value = mock_context

                await consumer._process_task(json.dumps(task_data))

                # Verify error was reported
                assert mock_redis.hset.called
                # Verify task moved to dead letter queue
                assert mock_redis.lpush.called

    @pytest.mark.asyncio
    async def test_process_task_handler_error(self, consumer, handler, task_data):
        """Test handler error handling."""
        handler.side_effect = ValueError("Handler failed")

        with patch.object(consumer, "_get_client") as mock_get_client:
            mock_redis = AsyncMock()
            mock_get_client.return_value = mock_redis

            with patch("pixell.sdk.task_consumer.UserContext") as mock_context_class:
                mock_context = AsyncMock()
                mock_context.__aenter__ = AsyncMock(return_value=mock_context)
                mock_context.__aexit__ = AsyncMock(return_value=None)
                mock_context_class.from_task.return_value = mock_context

                await consumer._process_task(json.dumps(task_data))

                # Verify error was reported
                assert mock_redis.hset.called
                # Verify task moved to dead letter queue
                assert mock_redis.lpush.called

    @pytest.mark.asyncio
    async def test_process_task_rate_limit_recoverable(self, consumer, handler, task_data):
        """Test rate limit error is marked as recoverable."""
        handler.side_effect = RateLimitError("Rate limited", retry_after=60)

        with patch.object(consumer, "_get_client") as mock_get_client:
            mock_redis = AsyncMock()
            mock_get_client.return_value = mock_redis

            with patch("pixell.sdk.task_consumer.UserContext") as mock_context_class:
                mock_context = AsyncMock()
                mock_context.__aenter__ = AsyncMock(return_value=mock_context)
                mock_context.__aexit__ = AsyncMock(return_value=None)
                mock_context_class.from_task.return_value = mock_context

                await consumer._process_task(json.dumps(task_data))

                # Verify error was reported (recoverable=True means no dead letter)
                assert mock_redis.hset.called
                # Should NOT be moved to dead letter queue
                assert not mock_redis.lpush.called


class TestTaskConsumerLifecycle:
    """Tests for consumer lifecycle methods."""

    @pytest.fixture
    def handler(self):
        """Create mock task handler."""
        return AsyncMock(return_value={"result": "success"})

    @pytest.fixture
    def consumer(self, handler):
        """Create TaskConsumer for testing."""
        return TaskConsumer(
            agent_id="test-agent",
            redis_url="redis://localhost:6379",
            pxui_base_url="https://api.example.com",
            handler=handler,
        )

    @pytest.mark.asyncio
    async def test_stop(self, consumer):
        """Test consumer stop."""
        consumer._running = True
        await consumer.stop()
        assert consumer._running is False

    @pytest.mark.asyncio
    async def test_stop_ungraceful(self, consumer):
        """Test ungraceful consumer stop."""
        consumer._running = True

        # Create some mock tasks
        mock_task = MagicMock()
        consumer._tasks = {mock_task}

        await consumer.stop(graceful=False)

        assert consumer._running is False
        mock_task.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_close(self, consumer):
        """Test consumer close."""
        with patch("redis.asyncio.from_url") as mock_from_url:
            mock_redis = AsyncMock()
            mock_from_url.return_value = mock_redis

            # Get client to initialize it
            await consumer._get_client()

            # Close
            await consumer.close()

            mock_redis.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(self, consumer):
        """Test async context manager."""
        # Set up mock client
        mock_redis = AsyncMock()
        consumer._client = mock_redis
        consumer._running = False  # Don't actually start polling

        async with consumer:
            pass

        mock_redis.aclose.assert_called_once()


class TestTaskConsumerUpdate:
    """Tests for status update methods."""

    @pytest.fixture
    def handler(self):
        """Create mock task handler."""
        return AsyncMock(return_value={"result": "success"})

    @pytest.fixture
    def consumer(self, handler):
        """Create TaskConsumer for testing."""
        return TaskConsumer(
            agent_id="test-agent",
            redis_url="redis://localhost:6379",
            pxui_base_url="https://api.example.com",
            handler=handler,
        )

    @pytest.mark.asyncio
    async def test_update_status(self, consumer):
        """Test status update."""
        with patch.object(consumer, "_get_client") as mock_get_client:
            mock_redis = AsyncMock()
            mock_get_client.return_value = mock_redis

            await consumer._update_status("task-123", "processing")

            mock_redis.hset.assert_called_once()
            call_args = mock_redis.hset.call_args
            assert "pixell:tasks:task-123:status" in call_args[0]

    @pytest.mark.asyncio
    async def test_update_status_with_result(self, consumer):
        """Test status update with result."""
        with patch.object(consumer, "_get_client") as mock_get_client:
            mock_redis = AsyncMock()
            mock_get_client.return_value = mock_redis

            await consumer._update_status(
                "task-123",
                "completed",
                result={"data": "result"},
            )

            mock_redis.hset.assert_called_once()
            call_args = mock_redis.hset.call_args
            mapping = call_args[1]["mapping"]
            assert "result" in mapping
