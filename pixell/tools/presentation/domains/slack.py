"""
Slack presentation tools for workspace integration.

These tools provide rich Slack UI rendering with channel lists,
message views, and interactive elements.
"""

from typing import Any, Literal

from pixell.tools.presentation.base import (
    PresentationOutput,
    presentation_tool,
)


@presentation_tool(
    name="display_slack_channels",
    description="""Display Slack channels in a channel list view.

BEST FOR:
- Showing available channels to browse
- Channel search/discovery results
- Workspace overview

NOT RECOMMENDED FOR:
- Channel messages (use display_slack_messages)
- Channel statistics/comparison (use display_table)
- Single channel info (describe in text)

Each channel should include: id, name, is_private, member_count, topic.
The frontend renders a channel list with join/view actions.""",
    parameters={
        "channels": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Channel ID"},
                    "name": {"type": "string", "description": "Channel name"},
                    "is_private": {"type": "boolean", "description": "Private channel flag"},
                    "is_member": {"type": "boolean", "description": "User is a member"},
                    "member_count": {"type": "integer", "description": "Number of members"},
                    "topic": {"type": "string", "description": "Channel topic"},
                    "purpose": {"type": "string", "description": "Channel purpose"},
                    "last_activity": {"type": "string", "description": "Last message timestamp"},
                },
            },
            "description": "Array of channel objects",
        },
        "workspace_name": {
            "type": "string",
            "description": "Slack workspace name for context",
        },
        "filter_type": {
            "type": "string",
            "enum": ["all", "member", "public", "private"],
            "description": "Channel filter applied",
        },
    },
    required=["channels"],
)
async def display_slack_channels(
    state: Any,
    channels: list[dict[str, Any]],
    workspace_name: str | None = None,
    filter_type: Literal["all", "member", "public", "private"] = "all",
    **kwargs,
) -> PresentationOutput:
    """Display Slack channels in a list view."""
    return PresentationOutput(
        output_type="slack_channels",
        data={
            "channels": channels,
            "workspace_name": workspace_name,
            "filter_type": filter_type,
            "total_count": len(channels),
            "private_count": sum(1 for c in channels if c.get("is_private")),
            "member_count": sum(1 for c in channels if c.get("is_member")),
        },
    )


@presentation_tool(
    name="display_slack_messages",
    description="""Display Slack messages in a message thread view.

BEST FOR:
- Showing channel message history
- Search results (messages matching a query)
- Thread conversations
- DM conversations

NOT RECOMMENDED FOR:
- Message statistics/analysis (use display_table or display_chart)
- Channel list (use display_slack_channels)
- User list (use display_table)

Each message should include: ts, user, text, reactions, thread_ts.
The frontend renders a message timeline with user avatars and reactions.""",
    parameters={
        "messages": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ts": {"type": "string", "description": "Message timestamp (Slack ts format)"},
                    "user": {"type": "string", "description": "User ID or name"},
                    "user_name": {"type": "string", "description": "Display name"},
                    "user_avatar": {"type": "string", "description": "Avatar URL"},
                    "text": {"type": "string", "description": "Message text"},
                    "thread_ts": {"type": "string", "description": "Thread parent timestamp"},
                    "reply_count": {"type": "integer", "description": "Number of thread replies"},
                    "reactions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "count": {"type": "integer"},
                            },
                        },
                        "description": "Message reactions",
                    },
                    "attachments": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Message attachments",
                    },
                    "files": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Shared files",
                    },
                },
            },
            "description": "Array of message objects",
        },
        "channel_name": {
            "type": "string",
            "description": "Channel name for context",
        },
        "channel_id": {
            "type": "string",
            "description": "Channel ID",
        },
        "is_thread": {
            "type": "boolean",
            "description": "True if showing a thread conversation",
        },
        "query": {
            "type": "string",
            "description": "Search query if from search results",
        },
    },
    required=["messages"],
)
async def display_slack_messages(
    state: Any,
    messages: list[dict[str, Any]],
    channel_name: str | None = None,
    channel_id: str | None = None,
    is_thread: bool = False,
    query: str | None = None,
    **kwargs,
) -> PresentationOutput:
    """Display Slack messages in a message view."""
    return PresentationOutput(
        output_type="slack_messages",
        data={
            "messages": messages,
            "channel_name": channel_name,
            "channel_id": channel_id,
            "is_thread": is_thread,
            "query": query,
            "total_count": len(messages),
            "has_threads": any(m.get("reply_count", 0) > 0 for m in messages),
        },
    )


# Tool collection for easy registration
SLACK_PRESENTATION_TOOLS = {
    "display_slack_channels": display_slack_channels,
    "display_slack_messages": display_slack_messages,
}
