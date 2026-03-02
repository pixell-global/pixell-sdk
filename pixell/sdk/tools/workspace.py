"""Platform tools mixin: workspace access, web fetch, and brand context.

Provides @tool-decorated methods that agents inherit by mixing in PlatformToolsMixin.
These tools use the authenticated data_client from the A2A MessageContext.

Usage:
    class MyAgent(PlatformToolsMixin, ToolBasedAgent):
        @tool(name="my_tool", description="...")
        async def my_tool(self, query: str) -> Result:
            ...

    # The agent now also has workspace_search, workspace_read,
    # workspace_list, workspace_write, web_fetch, and get_brand_context tools.
"""

import logging
import re

from pixell.sdk.tool_mode.agent import tool

logger = logging.getLogger(__name__)


class PlatformToolsMixin:
    """Mixin that adds platform-level tools to any ToolBasedAgent.

    Requires self._current_ctx to be a MessageContext with data_client.
    """

    @tool(
        name="workspace_search",
        description="Search the user's workspace files by keyword. Returns matching files with snippets.",
        parameters={
            "query": {"type": "string", "description": "Search query"},
        },
    )
    async def workspace_search(self, query: str):
        """Search workspace files."""
        from pixell.sdk.plan_mode.agent import Result

        try:
            client = await self._get_workspace_client()
            result = await client._request("GET", "/api/v1/workspace/search", params={"query": query})
            return Result(answer=f"Found workspace results for '{query}'.", data=result)
        except Exception as e:
            logger.warning("workspace_search failed: %s", e)
            return Result(answer=f"Search failed: {e}")

    @tool(
        name="workspace_read",
        description="Read a file from the user's workspace. Returns file content.",
        parameters={
            "path": {"type": "string", "description": "File path (e.g., /brand-persona.yaml)"},
        },
    )
    async def workspace_read(self, path: str):
        """Read a workspace file."""
        from pixell.sdk.plan_mode.agent import Result

        try:
            client = await self._get_workspace_client()
            result = await client._request(
                "GET", "/api/v1/workspace/files",
                params={"path": path, "token_budget": 4000},
            )
            return Result(answer=f"Read file: {path}", data=result)
        except Exception as e:
            logger.warning("workspace_read failed: %s", e)
            return Result(answer=f"Failed to read {path}: {e}")

    @tool(
        name="workspace_list",
        description="List files and folders in the user's workspace directory.",
        parameters={
            "path": {"type": "string", "description": "Directory path (default: /)"},
        },
    )
    async def workspace_list(self, path: str = "/"):
        """List workspace directory."""
        from pixell.sdk.plan_mode.agent import Result

        try:
            client = await self._get_workspace_client()
            result = await client._request(
                "GET", "/api/v1/workspace/tree",
                params={"path": path, "recursive": False},
            )
            return Result(answer=f"Listed directory: {path}", data=result)
        except Exception as e:
            logger.warning("workspace_list failed: %s", e)
            return Result(answer=f"Failed to list {path}: {e}")

    @tool(
        name="workspace_write",
        description="Write content to a file in the user's workspace.",
        parameters={
            "path": {"type": "string", "description": "File path to write"},
            "content": {"type": "string", "description": "File content"},
        },
    )
    async def workspace_write(self, path: str, content: str):
        """Write a workspace file."""
        from pixell.sdk.plan_mode.agent import Result

        try:
            client = await self._get_workspace_client()
            result = await client._request(
                "PUT", "/api/v1/workspace/files",
                json={"path": path, "content": content, "source": "agent"},
            )
            return Result(answer=f"Wrote file: {path}", data=result)
        except Exception as e:
            logger.warning("workspace_write failed: %s", e)
            return Result(answer=f"Failed to write {path}: {e}")

    @tool(
        name="web_fetch",
        description="Fetch a web page URL and extract its text content. Useful for researching URLs.",
        parameters={
            "url": {"type": "string", "description": "URL to fetch"},
        },
    )
    async def web_fetch(self, url: str):
        """Fetch URL and extract text."""
        import httpx
        from pixell.sdk.plan_mode.agent import Result

        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        try:
            async with httpx.AsyncClient(
                timeout=15.0,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (compatible; PixellAgent/1.0)"},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

                content_type = response.headers.get("content-type", "")
                if "text/html" in content_type:
                    text = _strip_html(response.text)
                else:
                    text = response.text

                text = re.sub(r"\s+", " ", text).strip()[:10000]
                return Result(answer=f"Fetched {url} ({len(text)} chars)", data={"url": url, "text": text})

        except Exception as e:
            logger.warning("web_fetch failed for %s: %s", url, e)
            return Result(answer=f"Failed to fetch {url}: {e}")

    @tool(
        name="get_brand_context",
        description="Get the user's brand profile including competitors, enrichment data, and research intelligence.",
        parameters={},
    )
    async def get_brand_context(self):
        """Fetch brand context from the platform API."""
        from pixell.sdk.plan_mode.agent import Result

        try:
            client = await self._get_workspace_client()
            brand_ctx = await client.get_brand_context()
            if not brand_ctx:
                return Result(answer="No brand configured. The user hasn't set up their brand profile yet.")
            return Result(
                answer=f"Brand: {brand_ctx.get('brand_name', 'Unknown')}",
                data=brand_ctx,
            )
        except Exception as e:
            logger.warning("get_brand_context failed: %s", e)
            return Result(answer=f"Failed to fetch brand context: {e}")

    async def _get_workspace_client(self):
        """Get the authenticated PXUIDataClient from the current context."""
        ctx = self._current_ctx
        if ctx is None:
            raise RuntimeError("No active context — cannot access workspace")
        return ctx.data_client


def _strip_html(html: str) -> str:
    """Simple HTML to text extraction."""
    from html.parser import HTMLParser

    class _Extractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self._parts: list[str] = []
            self._skip = False
            self._skip_tags = {"script", "style", "noscript", "svg", "head"}

        def handle_starttag(self, tag, attrs):
            if tag.lower() in self._skip_tags:
                self._skip = True

        def handle_endtag(self, tag):
            if tag.lower() in self._skip_tags:
                self._skip = False

        def handle_data(self, data):
            if not self._skip:
                text = data.strip()
                if text:
                    self._parts.append(text)

        def get_text(self):
            return " ".join(self._parts)

    extractor = _Extractor()
    extractor.feed(html)
    return extractor.get_text()
