#!/usr/bin/env python3
"""Test UserContext usage."""

from datetime import datetime
from pixell.sdk import UserContext, TaskMetadata, ContextNotInitializedError


def test_task_metadata_creation():
    """Test TaskMetadata dataclass creation."""
    metadata = TaskMetadata(
        task_id="task-123",
        agent_id="test-agent",
        user_id="user-456",
        tenant_id="tenant-789",
        trace_id="trace-abc",
        created_at=datetime.utcnow(),
        payload={"prompt": "test"},
    )
    assert metadata.task_id == "task-123"
    assert metadata.agent_id == "test-agent"
    assert metadata.user_id == "user-456"
    assert metadata.tenant_id == "tenant-789"
    assert metadata.trace_id == "trace-abc"
    assert metadata.payload == {"prompt": "test"}
    print("✓ TaskMetadata created successfully")


def test_task_metadata_all_required_fields():
    """Test TaskMetadata with all required fields."""
    metadata = TaskMetadata(
        task_id="task-123",
        agent_id="test-agent",
        user_id="user-456",
        tenant_id="tenant-789",
        trace_id="trace-xyz",
        created_at=datetime.utcnow(),
    )
    assert metadata.task_id == "task-123"
    assert metadata.trace_id == "trace-xyz"
    assert metadata.created_at is not None
    print("✓ TaskMetadata all required fields work correctly")


def test_context_factory_exists():
    """Test UserContext.from_task factory method exists."""
    assert hasattr(UserContext, "from_task")
    assert callable(UserContext.from_task)
    print("✓ UserContext.from_task factory method exists")


def test_context_methods_signature():
    """Verify UserContext has expected methods (by checking class)."""
    expected_methods = [
        "from_task",
        "get_user_profile",
        "get_files",
        "call_oauth_api",
        "report_progress",
        "report_error",
    ]

    for method_name in expected_methods:
        assert hasattr(UserContext, method_name), f"Missing method: {method_name}"

    print("✓ UserContext has all expected methods")


def test_context_not_initialized_error():
    """Test ContextNotInitializedError."""
    error = ContextNotInitializedError()
    assert str(error) == "Context not initialized"
    assert error.code == "CONTEXT_NOT_INITIALIZED"

    error_with_message = ContextNotInitializedError("Custom message")
    assert str(error_with_message) == "Custom message"
    print("✓ ContextNotInitializedError works correctly")


if __name__ == "__main__":
    test_task_metadata_creation()
    test_task_metadata_all_required_fields()
    test_context_factory_exists()
    test_context_methods_signature()
    test_context_not_initialized_error()
    print("\n✓ All UserContext tests passed!")
