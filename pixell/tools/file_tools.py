"""Agent File Tools - CRUD operations for agent files in user's S3 space.

This module provides a high-level interface for agents to manage files
in their designated folder within the user's S3 storage.

S3 Path Structure:
    s3://pixell-agents/users/{user_id}/{agent_id}/{filename}

Example:
    from pixell.tools.file_tools import AgentFileTools

    # In your agent's message handler
    async def handle_message(ctx: MessageContext):
        # Initialize file tools with the message context
        file_tools = AgentFileTools(ctx.data_client, "reddit-agent")

        # List existing files at session start
        files = await file_tools.list_files()
        for f in files:
            print(f"Found: {f['name']} ({f['metadata'].get('item_count', 0)} items)")

        # Read file content
        opportunities = await file_tools.read_file("engagement_opportunities.json")

        # Write new file
        await file_tools.write_file(
            "engagement_opportunities.json",
            {"items": new_opportunities, "finding_type": "engagement"},
            description="Engagement Opportunities"
        )

        # Append to existing file
        await file_tools.append_to_file(
            "engagement_opportunities.json",
            new_items,
            key="items"
        )

        # Delete file
        await file_tools.delete_file("old_data.json")
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pixell.sdk.data_client import PXUIDataClient


@dataclass
class FileInfo:
    """Information about an agent file."""

    id: str
    name: str
    agent_id: str
    size: int
    mime_type: str
    metadata: dict[str, Any]
    created_at: str

    @property
    def item_count(self) -> int:
        """Get item count from metadata."""
        return self.metadata.get("item_count", 0)

    @property
    def finding_type(self) -> str | None:
        """Get finding type from metadata."""
        return self.metadata.get("finding_type")


class AgentFileTools:
    """CRUD operations for agent files in user's S3 space.

    Each agent has its own folder within the user's storage area.
    Files are stored as JSON and can contain structured data like
    research findings, engagement opportunities, drafts, etc.

    Attributes:
        data_client: The PXUIDataClient for API calls
        agent_id: Agent identifier (e.g., "reddit-agent")
    """

    def __init__(self, data_client: "PXUIDataClient", agent_id: str):
        """Initialize AgentFileTools.

        Args:
            data_client: PXUIDataClient instance (from ctx.data_client)
            agent_id: Agent identifier used for file path
        """
        self.data_client = data_client
        self.agent_id = agent_id

    async def list_files(self) -> list[FileInfo]:
        """List all files in this agent's folder for the current user.

        Use this at the start of a session to understand what already exists
        and provide contextual responses.

        Returns:
            List of FileInfo objects with metadata.
        """
        items = await self.data_client.list_agent_files(self.agent_id)
        return [
            FileInfo(
                id=item.get("id", ""),
                name=item.get("name", ""),
                agent_id=item.get("agent_id", self.agent_id),
                size=item.get("size", 0),
                mime_type=item.get("mime_type", "application/json"),
                metadata=item.get("metadata") or {},
                created_at=item.get("created_at", ""),
            )
            for item in items
        ]

    async def read_file(self, filename: str) -> dict[str, Any]:
        """Read a JSON file from the agent's folder.

        Args:
            filename: Name of the file (e.g., "engagement_opportunities.json")

        Returns:
            The parsed JSON content.

        Raises:
            APIError: If file doesn't exist (404) or other API error.
        """
        return await self.data_client.read_agent_file(self.agent_id, filename)

    async def write_file(
        self,
        filename: str,
        content: dict[str, Any],
        description: str = "",
    ) -> FileInfo:
        """Create or update a file in the agent's folder.

        Args:
            filename: Name of the file (e.g., "engagement_opportunities.json")
            content: JSON-serializable data to write
            description: Human-readable description for the Files panel

        Returns:
            FileInfo with the created/updated file details.

        Notes:
            - Creates the file if it doesn't exist
            - Overwrites existing content if file exists
            - Automatically adds created_at/updated_at timestamps
        """
        result = await self.data_client.write_agent_file(
            self.agent_id, filename, content, description
        )
        return FileInfo(
            id=result.get("id", ""),
            name=result.get("name", ""),
            agent_id=result.get("agent_id", self.agent_id),
            size=result.get("size", 0),
            mime_type=result.get("mime_type", "application/json"),
            metadata=result.get("metadata") or {},
            created_at=result.get("created_at", ""),
        )

    async def delete_file(self, filename: str) -> bool:
        """Delete a file from the agent's folder.

        Args:
            filename: Name of the file to delete

        Returns:
            True if deleted, False if not found.
        """
        return await self.data_client.delete_agent_file(self.agent_id, filename)

    async def append_to_file(
        self,
        filename: str,
        items: list[dict[str, Any]],
        key: str = "items",
    ) -> FileInfo:
        """Append items to an existing JSON file's array.

        This is the recommended way to add new findings to an existing file
        without overwriting previous data.

        Args:
            filename: Name of the file
            items: Items to append to the array
            key: The array key in the JSON (default: "items")

        Returns:
            FileInfo with updated file details.

        Notes:
            - Creates the file if it doesn't exist
            - Creates the array key if it doesn't exist
            - Preserves existing items in the array
        """
        result = await self.data_client.append_to_agent_file(
            self.agent_id, filename, items, key
        )
        return FileInfo(
            id=result.get("id", ""),
            name=result.get("name", ""),
            agent_id=result.get("agent_id", self.agent_id),
            size=result.get("size", 0),
            mime_type=result.get("mime_type", "application/json"),
            metadata=result.get("metadata") or {},
            created_at=result.get("created_at", ""),
        )

    async def scan_context(self) -> dict[str, Any]:
        """Scan existing files and build context for the session.

        This is a convenience method that:
        1. Lists all existing files
        2. Reads their content
        3. Returns a structured context dict

        Use this at session start to understand what the user already has.

        Returns:
            Dict with:
            - files: List of FileInfo
            - content: Dict mapping filename to content
            - summary: Dict with counts and types
        """
        files = await self.list_files()

        content: dict[str, Any] = {}
        total_items = 0
        finding_types: set[str] = set()

        for file in files:
            try:
                file_content = await self.read_file(file.name)
                content[file.name] = file_content

                # Track stats
                if "items" in file_content and isinstance(file_content["items"], list):
                    total_items += len(file_content["items"])
                if file.finding_type:
                    finding_types.add(file.finding_type)
            except Exception:
                # Skip files that can't be read
                continue

        return {
            "files": files,
            "content": content,
            "summary": {
                "file_count": len(files),
                "total_items": total_items,
                "finding_types": list(finding_types),
            },
        }
