"""Tests for the `pixell test` command."""

import json
import tempfile
from pathlib import Path
from click.testing import CliRunner

from pixell.cli.main import cli


class TestCLITestCommand:
    """Test the pixell test CLI command."""

    def test_test_command_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["test", "--help"])

        assert result.exit_code == 0
        assert "Test agent comprehensively before deployment" in result.output
        assert "--level" in result.output
        assert "--json" in result.output
        assert "--category" in result.output

    def test_test_static_level_on_scaffold(self):
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            project_name = "sample-agent"

            with runner.isolated_filesystem(temp_dir=temp_dir):
                # Create a scaffolded agent project
                init_res = runner.invoke(cli, ["init", project_name])
                assert init_res.exit_code == 0

                project_path = Path.cwd() / project_name
                assert (project_path / "agent.yaml").exists()
                # Ensure .env exists for validator used inside the test runner
                (project_path / ".env").write_text("API_KEY=placeholder\n")

                # Run pixell test at static level with JSON output
                test_res = runner.invoke(
                    cli,
                    [
                        "test",
                        "--path",
                        str(project_path),
                        "--level",
                        "static",
                        "--json",
                    ],
                )

                assert test_res.exit_code == 0

                # Parse JSON output
                payload = json.loads(test_res.output)
                assert payload["success"] is True
                assert isinstance(payload["passed"], list)
                # Expect that structure check or manifest validation appears
                assert (
                    any("agent.yaml" in msg or "Manifest" in msg for msg in payload["passed"])
                    or not payload["failed"]
                )

    def test_test_build_level_on_scaffold(self):
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            project_name = "build-agent"

            with runner.isolated_filesystem(temp_dir=temp_dir):
                init_res = runner.invoke(cli, ["init", project_name])
                assert init_res.exit_code == 0

                project_path = Path.cwd() / project_name
                assert (project_path / "agent.yaml").exists()
                # Ensure .env exists for builder used inside the test runner
                (project_path / ".env").write_text("API_KEY=placeholder\n")

                # Run pixell test at build level with JSON output
                test_res = runner.invoke(
                    cli,
                    [
                        "test",
                        "--path",
                        str(project_path),
                        "--level",
                        "build",
                        "--json",
                    ],
                )

                assert test_res.exit_code == 0
                payload = json.loads(test_res.output)
                assert payload["success"] is True
                # Should include a message indicating APKG build success
                assert (
                    any("APKG built successfully" in msg for msg in payload["passed"])
                    or not payload["failed"]
                )
