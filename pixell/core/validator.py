"""Agent validation functionality."""

from pathlib import Path
from typing import List, Tuple, Optional
import re
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

            # Validate optional surfaces
            self._validate_surfaces(manifest)

        # Validate .env presence and contents
        self._validate_env_file()

        return len(self.errors) == 0, self.errors, self.warnings

    def _validate_project_structure(self):
        """Check required files and directories exist."""
        required_files = ["agent.yaml"]

        for file in required_files:
            file_path = self.project_dir / file
            if not file_path.exists():
                self.errors.append(f"Required file missing: {file}")

        # Require .env at project root
        env_path = self.project_dir / ".env"
        if not env_path.exists():
            self.errors.append(
                "Missing required .env file at project root. Create a `.env` with placeholders or real values. See `.env.example`."
            )

        # Check for source directory
        src_dir = self.project_dir / "src"
        if not src_dir.exists():
            self.errors.append("Source directory 'src/' not found")
        elif not src_dir.is_dir():
            self.errors.append("'src' exists but is not a directory")

        # Check for requirements.txt (warning if missing)
        if not (self.project_dir / "requirements.txt").exists():
            self.warnings.append(
                "No requirements.txt found - dependencies from agent.yaml will be used"
            )

    def _validate_manifest(self) -> Optional[AgentManifest]:
        """Validate agent.yaml file."""
        manifest_path = self.project_dir / "agent.yaml"

        if not manifest_path.exists():
            return None

        try:
            with open(manifest_path, "r") as f:
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
                field = ".".join(str(x) for x in error["loc"])
                msg = error["msg"]
                self.errors.append(f"agent.yaml: {field} - {msg}")
            return None
        except Exception as e:
            self.errors.append(f"Error reading agent.yaml: {e}")
            return None

    def _validate_entrypoint(self, manifest: AgentManifest):
        """Validate the entrypoint exists and is callable."""
        # Entrypoint can be optional when any surface is configured
        if not manifest.entrypoint:
            if not (manifest.rest or manifest.a2a or manifest.ui):
                self.errors.append("Entrypoint is required when no surfaces are configured")
            return
        module_path, function_name = manifest.entrypoint.split(":", 1)

        # Convert module path to file path
        file_path = self.project_dir / (module_path.replace(".", "/") + ".py")

        if not file_path.exists():
            self.errors.append(f"Entrypoint module not found: {file_path}")
            return

        # Basic check: look for function definition
        try:
            with open(file_path, "r") as f:
                content = f.read()
                if f"def {function_name}" not in content:
                    self.warnings.append(f"Function '{function_name}' not found in {file_path}")
        except Exception as e:
            self.errors.append(f"Error reading entry point file: {e}")

    def _validate_surfaces(self, manifest: AgentManifest):
        """Validate A2A, REST, and UI configuration."""
        # REST
        if manifest.rest:
            try:
                rest_module, rest_func = manifest.rest.entry.split(":", 1)
                rest_file = self.project_dir / (rest_module.replace(".", "/") + ".py")
                if not rest_file.exists():
                    self.errors.append(f"REST entry module not found: {rest_file}")
                else:
                    try:
                        with open(rest_file, "r") as f:
                            content = f.read()
                            if f"def {rest_func}" not in content:
                                self.warnings.append(
                                    f"REST entry function '{rest_func}' not found in {rest_file}"
                                )
                    except Exception as exc:
                        self.warnings.append(f"Could not read REST entry file: {exc}")
            except ValueError:
                self.errors.append("REST entry must be in 'module:function' format")

        # A2A
        if manifest.a2a:
            try:
                a2a_module, a2a_func = manifest.a2a.service.split(":", 1)
                a2a_file = self.project_dir / (a2a_module.replace(".", "/") + ".py")
                if not a2a_file.exists():
                    self.errors.append(f"A2A service module not found: {a2a_file}")
                else:
                    try:
                        with open(a2a_file, "r") as f:
                            content = f.read()
                            if f"def {a2a_func}" not in content:
                                self.warnings.append(
                                    f"A2A service function '{a2a_func}' not found in {a2a_file}"
                                )
                    except Exception as exc:
                        self.warnings.append(f"Could not read A2A service file: {exc}")
            except ValueError:
                self.errors.append("A2A service must be in 'module:function' format")

        # UI
        if manifest.ui and manifest.ui.path:
            ui_path = self.project_dir / manifest.ui.path
            if not ui_path.exists():
                self.errors.append(f"UI path not found: {manifest.ui.path}")
            elif not ui_path.is_dir():
                self.errors.append(f"UI path is not a directory: {manifest.ui.path}")

    def _validate_dependencies(self, manifest: AgentManifest):
        """Validate dependencies format."""
        # Dependencies are validated by Pydantic model
        # Both agent.yaml and requirements.txt are valid sources
        pass

    def _validate_mcp_config(self, manifest: AgentManifest):
        """Validate MCP configuration if enabled."""
        if manifest.mcp and manifest.mcp.config_file:
            mcp_path = self.project_dir / manifest.mcp.config_file
            if not mcp_path.exists():
                self.errors.append(f"MCP config file not found: {manifest.mcp.config_file}")
            else:
                # Could add JSON validation here
                pass

    def _validate_env_file(self) -> None:
        """Validate presence and content hygiene of the .env file.

        Warnings:
          - Suspicious absolute paths that may harm portability
        """
        env_path = self.project_dir / ".env"
        if not env_path.exists():
            # Presence is handled in structure validation; nothing else to do
            return

        try:
            content = env_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            # If we cannot read, do not block build; warn instead
            self.warnings.append(
                "Could not read .env file for validation; proceeding without checks"
            )
            return

        entries = self._parse_env_content(content)

        # Path hygiene checks for portability - warn about user-specific absolute paths
        pathy_keys: List[str] = []
        for key, value in entries.items():
            if not value:
                continue
            v = value.strip().strip('"').strip("'")
            if v.startswith("/") and ("/Users/" in v or "/home/" in v):
                pathy_keys.append(key)
            # Windows absolute paths
            if re.match(r"^[A-Za-z]:\\\\", v) or re.match(r"^[A-Za-z]:/", v):
                pathy_keys.append(key)

        if pathy_keys:
            unique_path_keys = sorted(set(pathy_keys))
            self.warnings.append(
                ".env contains absolute path values that may harm portability for keys: "
                + ", ".join(unique_path_keys)
                + ". Prefer relative paths or standard locations."
            )

    def _parse_env_content(self, content: str) -> dict:
        """Parse simple KEY=VALUE lines from .env content.

        - Ignores blank lines and comments starting with '#'
        - Trims whitespace around keys/values
        - Strips matching single or double quotes around values
        - Does not support multi-line values
        """
        entries: dict = {}
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip()
            # Strip matching quotes
            if (val.startswith("'") and val.endswith("'")) or (
                val.startswith('"') and val.endswith('"')
            ):
                if len(val) >= 2:
                    val = val[1:-1]
            entries[key] = val
        return entries
