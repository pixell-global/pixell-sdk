"""Tests for surface validation in AgentValidator."""

import tempfile
import yaml
from pathlib import Path

from pixell.core.validator import AgentValidator


class TestValidatorSurfaces:
    """Test surface validation in AgentValidator."""

    def test_validate_rest_surface_success(self):
        """Test successful REST surface validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Create agent.yaml
            manifest_data = {
                "version": "1.0",
                "name": "test-agent",
                "display_name": "Test Agent",
                "description": "A test agent",
                "author": "Test Author",
                "license": "MIT",
                "runtime": "python3.11",
                "metadata": {"version": "1.0.0"},
                "rest": {"entry": "src.rest.index:mount"},
            }

            with open(project_dir / "agent.yaml", "w") as f:
                yaml.dump(manifest_data, f)

            # Create src directory and REST module
            (project_dir / "src" / "rest").mkdir(parents=True)
            (project_dir / "src" / "rest" / "index.py").write_text("""
def mount(app):
    pass
""")

            # Required .env
            (project_dir / ".env").write_text("API_KEY=placeholder\n")
            validator = AgentValidator(project_dir)
            is_valid, errors, warnings = validator.validate()

            assert is_valid
            assert len(errors) == 0

    def test_validate_rest_surface_missing_module(self):
        """Test REST surface validation with missing module."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Create agent.yaml
            manifest_data = {
                "version": "1.0",
                "name": "test-agent",
                "display_name": "Test Agent",
                "description": "A test agent",
                "author": "Test Author",
                "license": "MIT",
                "runtime": "python3.11",
                "metadata": {"version": "1.0.0"},
                "rest": {"entry": "src.rest.index:mount"},
            }

            with open(project_dir / "agent.yaml", "w") as f:
                yaml.dump(manifest_data, f)

            # Create src directory but no REST module
            (project_dir / "src").mkdir()

            # Required .env
            (project_dir / ".env").write_text("API_KEY=placeholder\n")
            validator = AgentValidator(project_dir)
            is_valid, errors, warnings = validator.validate()

            assert not is_valid
            assert any("REST entry module not found" in error for error in errors)

    def test_validate_rest_surface_missing_function(self):
        """Test REST surface validation with missing function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Create agent.yaml
            manifest_data = {
                "version": "1.0",
                "name": "test-agent",
                "display_name": "Test Agent",
                "description": "A test agent",
                "author": "Test Author",
                "license": "MIT",
                "runtime": "python3.11",
                "metadata": {"version": "1.0.0"},
                "rest": {"entry": "src.rest.index:mount"},
            }

            with open(project_dir / "agent.yaml", "w") as f:
                yaml.dump(manifest_data, f)

            # Create src directory and REST module without the function
            (project_dir / "src" / "rest").mkdir(parents=True)
            (project_dir / "src" / "rest" / "index.py").write_text("""
def other_function():
    pass
