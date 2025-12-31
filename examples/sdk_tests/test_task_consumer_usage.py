#!/usr/bin/env python3
"""Test TaskConsumer usage."""

from pixell.sdk import TaskConsumer, UserContext


async def sample_handler(ctx: UserContext, payload: dict) -> dict:
    """Sample task handler."""
    return {"status": "success"}


def test_consumer_creation():
    """Test consumer can be created with all parameters."""
    consumer = TaskConsumer(
        agent_id="test-agent",
        redis_url="redis://localhost:6379",
        pxui_base_url="https://api.example.com",
        handler=sample_handler,
        concurrency=5,
        poll_interval=1.0,
        task_timeout=300.0,
    )
    assert consumer.agent_id == "test-agent"
    assert consumer.redis_url == "redis://localhost:6379"
    assert consumer.pxui_base_url == "https://api.example.com"
    assert consumer.handler is sample_handler
    assert consumer.concurrency == 5
    assert consumer.poll_interval == 1.0
    assert consumer.task_timeout == 300.0
    print("✓ TaskConsumer created successfully with all parameters")


def test_consumer_defaults():
    """Test consumer with default parameters."""
    consumer = TaskConsumer(
        agent_id="test-agent",
        redis_url="redis://localhost:6379",
        pxui_base_url="https://api.example.com",
        handler=sample_handler,
    )
    assert consumer.agent_id == "test-agent"
    # Verify defaults exist
    assert hasattr(consumer, "concurrency")
    assert hasattr(consumer, "poll_interval")
    assert hasattr(consumer, "task_timeout")
    print("✓ TaskConsumer created with default parameters")


def test_consumer_queue_keys():
    """Test consumer Redis key generation."""
    consumer = TaskConsumer(
        agent_id="my-agent",
        redis_url="redis://localhost:6379",
        pxui_base_url="https://api.example.com",
        handler=sample_handler,
    )
    assert consumer.queue_key == "pixell:agents:my-agent:tasks"
    assert consumer.processing_key == "pixell:agents:my-agent:processing"
    assert consumer.status_key == "pixell:agents:my-agent:status"
    assert consumer.dead_letter_key == "pixell:agents:my-agent:dead_letter"
    print("✓ TaskConsumer Redis keys generated correctly")


def test_consumer_methods_exist():
    """Test consumer has all expected methods."""
    consumer = TaskConsumer(
        agent_id="test-agent",
        redis_url="redis://localhost:6379",
        pxui_base_url="https://api.example.com",
        handler=sample_handler,
    )

    # Lifecycle methods
    assert hasattr(consumer, "start")
    assert callable(consumer.start)

    assert hasattr(consumer, "stop")
    assert callable(consumer.stop)

    assert hasattr(consumer, "close")
    assert callable(consumer.close)

    print("✓ TaskConsumer has all expected methods")


def test_consumer_with_different_agents():
    """Test creating consumers for different agents."""
    agents = ["agent-a", "agent-b", "agent-c"]

    for agent_id in agents:
        consumer = TaskConsumer(
            agent_id=agent_id,
            redis_url="redis://localhost:6379",
            pxui_base_url="https://api.example.com",
            handler=sample_handler,
        )
        assert consumer.agent_id == agent_id
        assert agent_id in consumer.queue_key

    print("✓ Multiple TaskConsumers can be created for different agents")


if __name__ == "__main__":
    test_consumer_creation()
    test_consumer_defaults()
    test_consumer_queue_keys()
    test_consumer_methods_exist()
    test_consumer_with_different_agents()
    print("\n✓ All TaskConsumer tests passed!")
