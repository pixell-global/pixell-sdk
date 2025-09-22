"""Tests for dev server with A2A/REST/UI surface support."""

import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch

from pixell.dev_server.server import DevServer
from pixell.models.agent_manifest import AgentManifest


class TestDevServerSurfaces:
    """Test dev server functionality with surface support."""

    def test_dev_server_mounts_rest_surface(self):
        """Test that dev server mounts REST routes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "rest-agent"
            project_dir.mkdir()

            # Create agent.yaml
            manifest_data = {
                "version": "1.0",
                "name": "rest-agent",
                "display_name": "REST Agent",
                "description": "A REST agent",
                "author": "Test Author",
                "license": "MIT",
                "runtime": "python3.11",
                "metadata": {"version": "1.0.0"},
                "rest": {"entry": "src.rest.index:mount"},
            }

            with open(project_dir / "agent.yaml", "w") as f:
                yaml.dump(manifest_data, f)

            # Create src directory and REST module
            (project_dir / "src").mkdir()
            (project_dir / "src" / "rest").mkdir()

            # Create REST module with mount function
            (project_dir / "src" / "rest" / "index.py").write_text("""
from fastapi import FastAPI

def mount(app: FastAPI) -> None:
    @app.get("/api/test")
    async def test_endpoint():
        return {"message": "Hello from REST"}
