"""
Research presentation tools for analysis and findings display.

These tools provide rich research UI rendering with findings,
quotes, sources, and sentiment analysis.
"""

from typing import Any, Literal

from pixell.tools.presentation.base import (
    PresentationOutput,
    presentation_tool,
)


@presentation_tool(
    name="display_research_report",
    description="""Display research findings in a structured report format.

BEST FOR:
- Research results with key findings and insights
- Analysis summaries with supporting evidence
- Multi-source research (Reddit, news, social media)
- Reports with quotes, themes, and sentiment

NOT RECOMMENDED FOR:
- Raw data listings (use display_table)
- Simple search results (use display_list)
- Single posts/articles (describe in text)

Include findings (key insights), quotes (supporting evidence),
themes (patterns identified), and sentiment (overall tone).
The frontend renders a rich research card with expandable sections.""",
    parameters={
        "title": {
            "type": "string",
            "description": "Research report title",
        },
        "summary": {
            "type": "string",
            "description": "Executive summary of findings (2-3 sentences)",
        },
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Finding headline"},
                    "description": {"type": "string", "description": "Finding details"},
                    "confidence": {"type": "string", "enum": ["high", "medium", "low"], "description": "Confidence level"},
                    "source_count": {"type": "integer", "description": "Number of supporting sources"},
                },
            },
            "description": "Key findings/insights from the research",
        },
        "quotes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Quote text"},
                    "source": {"type": "string", "description": "Source attribution"},
                    "url": {"type": "string", "description": "Link to source"},
                    "sentiment": {"type": "string", "enum": ["positive", "negative", "neutral"]},
                },
            },
            "description": "Notable quotes/excerpts supporting findings",
        },
        "themes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Main themes/topics identified",
        },
        "sentiment": {
            "type": "object",
            "properties": {
                "overall": {"type": "string", "enum": ["positive", "negative", "neutral", "mixed"]},
                "positive_pct": {"type": "number", "description": "Percentage positive (0-100)"},
                "negative_pct": {"type": "number", "description": "Percentage negative (0-100)"},
                "neutral_pct": {"type": "number", "description": "Percentage neutral (0-100)"},
            },
            "description": "Sentiment analysis summary",
        },
        "sources": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Source name (e.g., 'r/technology')"},
                    "type": {"type": "string", "description": "Source type (reddit, news, etc.)"},
                    "url": {"type": "string", "description": "Source URL"},
                    "post_count": {"type": "integer", "description": "Number of posts analyzed"},
                },
            },
            "description": "Sources used in the research",
        },
        "top_posts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "url": {"type": "string"},
                    "score": {"type": "integer"},
                    "comment_count": {"type": "integer"},
                    "subreddit": {"type": "string"},
                },
            },
            "description": "Top relevant posts (for Reddit research)",
        },
        "metadata": {
            "type": "object",
            "properties": {
                "posts_analyzed": {"type": "integer"},
                "date_range": {"type": "string"},
                "research_type": {"type": "string"},
            },
            "description": "Research metadata",
        },
    },
    required=["title", "findings"],
)
async def display_research_report(
    state: Any,
    title: str,
    findings: list[dict[str, Any]],
    summary: str | None = None,
    quotes: list[dict[str, Any]] | None = None,
    themes: list[str] | None = None,
    sentiment: dict[str, Any] | None = None,
    sources: list[dict[str, Any]] | None = None,
    top_posts: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
    **kwargs,
) -> PresentationOutput:
    """Display research findings in a report format."""
    return PresentationOutput(
        output_type="research_report",
        data={
            "title": title,
            "summary": summary,
            "findings": findings,
            "quotes": quotes or [],
            "themes": themes or [],
            "sentiment": sentiment,
            "sources": sources or [],
            "top_posts": top_posts or [],
            "metadata": metadata or {},
            "finding_count": len(findings),
            "quote_count": len(quotes) if quotes else 0,
            "source_count": len(sources) if sources else 0,
        },
    )


# Tool collection for easy registration
RESEARCH_PRESENTATION_TOOLS = {
    "display_research_report": display_research_report,
}
