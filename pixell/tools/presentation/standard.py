"""
Standard presentation tools for common output types.

These tools handle generic data presentation: tables, lists, and charts.
For domain-specific presentation (emails, Slack, research), see the
domain modules.
"""

from typing import Any, Literal

from pixell.tools.presentation.base import (
    PresentationOutput,
    presentation_tool,
)


@presentation_tool(
    name="display_table",
    description="""Display data as a table with columns and rows.

BEST FOR:
- Structured data with consistent columns
- Comparing multiple items side-by-side
- Data that users may want to sort, filter, or export
- Query results from databases or spreadsheets

NOT RECOMMENDED FOR:
- Long text content per cell (use display_list instead)
- Hierarchical/nested data (describe in text or use nested list)
- Single items (just describe in your response text)
- Emails (use display_email_inbox for better UX)

The frontend will render an interactive table with optional sorting and
column resizing. Include total_count if the data is paginated.""",
    parameters={
        "columns": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Column names/headers for the table",
        },
        "rows": {
            "type": "array",
            "items": {"type": "object"},
            "description": "Array of row objects with keys matching column names",
        },
        "title": {
            "type": "string",
            "description": "Optional title displayed above the table",
        },
        "total_count": {
            "type": "integer",
            "description": "Total rows in dataset (if paginated/truncated)",
        },
    },
    required=["columns", "rows"],
)
async def display_table(
    state: Any,
    columns: list[str],
    rows: list[dict[str, Any]],
    title: str | None = None,
    total_count: int | None = None,
    **kwargs,
) -> PresentationOutput:
    """Display data as an interactive table."""
    row_count = len(rows)
    is_truncated = total_count is not None and total_count > row_count

    return PresentationOutput(
        output_type="table",
        data={
            "columns": columns,
            "rows": rows,
            "title": title,
            "row_count": row_count,
            "total_count": total_count or row_count,
            "is_truncated": is_truncated,
        },
    )


@presentation_tool(
    name="display_list",
    description="""Display items as a formatted list.

BEST FOR:
- Sequential items (steps, instructions, ranked items)
- Items with varying structures or fields
- Long text content per item (summaries, descriptions)
- Search results with mixed content types

NOT RECOMMENDED FOR:
- Data with many comparable numeric fields (use display_table)
- Emails (use display_email_inbox)
- Data that needs sorting/filtering (use display_table)

Each item can have a title, description, and optional metadata.
Use ordered=True for numbered lists (rankings, steps).""",
    parameters={
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Item title/headline"},
                    "description": {"type": "string", "description": "Item description or content"},
                    "metadata": {"type": "object", "description": "Additional key-value pairs to display"},
                },
            },
            "description": "Array of items to display",
        },
        "title": {
            "type": "string",
            "description": "Optional title displayed above the list",
        },
        "ordered": {
            "type": "boolean",
            "description": "True for numbered list, False for bullet points (default: False)",
        },
    },
    required=["items"],
)
async def display_list(
    state: Any,
    items: list[dict[str, Any]],
    title: str | None = None,
    ordered: bool = False,
    **kwargs,
) -> PresentationOutput:
    """Display items as a formatted list."""
    return PresentationOutput(
        output_type="list",
        data={
            "items": items,
            "title": title,
            "ordered": ordered,
            "item_count": len(items),
        },
    )


@presentation_tool(
    name="display_chart",
    description="""Display data as a chart visualization.

BEST FOR:
- Trends over time -> use chart_type="line"
- Comparing categories/groups -> use chart_type="bar"
- Parts of a whole (proportions) -> use chart_type="pie"
- Numeric summaries and aggregations

NOT RECOMMENDED FOR:
- Raw data exploration (use display_table first, then chart)
- More than 10-15 categories for pie charts (use bar instead)
- Non-numeric data (use display_table or display_list)

The frontend renders interactive charts using Recharts.
x_field is the category/time axis, y_field is the numeric value.""",
    parameters={
        "data": {
            "type": "array",
            "items": {"type": "object"},
            "description": "Array of data points with x and y values",
        },
        "chart_type": {
            "type": "string",
            "enum": ["bar", "line", "pie"],
            "description": "Type of chart: bar (comparisons), line (trends), pie (proportions)",
        },
        "x_field": {
            "type": "string",
            "description": "Field name for x-axis (categories or dates)",
        },
        "y_field": {
            "type": "string",
            "description": "Field name for y-axis (numeric values)",
        },
        "title": {
            "type": "string",
            "description": "Chart title",
        },
    },
    required=["data", "chart_type", "x_field", "y_field"],
)
async def display_chart(
    state: Any,
    data: list[dict[str, Any]],
    chart_type: Literal["bar", "line", "pie"],
    x_field: str,
    y_field: str,
    title: str | None = None,
    **kwargs,
) -> PresentationOutput:
    """Display data as a chart visualization."""
    # Build visualization config compatible with existing frontend
    config = {
        "xField": x_field,
        "yField": y_field,
    }

    # Type-specific config
    if chart_type == "pie":
        config["nameField"] = x_field
        config["valueField"] = y_field
    elif chart_type == "line":
        config["smooth"] = True
    elif chart_type == "bar":
        config["radius"] = [4, 4, 0, 0]

    return PresentationOutput(
        output_type="chart",
        data={
            "chart_type": chart_type,
            "data": data,
            "config": config,
            "title": title,
            "data_points": len(data),
        },
    )


# Tool collection for easy registration
STANDARD_PRESENTATION_TOOLS = {
    "display_table": display_table,
    "display_list": display_list,
    "display_chart": display_chart,
}
