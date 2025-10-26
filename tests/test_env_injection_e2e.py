"""End-to-end tests for environment variable injection feature."""

import tempfile
import json
import yaml
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

from pixell.core.builder import AgentBuilder
from pixell.core.deployment import DeploymentClient, extract_environment_from_apkg


class TestEnvironmentInjectionE2E:
    """End-to-end tests for environment variable injection."""

    def test_complete_environment_injection_flow(self):
        """Test the complete flow: build agent with env vars, extract, and deploy."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "test-agent"
            project_dir.mkdir()

            # Create agent.yaml with environment variables
            manifest_data = {
                "version": "1.0",
                "name": "test-env-agent",
                "display_name": "Test Environment Agent",
                "description": "An agent for testing environment variable injection",
                "author": "Test Author",
                "license": "MIT",
                "runtime": "python3.11",
                "entrypoint": "src.main:handler",
                "metadata": {"version": "1.0.0"},
                "environment": {
                    "A2A_AGENT_APPS": "agent1,agent2,agent3",
                    "CUSTOM_VAR": "static_value",
                    "A2A_PORT": "${A2A_PORT:-50051}",
                    "DATABASE_URL": "${DATABASE_URL}",
                },
            }

            with open(project_dir / "agent.yaml", "w") as f:
                yaml.dump(manifest_data, f)

            # Create src directory and main file
            (project_dir / "src").mkdir()
            (project_dir / "src" / "main.py").write_text("""
import os

def handler(context):
    # Load environment variables
    agent_apps = os.getenv("A2A_AGENT_APPS", "").split(",")
    custom_var = os.getenv("CUSTOM_VAR")
    port = os.getenv("A2A_PORT")
    db_url = os.getenv("DATABASE_URL")

    return {
        "status": "success",
        "agent_apps": agent_apps,
        "custom_var": custom_var,
        "port": port,
        "database_url": db_url,
    }
