"""
Shared Presentation Tools for Pixell Agents

Presentation is a separate tool layer that the LLM chooses.
Data tools return raw data; LLM picks how to present it.

Example flow:
    User: "Show me my emails"
      |
    Domain Tool (list_emails)     ->    Raw Data (email objects)
      |
    LLM Decision: "User wants quick overview"
      |
    Presentation Tool (display_email_inbox)    ->    Structured UI Output
      |
    Frontend renders EmailInboxCard

Usage in agents:
    from pixell.tools.presentation import (
        display_table,
        display_list,
        display_email_inbox,
        ALL_PRESENTATION_TOOLS,
    )

    # Register alongside domain tools
    ALL_TOOLS = {
        **DOMAIN_TOOLS,
        **ALL_PRESENTATION_TOOLS,  # Or pick specific ones
    }
"""

from pixell.tools.presentation.base import (
    PresentationOutput,
    presentation_tool,
)

from pixell.tools.presentation.standard import (
    display_table,
    display_list,
    display_chart,
    STANDARD_PRESENTATION_TOOLS,
)

from pixell.tools.presentation.domains.email import (
    display_email_inbox,
    display_email_detail,
    EMAIL_PRESENTATION_TOOLS,
)

from pixell.tools.presentation.domains.slack import (
    display_slack_channels,
    display_slack_messages,
    SLACK_PRESENTATION_TOOLS,
)

from pixell.tools.presentation.domains.research import (
    display_research_report,
    RESEARCH_PRESENTATION_TOOLS,
)

from pixell.tools.presentation.guidance import (
    PRESENTATION_GUIDANCE,
    get_presentation_guidance,
)

# Aggregate all presentation tools for easy registration
ALL_PRESENTATION_TOOLS = {
    **STANDARD_PRESENTATION_TOOLS,
    **EMAIL_PRESENTATION_TOOLS,
    **SLACK_PRESENTATION_TOOLS,
    **RESEARCH_PRESENTATION_TOOLS,
}

__all__ = [
    # Core
    "PresentationOutput",
    "presentation_tool",
    # Standard
    "display_table",
    "display_list",
    "display_chart",
    "STANDARD_PRESENTATION_TOOLS",
    # Domain-specific
    "display_email_inbox",
    "display_email_detail",
    "EMAIL_PRESENTATION_TOOLS",
    "display_slack_channels",
    "display_slack_messages",
    "SLACK_PRESENTATION_TOOLS",
    "display_research_report",
    "RESEARCH_PRESENTATION_TOOLS",
    # All tools
    "ALL_PRESENTATION_TOOLS",
    # Guidance
    "PRESENTATION_GUIDANCE",
    "get_presentation_guidance",
]
