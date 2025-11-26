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
    author_email: Optional[str] = Field(default=None, description="Author email address")


class PermissionsConfig(BaseModel):
    """Permission requirements for the agent.

    Permissions define what data and APIs the agent needs access to.
    Required permissions must be granted for the agent to function.
    Optional permissions enhance functionality but aren't mandatory.
    """

    required: List[str] = Field(
        default_factory=list,
        description="Permissions that must be granted for the agent to function",
    )
    optional: List[str] = Field(
        default_factory=list,
        description="Permissions that enhance functionality but aren't required",
    )

    @field_validator("required", "optional")
    @classmethod
    def validate_permissions(cls, v: List[str]) -> List[str]:
        """Validate permission format."""
        valid_prefixes = [
            "user.profile",
            "user.files",
            "user.conversations",
            "oauth.",
            "files.",
            "conversations.",
            "tasks.",
        ]
        for perm in v:
            if not any(perm.startswith(prefix) for prefix in valid_prefixes):
                # Allow custom permissions but warn
                pass
        return v


class DataAccessConfig(BaseModel):
    """Data access documentation for the agent.

    Documents what external services and user data the agent accesses.
    This is primarily for transparency and user consent.
    """

    oauth_providers: List[str] = Field(
        default_factory=list,
        description="OAuth providers the agent uses (e.g., google, github, tiktok)",
    )
    user_data: List[str] = Field(
        default_factory=list,
        description="Types of user data accessed (e.g., profile, files, conversations)",
    )
    external_apis: List[str] = Field(
        default_factory=list,
        description="External APIs the agent calls",
    )


class AgentManifest(BaseModel):
    """Agent manifest schema for agent.yaml files."""

    # Required fields
    version: str = Field(description="Manifest version", default="1.0")
    name: str = Field(description="Agent package name (lowercase, hyphens)")
    display_name: str = Field(description="Human-readable agent name")
    description: str = Field(description="Agent description")
    author: str = Field(description="Agent author name")
    license: str = Field(description="License identifier (e.g., MIT, Apache-2.0)")
    entrypoint: Optional[str] = Field(
        default=None,
        description="Python module:function entry point (optional if REST or A2A configured)",
    )

    # Optional fields
    capabilities: List[str] = Field(default_factory=list, description="Agent capabilities")
    runtime: str = Field(default="python3.11", description="Runtime environment")
    environment: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    dependencies: List[str] = Field(default_factory=list, description="Python dependencies")
    mcp: Optional[MCPConfig] = Field(default=None)
    metadata: MetadataConfig = Field(..., description="Agent metadata")
    permissions: Optional[PermissionsConfig] = Field(
        default=None, description="Permission requirements for the agent"
    )
    data_access: Optional[DataAccessConfig] = Field(
        default=None, description="Data access documentation for the agent"
    )

    # Surfaces (optional)
    class A2AConfig(BaseModel):
        # Prefer 'entry' for consistency with REST; keep 'service' for backwards compatibility
        entry: Optional[str] = Field(
            default=None,
            description="Module:function for A2A gRPC server entry (optional)",
        )
        # Backwards compatible alias for manifests that still use `service`
        service: Optional[str] = Field(
            default=None,
            description="DEPRECATED: use 'entry' instead",
            alias="service",
        )

        @field_validator("entry")
        @classmethod
        def validate_entry(cls, v):  # type: ignore[no-redef]
            # Allow omission; full path validation is handled in Validator/Builder
            if v is not None and ":" not in v:
                raise ValueError("A2A entry must be in format 'module:function'")
            return v

        @model_validator(mode="after")
        def _populate_entry_from_service(self):  # type: ignore[no-redef]
            # If only legacy `service` is provided, mirror it into `entry`
            if self.entry is None and self.service is not None:
                self.entry = self.service
            return self

    class RestConfig(BaseModel):
        entry: str = Field(description="Module:function that mounts REST routes on FastAPI app, or just function name to use entrypoint's module")

        @field_validator("entry")
        @classmethod
        def validate_entry(cls, v):  # type: ignore[no-redef]
            # Allow function name only (will use entrypoint's module in validator)
            # Full validation happens in AgentValidator._validate_surfaces
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

    @model_validator(mode="after")
    def validate_entrypoint_optional_when_surfaces(self):  # type: ignore[no-redef]
        # Allow omission when REST or A2A is configured
        if self.entrypoint is None:
            has_surfaces = any(
                [
                    getattr(self, "a2a", None) is not None,
                    getattr(self, "rest", None) is not None,
                    getattr(self, "ui", None) is not None,
                ]
            )
            if not has_surfaces:
                raise ValueError("Entrypoint is required when no surfaces are configured")
        return self

    model_config = {"extra": "forbid"}  # Don't allow extra fields
