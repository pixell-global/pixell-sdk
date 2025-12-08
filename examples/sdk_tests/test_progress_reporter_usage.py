#!/usr/bin/env python3
"""Test ProgressReporter usage."""

from pixell.sdk import ProgressReporter, ProgressError


def test_reporter_creation():
    """Test reporter can be created."""
    reporter = ProgressReporter(
        redis_url="redis://localhost:6379",
        task_id="task-123",
        user_id="user-456",
    )
    assert reporter.task_id == "task-123"
    assert reporter.user_id == "user-456"
    print("✓ ProgressReporter created successfully")


def test_channel_property():
    """Test channel property generates correct Redis channel."""
    reporter = ProgressReporter(
        redis_url="redis://localhost:6379",
        task_id="task-123",
        user_id="user-456",
    )
    assert reporter.channel == "pixell:tasks:task-123:progress"
    print("✓ ProgressReporter channel property works correctly")


def test_reporter_methods_exist():
    """Test reporter has all expected methods."""
    reporter = ProgressReporter(
        redis_url="redis://localhost:6379",
        task_id="task-123",
        user_id="user-456",
    )

    # Core methods
    assert hasattr(reporter, "update")
    assert callable(reporter.update)

    assert hasattr(reporter, "error")
    assert callable(reporter.error)

    assert hasattr(reporter, "complete")
    assert callable(reporter.complete)

    # Lifecycle methods
    assert hasattr(reporter, "close")
    assert callable(reporter.close)

    print("✓ ProgressReporter has all expected methods")


def test_progress_error_class():
    """Test ProgressError can be raised."""
    error = ProgressError("Invalid percent value", code="INVALID_PERCENT")
    assert error.code == "INVALID_PERCENT"
    assert str(error) == "Invalid percent value"
    print("✓ ProgressError can be created and used")


if __name__ == "__main__":
    test_reporter_creation()
    test_channel_property()
    test_reporter_methods_exist()
    test_progress_error_class()
    print("\n✓ All ProgressReporter tests passed!")
