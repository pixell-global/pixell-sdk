"""Agent capability models for tool discovery.

These models define how agents expose their capabilities to frontends.
Used by the agent/getCapabilities JSON-RPC method.
"""

from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class CapabilityTier(str, Enum):
    """Capability tier classification."""

    LIGHT = "light"   # Quick, always available, low cost
    HEAVY = "heavy"   # Comprehensive, requires confirmation, expensive


class CapabilityCategory(str, Enum):
    """Standard capability categories for UI grouping."""

    REPORTS = "reports"       # Generate reports (brand, product, competitor)
    SEARCH = "search"         # Search and discovery
    ANALYSIS = "analysis"     # Data analysis and trends
    DATA = "data"             # Data retrieval
    USERS = "users"           # User-related operations


class OutputType(str, Enum):
    """Output types for capabilities."""

    TEXT = "text"             # Plain text response
    HTML_REPORT = "html_report"  # HTML report with URL
    CHART = "chart"           # Chart/visualization data
    LIST = "list"             # List of items
    TABLE = "table"           # Tabular data


class EstimatedTime(str, Enum):
    """Estimated execution time."""

    INSTANT = "instant"       # < 1 second
    SECONDS = "seconds"       # 1-10 seconds
    MINUTES = "minutes"       # > 10 seconds


@dataclass
class Capability:
    """
    A single agent capability (tool) exposed to frontends.

    Capabilities are grouped by category and tier for UI display.
    """

    # Identity
    id: str                    # Tool ID (e.g., "generate_brand_report")
    name: str                  # Display name (e.g., "Brand Report")
    description: str           # Human-readable description

    # Classification
    category: str              # Category for grouping (reports, search, analysis, data, users)
    tier: str                  # "light" or "heavy"

    # UI hints
    icon: str = "default"      # Icon identifier (chart, search, users, document, etc.)
    estimated_time: str = "seconds"  # instant, seconds, minutes

    # Behavior
    requires_confirmation: bool = False  # Show confirmation dialog before execution

    # Schema
    input_schema: dict[str, Any] = field(default_factory=dict)  # JSON Schema for parameters
    output_type: str = "text"  # Expected output type

    # Examples for UI
    examples: list[str] = field(default_factory=list)  # Example prompts

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "tier": self.tier,
            "icon": self.icon,
            "estimated_time": self.estimated_time,
            "requires_confirmation": self.requires_confirmation,
            "input_schema": self.input_schema,
            "output_type": self.output_type,
            "examples": self.examples,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Capability":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            category=data["category"],
            tier=data["tier"],
            icon=data.get("icon", "default"),
            estimated_time=data.get("estimated_time", "seconds"),
            requires_confirmation=data.get("requires_confirmation", False),
            input_schema=data.get("input_schema", {}),
            output_type=data.get("output_type", "text"),
            examples=data.get("examples", []),
        )


@dataclass
class CategoryInfo:
    """Category metadata for UI grouping."""

    id: str                    # Category ID (e.g., "reports")
    name: str                  # Display name (e.g., "Reports")
    description: str           # Category description
    icon: str = "folder"       # Category icon

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
        }


@dataclass
class AgentCapabilities:
    """
    Complete capability manifest for an agent.

    Returned by the agent/getCapabilities JSON-RPC method.
    """

    agent_id: str              # Agent identifier
    agent_name: str            # Human-readable agent name
    platform: str              # Platform (reddit, tiktok, general)

    # Capability data
    categories: list[CategoryInfo] = field(default_factory=list)
    capabilities: list[Capability] = field(default_factory=list)

    # Version info
    version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "platform": self.platform,
            "version": self.version,
            "categories": [c.to_dict() for c in self.categories],
            "capabilities": [c.to_dict() for c in self.capabilities],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentCapabilities":
        """Create from dictionary."""
        return cls(
            agent_id=data["agent_id"],
            agent_name=data["agent_name"],
            platform=data["platform"],
            version=data.get("version", "1.0.0"),
            categories=[CategoryInfo(**c) for c in data.get("categories", [])],
            capabilities=[Capability.from_dict(c) for c in data.get("capabilities", [])],
        )

    def get_by_category(self, category: str) -> list[Capability]:
        """Get capabilities filtered by category."""
        return [c for c in self.capabilities if c.category == category]

    def get_by_tier(self, tier: str) -> list[Capability]:
        """Get capabilities filtered by tier."""
        return [c for c in self.capabilities if c.tier == tier]


# Standard category definitions for consistency across agents
STANDARD_CATEGORIES = [
    CategoryInfo(
        id="reports",
        name="Reports",
        description="Generate comprehensive analysis reports",
        icon="chart",
    ),
    CategoryInfo(
        id="search",
        name="Search",
        description="Search and discover content",
        icon="search",
    ),
    CategoryInfo(
        id="analysis",
        name="Analysis",
        description="Analyze data and trends",
        icon="trending",
    ),
    CategoryInfo(
        id="data",
        name="Data",
        description="Retrieve raw data",
        icon="database",
    ),
    CategoryInfo(
        id="users",
        name="Users",
        description="User profiles and activity",
        icon="users",
    ),
]
