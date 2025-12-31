#!/usr/bin/env python3
"""Verify all pixell-sdk imports work correctly."""


def test_core_imports():
    """Test core component imports."""
    from pixell.sdk import UserContext
    from pixell.sdk import TaskMetadata
    from pixell.sdk import TaskConsumer
    from pixell.sdk import PXUIDataClient
    from pixell.sdk import ProgressReporter
    print("✓ All core components imported successfully")


def test_error_imports():
    """Test error class imports."""
    from pixell.sdk import (
        SDKError,
        ConsumerError,
        TaskTimeoutError,
        TaskHandlerError,
        QueueError,
        ClientError,
        AuthenticationError,
        RateLimitError,
        APIError,
        ConnectionError,
        ContextError,
        ContextNotInitializedError,
        ProgressError,
    )
    print("✓ All error classes imported successfully")


def test_version():
    """Test version is accessible."""
    import pixell
    print(f"✓ Package version: {pixell.__version__}")


if __name__ == "__main__":
    test_core_imports()
    test_error_imports()
    test_version()
    print("\n✓ All import tests passed!")
