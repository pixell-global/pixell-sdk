"""Agent package builder functionality."""

import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Optional
import yaml
import json

from pixell.models.agent_manifest import AgentManifest
from pixell.core.validator import AgentValidator


class BuildError(Exception):
    """Build process error."""

    pass


class AgentBuilder:
    """Builds agent packages into APKG files."""

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir).resolve()
        self.manifest: Optional[AgentManifest] = None

    def build(self, output_dir: Optional[Path] = None) -> Path:
        """
        Build the agent into an APKG file.

        Args:
            output_dir: Directory to output the APKG file (default: current directory)

        Returns:
            Path to the created APKG file
        """
        # Validate first
        validator = AgentValidator(self.project_dir)
        is_valid, errors, _ = validator.validate()

        if not is_valid:
            raise BuildError(f"Validation failed: {', '.join(errors)}")

        # Load manifest
        self._load_manifest()

        # Determine output path
        if output_dir is None:
            output_dir = Path.cwd()
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        # Create APKG filename
        if not self.manifest:
            raise BuildError("Manifest not loaded")
        version = self.manifest.metadata.version
        apkg_filename = f"{self.manifest.name}-{version}.apkg"
        output_path = output_dir / apkg_filename

        # Build the package
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Copy files to temp directory
            self._copy_agent_files(temp_path)

            # Create metadata
            self._create_metadata(temp_path)

            # Create requirements.txt if needed
            self._create_requirements(temp_path)

            # Create dist/ layout for surfaces
            self._create_dist_layout(temp_path)

            # Create deploy.json hand-off metadata
            self._create_deploy_metadata(temp_path)

            # Create the APKG archive
            self._create_apkg(temp_path, output_path)

        return output_path

    def _load_manifest(self):
        """Load and parse agent.yaml."""
        manifest_path = self.project_dir / "agent.yaml"

        with open(manifest_path, "r") as f:
            data = yaml.safe_load(f)

        self.manifest = AgentManifest(**data)

    def _copy_agent_files(self, dest_dir: Path):
        """Copy agent files to the build directory."""
        # Files and directories to include
        include_items = ["src", "agent.yaml"]

        # Optional files
        optional_items = ["requirements.txt", "README.md", "LICENSE"]

        # MCP config if specified
        if self.manifest and self.manifest.mcp and self.manifest.mcp.config_file:
            optional_items.append(self.manifest.mcp.config_file)

        # Copy required items
        for item in include_items:
            src_path = self.project_dir / item
            dest_path = dest_dir / item

            print(f"Copying {item}: {src_path} -> {dest_path}")
            if src_path.is_dir():
                shutil.copytree(
                    src_path, dest_path, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
                )
                # List files in the copied directory for debugging
                for root, dirs, files in os.walk(dest_path):
                    for file in files:
                        file_path = Path(root) / file
                        print(f"  Included: {file_path.relative_to(dest_dir)}")
            else:
                shutil.copy2(src_path, dest_path)
                print(f"  Included: {dest_path.relative_to(dest_dir)}")

        # Copy optional items if they exist
        for item in optional_items:
            src_path = self.project_dir / item
            if src_path.exists():
                dest_path = dest_dir / item
                if src_path.is_dir():
                    shutil.copytree(
                        src_path, dest_path, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
                    )
                else:
                    shutil.copy2(src_path, dest_path)

    def _create_metadata(self, build_dir: Path):
        """Create package metadata files."""
        metadata_dir = build_dir / ".pixell"
        metadata_dir.mkdir(exist_ok=True)

        # Create package metadata
        if not self.manifest:
            raise BuildError("Manifest not loaded")
        package_meta = {
            "format_version": "1.0",
            "created_by": "pixell-kit",
            "created_at": self._get_timestamp(),
            "manifest": self.manifest.model_dump(),
        }

        with open(metadata_dir / "package.json", "w") as f:
            json.dump(package_meta, f, indent=2)

    def _create_requirements(self, build_dir: Path):
        """Create requirements.txt from manifest if not present."""
        req_path = build_dir / "requirements.txt"

        if not req_path.exists() and self.manifest and self.manifest.dependencies:
            with open(req_path, "w") as f:
                for dep in self.manifest.dependencies:
                    f.write(f"{dep}\n")

    def _create_dist_layout(self, build_dir: Path):
        """Create /dist directory with surfaces assets according to PRD."""
        if not self.manifest:
            raise BuildError("Manifest not loaded")

        dist_dir = build_dir / "dist"
        dist_dir.mkdir(exist_ok=True)

        # A2A: copy server implementation into dist/a2a/
        if getattr(self.manifest, "a2a", None) and self.manifest.a2a:
            module_path, _func = self.manifest.a2a.service.split(":", 1)
            src_file = self.project_dir / (module_path.replace(".", "/") + ".py")
            a2a_dir = dist_dir / "a2a"
            a2a_dir.mkdir(exist_ok=True)
            if src_file.exists():
                shutil.copy2(src_file, a2a_dir / src_file.name)

        # REST: copy entry module into dist/rest/
        if getattr(self.manifest, "rest", None) and self.manifest.rest:
            module_path, _func = self.manifest.rest.entry.split(":", 1)
            src_file = self.project_dir / (module_path.replace(".", "/") + ".py")
            rest_dir = dist_dir / "rest"
            rest_dir.mkdir(exist_ok=True)
            if src_file.exists():
                shutil.copy2(src_file, rest_dir / src_file.name)

        # UI: copy static directory to dist/ui/
        if getattr(self.manifest, "ui", None) and self.manifest.ui and self.manifest.ui.path:
            ui_src = self.project_dir / self.manifest.ui.path
            ui_dest = dist_dir / "ui"
            if ui_src.exists() and ui_src.is_dir():
                if ui_dest.exists():
                    shutil.rmtree(ui_dest)
                shutil.copytree(ui_src, ui_dest)

    def _create_deploy_metadata(self, build_dir: Path):
        """Emit deploy.json with exposed surfaces and ports."""
        if not self.manifest:
            raise BuildError("Manifest not loaded")

        expose = []
        ports = {}

        if getattr(self.manifest, "rest", None) and self.manifest.rest:
            expose.append("rest")
            ports["rest"] = 8080
        if getattr(self.manifest, "a2a", None) and self.manifest.a2a:
            expose.append("a2a")
            ports["a2a"] = 50051
        if getattr(self.manifest, "ui", None) and self.manifest.ui:
            expose.append("ui")
            ports["ui"] = 3000

        deploy = {
            "expose": expose,
            "ports": ports,
            "multiplex": True,
        }

        with open(build_dir / "deploy.json", "w") as f:
            json.dump(deploy, f, indent=2)

    def _create_apkg(self, source_dir: Path, output_path: Path):
        """Create the APKG ZIP archive."""
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(source_dir):
                # Skip __pycache__ directories
                dirs[:] = [d for d in dirs if d != "__pycache__"]

                # Add empty directories
                for dir_name in dirs:
                    dir_path = Path(root) / dir_name
                    arcname = dir_path.relative_to(source_dir)
                    # Create empty directory entry
                    zf.writestr(str(arcname) + "/", "")

                for file in files:
                    # Skip .pyc files
                    if file.endswith(".pyc"):
                        continue

                    file_path = Path(root) / file
                    arcname = file_path.relative_to(source_dir)
                    zf.write(file_path, arcname)

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime

        return datetime.utcnow().isoformat() + "Z"
