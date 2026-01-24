"""
Domain-specific presentation tools.

These provide specialized UI rendering for specific data types:
- email: Gmail inbox and detail views
- slack: Channels and message views
- research: Research reports and findings
"""

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

__all__ = [
    # Email
    "display_email_inbox",
    "display_email_detail",
    "EMAIL_PRESENTATION_TOOLS",
    # Slack
    "display_slack_channels",
    "display_slack_messages",
    "SLACK_PRESENTATION_TOOLS",
    # Research
    "display_research_report",
    "RESEARCH_PRESENTATION_TOOLS",
]
