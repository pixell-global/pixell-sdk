#!/usr/bin/env python3
"""Test PXUIDataClient usage."""

import asyncio
from pixell.sdk import PXUIDataClient


def test_client_creation():
    """Test client can be created with all parameters."""
    client = PXUIDataClient(
        base_url="https://api.example.com",
        jwt_token="test-token",
        timeout=30.0,
        max_retries=3,
    )
    assert client.base_url == "https://api.example.com"
    assert client.jwt_token == "test-token"
    assert client.timeout == 30.0
    assert client.max_retries == 3
    print("✓ PXUIDataClient created successfully with all parameters")


def test_client_defaults():
    """Test client with default parameters."""
    client = PXUIDataClient(
        base_url="https://api.example.com",
        jwt_token="test-token",
    )
    assert client.base_url == "https://api.example.com"
    assert client.jwt_token == "test-token"
    # Verify defaults exist
    assert hasattr(client, "timeout")
    assert hasattr(client, "max_retries")
    print("✓ PXUIDataClient created with default parameters")


def test_client_methods_exist():
    """Test client has all expected methods."""
    client = PXUIDataClient(
        base_url="https://api.example.com",
        jwt_token="test-token",
    )

    # Core methods
    assert hasattr(client, "oauth_proxy_call")
    assert callable(client.oauth_proxy_call)

    assert hasattr(client, "get_user_profile")
    assert callable(client.get_user_profile)

    assert hasattr(client, "list_files")
    assert callable(client.list_files)

    assert hasattr(client, "get_file_content")
    assert callable(client.get_file_content)

    assert hasattr(client, "list_conversations")
    assert callable(client.list_conversations)

    assert hasattr(client, "list_task_history")
    assert callable(client.list_task_history)

    # Lifecycle methods
    assert hasattr(client, "close")
    assert callable(client.close)

    print("✓ PXUIDataClient has all expected methods")


async def test_client_context_manager():
    """Test client as async context manager."""
    async with PXUIDataClient(
        base_url="https://api.example.com",
        jwt_token="test-token",
    ) as client:
        assert client is not None
    print("✓ PXUIDataClient context manager works")


if __name__ == "__main__":
    test_client_creation()
    test_client_defaults()
    test_client_methods_exist()
    asyncio.run(test_client_context_manager())
    print("\n✓ All PXUIDataClient tests passed!")