""")

            # Required .env
            (project_dir / ".env").write_text("API_KEY=placeholder\n")
            validator = AgentValidator(project_dir)
            is_valid, errors, warnings = validator.validate()

            assert is_valid  # Should be valid but with warning
            assert any("REST entry function 'mount' not found" in warning for warning in warnings)

    def test_validate_a2a_surface_success(self):
        """Test successful A2A surface validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Create agent.yaml
            manifest_data = {
                "version": "1.0",
                "name": "test-agent",
                "display_name": "Test Agent",
                "description": "A test agent",
                "author": "Test Author",
                "license": "MIT",
                "runtime": "python3.11",
                "metadata": {"version": "1.0.0"},
                "a2a": {"service": "src.a2a.server:serve"},
            }

            with open(project_dir / "agent.yaml", "w") as f:
                yaml.dump(manifest_data, f)

            # Create src directory and A2A module
            (project_dir / "src" / "a2a").mkdir(parents=True)
            (project_dir / "src" / "a2a" / "server.py").write_text("""
def serve():
    pass
""")

            # Required .env
            (project_dir / ".env").write_text("API_KEY=placeholder\n")
            validator = AgentValidator(project_dir)
            is_valid, errors, warnings = validator.validate()

            assert is_valid
            assert len(errors) == 0

    def test_validate_a2a_surface_missing_module(self):
        """Test A2A surface validation with missing module."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Create agent.yaml
            manifest_data = {
                "version": "1.0",
                "name": "test-agent",
                "display_name": "Test Agent",
                "description": "A test agent",
                "author": "Test Author",
                "license": "MIT",
                "runtime": "python3.11",
                "metadata": {"version": "1.0.0"},
                "a2a": {"service": "src.a2a.server:serve"},
            }

            with open(project_dir / "agent.yaml", "w") as f:
                yaml.dump(manifest_data, f)

            # Create src directory but no A2A module
            (project_dir / "src").mkdir()

            # Required .env
            (project_dir / ".env").write_text("API_KEY=placeholder\n")
            validator = AgentValidator(project_dir)
            is_valid, errors, warnings = validator.validate()

            assert not is_valid
            assert any("A2A service module not found" in error for error in errors)

    def test_validate_ui_surface_success(self):
        """Test successful UI surface validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Create agent.yaml
            manifest_data = {
                "version": "1.0",
                "name": "test-agent",
                "display_name": "Test Agent",
                "description": "A test agent",
                "author": "Test Author",
                "license": "MIT",
                "runtime": "python3.11",
                "metadata": {"version": "1.0.0"},
                "ui": {"path": "ui"},
            }

            with open(project_dir / "agent.yaml", "w") as f:
                yaml.dump(manifest_data, f)

            # Create src directory and UI directory
            (project_dir / "src").mkdir()
            (project_dir / "ui").mkdir()
            (project_dir / "ui" / "index.html").write_text("<html></html>")

            # Required .env
            (project_dir / ".env").write_text("API_KEY=placeholder\n")
            validator = AgentValidator(project_dir)
            is_valid, errors, warnings = validator.validate()

            assert is_valid
            assert len(errors) == 0

    def test_validate_ui_surface_missing_path(self):
        """Test UI surface validation with missing path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Create agent.yaml
            manifest_data = {
                "version": "1.0",
                "name": "test-agent",
                "display_name": "Test Agent",
                "description": "A test agent",
                "author": "Test Author",
                "license": "MIT",
                "runtime": "python3.11",
                "metadata": {"version": "1.0.0"},
                "ui": {"path": "ui"},
            }

            with open(project_dir / "agent.yaml", "w") as f:
                yaml.dump(manifest_data, f)

            # Create src directory but no UI directory
            (project_dir / "src").mkdir()

            # Required .env
            (project_dir / ".env").write_text("API_KEY=placeholder\n")
            validator = AgentValidator(project_dir)
            is_valid, errors, warnings = validator.validate()

            assert not is_valid
            assert any("UI path not found" in error for error in errors)

    def test_validate_ui_surface_not_directory(self):
        """Test UI surface validation when path is not a directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Create agent.yaml
            manifest_data = {
                "version": "1.0",
                "name": "test-agent",
                "display_name": "Test Agent",
                "description": "A test agent",
                "author": "Test Author",
                "license": "MIT",
                "runtime": "python3.11",
                "metadata": {"version": "1.0.0"},
                "ui": {"path": "ui"},
            }

            with open(project_dir / "agent.yaml", "w") as f:
                yaml.dump(manifest_data, f)

            # Create src directory and UI as a file (not directory)
            (project_dir / "src").mkdir()
            (project_dir / "ui").write_text("not a directory")

            validator = AgentValidator(project_dir)
            is_valid, errors, warnings = validator.validate()

            assert not is_valid
            assert any("UI path is not a directory" in error for error in errors)

    def test_validate_optional_entrypoint_with_surfaces(self):
        """Test that entrypoint is optional when surfaces are configured."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Create agent.yaml without entrypoint but with REST
            manifest_data = {
                "version": "1.0",
                "name": "test-agent",
                "display_name": "Test Agent",
                "description": "A test agent",
                "author": "Test Author",
                "license": "MIT",
                "runtime": "python3.11",
                "metadata": {"version": "1.0.0"},
                "rest": {"entry": "src.rest.index:mount"},
            }

            with open(project_dir / "agent.yaml", "w") as f:
                yaml.dump(manifest_data, f)

            # Create src directory and REST module
            (project_dir / "src" / "rest").mkdir(parents=True)
            (project_dir / "src" / "rest" / "index.py").write_text("""
def mount(app):
    pass
""")

            # Required .env
            (project_dir / ".env").write_text("API_KEY=placeholder\n")
            validator = AgentValidator(project_dir)
            is_valid, errors, warnings = validator.validate()

            assert is_valid
            assert len(errors) == 0

    def test_validate_required_entrypoint_without_surfaces(self):
        """Test that entrypoint is required when no surfaces are configured."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Create agent.yaml without entrypoint and without surfaces
            manifest_data = {
                "version": "1.0",
                "name": "test-agent",
                "display_name": "Test Agent",
                "description": "A test agent",
                "author": "Test Author",
                "license": "MIT",
                "runtime": "python3.11",
                "metadata": {"version": "1.0.0"},
            }

            with open(project_dir / "agent.yaml", "w") as f:
                yaml.dump(manifest_data, f)

            # Create src directory
            (project_dir / "src").mkdir()

            validator = AgentValidator(project_dir)
            is_valid, errors, warnings = validator.validate()

            assert not is_valid
            assert any(
                "Entrypoint is required when no surfaces are configured" in error
                for error in errors
            )
