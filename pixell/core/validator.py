"""Agent validation functionality."""
from pathlib import Path
from typing import List, Tuple, Optional
import yaml
from pydantic import ValidationError

from pixell.models.agent_manifest import AgentManifest


class AgentValidator:
    """Validates agent projects and manifests."""
    
    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate(self) -> Tuple[bool, List[str], List[str]]:
        """
        Validate the agent project.
        
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        # Check project structure
        self._validate_project_structure()
        
        # Validate manifest
        manifest = self._validate_manifest()
        
        if manifest:
            # Validate entrypoint
            self._validate_entrypoint(manifest)
            
            # Validate dependencies
            self._validate_dependencies(manifest)
            
            # Validate MCP config if specified
            if manifest.mcp and manifest.mcp.enabled:
                self._validate_mcp_config(manifest)
        
        return len(self.errors) == 0, self.errors, self.warnings
    
    def _validate_project_structure(self):
        """Check required files and directories exist."""
        required_files = ['agent.yaml']
        
        for file in required_files:
            file_path = self.project_dir / file
            if not file_path.exists():
                self.errors.append(f"Required file missing: {file}")
        
        # Check for source directory
        src_dir = self.project_dir / 'src'
        if not src_dir.exists():
            self.errors.append("Source directory 'src/' not found")
        elif not src_dir.is_dir():
            self.errors.append("'src' exists but is not a directory")
        
        # Check for requirements.txt (warning if missing)
        if not (self.project_dir / 'requirements.txt').exists():
            self.warnings.append("No requirements.txt found - dependencies from agent.yaml will be used")
    
    def _validate_manifest(self) -> Optional[AgentManifest]:
        """Validate agent.yaml file."""
        manifest_path = self.project_dir / 'agent.yaml'
        
        if not manifest_path.exists():
            return None
        
        try:
            with open(manifest_path, 'r') as f:
                data = yaml.safe_load(f)
            
            if not isinstance(data, dict):
                self.errors.append("agent.yaml must contain a YAML dictionary")
                return None
            
            # Parse with Pydantic model
            manifest = AgentManifest(**data)
            return manifest
            
        except yaml.YAMLError as e:
            self.errors.append(f"Invalid YAML in agent.yaml: {e}")
            return None
        except ValidationError as e:
            for error in e.errors():
                field = '.'.join(str(x) for x in error['loc'])
                msg = error['msg']
                self.errors.append(f"agent.yaml: {field} - {msg}")
            return None
        except Exception as e:
            self.errors.append(f"Error reading agent.yaml: {e}")
            return None
    
    def _validate_entrypoint(self, manifest: AgentManifest):
        """Validate the entrypoint exists and is callable."""
        module_path, function_name = manifest.entrypoint.split(':', 1)
        
        # Convert module path to file path
        file_path = self.project_dir / (module_path.replace('.', '/') + '.py')
        
        if not file_path.exists():
            self.errors.append(f"Entrypoint module not found: {file_path}")
            return
        
        # Basic check: look for function definition
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                if f"def {function_name}" not in content:
                    self.warnings.append(f"Function '{function_name}' not found in {file_path}")
        except Exception as e:
            self.errors.append(f"Error reading entry point file: {e}")
    
    def _validate_dependencies(self, manifest: AgentManifest):
        """Validate dependencies format."""
        # Check if requirements.txt exists and compare
        req_file = self.project_dir / 'requirements.txt'
        if req_file.exists():
            try:
                with open(req_file, 'r') as f:
                    req_deps = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                
                # Simple comparison - could be enhanced
                manifest_deps = set(manifest.dependencies)
                req_deps_set = set(req_deps)
                
                if manifest_deps != req_deps_set:
                    self.warnings.append("Dependencies in agent.yaml differ from requirements.txt")
            except Exception as e:
                self.warnings.append(f"Could not read requirements.txt: {e}")
    
    def _validate_mcp_config(self, manifest: AgentManifest):
        """Validate MCP configuration if enabled."""
        if manifest.mcp and manifest.mcp.config_file:
            mcp_path = self.project_dir / manifest.mcp.config_file
            if not mcp_path.exists():
                self.errors.append(f"MCP config file not found: {manifest.mcp.config_file}")
            else:
                # Could add JSON validation here
                pass