"""
Base classes and utilities for presentation tools.

Presentation tools return structured output that the frontend can render
using specialized components. The `__output_type__` field tells the frontend
which component to use.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar
import functools

T = TypeVar("T")


@dataclass
class PresentationOutput:
    """
    Base class for all presentation tool outputs.

    The frontend uses `__output_type__` to select the appropriate component.
    Additional data is passed directly to the component.

    Example output:
        {
            "__output_type__": "table",
            "columns": ["name", "email"],
            "rows": [{"name": "Alice", "email": "alice@example.com"}],
            "title": "Users",
            ...
        }
    """

    output_type: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for agent response."""
        return {
            "__output_type__": self.output_type,
            **self.data,
        }


def _tool_def(
    name: str,
    description: str,
    parameters: dict[str, Any],
    required: list[str] | None = None,
) -> dict[str, Any]:
    """Create OpenAI-style tool definition."""
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": required or [],
            },
        },
    }


def presentation_tool(
    name: str,
    description: str,
    parameters: dict[str, Any],
    required: list[str] | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to mark a function as a presentation tool.

    This attaches the tool definition in OpenAI format to the function,
    following the same pattern used by agent tools.

    Args:
        name: Tool name (used by LLM to call it)
        description: Description for LLM (critical for tool selection)
        parameters: JSON Schema for parameters
        required: List of required parameter names

    Example:
        @presentation_tool(
            name="display_table",
            description="Display data as a table...",
            parameters={
                "columns": {"type": "array", "description": "..."},
                "rows": {"type": "array", "description": "..."},
            },
            required=["columns", "rows"],
        )
        async def display_table(state, columns, rows, **kwargs):
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Attach tool definition for LLM consumption
        func._tool_def = _tool_def(name, description, parameters, required)

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            # If result is PresentationOutput, convert to dict
            if isinstance(result, PresentationOutput):
                return result.to_dict()
            return result

        # Copy tool definition to wrapper
        wrapper._tool_def = func._tool_def
        return wrapper

    return decorator
