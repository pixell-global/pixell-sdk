"""Integration tests for the complete A2A/REST/UI workflow."""

import tempfile
import yaml
import json
from pathlib import Path
from click.testing import CliRunner

from pixell.cli.main import cli


class TestIntegrationSurfaces:
    """Integration tests for the complete surface workflow."""

    def test_complete_workflow_init_validate_build(self):
        """Test complete workflow: init -> validate -> build."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            project_name = "integration-test-agent"

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
                )
                project_path = Path.cwd() / project_name

                assert result.exit_code == 0
                assert project_path.exists()

                # Step 2: Validate the project
                result = runner.invoke(cli, ["validate", "--path", str(project_path)])

                assert result.exit_code == 0
                assert "SUCCESS: Validation passed!" in result.output

                # Step 3: Build the project
                result = runner.invoke(
                    cli,
                    [
                        "build",
                        "--path",
                        str(project_path),
                        "--output",
                        str(project_path.parent),
                    ],
                )

                assert result.exit_code == 0
                assert "SUCCESS: Build successful!" in result.output

                # Verify the built package
                apkg_files = list(project_path.parent.glob("*.apkg"))
                assert len(apkg_files) == 1

                apkg_file = apkg_files[0]
                assert apkg_file.name == f"{project_name}-0.1.0.apkg"

    def test_rest_only_workflow(self):
        """Test workflow with REST-only agent."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            project_name = "rest-only-agent"

            with runner.isolated_filesystem(temp_dir=temp_dir):
                result = runner.invoke(cli, ["init", project_name, "--surface", "rest"])
                project_path = Path.cwd() / project_name

                assert result.exit_code == 0

                # Validate
                result = runner.invoke(cli, ["validate", "--path", str(project_path)])
                assert result.exit_code == 0

                # Build
                result = runner.invoke(
                    cli,
                    [
                        "build",
                        "--path",
                        str(project_path),
                        "--output",
                        str(project_path.parent),
                    ],
                )

                assert result.exit_code == 0

                # Verify package contents
                apkg_files = list(project_path.parent.glob("*.apkg"))
                assert len(apkg_files) == 1

                # Extract and verify deploy.json
                import zipfile

                with zipfile.ZipFile(apkg_files[0], "r") as zf:
                    with zf.open("deploy.json") as f:
                        deploy_data = json.load(f)

                assert deploy_data["expose"] == ["rest"]
                assert deploy_data["ports"]["rest"] == 8080

    def test_ui_only_workflow(self):
        """Test workflow with UI-only agent."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            project_name = "ui-only-agent"

            with runner.isolated_filesystem(temp_dir=temp_dir):
                result = runner.invoke(cli, ["init", project_name, "--surface", "ui"])
                project_path = Path.cwd() / project_name

                assert result.exit_code == 0

                # Validate
                result = runner.invoke(cli, ["validate", "--path", str(project_path)])
                assert result.exit_code == 0

                # Build
                result = runner.invoke(
                    cli,
                    [
                        "build",
                        "--path",
                        str(project_path),
                        "--output",
                        str(project_path.parent),
                    ],
                )

                assert result.exit_code == 0

                # Verify package contents
                apkg_files = list(project_path.parent.glob("*.apkg"))
                assert len(apkg_files) == 1

                # Extract and verify deploy.json
                import zipfile

                with zipfile.ZipFile(apkg_files[0], "r") as zf:
                    with zf.open("deploy.json") as f:
                        deploy_data = json.load(f)

                assert deploy_data["expose"] == ["ui"]
                assert deploy_data["ports"]["ui"] == 3000

    def test_validation_fails_with_missing_files(self):
        """Test that validation fails when surface files are missing."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            project_name = "incomplete-agent"

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
                )
                project_path = Path.cwd() / project_name

                assert result.exit_code == 0

                # Remove some files to make it incomplete
                (project_path / "src" / "rest" / "index.py").unlink()
                import shutil

                shutil.rmtree(project_path / "ui")

                # Validation should fail
                result = runner.invoke(cli, ["validate", "--path", str(project_path)])

                assert result.exit_code == 1
                assert "FAILED: Validation failed:" in result.output
                assert "REST entry module not found" in result.output
                assert "UI path not found" in result.output

    def test_build_fails_with_validation_errors(self):
        """Test that build fails when validation fails."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            project_name = "broken-agent"
            project_path = Path(temp_dir) / project_name

            # Initialize project
            with runner.isolated_filesystem(temp_dir=temp_dir):
                result = runner.invoke(cli, ["init", project_name])
                project_path = Path.cwd() / project_name
                assert result.exit_code == 0

                # Break the agent.yaml
                agent_yaml_path = project_path / "agent.yaml"
                with open(agent_yaml_path, "w") as f:
                    f.write("invalid: yaml: content: [")

                # Build should fail
                result = runner.invoke(
                    cli, ["build", "--path", str(project_path), "--output", str(project_path.parent)]
                )

                assert result.exit_code == 1
                assert "FAILED: Build failed:" in result.output

    def test_dev_command_alias(self):
        """Test that the dev command alias works."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            project_name = "dev-test-agent"
            project_path = Path(temp_dir) / project_name

            # Initialize project
            with runner.isolated_filesystem(temp_dir=temp_dir):
                result = runner.invoke(cli, ["init", project_name])
                project_path = Path.cwd() / project_name
                assert result.exit_code == 0

                # Test that dev command exists and accepts same options as run-dev
                result = runner.invoke(
                    cli, ["dev", "--path", str(project_path), "--port", "8081", "--help"]
                )

                # Should show help for dev command
                assert result.exit_code == 0
                assert "Alias for run-dev" in result.output

    def test_manifest_roundtrip_consistency(self):
        """Test that manifest data is consistent through init -> validate -> build."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            project_name = "consistency-test-agent"

            with runner.isolated_filesystem(temp_dir=temp_dir):
                result = runner.invoke(
                    cli, ["init", project_name, "--surface", "rest", "--surface", "ui"]
                )
                project_path = Path.cwd() / project_name

                assert result.exit_code == 0

                # Read the generated manifest
                with open(project_path / "agent.yaml") as f:
                    original_manifest = yaml.safe_load(f)

                # Validate
                result = runner.invoke(cli, ["validate", "--path", str(project_path)])
                assert result.exit_code == 0

                # Build
                result = runner.invoke(
                    cli,
                    [
                        "build",
                        "--path",
                        str(project_path),
                        "--output",
                        str(project_path.parent),
                    ],
                )

                assert result.exit_code == 0

                # Extract and verify manifest in package
                import zipfile

                apkg_files = list(project_path.parent.glob("*.apkg"))
                with zipfile.ZipFile(apkg_files[0], "r") as zf:
                    with zf.open("agent.yaml") as f:
                        packaged_manifest = yaml.safe_load(f)

                # Key fields should be consistent
                assert original_manifest["name"] == packaged_manifest["name"]
                assert original_manifest["display_name"] == packaged_manifest["display_name"]
                assert original_manifest["rest"] == packaged_manifest["rest"]
                assert original_manifest["ui"] == packaged_manifest["ui"]

    def test_multiple_surface_combinations(self):
        """Test various combinations of surfaces."""
        runner = CliRunner()

        surface_combinations = [
            (["a2a"], ["a2a"]),
            (["rest"], ["rest"]),
            (["ui"], ["ui"]),
            (["a2a", "rest"], ["a2a", "rest"]),
            (["a2a", "ui"], ["a2a", "ui"]),
            (["rest", "ui"], ["rest", "ui"]),
            (["a2a", "rest", "ui"], ["a2a", "rest", "ui"]),
        ]

        for surfaces, expected_expose in surface_combinations:
            with tempfile.TemporaryDirectory() as temp_dir:
                project_name = f"combo-{'-'.join(surfaces)}-agent"

                # Initialize with specific surfaces
                cmd = ["init", project_name] + [
                    arg for surface in surfaces for arg in ["--surface", surface]
                ]
                with runner.isolated_filesystem(temp_dir=temp_dir):
                    result = runner.invoke(cli, cmd)
                    project_path = Path.cwd() / project_name

                    assert result.exit_code == 0, f"Failed for surfaces: {surfaces}"

                    # Build
                    result = runner.invoke(
                        cli,
                        [
                            "build",
                            "--path",
                            str(project_path),
                            "--output",
                            str(project_path.parent),
                        ],
                    )

                    assert result.exit_code == 0, f"Build failed for surfaces: {surfaces}"

                    # Verify deploy.json
                    import zipfile

                    apkg_files = list(project_path.parent.glob("*.apkg"))
                    with zipfile.ZipFile(apkg_files[0], "r") as zf:
                        with zf.open("deploy.json") as f:
                            deploy_data = json.load(f)

                    assert set(deploy_data["expose"]) == set(expected_expose), (
                        f"Expose mismatch for surfaces: {surfaces}"
                    )
