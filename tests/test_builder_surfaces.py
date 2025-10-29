"""Tests for builder with A2A/REST/UI surface support."""

import pytest
import tempfile
import json
import yaml
from pathlib import Path
import zipfile

from pixell.core.builder import AgentBuilder, BuildError


class TestBuilderSurfaces:
    """Test builder functionality with surface support."""

    def test_build_with_all_surfaces(self):
        """Test building an agent with all surfaces."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "test-agent"
            project_dir.mkdir()

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
                "rest": {"entry": "src.rest.index:mount"},
                "ui": {"path": "ui"},
            }

            with open(project_dir / "agent.yaml", "w") as f:
                yaml.dump(manifest_data, f)

            # Create src directory structure
            (project_dir / "src").mkdir()
            (project_dir / "src" / "a2a").mkdir()
            (project_dir / "src" / "rest").mkdir()

            # Create A2A server file
            (project_dir / "src" / "a2a" / "server.py").write_text("""
def serve():
    pass
""")

            # Create REST index file
            (project_dir / "src" / "rest" / "index.py").write_text("""
def mount(app):
    pass
""")

            # Create UI directory and files
            (project_dir / "ui").mkdir()
            (project_dir / "ui" / "index.html").write_text("<html></html>")
            (project_dir / "ui" / "style.css").write_text("body { margin: 0; }")

            # Build the package
            # Required .env
            (project_dir / ".env").write_text("API_KEY=placeholder\n")
            builder = AgentBuilder(project_dir)
            output_path = builder.build()

            assert output_path.exists()
            assert output_path.suffix == ".apkg"

            # Extract and verify contents
            with tempfile.TemporaryDirectory() as extract_dir:
                with zipfile.ZipFile(output_path, "r") as zf:
                    zf.extractall(extract_dir)

                extract_path = Path(extract_dir)

                # Check basic structure
                assert (extract_path / "agent.yaml").exists()
                assert (extract_path / "src").exists()

                # Check dist layout
                assert (extract_path / "dist").exists()
                assert (extract_path / "dist" / "a2a").exists()
                assert (extract_path / "dist" / "rest").exists()
                assert (extract_path / "dist" / "ui").exists()

                # Check A2A files in dist
                assert (extract_path / "dist" / "a2a" / "server.py").exists()

                # Check REST files in dist
                assert (extract_path / "dist" / "rest" / "index.py").exists()

                # Check UI files in dist
                assert (extract_path / "dist" / "ui" / "index.html").exists()
                assert (extract_path / "dist" / "ui" / "style.css").exists()

                # Check deploy.json
                deploy_json_path = extract_path / "deploy.json"
                assert deploy_json_path.exists()

                with open(deploy_json_path) as f:
                    deploy_data = json.load(f)

                assert "expose" in deploy_data
                assert "ports" in deploy_data
                assert "multiplex" in deploy_data
                assert deploy_data["expose"] == ["rest", "a2a", "ui"]
                assert deploy_data["ports"]["rest"] == 8080
                assert deploy_data["ports"]["a2a"] == 50051
                assert deploy_data["ports"]["ui"] == 3000
                assert deploy_data["multiplex"] is True

    def test_build_with_rest_only(self):
        """Test building an agent with only REST surface."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "rest-agent"
            project_dir.mkdir()

            # Create agent.yaml
            manifest_data = {
                "version": "1.0",
                "name": "rest-agent",
                "display_name": "REST Agent",
                "description": "A REST-only agent",
                "author": "Test Author",
                "license": "MIT",
                "runtime": "python3.11",
                "metadata": {"version": "1.0.0"},
                "rest": {"entry": "src.rest.index:mount"},
            }

            with open(project_dir / "agent.yaml", "w") as f:
                yaml.dump(manifest_data, f)

            # Create src directory structure
            (project_dir / "src").mkdir()
            (project_dir / "src" / "rest").mkdir()

            # Create REST index file
            (project_dir / "src" / "rest" / "index.py").write_text("""
def mount(app):
    pass
""")

            # Build the package
            # Required .env
            (project_dir / ".env").write_text("API_KEY=placeholder\n")
            builder = AgentBuilder(project_dir)
            output_path = builder.build()

            # Extract and verify contents
            with tempfile.TemporaryDirectory() as extract_dir:
                with zipfile.ZipFile(output_path, "r") as zf:
                    zf.extractall(extract_dir)

                extract_path = Path(extract_dir)

                # Check dist layout
                assert (extract_path / "dist").exists()
                assert (extract_path / "dist" / "rest").exists()
                assert not (extract_path / "dist" / "a2a").exists()
                assert not (extract_path / "dist" / "ui").exists()

                # Check deploy.json
                deploy_json_path = extract_path / "deploy.json"
                with open(deploy_json_path) as f:
                    deploy_data = json.load(f)

                assert deploy_data["expose"] == ["rest"]
                assert deploy_data["ports"]["rest"] == 8080
                assert "a2a" not in deploy_data["ports"]
                assert "ui" not in deploy_data["ports"]

    def test_build_with_ui_only(self):
        """Test building an agent with only UI surface."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "ui-agent"
            project_dir.mkdir()

            # Create agent.yaml
            manifest_data = {
                "version": "1.0",
                "name": "ui-agent",
                "display_name": "UI Agent",
                "description": "A UI-only agent",
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
            (project_dir / "ui" / "index.html").write_text("<html></html>")
            (project_dir / "ui" / "app.js").write_text("console.log('hello');")

            # Build the package
            # Required .env
            (project_dir / ".env").write_text("API_KEY=placeholder\n")
            builder = AgentBuilder(project_dir)
            output_path = builder.build()

            # Extract and verify contents
            with tempfile.TemporaryDirectory() as extract_dir:
                with zipfile.ZipFile(output_path, "r") as zf:
                    zf.extractall(extract_dir)

                extract_path = Path(extract_dir)

                # Check dist layout
                assert (extract_path / "dist").exists()
                assert (extract_path / "dist" / "ui").exists()
                assert not (extract_path / "dist" / "a2a").exists()
                assert not (extract_path / "dist" / "rest").exists()

                # Check UI files are copied
                assert (extract_path / "dist" / "ui" / "index.html").exists()
                assert (extract_path / "dist" / "ui" / "app.js").exists()

                # Check deploy.json
                deploy_json_path = extract_path / "deploy.json"
                with open(deploy_json_path) as f:
                    deploy_data = json.load(f)

                assert deploy_data["expose"] == ["ui"]
                assert deploy_data["ports"]["ui"] == 3000
                assert "a2a" not in deploy_data["ports"]
                assert "rest" not in deploy_data["ports"]

    def test_build_without_surfaces(self):
        """Test building a traditional agent without surfaces."""
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

            # Build the package
            # Required .env
            (project_dir / ".env").write_text("API_KEY=placeholder\n")
            builder = AgentBuilder(project_dir)
            output_path = builder.build()

            # Extract and verify contents
            with tempfile.TemporaryDirectory() as extract_dir:
                with zipfile.ZipFile(output_path, "r") as zf:
                    zf.extractall(extract_dir)

                extract_path = Path(extract_dir)

                # Check basic structure
                assert (extract_path / "agent.yaml").exists()
                assert (extract_path / "src").exists()
                assert (extract_path / "src" / "main.py").exists()

                # Check dist directory exists but is empty
                assert (extract_path / "dist").exists()
                assert not (extract_path / "dist" / "a2a").exists()
                assert not (extract_path / "dist" / "rest").exists()
                assert not (extract_path / "dist" / "ui").exists()

                # Check deploy.json
                deploy_json_path = extract_path / "deploy.json"
                with open(deploy_json_path) as f:
                    deploy_data = json.load(f)

                assert deploy_data["expose"] == []
                assert deploy_data["ports"] == {}
                assert deploy_data["multiplex"] is True

    def test_build_missing_surface_files(self):
        """Test building when surface files are missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "incomplete-agent"
            project_dir.mkdir()

            # Create agent.yaml with surfaces but missing files
            manifest_data = {
                "version": "1.0",
                "name": "incomplete-agent",
                "display_name": "Incomplete Agent",
                "description": "An incomplete agent",
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

            # Build should fail validation
            # Required .env (even though build will fail for other reasons)
            (project_dir / ".env").write_text("API_KEY=placeholder\n")
            builder = AgentBuilder(project_dir)
            with pytest.raises(BuildError, match="Validation failed"):
                builder.build()

    def test_build_with_environment_variables(self):
        """Test that environment variables from agent.yaml are included in deploy.json."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "env-agent"
            project_dir.mkdir()

            # Create agent.yaml with environment variables
            manifest_data = {
                "version": "1.0",
                "name": "env-agent",
                "display_name": "Environment Agent",
                "description": "An agent with environment variables",
                "author": "Test Author",
                "license": "MIT",
                "runtime": "python3.11",
                "entrypoint": "src.main:handler",
                "metadata": {"version": "1.0.0"},
                "environment": {
                    "A2A_AGENT_APPS": "agent1,agent2,agent3",
                    "CUSTOM_VAR": "static_value",
                    "A2A_PORT": "${A2A_PORT:-50051}",
                },
            }

            with open(project_dir / "agent.yaml", "w") as f:
                yaml.dump(manifest_data, f)

            # Create src directory and main file
            (project_dir / "src").mkdir()
            (project_dir / "src" / "main.py").write_text("""
def handler(context):
    return {"status": "success"}
""")

            # Required .env
            (project_dir / ".env").write_text("API_KEY=placeholder\n")
            builder = AgentBuilder(project_dir)
            output_path = builder.build()

            assert output_path.exists()

            # Extract and verify environment in deploy.json
            with tempfile.TemporaryDirectory() as extract_dir:
                with zipfile.ZipFile(output_path, "r") as zf:
                    zf.extractall(extract_dir)

                extract_path = Path(extract_dir)

                # Check deploy.json contains environment
                deploy_json_path = extract_path / "deploy.json"
                assert deploy_json_path.exists()

                with open(deploy_json_path) as f:
                    deploy_data = json.load(f)

                assert "environment" in deploy_data
                assert deploy_data["environment"]["A2A_AGENT_APPS"] == "agent1,agent2,agent3"
                assert deploy_data["environment"]["CUSTOM_VAR"] == "static_value"
                assert deploy_data["environment"]["A2A_PORT"] == "${A2A_PORT:-50051}"

    def test_build_with_empty_environment(self):
        """Test that empty environment dict is handled correctly in deploy.json."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "no-env-agent"
            project_dir.mkdir()

            # Create agent.yaml without environment variables
            manifest_data = {
                "version": "1.0",
                "name": "no-env-agent",
                "display_name": "No Env Agent",
                "description": "An agent without environment variables",
                "author": "Test Author",
                "license": "MIT",
                "runtime": "python3.11",
                "entrypoint": "src.main:handler",
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

            # Required .env
            (project_dir / ".env").write_text("API_KEY=placeholder\n")
            builder = AgentBuilder(project_dir)
            output_path = builder.build()

            assert output_path.exists()

            # Extract and verify environment in deploy.json is empty dict
            with tempfile.TemporaryDirectory() as extract_dir:
                with zipfile.ZipFile(output_path, "r") as zf:
                    zf.extractall(extract_dir)

                extract_path = Path(extract_dir)

                # Check deploy.json contains empty environment
                deploy_json_path = extract_path / "deploy.json"
                assert deploy_json_path.exists()

                with open(deploy_json_path) as f:
                    deploy_data = json.load(f)

                assert "environment" in deploy_data
                assert deploy_data["environment"] == {}

    def test_build_with_agents_config_json(self):
        """Test that agents_config.json is included in APKG when present."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "multi-agent"
            project_dir.mkdir()

            # Create agent.yaml
            manifest_data = {
                "version": "1.0",
                "name": "multi-agent",
                "display_name": "Multi Agent",
                "description": "A multi-agent orchestrator",
                "author": "Test Author",
                "license": "MIT",
                "runtime": "python3.11",
                "entrypoint": "src.main:handler",
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

            # Create agents_config.json with sample multi-agent config
            agents_config = {
                "agents": [
                    {
                        "agent_app_id": "4906eeb7-9959-414e-84c6-f2445822ebe4",
                        "name": "Test Agent",
                        "endpoint": "https://par.pixell.global/agents/test",
                        "protocol": "grpc",
                        "description": "Test agent for coordination",
                        "capabilities": [
                            "test capability 1",
                            "test capability 2"
                        ],
                        "example_queries": [
                            "test query 1",
                            "test query 2"
                        ]
                    }
                ]
            }

            with open(project_dir / "agents_config.json", "w") as f:
                json.dump(agents_config, f, indent=2)

            # Required .env
            (project_dir / ".env").write_text("API_KEY=placeholder\n")
            builder = AgentBuilder(project_dir)
            output_path = builder.build()

            assert output_path.exists()

            # Extract and verify agents_config.json is included
            with tempfile.TemporaryDirectory() as extract_dir:
                with zipfile.ZipFile(output_path, "r") as zf:
                    zf.extractall(extract_dir)

                extract_path = Path(extract_dir)

                # Check that agents_config.json exists
                agents_config_path = extract_path / "agents_config.json"
                assert agents_config_path.exists(), "agents_config.json should be included in APKG"

                # Verify the content is valid JSON and matches what we wrote
                with open(agents_config_path) as f:
                    extracted_config = json.load(f)

                assert "agents" in extracted_config
                assert len(extracted_config["agents"]) == 1
                assert extracted_config["agents"][0]["name"] == "Test Agent"
                assert extracted_config["agents"][0]["agent_app_id"] == "4906eeb7-9959-414e-84c6-f2445822ebe4"

    def test_build_without_agents_config_json(self):
        """Test that build succeeds when agents_config.json is absent."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "simple-agent"
            project_dir.mkdir()

            # Create agent.yaml
            manifest_data = {
                "version": "1.0",
                "name": "simple-agent",
                "display_name": "Simple Agent",
                "description": "A simple agent without multi-agent coordination",
                "author": "Test Author",
                "license": "MIT",
                "runtime": "python3.11",
                "entrypoint": "src.main:handler",
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

            # Required .env
            (project_dir / ".env").write_text("API_KEY=placeholder\n")

            # DO NOT create agents_config.json - this is the test case
            builder = AgentBuilder(project_dir)
            output_path = builder.build()

            # Build should succeed
            assert output_path.exists()

            # Extract and verify agents_config.json is NOT included
            with tempfile.TemporaryDirectory() as extract_dir:
                with zipfile.ZipFile(output_path, "r") as zf:
                    zf.extractall(extract_dir)

                extract_path = Path(extract_dir)

                # Check that agents_config.json does NOT exist
                agents_config_path = extract_path / "agents_config.json"
                assert not agents_config_path.exists(), "agents_config.json should not be included when absent"

    def test_build_with_invalid_agents_config_json(self):
        """Test that build succeeds even with malformed agents_config.json (validation is runtime concern)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "invalid-config-agent"
            project_dir.mkdir()

            # Create agent.yaml
            manifest_data = {
                "version": "1.0",
                "name": "invalid-config-agent",
                "display_name": "Invalid Config Agent",
                "description": "Agent with invalid agents_config.json",
                "author": "Test Author",
                "license": "MIT",
                "runtime": "python3.11",
                "entrypoint": "src.main:handler",
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

            # Create invalid agents_config.json (malformed but still a file)
            # Build should still succeed - validation is a runtime concern
            with open(project_dir / "agents_config.json", "w") as f:
                f.write("invalid json content {]")

            # Required .env
            (project_dir / ".env").write_text("API_KEY=placeholder\n")
            builder = AgentBuilder(project_dir)

            # Build should succeed - we don't validate the JSON content during build
            output_path = builder.build()
            assert output_path.exists()

            # Extract and verify the file is included (even though it's invalid)
            with tempfile.TemporaryDirectory() as extract_dir:
                with zipfile.ZipFile(output_path, "r") as zf:
                    zf.extractall(extract_dir)

                extract_path = Path(extract_dir)
                agents_config_path = extract_path / "agents_config.json"
                assert agents_config_path.exists(), "agents_config.json should be included even if invalid"
