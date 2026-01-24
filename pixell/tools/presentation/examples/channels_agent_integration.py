"""
Example: Integrating Presentation Tools into channels-agent

This file shows how to integrate the shared presentation tools into an agent.
The actual migration would update channels-agent files to follow this pattern.

## Step 1: Update tools/__init__.py

Add presentation tools alongside domain tools:

```python
from pixell.tools.presentation import (
    # Standard presentation
    display_table,
    display_list,
    display_chart,
    # Email-specific presentation
    display_email_inbox,
    display_email_detail,
    # Slack-specific presentation
    display_slack_channels,
    display_slack_messages,
    # Tool collections
    EMAIL_PRESENTATION_TOOLS,
    SLACK_PRESENTATION_TOOLS,
)

# Existing tools...
GMAIL_TOOLS = {...}
SLACK_TOOLS = {...}
TERMINAL_TOOLS = {...}

# Add presentation tools
PRESENTATION_TOOLS = {
    **EMAIL_PRESENTATION_TOOLS,
    **SLACK_PRESENTATION_TOOLS,
    "display_table": display_table,
    "display_list": display_list,
    "display_chart": display_chart,
}

# All tools now includes presentation
ALL_TOOLS = {
    **GMAIL_TOOLS,
    **SLACK_TOOLS,
    **TERMINAL_TOOLS,
    **PRESENTATION_TOOLS,
}
```

## Step 2: Update system prompt

Add presentation guidance to the system prompt:

```python
from pixell.tools.presentation import PRESENTATION_GUIDANCE

SYSTEM_PROMPT = '''
[existing prompt content...]

{presentation_guidance}
'''.format(presentation_guidance=PRESENTATION_GUIDANCE)
```

## Step 3: Modify tool outputs to return raw data

Before (hardcoded presentation):
```python
async def list_emails(state, max_results=20, **kwargs):
    emails = await gmail.list_emails(max_results=max_results)
    return {
        "_action": "complete",
        "answer": f"Here are your {len(emails)} emails:",
        "email_list": {"emails": [e.to_dict() for e in emails]},
    }
```

After (raw data - LLM decides presentation):
```python
async def list_emails(state, max_results=20, **kwargs):
    emails = await gmail.list_emails(max_results=max_results)
    # Return raw data, let LLM choose presentation tool
    return {
        "success": True,
        "emails": [e.to_dict() for e in emails],
        "count": len(emails),
    }
```

Then the LLM calls `display_email_inbox` based on user intent.

## Step 4: Example LLM flow

User: "Show me my emails"
  LLM -> list_emails(max_results=10)
  Result -> {"success": true, "emails": [...], "count": 10}
  LLM -> display_email_inbox(emails=[...], view_mode="list")
  Result -> {"__output_type__": "email_inbox", "emails": [...]}
  LLM -> complete(...)

User: "How many emails from each sender?"
  LLM -> list_emails(max_results=50)
  Result -> {"success": true, "emails": [...], "count": 50}
  LLM analyzes and aggregates data
  LLM -> display_table(columns=["Sender", "Count"], rows=[...])
  Result -> {"__output_type__": "table", "columns": [...], "rows": [...]}
  LLM -> complete(...)

The key insight: Same data retrieval tool, different presentation based on intent.
"""

# Example tool definitions with presentation support

from pixell.tools.presentation import (
    display_email_inbox,
    display_email_detail,
    display_slack_channels,
    display_slack_messages,
    display_table,
    PRESENTATION_GUIDANCE,
)


# Example: Modified list_emails that returns raw data
async def list_emails_raw(state, max_results=20, label="INBOX", **kwargs):
    """
    List emails from Gmail (returns raw data for LLM presentation choice).

    This is the "after" version that returns raw data, allowing the LLM
    to choose how to present it using a presentation tool.
    """
    # Get Gmail service (implementation detail)
    from app.services.gmail_service import get_gmail_service

    gmail = get_gmail_service()

    try:
        emails = await gmail.list_emails(max_results=max_results, label_ids=[label])

        # Return raw data - LLM will decide presentation
        return {
            "success": True,
            "emails": [
                {
                    "id": e.id,
                    "from": e.from_address,
                    "to": e.to_addresses,
                    "subject": e.subject,
                    "snippet": e.snippet,
                    "date": e.date,
                    "is_read": e.is_read,
                    "is_starred": e.is_starred,
                    "labels": e.labels,
                }
                for e in emails
            ],
            "count": len(emails),
            "label": label,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "user_message": f"Failed to list emails: {str(e)}",
        }


# Example: How LLM would use the data
async def example_llm_flow_email_inbox():
    """
    Simulates LLM choosing display_email_inbox for "Show me my emails".
    """
    from unittest.mock import MagicMock

    state = MagicMock()

    # Step 1: LLM calls list_emails
    raw_result = await list_emails_raw(state, max_results=10)

    if raw_result["success"]:
        # Step 2: LLM decides user wants inbox view, calls display_email_inbox
        presentation_result = await display_email_inbox(
            state,
            emails=raw_result["emails"],
            view_mode="list",
            folder=raw_result.get("label"),
        )

        # Step 3: Result has __output_type__ for frontend
        assert presentation_result["__output_type__"] == "email_inbox"
        print("Success! Presentation output:", presentation_result)


async def example_llm_flow_email_analysis():
    """
    Simulates LLM choosing display_table for "How many emails from each sender?".
    """
    from collections import Counter
    from unittest.mock import MagicMock

    state = MagicMock()

    # Step 1: LLM calls list_emails (same tool!)
    raw_result = await list_emails_raw(state, max_results=50)

    if raw_result["success"]:
        # Step 2: LLM decides to aggregate and show as table
        sender_counts = Counter(e["from"] for e in raw_result["emails"])
        rows = [
            {"sender": sender, "count": count}
            for sender, count in sender_counts.most_common(10)
        ]

        # Step 3: Call display_table instead of display_email_inbox
        presentation_result = await display_table(
            state,
            columns=["sender", "count"],
            rows=rows,
            title="Emails by Sender",
        )

        # Result has different __output_type__
        assert presentation_result["__output_type__"] == "table"
        print("Success! Table output:", presentation_result)


if __name__ == "__main__":
    import asyncio

    print("=== Email Inbox Flow ===")
    asyncio.run(example_llm_flow_email_inbox())

    print("\n=== Email Analysis Flow ===")
    asyncio.run(example_llm_flow_email_analysis())
