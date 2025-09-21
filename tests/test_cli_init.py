"""Tests for CLI init command with A2A/REST/UI scaffolding."""

import tempfile
import yaml
from pathlib import Path
from click.testing import CliRunner

from pixell.cli.main import cli


class TestCLIInit:
    """Test CLI init command functionality."""

    def test_init_with_all_surfaces(self):
        """Test init command with all surfaces."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            project_name = "test-agent"

            with runner.isolated_filesystem(temp_dir=temp_dir):
                result = runner.invoke(
                    cli,
                    [
                        "init",
                        project_name,
                        "--surface",
                        "a2a",
                        "--surface",
                        "rest",
                        "--surface",
                        "ui",
                    ],
                    input="\n",
                )  # Accept default values

                # Check that the project was created in the isolated filesystem
                project_path = Path.cwd() / project_name
                assert result.exit_code == 0
                assert project_path.exists()
                assert project_path.is_dir()

                # Check agent.yaml
                agent_yaml_path = project_path / "agent.yaml"
                assert agent_yaml_path.exists()

                with open(agent_yaml_path) as f:
                    manifest_data = yaml.safe_load(f)

                assert manifest_data["name"] == "test-agent"
                assert manifest_data["display_name"] == "Test Agent"
                assert "a2a" in manifest_data
                assert "rest" in manifest_data
                assert "ui" in manifest_data
                assert manifest_data["a2a"]["service"] == "src.a2a.server:serve"
                assert manifest_data["rest"]["entry"] == "src.rest.index:mount"
                assert manifest_data["ui"]["path"] == "ui"

                # Check directory structure
                assert (project_path / "src").exists()
                assert (project_path / "src" / "a2a").exists()
                assert (project_path / "src" / "rest").exists()
                assert (project_path / "ui").exists()

                # Check generated files
                assert (project_path / "src" / "main.py").exists()
                assert (project_path / "src" / "a2a" / "server.py").exists()
                assert (project_path / "src" / "rest" / "index.py").exists()
                assert (project_path / "ui" / "index.html").exists()
                assert (project_path / "requirements.txt").exists()
                assert (project_path / "README.md").exists()

    def test_init_with_default_surfaces(self):
        """Test init command with default surfaces (all)."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            project_name = "test-agent"
            project_path = Path(temp_dir) / project_name

            with runner.isolated_filesystem(temp_dir=temp_dir):
                result = runner.invoke(cli, ["init", project_name])

            assert result.exit_code == 0
            assert project_path.exists()

            # Check agent.yaml has all surfaces by default
            agent_yaml_path = project_path / "agent.yaml"
            with open(agent_yaml_path) as f:
                manifest_data = yaml.safe_load(f)

            assert "a2a" in manifest_data
            assert "rest" in manifest_data
            assert "ui" in manifest_data

    def test_init_with_specific_surfaces(self):
        """Test init command with specific surfaces only."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            project_name = "rest-only-agent"
            project_path = Path(temp_dir) / project_name

            with runner.isolated_filesystem(temp_dir=temp_dir):
                result = runner.invoke(cli, ["init", project_name, "--surface", "rest"])

            assert result.exit_code == 0
            assert project_path.exists()

            # Check agent.yaml has only REST surface
            agent_yaml_path = project_path / "agent.yaml"
            with open(agent_yaml_path) as f:
                manifest_data = yaml.safe_load(f)

            assert "rest" in manifest_data
            assert "a2a" not in manifest_data
            assert "ui" not in manifest_data

            # Check directory structure
            assert (project_path / "src" / "rest").exists()
            assert not (project_path / "src" / "a2a").exists()
            assert not (project_path / "ui").exists()

    def test_init_with_ui_only(self):
        """Test init command with UI surface only."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            project_name = "ui-only-agent"
            project_path = Path(temp_dir) / project_name

            with runner.isolated_filesystem(temp_dir=temp_dir):
                result = runner.invoke(cli, ["init", project_name, "--surface", "ui"])

            assert result.exit_code == 0
            assert project_path.exists()

            # Check agent.yaml has only UI surface
            agent_yaml_path = project_path / "agent.yaml"
            with open(agent_yaml_path) as f:
                manifest_data = yaml.safe_load(f)

            assert "ui" in manifest_data
            assert "a2a" not in manifest_data
            assert "rest" not in manifest_data

            # Check directory structure
            assert (project_path / "ui").exists()
            assert not (project_path / "src" / "a2a").exists()
            assert not (project_path / "src" / "rest").exists()

    def test_init_existing_directory_error(self):
        """Test init command fails when directory already exists."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            project_name = "existing-agent"
            project_path = Path(temp_dir) / project_name
            project_path.mkdir()  # Create directory first

            with runner.isolated_filesystem(temp_dir=temp_dir):
                result = runner.invoke(cli, ["init", project_name])

            assert result.exit_code == 1
            assert "Directory already exists" in result.output

    def test_init_generated_files_content(self):
        """Test that generated files have correct content."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            project_name = "content-test-agent"
            project_path = Path(temp_dir) / project_name

            with runner.isolated_filesystem(temp_dir=temp_dir):
                result = runner.invoke(cli, ["init", project_name, "--surface", "rest"])

            assert result.exit_code == 0

            # Check REST module content
            rest_file = project_path / "src" / "rest" / "index.py"
            assert rest_file.exists()
            content = rest_file.read_text()
            assert "def mount(app: FastAPI)" in content
            assert "from fastapi import FastAPI" in content
            assert "/api/hello" in content

            # Check main.py content
            main_file = project_path / "src" / "main.py"
            assert main_file.exists()
            content = main_file.read_text()
            assert "def handler(context)" in content

            # Check requirements.txt content
            req_file = project_path / "requirements.txt"
            assert req_file.exists()
            content = req_file.read_text()
            assert "fastapi>=" in content
            assert "uvicorn>=" in content
            assert "watchdog>=" in content

            # Check README.md content
            readme_file = project_path / "README.md"
            assert readme_file.exists()
            content = readme_file.read_text()
            assert project_name in content
            assert "pixell dev" in content

    def test_init_name_normalization(self):
        """Test that project names are normalized correctly."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            project_name = "Test_Agent_With_Underscores"
            project_path = Path(temp_dir) / project_name

            with runner.isolated_filesystem(temp_dir=temp_dir):
                result = runner.invoke(cli, ["init", project_name])

            assert result.exit_code == 0

            # Check agent.yaml has normalized name
            agent_yaml_path = project_path / "agent.yaml"
            with open(agent_yaml_path) as f:
                manifest_data = yaml.safe_load(f)

            assert manifest_data["name"] == "test-agent-with-underscores"
            assert manifest_data["display_name"] == "Test Agent With Underscores"
