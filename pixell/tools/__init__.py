"""
Pixell SDK Shared Tools

This module provides shared tools that can be used across all agents.
Tools are organized by purpose:

- presentation: LLM-driven presentation tools for structured output
- file_tools: Agent file storage for persistent data across sessions
"""

from pixell.tools.file_tools import AgentFileTools, FileInfo
from pixell.tools.presentation import (
    # Core exports
    PresentationOutput,
    presentation_tool,
    # Standard presentation tools
    display_table,
    display_list,
    display_chart,
    # Domain-specific tools
    display_email_inbox,
    display_email_detail,
    display_slack_channels,
    display_slack_messages,
    display_research_report,
    # Tool collections for agent registration
    STANDARD_PRESENTATION_TOOLS,
    EMAIL_PRESENTATION_TOOLS,
    SLACK_PRESENTATION_TOOLS,
    RESEARCH_PRESENTATION_TOOLS,
    ALL_PRESENTATION_TOOLS,
    # Guidance
    PRESENTATION_GUIDANCE,
    get_presentation_guidance,
)

__all__ = [
    # File tools
    "AgentFileTools",
    "FileInfo",
    # Presentation - Core
    "PresentationOutput",
    "presentation_tool",
    # Presentation - Standard
    "display_table",
    "display_list",
    "display_chart",
    # Presentation - Domain-specific
    "display_email_inbox",
    "display_email_detail",
    "display_slack_channels",
    "display_slack_messages",
    "display_research_report",
    # Presentation - Tool collections
    "STANDARD_PRESENTATION_TOOLS",
    "EMAIL_PRESENTATION_TOOLS",
    "SLACK_PRESENTATION_TOOLS",
    "RESEARCH_PRESENTATION_TOOLS",
    "ALL_PRESENTATION_TOOLS",
    # Presentation - Guidance
    "PRESENTATION_GUIDANCE",
    "get_presentation_guidance",
]
