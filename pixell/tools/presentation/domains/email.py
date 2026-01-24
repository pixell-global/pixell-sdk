"""
Email presentation tools for Gmail integration.

These tools provide rich email UI rendering with inbox views,
thread support, and interactive actions.
"""

from typing import Any, Literal

from pixell.tools.presentation.base import (
    PresentationOutput,
    presentation_tool,
)


@presentation_tool(
    name="display_email_inbox",
    description="""Display emails in an inbox view with message previews and actions.

BEST FOR:
- Showing multiple emails for browsing (list views)
- Search results from email queries
- Inbox/folder contents
- When email actions (star, archive, reply) are relevant

NOT RECOMMENDED FOR:
- Analyzing email metadata/statistics (use display_table)
- Reading a single email in full (use display_email_detail)
- Summarizing email patterns (describe in text with display_table)

Each email should include: id, from, to, subject, snippet, date, labels.
The frontend renders an interactive inbox with expand/collapse and actions.""",
    parameters={
        "emails": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Unique email ID"},
                    "from": {"type": "string", "description": "Sender email/name"},
                    "to": {"type": "array", "items": {"type": "string"}, "description": "Recipients"},
                    "subject": {"type": "string", "description": "Email subject"},
                    "snippet": {"type": "string", "description": "Preview text (first ~100 chars)"},
                    "date": {"type": "string", "description": "Date received (ISO format)"},
                    "is_read": {"type": "boolean", "description": "Read status"},
                    "is_starred": {"type": "boolean", "description": "Starred status"},
                    "labels": {"type": "array", "items": {"type": "string"}, "description": "Gmail labels"},
                    "has_attachments": {"type": "boolean", "description": "Has attachments"},
                },
            },
            "description": "Array of email objects to display",
        },
        "view_mode": {
            "type": "string",
            "enum": ["list", "threads"],
            "description": "Display mode: 'list' for individual emails, 'threads' for conversation grouping",
        },
        "query": {
            "type": "string",
            "description": "Search query used (displayed as context)",
        },
        "folder": {
            "type": "string",
            "description": "Folder/label being viewed (e.g., 'INBOX', 'SENT')",
        },
    },
    required=["emails"],
)
async def display_email_inbox(
    state: Any,
    emails: list[dict[str, Any]],
    view_mode: Literal["list", "threads"] = "list",
    query: str | None = None,
    folder: str | None = None,
    **kwargs,
) -> PresentationOutput:
    """Display emails in an inbox view."""
    return PresentationOutput(
        output_type="email_inbox",
        data={
            "emails": emails,
            "view_mode": view_mode,
            "query": query,
            "folder": folder,
            "total_count": len(emails),
            "unread_count": sum(1 for e in emails if not e.get("is_read", True)),
        },
    )


@presentation_tool(
    name="display_email_detail",
    description="""Display a single email in full detail with body content.

BEST FOR:
- User asks to "read", "show", or "open" a specific email
- Showing full email body content
- Email reply/forward workflows

NOT RECOMMENDED FOR:
- Multiple emails (use display_email_inbox)
- Email list/search results (use display_email_inbox)

Include full email body (HTML or plain text), headers, and attachments.
The frontend renders a full email view with reply/forward actions.""",
    parameters={
        "email": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "Unique email ID"},
                "from": {"type": "string", "description": "Sender email/name"},
                "to": {"type": "array", "items": {"type": "string"}, "description": "Recipients"},
                "cc": {"type": "array", "items": {"type": "string"}, "description": "CC recipients"},
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Full email body (HTML or text)"},
                "body_type": {"type": "string", "enum": ["html", "text"], "description": "Body content type"},
                "date": {"type": "string", "description": "Date received (ISO format)"},
                "labels": {"type": "array", "items": {"type": "string"}, "description": "Gmail labels"},
                "attachments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "filename": {"type": "string"},
                            "mime_type": {"type": "string"},
                            "size": {"type": "integer"},
                        },
                    },
                    "description": "Email attachments",
                },
            },
            "description": "Full email object with body content",
        },
        "show_thread": {
            "type": "boolean",
            "description": "Show full thread conversation (default: False)",
        },
        "thread_messages": {
            "type": "array",
            "items": {"type": "object"},
            "description": "Other messages in the thread (if show_thread=True)",
        },
    },
    required=["email"],
)
async def display_email_detail(
    state: Any,
    email: dict[str, Any],
    show_thread: bool = False,
    thread_messages: list[dict[str, Any]] | None = None,
    **kwargs,
) -> PresentationOutput:
    """Display a single email in full detail."""
    return PresentationOutput(
        output_type="email_detail",
        data={
            "email": email,
            "show_thread": show_thread,
            "thread_messages": thread_messages or [],
            "thread_count": len(thread_messages) + 1 if thread_messages else 1,
        },
    )


# Tool collection for easy registration
EMAIL_PRESENTATION_TOOLS = {
    "display_email_inbox": display_email_inbox,
    "display_email_detail": display_email_detail,
}
