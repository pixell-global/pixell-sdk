"""
Presentation Guidance for Agent System Prompts

Add this guidance to agent system prompts to help the LLM choose
the appropriate presentation tool based on user intent.
"""

PRESENTATION_GUIDANCE = """
## Presenting Results to Users

After retrieving data with a domain tool, choose the appropriate presentation tool
based on what the user is trying to accomplish.

### Standard Presentation Tools

| User Intent | Presentation Tool | When to Use |
|-------------|------------------|-------------|
| "Show me the data" | `display_table` | Structured data with consistent columns |
| "List the items" | `display_list` | Sequential items, varied structures |
| "Show the trend" | `display_chart` (line) | Time-series data, changes over time |
| "Compare these" | `display_chart` (bar) | Category comparisons |
| "What's the breakdown?" | `display_chart` (pie) | Parts of a whole (<=10 items) |

### Domain-Specific Presentation Tools

| User Intent | Presentation Tool | When to Use |
|-------------|------------------|-------------|
| "Show me my emails" | `display_email_inbox` | Email list for browsing |
| "Read this email" | `display_email_detail` | Single email with full body |
| "Show channels" | `display_slack_channels` | Slack channel list |
| "Show messages" | `display_slack_messages` | Slack message history |
| "Summarize the research" | `display_research_report` | Research findings with quotes/themes |

### Decision Guidelines

1. **Consider user intent**:
   - "Show me" / "List" → browse/scan (inbox, list, table)
   - "How many" / "Compare" → analyze (chart, table with aggregation)
   - "Read" / "Open" / "Details" → deep dive (detail view)
   - "Summarize" / "What did you find" → synthesis (report)

2. **Consider data shape**:
   - Many items with same fields → table
   - Items with varying content → list
   - Numeric data over time → line chart
   - Categories with values → bar chart
   - Small set of proportions → pie chart

3. **Consider follow-up actions**:
   - Will user want to interact (star, reply, archive)? → specialized view
   - Will user want to sort/filter? → table
   - Will user want to drill down? → consider both summary + detail

### Examples

**Example 1: Email request**
```
User: "Show me my recent emails"
1. Call list_emails to get email data
2. Call display_email_inbox to render inbox view
   (User wants to browse, likely star/archive/reply to some)
```

**Example 2: Email analysis**
```
User: "How many emails did I get from each sender?"
1. Call list_emails to get email data
2. Aggregate the data by sender
3. Call display_table with sender counts
   (User wants to analyze patterns, not browse emails)
```

**Example 3: Research request**
```
User: "Research what people think about X"
1. Perform research with domain tools
2. Call display_research_report with findings, quotes, themes
   (User wants synthesis, not raw data)
```

### Important Notes

- NEVER skip the presentation step - always call a presentation tool for user-facing results
- ALWAYS describe what you found in your response text, even when using presentation tools
- If data is empty, explain why in your response instead of showing empty visualization
- If multiple visualizations make sense, prefer the one that best matches user intent
"""


def get_presentation_guidance() -> str:
    """Get the presentation guidance text for agent system prompts."""
    return PRESENTATION_GUIDANCE
