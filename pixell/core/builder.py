"""Agent package builder functionality."""

import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Optional, List
import yaml
import json
import logging

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
        self._logger = logging.getLogger(__name__)

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

            # Copy pre-built frontend if configured
            self._copy_frontend_assets(temp_path)

            # Create metadata
            self._create_metadata(temp_path)

            # Create requirements.txt if needed
            self._create_requirements(temp_path)

            # Create setup.py for package installation
            self._create_package_metadata(temp_path)

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
        # Required files and directories
        include_items = ["agent.yaml", ".env"]

        # Optional files and directories (common Python project structures)
        optional_items = [
            "src",  # src/ directory is now optional
            "README.md",
            "LICENSE",
            "core",
            "app",
            "setup.py",
            "pak.yaml",
            "agents_config.json",  # Multi-agent coordination config
        ]

        # MCP config if specified
        if self.manifest and self.manifest.mcp and self.manifest.mcp.config_file:
            optional_items.append(self.manifest.mcp.config_file)

        # Check for pyproject.toml (uv dependency management)
        # If pyproject.toml exists, use it and skip requirements.txt
        pyproject_toml = self.project_dir / "pyproject.toml"
        requirements_txt = self.project_dir / "requirements.txt"
        
        if pyproject_toml.exists():
            optional_items.append("pyproject.toml")
            print(f"[INFO] pyproject.toml found - will use it instead of requirements.txt")
        elif requirements_txt.exists():
            optional_items.append("requirements.txt")

        # Copy required items
        for item in include_items:
            src_path = self.project_dir / item
            dest_path = dest_dir / item

            if not src_path.exists():
                continue
            
            # Special handling for agent.yaml: remove None values (especially entrypoint when optional)
            if item == "agent.yaml" and self.manifest:
                print(f"Copying {item} (with None values excluded): {src_path} -> {dest_path}")
                # Dump manifest excluding None values to match server validation expectations
                manifest_dict = self.manifest.model_dump(exclude_none=True)
                with open(dest_path, "w", encoding="utf-8") as f:
                    yaml.dump(manifest_dict, f, default_flow_style=False, sort_keys=False)
                print(f"  Included: {dest_path.relative_to(dest_dir)}")
            else:
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

    def _copy_frontend_assets(self, build_dir: Path):
        """Copy pre-built frontend assets if configured."""
        if not self.manifest or not getattr(self.manifest, "ui", None):
            return
        
        ui_config = self.manifest.ui
        if not ui_config or not ui_config.path:
            return
        
        # UI 소스 디렉토리 찾기 (agent.yaml에서 지정된 경로만 사용)
        if not ui_config.path:
            print(f"[WARN] UI path not specified in agent.yaml")
            return
        
        ui_source_dir = self.project_dir / ui_config.path
        if not ui_source_dir.exists() or not ui_source_dir.is_dir():
            print(f"[ERROR] Specified UI path not found: {ui_config.path}")
            print(f"[INFO] Please ensure the path exists and contains built frontend files")
            return
        
        print(f"[INFO] Using UI path: {ui_config.path}")
        
        # 빌드 결과물을 APKG에 복사 (원본 경로 구조 유지)
        try:
            # agent.yaml에서 지정한 경로 구조를 그대로 유지
            ui_dest = build_dir / ui_config.path
            ui_dest.parent.mkdir(parents=True, exist_ok=True)
            
            if ui_dest.exists():
                shutil.rmtree(ui_dest)
            shutil.copytree(ui_source_dir, ui_dest)
            print(f"[SUCCESS] Copied frontend to APKG at {ui_config.path}")
            
        except Exception as e:
            print(f"[ERROR] Failed to copy frontend: {e}")

    def _create_metadata(self, build_dir: Path):
        """Create package metadata files."""
        metadata_dir = build_dir / ".pixell"
        metadata_dir.mkdir(exist_ok=True)

        # Create package metadata
        if not self.manifest:
            raise BuildError("Manifest not loaded")
        
        # Dump manifest, excluding None values (especially entrypoint when optional)
        manifest_dict = self.manifest.model_dump(exclude_none=True)
        
        package_meta = {
            "format_version": "1.0",
            "created_by": "pixell-kit",
            "created_at": self._get_timestamp(),
            "manifest": manifest_dict,
        }

        with open(metadata_dir / "package.json", "w") as f:
            json.dump(package_meta, f, indent=2)

    def _create_requirements(self, build_dir: Path):
        """Create requirements.txt from manifest if not present and pyproject.toml doesn't exist."""
        # Skip if pyproject.toml exists (uv dependency management takes priority)
        pyproject_toml = build_dir / "pyproject.toml"
        if pyproject_toml.exists():
            print("[INFO] pyproject.toml found - skipping requirements.txt generation")
            return
        
        req_path = build_dir / "requirements.txt"

        if not req_path.exists() and self.manifest and self.manifest.dependencies:
            with open(req_path, "w") as f:
                for dep in self.manifest.dependencies:
                    f.write(f"{dep}\n")

    def _discover_packages(self, build_dir: Path) -> List[str]:
        """Discover all Python packages in the build directory.

        Returns:
            List of package names (e.g., ['src', 'core', 'app', 'app.v1'])
        """
        packages: List[str] = []

        # Directories to skip entirely during discovery
        skip_dir_names = {"__pycache__", "dist", ".pixell", ".git", ".hg", ".svn"}

        # Walk through build directory
        for root, dirs, files in os.walk(build_dir):
            # Skip hidden directories, __pycache__, dist, and internal metadata dirs
            dirs[:] = [d for d in dirs if d not in skip_dir_names and not d.startswith(".")]

            # Check if this directory contains Python files
            has_python = any(f.endswith(".py") for f in files)

            if has_python:
                # Calculate package name relative to build_dir
                rel_path = Path(root).relative_to(build_dir)
                package_name = str(rel_path).replace(os.sep, ".")

                # Skip if it's just build_dir itself
                if package_name != ".":
                    packages.append(package_name)

        # Sort for consistency
        packages.sort()
        return packages

    def _parse_requirements(self, req_file: Path) -> List[str]:
        """Parse requirements.txt and return list of dependency specifications.

        Args:
            req_file: Path to requirements.txt

        Returns:
            List of dependency strings suitable for install_requires
        """
        if not req_file.exists():
            return []

        requirements: List[str] = []

        try:
            with open(req_file, "r") as f:
                for line in f:
                    line = line.strip()

                    # Skip empty lines and comments
                    if not line or line.startswith("#"):
                        continue

                    # Skip editable installs (-e .)
                    if line.startswith("-e") or line.startswith("--editable"):
                        self._logger.warning(f"Skipping editable requirement: {line}")
                        continue

                    # Skip index URLs and other pip options
                    if line.startswith("-") or line.startswith("--"):
                        continue

                    # Handle inline comments
                    if "#" in line:
                        line = line.split("#")[0].strip()

                    if line:
                        requirements.append(line)

            self._logger.info(f"Parsed {len(requirements)} dependencies from requirements.txt")
            return requirements

        except Exception as e:
            self._logger.error(f"Failed to parse requirements.txt: {e}")
            return []

    def _generate_setup_py(self, packages: list, install_requires: List[str] | None = None) -> str:
        """Generate setup.py content from template.

        Args:
            packages: List of package names to include
            install_requires: List of dependency specifications (optional)

        Returns:
            setup.py file content as string
        """
        if not self.manifest:
            raise BuildError("Manifest not loaded")

        # Ensure we have at least 'src' package
        if not packages:
            packages = ["src"]

        # Format packages list as Python list literal
        packages_str = "[\n"
        for pkg in packages:
            packages_str += f"        '{pkg}',\n"
        packages_str += "    ]"

        # Format install_requires list
        if install_requires:
            install_requires_str = "[\n"
            for req in install_requires:
                req_escaped = req.replace('"', '\\"')
                install_requires_str += f"        '{req_escaped}',\n"
            install_requires_str += "    ]"
            install_requires_comment = (
                f"  # Populated from requirements.txt ({len(install_requires)} dependencies)"
            )
        else:
            install_requires_str = "[]"
            install_requires_comment = "  # No dependencies specified"

        # Generate setup.py content
        setup_content = f'''#!/usr/bin/env python3
"""
Auto-generated setup.py for agent package installation.
Generated by Pixell Agent Kit (PAK) during build.

Discovered packages: {", ".join(packages) if packages else "none"}
Dependencies: {len(install_requires) if install_requires else 0} from requirements.txt
"""

from setuptools import setup

setup(
    name="{self.manifest.name}",
    version="{self.manifest.metadata.version}",
    description="{self.manifest.description or "Agent package"}",
    packages={packages_str},
    package_dir={{"": "."}},
    install_requires={install_requires_str},{install_requires_comment}
    python_requires=">=3.9",
    include_package_data=True,
)
'''
        return setup_content

    def _create_package_metadata(self, build_dir: Path):
        """Generate setup.py for agent package installation."""
        # Discover packages (always) and ensure package structure
        setup_file = build_dir / "setup.py"
        packages = self._discover_packages(build_dir)

        if not packages:
            packages = ["src"]  # Fallback to src directory
            print("Warning: No packages discovered, defaulting to 'src'")

        print(f"Discovered packages: {', '.join(packages)}")

        # Load optional PAK config for namespace_packages opt-out
        config = self._load_pak_config()
        namespace_packages = set(
            config.get("namespace_packages", []) if isinstance(config, dict) else []
        )
        generate_install_requires = (
            bool(config.get("generate_install_requires", False))
            if isinstance(config, dict)
            else False
        )

        # Ensure package structure by creating missing __init__.py files
        created_inits = self._ensure_package_structure(build_dir, packages, namespace_packages)
        if created_inits:
            print(
                "\u26a0\ufe0f  Created missing __init__.py files for: " + ", ".join(created_inits)
            )
            print("   Consider adding these files to your repository for proper packaging.")

        # If user provided setup.py, skip generation but we already ensured structure
        if setup_file.exists():
            print("Agent already has setup.py, skipping generation")
            return

        # Optionally parse requirements.txt and include in setup.py
        install_requires: List[str] | None = None
        if generate_install_requires:
            req_file = build_dir / "requirements.txt"
            if req_file.exists():
                install_requires = self._parse_requirements(req_file)
                print(f"Parsed {len(install_requires)} dependencies from requirements.txt")
            else:
                print("Warning: generate_install_requires enabled but no requirements.txt found")

        # Generate setup.py content
        setup_content = self._generate_setup_py(packages, install_requires)

        # Write setup.py
        setup_file.write_text(setup_content)
        if install_requires:
            print(f"Generated setup.py with {len(install_requires)} dependencies")
        else:
            print("Generated setup.py for package installation")

    def _load_pak_config(self) -> dict:
        """Load optional PAK build configuration from pak.yaml in the project root.

        Returns an empty dict if the file doesn't exist or can't be parsed.
        """
        try:
            config_path = self.project_dir / "pak.yaml"
            if config_path.exists():
                with open(config_path, "r") as f:
                    data = yaml.safe_load(f) or {}
                    if isinstance(data, dict):
                        return data
        except Exception as e:
            print(f"Warning: Failed to load pak.yaml: {e}")
        return {}

    def _ensure_package_structure(
        self, build_dir: Path, packages: List[str], namespace_packages: set
    ) -> List[str]:
        """Ensure all discovered packages have an __init__.py, unless opted out.

        Args:
            build_dir: Temporary build directory path
            packages: List of discovered package names
            namespace_packages: Set of package names to treat as PEP 420 namespaces (skip)

        Returns:
            List of package names for which __init__.py was created
        """
        created: List[str] = []

        def is_namespaced(pkg: str) -> bool:
            # Skip if the package equals or is under any declared namespace
            for ns in namespace_packages:
                if pkg == ns or pkg.startswith(ns + "."):
                    return True
            return False

        # For each discovered package, also ensure its ancestor packages have __init__.py
        all_to_check: set[str] = set()
        for pkg in packages:
            parts = pkg.split(".") if pkg else []
            for i in range(1, len(parts) + 1):
                ancestor = ".".join(parts[:i])
                all_to_check.add(ancestor)

        for pkg in sorted(all_to_check):
            if not pkg or is_namespaced(pkg):
                continue

            pkg_path = build_dir / pkg.replace(".", "/")
            init_file = pkg_path / "__init__.py"
            try:
                if pkg_path.is_dir() and not init_file.exists():
                    init_file.write_text('"""Auto-generated by Pixell Agent Kit during build."""\n')
                    created.append(pkg)
            except Exception as e:
                print(f"Warning: Failed to create {init_file}: {e}")

        return created

    def _create_dist_layout(self, build_dir: Path):
        """Copy surface files directly to APKG root (no dist/ folder)."""
        if not self.manifest:
            raise BuildError("Manifest not loaded")

        # A2A: copy entry file directly to APKG root
        if getattr(self.manifest, "a2a", None) and self.manifest.a2a and getattr(
            self.manifest.a2a, "entry", None
        ):
            module_path, _func = self.manifest.a2a.entry.split(":", 1)
            src_file = self.project_dir / (module_path.replace(".", "/") + ".py")
            if src_file.exists():
                dest_file = build_dir / src_file.name
                shutil.copy2(src_file, dest_file)
                print(f"[A2A] Copied {src_file.name} to APKG root")

        # REST: copy entry file directly to APKG root
        if getattr(self.manifest, "rest", None) and self.manifest.rest:
            rest_entry = self.manifest.rest.entry
            # If rest.entry doesn't have ':', use entrypoint's module
            if ":" not in rest_entry:
                if self.manifest.entrypoint and ":" in self.manifest.entrypoint:
                    module_path, _ = self.manifest.entrypoint.split(":", 1)
                else:
                    # Skip if no entrypoint to derive module from
                    print(f"[WARN] REST entry '{rest_entry}' is not in 'module:function' format and no entrypoint available")
                    return
            else:
                module_path, _func = rest_entry.split(":", 1)
            
            src_file = self.project_dir / (module_path.replace(".", "/") + ".py")
            if src_file.exists():
                dest_file = build_dir / src_file.name
                shutil.copy2(src_file, dest_file)
                print(f"[REST] Copied {src_file.name} to APKG root")

        # UI: copy UI assets with original path structure to APKG root
        if getattr(self.manifest, "ui", None) and self.manifest.ui and self.manifest.ui.path:
            ui_src = self.project_dir / self.manifest.ui.path
            if ui_src.exists() and ui_src.is_dir():
                # Preserve original path structure (e.g., "client/dist" -> "client/dist" in APKG)
                ui_dest = build_dir / self.manifest.ui.path
                ui_dest.parent.mkdir(parents=True, exist_ok=True)
                if ui_dest.exists():
                    shutil.rmtree(ui_dest)
                shutil.copytree(ui_src, ui_dest)
                print(f"[UI] Copied UI assets to {self.manifest.ui.path} in APKG root")

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
            "environment": self.manifest.environment,
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