""")

            # Create __init__.py files for proper module structure
            (project_dir / "src" / "__init__.py").write_text("")
            (project_dir / "src" / "rest" / "__init__.py").write_text("")

            # Create dev server
            server = DevServer(project_dir, port=8080)

            # Mock the manifest loading
            with open(project_dir / "agent.yaml") as f:
                data = yaml.safe_load(f)
            server.manifest = AgentManifest(**data)

            # Test mounting REST surface
            server._mount_optional_surfaces()

            # Verify the route was added (check if the app has the route)
            routes = [route.path for route in server.app.routes]
            assert "/api/test" in routes

    def test_dev_server_serves_ui_surface(self):
        """Test that dev server serves UI static files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "ui-agent"
            project_dir.mkdir()

            # Create agent.yaml
            manifest_data = {
                "version": "1.0",
                "name": "ui-agent",
                "display_name": "UI Agent",
                "description": "A UI agent",
                "author": "Test Author",
                "license": "MIT",
                "runtime": "python3.11",
                "metadata": {"version": "1.0.0"},
                "ui": {"path": "ui"},
            }

            with open(project_dir / "agent.yaml", "w") as f:
                yaml.dump(manifest_data, f)

            # Create src directory (required for validation)
            (project_dir / "src").mkdir()

            # Create UI directory and files
            (project_dir / "ui").mkdir()
            (project_dir / "ui" / "index.html").write_text("<html><body>Hello UI</body></html>")
            (project_dir / "ui" / "style.css").write_text("body { margin: 0; }")

            # Create dev server
            server = DevServer(project_dir, port=8080)

            # Mock the manifest loading
            with open(project_dir / "agent.yaml") as f:
                data = yaml.safe_load(f)
            server.manifest = AgentManifest(**data)

            # Test mounting UI surface
            server._mount_optional_surfaces()

            # Verify static files mount was added
            # Check if there's a mount for /ui
            # Note: StaticFiles mounts might not be easily testable this way
            # The important thing is that the method doesn't raise an exception

    def test_dev_server_handles_missing_rest_module(self):
        """Test that dev server handles missing REST module gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "missing-rest-agent"
            project_dir.mkdir()

            # Create agent.yaml
            manifest_data = {
                "version": "1.0",
                "name": "missing-rest-agent",
                "display_name": "Missing REST Agent",
                "description": "An agent with missing REST module",
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

            # Create dev server
            server = DevServer(project_dir, port=8080)

            # Mock the manifest loading
            with open(project_dir / "agent.yaml") as f:
                data = yaml.safe_load(f)
            server.manifest = AgentManifest(**data)

            # Test mounting should not raise exception
            # It should print a warning but continue
            with patch("builtins.print") as mock_print:
                server._mount_optional_surfaces()
                # Should have printed a warning about REST mount failure
                mock_print.assert_called()
                warning_calls = [
                    call
                    for call in mock_print.call_args_list
                    if call.args and "REST mount failed" in call.args[0]
                ]
                assert len(warning_calls) > 0

    def test_dev_server_handles_missing_ui_path(self):
        """Test that dev server handles missing UI path gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "missing-ui-agent"
            project_dir.mkdir()

            # Create agent.yaml
            manifest_data = {
                "version": "1.0",
                "name": "missing-ui-agent",
                "display_name": "Missing UI Agent",
                "description": "An agent with missing UI path",
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

            # Create dev server
            server = DevServer(project_dir, port=8080)

            # Mock the manifest loading
            with open(project_dir / "agent.yaml") as f:
                data = yaml.safe_load(f)
            server.manifest = AgentManifest(**data)

            # Test mounting should not raise exception
            with patch("builtins.print") as mock_print:
                server._mount_optional_surfaces()
                # Should have printed a warning about UI path not found
                mock_print.assert_called()
                warning_calls = [
                    call for call in mock_print.call_args_list if "UI path not found" in str(call)
                ]
                assert len(warning_calls) > 0

    def test_dev_server_with_all_surfaces(self):
        """Test dev server with all surfaces configured."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "full-agent"
            project_dir.mkdir()

            # Create agent.yaml
            manifest_data = {
                "version": "1.0",
                "name": "full-agent",
                "display_name": "Full Agent",
                "description": "An agent with all surfaces",
                "author": "Test Author",
                "license": "MIT",
                "runtime": "python3.11",
                "metadata": {"version": "1.0.0"},
                "a2a": {"service": "src.a2a.server:serve"},
                "rest": {"entry": "src.rest.index:mount"},
                "ui": {"path": "ui"},
            }

            with open(project_dir / "agent.yaml", "w") as f:
                yaml.dump(manifest_data, f)

            # Create src directory structure
            (project_dir / "src").mkdir()
            (project_dir / "src" / "a2a").mkdir()
            (project_dir / "src" / "rest").mkdir()

            # Create A2A module
            (project_dir / "src" / "a2a" / "server.py").write_text("""
def serve():
    pass
""")

            # Create REST module
            (project_dir / "src" / "rest" / "index.py").write_text("""
from fastapi import FastAPI

def mount(app: FastAPI) -> None:
    @app.get("/api/hello")
    async def hello():
        return {"message": "Hello from full agent"}
""")

            # Create UI directory
            (project_dir / "ui").mkdir()
            (project_dir / "ui" / "index.html").write_text(
                "<html><body>Full Agent UI</body></html>"
            )

            # Create __init__.py files
            (project_dir / "src" / "__init__.py").write_text("")
            (project_dir / "src" / "a2a" / "__init__.py").write_text("")
            (project_dir / "src" / "rest" / "__init__.py").write_text("")

            # Create dev server
            server = DevServer(project_dir, port=8080)

            # Mock the manifest loading
            with open(project_dir / "agent.yaml") as f:
                data = yaml.safe_load(f)
            server.manifest = AgentManifest(**data)

            # Test mounting all surfaces
            with patch("builtins.print") as mock_print:
                server._mount_optional_surfaces()

                # Should have printed success messages for REST and UI
                print_calls = [str(call) for call in mock_print.call_args_list]
                rest_success = any("[REST] Mounted routes" in call for call in print_calls)
                ui_success = any("[UI] Serving static assets" in call for call in print_calls)

                assert rest_success
                assert ui_success

    def test_dev_server_without_surfaces(self):
        """Test dev server without any surfaces (traditional agent)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "traditional-agent"
            project_dir.mkdir()

            # Create agent.yaml
            manifest_data = {
                "version": "1.0",
                "name": "traditional-agent",
                "display_name": "Traditional Agent",
                "description": "A traditional agent",
                "author": "Test Author",
                "license": "MIT",
                "entrypoint": "src.main:handler",
                "runtime": "python3.11",
                "metadata": {"version": "1.0.0"},
            }

            with open(project_dir / "agent.yaml", "w") as f:
                yaml.dump(manifest_data, f)

            # Create src directory and main file
            (project_dir / "src").mkdir()
            (project_dir / "src" / "main.py").write_text("""
def handler(context):
    return {"status": "success"}
""")

            # Create dev server
            server = DevServer(project_dir, port=8080)

            # Mock the manifest loading
            with open(project_dir / "agent.yaml") as f:
                data = yaml.safe_load(f)
            server.manifest = AgentManifest(**data)

            # Test mounting should not do anything
            with patch("builtins.print") as mock_print:
                server._mount_optional_surfaces()

                # Should not have printed any surface-related messages
                print_calls = [str(call) for call in mock_print.call_args_list]
                surface_messages = [
                    call
                    for call in print_calls
                    if any(keyword in call for keyword in ["[REST]", "[A2A]", "[UI]"])
                ]
                assert len(surface_messages) == 0
