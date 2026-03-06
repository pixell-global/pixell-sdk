"""Workspace client for Sayou REST API.

Thin httpx wrapper used by workspace executors to access the user's
workspace (search, read, list, write, grep). Created per-request with
the user's API key.
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class WorkspaceClient:
    """Async HTTP client for the Sayou workspace REST API.

    Created per-request in agent orchestrators with the user's
    sayou_api_key. Lazy-initializes the httpx client so no resources
    are consumed if workspace tools are never called.

    Usage:
        async with WorkspaceClient(api_key=key, api_url=url) as ws:
            results = await ws.search("brand persona")
    """

    def __init__(self, api_key: str, api_url: str):
        if not api_key:
            raise ValueError("api_key is required")
        if not api_url:
            raise ValueError("api_url is required")
        self._api_key = api_key
        base = api_url.rstrip("/")
        # Don't double-append /api/v1 if caller already included it
        self._base_url = base if base.endswith("/api/v1") else base + "/api/v1"
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            logger.info("Initializing workspace client: %s", self._base_url)
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=30.0,
            )
        return self._client

    async def search(
        self,
        query: str,
        limit: int = 5,
        chunk_level: bool = False,
    ) -> dict[str, Any]:
        """Search workspace files by query."""
        client = await self._get_client()
        params: dict[str, Any] = {"query": query, "limit": limit}
        if chunk_level:
            params["chunk_level"] = True
        resp = await client.get("/workspace/search", params=params)
        resp.raise_for_status()
        return resp.json()

    async def read(
        self,
        path: str,
        token_budget: int = 4000,
    ) -> dict[str, Any]:
        """Read a file from the workspace."""
        client = await self._get_client()
        resp = await client.get(
            "/workspace/files",
            params={"path": path, "token_budget": token_budget},
        )
        resp.raise_for_status()
        return resp.json()

    async def list(
        self,
        path: str = "/",
        recursive: bool = False,
    ) -> dict[str, Any]:
        """List files and folders in a workspace directory."""
        client = await self._get_client()
        resp = await client.get(
            "/workspace/files",
            params={"path": path, "recursive": recursive},
        )
        resp.raise_for_status()
        return resp.json()

    async def write(
        self,
        path: str,
        content: str,
        source: str = "agent",
    ) -> dict[str, Any]:
        """Write content to a workspace file."""
        client = await self._get_client()
        resp = await client.post(
            "/workspace/files",
            json={"path": path, "content": content, "source": source},
        )
        resp.raise_for_status()
        return resp.json()

    async def grep(
        self,
        query: str,
        path_pattern: str | None = None,
    ) -> dict[str, Any]:
        """Search file contents for text."""
        client = await self._get_client()
        body: dict[str, Any] = {"query": query}
        if path_pattern:
            body["path_pattern"] = path_pattern
        resp = await client.post("/workspace/grep", json=body)
        resp.raise_for_status()
        return resp.json()

    async def close(self):
        """Close the underlying httpx client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.close()
