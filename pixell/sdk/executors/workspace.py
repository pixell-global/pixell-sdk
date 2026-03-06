"""Workspace executors for the agent LLM loop.

These executors use WorkspaceClient (httpx → Sayou REST API) to give
agents search/read/list/write access to the user's workspace.

Works with both BaseExecutor-based agents (reddit, tiktok) and
function-based agents (channels) via the as_function_tools() helper.
"""

import json
import logging
from typing import Any, Callable

from pixell.sdk.executors.base import BaseExecutor, ToolResult
from pixell.sdk.workspace import WorkspaceClient

logger = logging.getLogger(__name__)


class WorkspaceSearchExecutor(BaseExecutor):
    """Search the user's workspace for documents and past research."""

    def __init__(self, client: WorkspaceClient):
        self._ws = client

    @property
    def name(self) -> str:
        return "workspace_search"

    @property
    def description(self) -> str:
        return (
            "Search the user's workspace for documents, notes, and past research. "
            "Returns matching files with relevant snippets."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (keywords or natural language)",
                },
            },
            "required": ["query"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        query = kwargs.get("query", "")
        if not query:
            return ToolResult.error_result("query is required", recoverable=True)
        try:
            result = await self._ws.search(query=query)
            return ToolResult.success_result(json.dumps(result, default=str))
        except Exception as e:
            logger.warning("workspace_search failed: %s", e)
            return ToolResult.error_result(
                f"Workspace search failed: {e}", recoverable=True
            )


class WorkspaceReadExecutor(BaseExecutor):
    """Read a specific file from the user's workspace."""

    def __init__(self, client: WorkspaceClient):
        self._ws = client

    @property
    def name(self) -> str:
        return "workspace_read"

    @property
    def description(self) -> str:
        return "Read a file from the user's workspace. Returns file content and metadata."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path (e.g., /brand-persona.yaml, /agents/research/report.md)",
                },
            },
            "required": ["path"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path", "")
        if not path:
            return ToolResult.error_result("path is required", recoverable=True)
        try:
            result = await self._ws.read(path=path)
            return ToolResult.success_result(json.dumps(result, default=str))
        except Exception as e:
            logger.warning("workspace_read failed for %s: %s", path, e)
            return ToolResult.error_result(
                f"Failed to read {path}: {e}", recoverable=True
            )


class WorkspaceListExecutor(BaseExecutor):
    """List files and folders in a workspace directory."""

    def __init__(self, client: WorkspaceClient):
        self._ws = client

    @property
    def name(self) -> str:
        return "workspace_list"

    @property
    def description(self) -> str:
        return "List files and folders in the user's workspace directory."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path (default: /)",
                },
            },
            "required": [],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path", "/")
        try:
            result = await self._ws.list(path=path)
            return ToolResult.success_result(json.dumps(result, default=str))
        except Exception as e:
            logger.warning("workspace_list failed for %s: %s", path, e)
            return ToolResult.error_result(
                f"Failed to list {path}: {e}", recoverable=True
            )


class WorkspaceWriteExecutor(BaseExecutor):
    """Write content to a file in the user's workspace."""

    def __init__(self, client: WorkspaceClient):
        self._ws = client

    @property
    def name(self) -> str:
        return "workspace_write"

    @property
    def description(self) -> str:
        return (
            "Write or update a file in the user's workspace. "
            "Use for saving research results, reports, and agent artifacts."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path to write (e.g., /agents/research/report.md)",
                },
                "content": {
                    "type": "string",
                    "description": "File content (supports markdown with YAML frontmatter)",
                },
            },
            "required": ["path", "content"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path", "")
        content = kwargs.get("content", "")
        if not path:
            return ToolResult.error_result("path is required", recoverable=True)
        if not content:
            return ToolResult.error_result("content is required", recoverable=True)
        try:
            result = await self._ws.write(path=path, content=content, source="agent")
            return ToolResult.success_result(
                f"Successfully wrote {len(content)} chars to {path}"
            )
        except Exception as e:
            logger.warning("workspace_write failed for %s: %s", path, e)
            return ToolResult.error_result(
                f"Failed to write {path}: {e}", recoverable=True
            )


def create_workspace_executors(client: WorkspaceClient) -> list[BaseExecutor]:
    """Create all workspace executors for a given client.

    Convenience function for agents that use the BaseExecutor pattern.
    """
    return [
        WorkspaceSearchExecutor(client),
        WorkspaceReadExecutor(client),
        WorkspaceListExecutor(client),
        WorkspaceWriteExecutor(client),
    ]


def as_function_tools(client: WorkspaceClient) -> dict[str, Callable]:
    """Create function-based workspace tools for ReAct loop agents (channels).

    Returns a dict of {name: async_function} where each function has a
    _tool_def attribute with the OpenAI tool schema.
    """
    executors = create_workspace_executors(client)
    tools: dict[str, Callable] = {}

    for executor in executors:
        fn = _make_workspace_fn(executor)
        tools[executor.name] = fn

    return tools


def _make_workspace_fn(executor: BaseExecutor) -> Callable:
    """Create a single function-based tool wrapper for a workspace executor."""

    async def workspace_fn(state, **kwargs) -> dict[str, Any]:
        result = await executor.execute(**kwargs)
        if result.success:
            try:
                return {"success": True, "data": json.loads(result.output)}
            except (json.JSONDecodeError, TypeError):
                return {"success": True, "answer": result.output}
        else:
            return {"success": False, "error": result.error}

    workspace_fn.__doc__ = executor.description
    workspace_fn._tool_def = executor.as_tool_schema()
    return workspace_fn
