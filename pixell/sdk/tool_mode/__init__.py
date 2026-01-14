"""Tool Mode Module - LLM tool-calling based agents.

Unlike PlanModeAgent which uses phases (discovery → selection → execute),
ToolBasedAgent lets the LLM decide which tools to call, similar to
how OpenAI's ChatGPT and Anthropic's Claude handle tool use.

Example:
    from pixell.sdk.tool_mode import ToolBasedAgent, Tool, tool, result

    class MyAgent(ToolBasedAgent):
        @tool(
            name="search",
            description="Search for information",
            parameters={"query": {"type": "string", "description": "Search query"}}
        )
        async def search(self, query: str) -> Result:
            results = await do_search(query)
            return result(answer=f"Found: {results}")

        @tool(
            name="deep_research",
            description="In-depth research with user interaction",
        )
        async def deep_research(self, topic: str) -> Discovery:
            # This tool can return Discovery to trigger phase flow
            return discovery(items=subreddits, message="Select subreddits")

    MyAgent(agent_id="my-agent", port=9000).run()
"""

from pixell.sdk.tool_mode.agent import (
    ToolBasedAgent,
    Tool,
    ToolCall,
    ToolResult,
    tool,
)
from pixell.sdk.plan_mode.agent import (
    # Re-export response types from plan_mode
    Discovery,
    Clarification,
    Preview,
    Result,
    Error,
    Permission,
    AgentResponse,
    discovery,
    clarify,
    preview,
    result,
    error,
    permission,
)

__all__ = [
    # Core tool mode classes
    "ToolBasedAgent",
    "Tool",
    "ToolCall",
    "ToolResult",
    "tool",
    # Response types (re-exported from plan_mode)
    "Discovery",
    "Clarification",
    "Preview",
    "Result",
    "Error",
    "Permission",
    "AgentResponse",
    "discovery",
    "clarify",
    "preview",
    "result",
    "error",
    "permission",
]
