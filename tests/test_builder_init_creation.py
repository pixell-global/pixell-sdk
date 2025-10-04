"""Tests for auto-creation of __init__.py and setup.py generation."""

import tempfile
from pathlib import Path
import yaml

from pixell.core.builder import AgentBuilder


def _write_minimal_agent(project_dir: Path, name: str = "init-test-agent") -> None:
    manifest_data = {
        "version": "1.0",
        "name": name,
        "display_name": "Init Test Agent",
        "description": "Test",
        "author": "Test",
        "license": "MIT",
        "runtime": "python3.11",
        "metadata": {"version": "1.0.0"},
        # No surfaces; use entrypoint to satisfy validation
        "entrypoint": "src.main:handler",
    }
    (project_dir / "src").mkdir(parents=True, exist_ok=True)
    (project_dir / "src" / "main.py").write_text(
        """
def handler(context):
    return {"status": "ok"}
"""
    )
    (project_dir / ".env").write_text("API_KEY=test\n")
    with open(project_dir / "agent.yaml", "w") as f:
        yaml.dump(manifest_data, f)


def test_auto_creates_init_files_for_discovered_packages():
    with tempfile.TemporaryDirectory() as temp_dir:
        project_dir = Path(temp_dir) / "agent"
        project_dir.mkdir()

        _write_minimal_agent(project_dir)

        # Create additional package-like dirs without __init__.py
        (project_dir / "core").mkdir()
        (project_dir / "core" / "langchain_util.py").write_text("# util\n")
        (project_dir / "app").mkdir()
        (project_dir / "app" / "v1").mkdir(parents=True)
        (project_dir / "app" / "v1" / "svc.py").write_text("# svc\n")

        builder = AgentBuilder(project_dir)
        apkg_path = builder.build()
        assert apkg_path.exists()

        # After build, check the temp build directory contents by extracting APKG
        extract_dir = Path(temp_dir) / "extract"
        extract_dir.mkdir()

        import zipfile

        with zipfile.ZipFile(apkg_path, "r") as zf:
            zf.extractall(extract_dir)

        # __init__.py should have been created for both 'core' and 'app' paths
        assert (extract_dir / "core" / "__init__.py").exists()
        assert (extract_dir / "app" / "__init__.py").exists()
        # Nested packages also should have __init__.py at least at package roots
        assert (extract_dir / "app" / "v1" / "__init__.py").exists()

        # setup.py should list explicit packages
        setup_content = (extract_dir / "setup.py").read_text()
        assert "packages=[" in setup_content


def test_namespace_packages_opt_out_skips_init_creation():
    with tempfile.TemporaryDirectory() as temp_dir:
        project_dir = Path(temp_dir) / "agent"
        project_dir.mkdir()

        _write_minimal_agent(project_dir, name="ns-agent")

        # Create namespaced directory tree
        (project_dir / "vendor").mkdir()
        (project_dir / "vendor" / "lib").mkdir(parents=True)
        (project_dir / "vendor" / "lib" / "util.py").write_text("# vendor util\n")

        # Declare namespace_packages in pak.yaml
        (project_dir / "pak.yaml").write_text("namespace_packages:\n  - vendor\n")

        builder = AgentBuilder(project_dir)
        apkg_path = builder.build()
        assert apkg_path.exists()

        # Extract and check that __init__.py was NOT created under vendor/*
        extract_dir = Path(temp_dir) / "extract_ns"
        extract_dir.mkdir()
        import zipfile

        with zipfile.ZipFile(apkg_path, "r") as zf:
            zf.extractall(extract_dir)

        assert not (extract_dir / "vendor" / "__init__.py").exists()
        assert not (extract_dir / "vendor" / "lib" / "__init__.py").exists()
