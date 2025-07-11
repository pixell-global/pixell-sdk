"""Agent manifest (agent.yaml) data models."""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator


class RuntimeConfig(BaseModel):
    """Runtime configuration for the agent."""
    python_version: str = Field(default=">=3.8", description="Required Python version")
    memory: str = Field(default="256MB", description="Memory allocation")
    timeout: int = Field(default=300, description="Execution timeout in seconds")


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
    entry_point: str = Field(description="Python module:function entry point")
    
    # Optional fields
    capabilities: List[str] = Field(default_factory=list, description="Agent capabilities")
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    environment: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    dependencies: List[str] = Field(default_factory=list, description="Python dependencies")
    mcp: Optional[MCPConfig] = Field(default=None)
    metadata: MetadataConfig = Field(..., description="Agent metadata")
    
    @validator('name')
    def validate_name(cls, v):
        """Validate agent name format."""
        import re
        if not re.match(r'^[a-z][a-z0-9-]*$', v):
            raise ValueError("Name must be lowercase letters, numbers, and hyphens only")
        return v
    
    @validator('entry_point')
    def validate_entry_point(cls, v):
        """Validate entry point format."""
        if ':' not in v:
            raise ValueError("Entry point must be in format 'module:function'")
        return v
    
    @validator('dependencies')
    def validate_dependencies(cls, v):
        """Validate dependency format."""
        import re
        pattern = r'^[a-zA-Z0-9_-]+(\[[a-zA-Z0-9_,-]+\])?(>=|==|<=|>|<|~=|!=)[0-9.]+.*$'
        for dep in v:
            if not re.match(pattern, dep):
                raise ValueError(f"Invalid dependency format: {dep}")
        return v

    class Config:
        extra = "forbid"  # Don't allow extra fields