""")

            # Required .env
            (project_dir / ".env").write_text("API_KEY=placeholder\n")

            # Step 1: Build the package
            builder = AgentBuilder(project_dir)
            output_path = builder.build()

            assert output_path.exists()
            assert output_path.suffix == ".apkg"

            # Step 2: Verify deploy.json contains environment variables
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
                assert deploy_data["environment"]["DATABASE_URL"] == "${DATABASE_URL}"

            # Step 3: Extract environment from APKG
            extracted_env = extract_environment_from_apkg(output_path)
            assert extracted_env["A2A_AGENT_APPS"] == "agent1,agent2,agent3"
            assert extracted_env["CUSTOM_VAR"] == "static_value"
            assert extracted_env["A2A_PORT"] == "${A2A_PORT:-50051}"
            assert extracted_env["DATABASE_URL"] == "${DATABASE_URL}"

            # Step 4: Deploy with runtime environment overrides
            with patch("pixell.core.deployment.requests.Session.post") as mock_post:
                # Mock successful deployment response
                mock_response = Mock()
                mock_response.status_code = 202
                mock_response.json.return_value = {
                    "deployment": {"id": "deploy-123", "status": "queued"},
                    "package": {"id": "pkg-123", "version": "1.0.0"},
                    "tracking": {"status_url": "https://api.example.com/deployments/deploy-123"},
                }
                mock_post.return_value = mock_response

                # Deploy with runtime overrides
                client = DeploymentClient(environment="prod", api_key="test-key")
                runtime_env = {
                    "A2A_AGENT_APPS": "agent1,agent2,agent3,agent4",  # Override
                    "DATABASE_URL": "postgresql://prod-db:5432/mydb",  # Provide value
                }

                result = client.deploy(
                    "app-123",
                    output_path,
                    version="1.0.0",
                    runtime_env=runtime_env,
                )

                assert result["deployment"]["id"] == "deploy-123"

                # Verify the deployment API call
                mock_post.assert_called_once()
                call_args = mock_post.call_args
                data = dict(call_args[1]["data"])

                # Parse environment JSON
                env_json = data.get("environment")
                assert env_json is not None
                merged_env = json.loads(env_json)

                # Verify merged environment
                # Runtime override took precedence
                assert merged_env["A2A_AGENT_APPS"] == "agent1,agent2,agent3,agent4"
                # Original values preserved
                assert merged_env["CUSTOM_VAR"] == "static_value"
                assert merged_env["A2A_PORT"] == "${A2A_PORT:-50051}"
                # Runtime value provided
                assert merged_env["DATABASE_URL"] == "postgresql://prod-db:5432/mydb"

    def test_environment_injection_with_a2a_surface(self):
        """Test environment injection with A2A surface configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "a2a-agent"
            project_dir.mkdir()

            # Create agent.yaml with A2A surface and environment
            manifest_data = {
                "version": "1.0",
                "name": "a2a-agent",
                "display_name": "A2A Agent",
                "description": "An agent with A2A surface",
                "author": "Test Author",
                "license": "MIT",
                "runtime": "python3.11",
                "metadata": {"version": "1.0.0"},
                "a2a": {"service": "src.a2a.server:serve"},
                "environment": {
                    "A2A_PORT": "${A2A_PORT:-50051}",
                    "A2A_AGENT_APPS": "core_agent,search_agent",
                    "USE_UNIX_SOCKET": "${USE_UNIX_SOCKET:-true}",
                },
            }

            with open(project_dir / "agent.yaml", "w") as f:
                yaml.dump(manifest_data, f)

            # Create src directory and A2A server
            (project_dir / "src").mkdir()
            (project_dir / "src" / "a2a").mkdir()
            (project_dir / "src" / "a2a" / "server.py").write_text("""
import os

def serve():
    port = os.getenv("A2A_PORT", "50051")
    agents = os.getenv("A2A_AGENT_APPS", "").split(",")
    use_socket = os.getenv("USE_UNIX_SOCKET", "true")

    print(f"Starting A2A server on port {port}")
    print(f"Available agents: {agents}")
    print(f"Use Unix socket: {use_socket}")
""")

            # Required .env
            (project_dir / ".env").write_text("API_KEY=placeholder\n")

            # Build the package
            builder = AgentBuilder(project_dir)
            output_path = builder.build()

            # Verify deploy.json
            with tempfile.TemporaryDirectory() as extract_dir:
                with zipfile.ZipFile(output_path, "r") as zf:
                    zf.extractall(extract_dir)

                extract_path = Path(extract_dir)

                # Check deploy.json
                with open(extract_path / "deploy.json") as f:
                    deploy_data = json.load(f)

                # Verify surfaces are exposed
                assert "a2a" in deploy_data["expose"]
                assert deploy_data["ports"]["a2a"] == 50051

                # Verify environment variables
                assert "environment" in deploy_data
                assert deploy_data["environment"]["A2A_PORT"] == "${A2A_PORT:-50051}"
                assert deploy_data["environment"]["A2A_AGENT_APPS"] == "core_agent,search_agent"
                assert deploy_data["environment"]["USE_UNIX_SOCKET"] == "${USE_UNIX_SOCKET:-true}"

    def test_empty_environment_does_not_break_deployment(self):
        """Test that agents without environment variables still work."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "no-env-agent"
            project_dir.mkdir()

            # Create agent.yaml WITHOUT environment section
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

            # Create src directory
            (project_dir / "src").mkdir()
            (project_dir / "src" / "main.py").write_text("""
def handler(context):
    return {"status": "success"}
""")

            # Required .env
            (project_dir / ".env").write_text("API_KEY=placeholder\n")

            # Build the package
            builder = AgentBuilder(project_dir)
            output_path = builder.build()

            # Verify deploy.json has empty environment
            with tempfile.TemporaryDirectory() as extract_dir:
                with zipfile.ZipFile(output_path, "r") as zf:
                    zf.extractall(extract_dir)

                with open(Path(extract_dir) / "deploy.json") as f:
                    deploy_data = json.load(f)

                assert "environment" in deploy_data
                assert deploy_data["environment"] == {}

            # Deploy should work fine with no runtime env
            with patch("pixell.core.deployment.requests.Session.post") as mock_post:
                mock_response = Mock()
                mock_response.status_code = 202
                mock_response.json.return_value = {
                    "deployment": {"id": "deploy-123", "status": "queued"},
                    "package": {"id": "pkg-123", "version": "1.0.0"},
                    "tracking": {"status_url": "https://api.example.com/deployments/deploy-123"},
                }
                mock_post.return_value = mock_response

                client = DeploymentClient(environment="prod", api_key="test-key")
                result = client.deploy("app-123", output_path, version="1.0.0")

                assert result["deployment"]["id"] == "deploy-123"
