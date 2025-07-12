"""Registry module for managing agent metadata and installations."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class SubAgent:
    """Represents a sub-agent within a main agent."""
    name: str
    description: str
    endpoint: str
    capabilities: List[str]
    public: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class AgentInfo:
    """Complete information about an installed agent."""
    # Basic info from agent.yaml
    name: str
    display_name: str
    version: str
    description: str
    author: str
    license: str
    
    # Extended info
    extensive_description: Optional[str] = None
    capabilities: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    homepage: Optional[str] = None
    
    # Sub-agents
    sub_agents: Optional[List[SubAgent]] = None
    
    # Usage information
    usage_guide: Optional[str] = None
    examples: Optional[List[Dict[str, str]]] = None
    
    # Installation info
    install_date: Optional[datetime] = None
    install_path: Optional[str] = None
    package_size: Optional[int] = None
    
    # Runtime info
    runtime_requirements: Optional[Dict[str, Any]] = None
    dependencies: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        if self.install_date:
            data['install_date'] = self.install_date.isoformat()
        if self.sub_agents:
            data['sub_agents'] = [sa.to_dict() for sa in self.sub_agents]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentInfo':
        """Create from dictionary."""
        if 'install_date' in data and data['install_date']:
            data['install_date'] = datetime.fromisoformat(data['install_date'])
        if 'sub_agents' in data and data['sub_agents']:
            data['sub_agents'] = [SubAgent(**sa) for sa in data['sub_agents']]
        return cls(**data)


class Registry:
    """Manages the agent registry and installed agents."""
    
    def __init__(self, registry_path: Optional[Path] = None):
        """Initialize the registry.
        
        Args:
            registry_path: Path to the registry directory. Defaults to ~/.pixell/registry
        """
        if registry_path is None:
            registry_path = Path.home() / '.pixell' / 'registry'
        
        self.registry_path = Path(registry_path)
        self.agents_dir = self.registry_path / 'agents'
        self.metadata_dir = self.registry_path / 'metadata'
        
        # Create directories if they don't exist
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
    
    def list_agents(self, detailed: bool = False) -> List[AgentInfo]:
        """List all installed agents.
        
        Args:
            detailed: If True, include all metadata. If False, only basic info.
            
        Returns:
            List of AgentInfo objects
        """
        agents = []
        
        # Look for agent metadata files
        for metadata_file in self.metadata_dir.glob('*.json'):
            try:
                with open(metadata_file, 'r') as f:
                    data = json.load(f)
                    agent_info = AgentInfo.from_dict(data)
                    
                    if not detailed:
                        # For non-detailed view, clear some fields
                        agent_info.extensive_description = None
                        agent_info.usage_guide = None
                        agent_info.examples = None
                        agent_info.sub_agents = None
                    
                    agents.append(agent_info)
            except Exception as e:
                # Log error but continue with other agents
                print(f"Warning: Failed to load metadata for {metadata_file.stem}: {e}")
        
        # Sort by name
        agents.sort(key=lambda a: a.name)
        return agents
    
    def get_agent(self, name: str) -> Optional[AgentInfo]:
        """Get detailed information about a specific agent.
        
        Args:
            name: The agent name
            
        Returns:
            AgentInfo object or None if not found
        """
        metadata_file = self.metadata_dir / f"{name}.json"
        if not metadata_file.exists():
            return None
        
        try:
            with open(metadata_file, 'r') as f:
                data = json.load(f)
                return AgentInfo.from_dict(data)
        except Exception:
            return None
    
    def register_agent(self, agent_info: AgentInfo) -> None:
        """Register a new agent in the registry.
        
        Args:
            agent_info: The agent information to register
        """
        metadata_file = self.metadata_dir / f"{agent_info.name}.json"
        
        # Set install date if not already set
        if agent_info.install_date is None:
            agent_info.install_date = datetime.now()
        
        # Save metadata
        with open(metadata_file, 'w') as f:
            json.dump(agent_info.to_dict(), f, indent=2)
    
    def unregister_agent(self, name: str) -> bool:
        """Remove an agent from the registry.
        
        Args:
            name: The agent name
            
        Returns:
            True if removed, False if not found
        """
        metadata_file = self.metadata_dir / f"{name}.json"
        if metadata_file.exists():
            metadata_file.unlink()
            return True
        return False
    
    def search_agents(self, query: str) -> List[AgentInfo]:
        """Search for agents matching a query.
        
        Args:
            query: Search query (searches in name, display_name, description, tags)
            
        Returns:
            List of matching agents
        """
        query = query.lower()
        matching_agents = []
        
        for agent in self.list_agents(detailed=True):
            # Search in various fields
            if (query in agent.name.lower() or
                query in agent.display_name.lower() or
                query in agent.description.lower() or
                (agent.extensive_description and query in agent.extensive_description.lower()) or
                (agent.tags and any(query in tag.lower() for tag in agent.tags))):
                matching_agents.append(agent)
        
        return matching_agents