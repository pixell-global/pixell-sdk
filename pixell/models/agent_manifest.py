"""Agent manifest (agent.yaml) data models."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class MCPConfig(BaseModel):
    """MCP (Model Context Protocol) configuration."""

    enabled: bool = Field(default=False)
    config_file: Optional[str] = Field(default=None, description="Path to MCP config file")


class MetadataConfig(BaseModel):
    """Agent metadata."""

    version: str = Field(description="Agent version (semantic versioning)")
    homepage: Optional[str] = Field(default=None)
    repository: Optional[str] = Field(default=None)
    tags: List[str] = Field(default_factory=list)


class AgentManifest(BaseModel):
    """Agent manifest schema for agent.yaml files."""

    # Required fields
    version: str = Field(description="Manifest version", default="1.0")
    name: str = Field(description="Agent package name (lowercase, hyphens)")
    display_name: str = Field(description="Human-readable agent name")
    description: str = Field(description="Agent description")
    author: str = Field(description="Agent author name")
    license: str = Field(description="License identifier (e.g., MIT, Apache-2.0)")
    entrypoint: Optional[str] = Field(default=None, description="Python module:function entry point (optional if REST or A2A configured)")

    # Optional fields
    capabilities: List[str] = Field(default_factory=list, description="Agent capabilities")
    runtime: str = Field(default="python3.11", description="Runtime environment")
    environment: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    dependencies: List[str] = Field(default_factory=list, description="Python dependencies")
    mcp: Optional[MCPConfig] = Field(default=None)
    metadata: MetadataConfig = Field(..., description="Agent metadata")
    # Surfaces (optional)
    class A2AConfig(BaseModel):
        service: str = Field(description="Module:function for A2A gRPC server entry")

        @field_validator("service")
        @classmethod
        def validate_service(cls, v):  # type: ignore[no-redef]
            if ":" not in v:
                raise ValueError("A2A service must be in format 'module:function'")
            return v

    class RestConfig(BaseModel):
        entry: str = Field(description="Module:function that mounts REST routes on FastAPI app")

        @field_validator("entry")
        @classmethod
        def validate_entry(cls, v):  # type: ignore[no-redef]
            if ":" not in v:
                raise ValueError("REST entry must be in format 'module:function'")
            return v

    class UIConfig(BaseModel):
        path: str = Field(description="Path to built/static UI assets directory")

    a2a: Optional[A2AConfig] = Field(default=None)
    rest: Optional[RestConfig] = Field(default=None)
    ui: Optional[UIConfig] = Field(default=None)
    # UI optional fields (per PRD)
    ui_spec_version: Optional[str] = Field(
        default=None, description="UI spec version used by this agent"
    )
    required_ui_capabilities: Optional[List[str]] = Field(
        default=None, description="Capabilities this agent requires from the UI client"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        """Validate agent name format."""
        import re

        if not re.match(r"^[a-z][a-z0-9-]*$", v):
            raise ValueError("Name must be lowercase letters, numbers, and hyphens only")
        return v

    # Removed strict entrypoint enforcement here; see below validator

    @field_validator("runtime")
    @classmethod
    def validate_runtime(cls, v):
        """Validate runtime format."""
        valid_runtimes = ["node18", "node20", "python3.9", "python3.11", "go1.21"]
        if v not in valid_runtimes:
            raise ValueError(f"Invalid runtime: {v}. Valid options: {', '.join(valid_runtimes)}")
        return v

    @field_validator("dependencies")
    @classmethod
    def validate_dependencies(cls, v):
        """Validate dependency format."""
        import re

        pattern = r"^[a-zA-Z0-9_-]+(\[[a-zA-Z0-9_,-]+\])?(>=|==|<=|>|<|~=|!=)[0-9.]+.*$"
        for dep in v:
            if not re.match(pattern, dep):
                raise ValueError(f"Invalid dependency format: {dep}")
        return v

    @field_validator("entrypoint")
    @classmethod
    def validate_entrypoint_format(cls, v):  # type: ignore[no-redef]
        # Basic format validation - cross-field validation handled in model_validator
        if v is not None and ":" not in v:
            raise ValueError("Entrypoint must be in format 'module:function'")
        return v

    @model_validator(mode='after')
    def validate_entrypoint_optional_when_surfaces(self):  # type: ignore[no-redef]
        # Allow omission when REST or A2A is configured
        if self.entrypoint is None:
            has_surfaces = any([
                getattr(self, 'a2a', None) is not None,
                getattr(self, 'rest', None) is not None,
                getattr(self, 'ui', None) is not None
            ])
            if not has_surfaces:
                raise ValueError("Entrypoint is required when no surfaces are configured")
        return self

    model_config = {"extra": "forbid"}  # Don't allow extra fields
