"""Canonical executor interface for PER-style tools.

Provides BaseExecutor and ToolResult that agents can import instead
of maintaining their own copies.
"""

from pixell.sdk.executors.base import BaseExecutor, ToolResult
from pixell.sdk.executors.workspace import (
    WorkspaceSearchExecutor,
    WorkspaceReadExecutor,
    WorkspaceListExecutor,
    WorkspaceWriteExecutor,
)

__all__ = [
    "BaseExecutor",
    "ToolResult",
    "WorkspaceSearchExecutor",
    "WorkspaceReadExecutor",
    "WorkspaceListExecutor",
    "WorkspaceWriteExecutor",
]
