"""Test command for pixell CLI."""

import click
import asyncio
from pathlib import Path


@click.command()
@click.option("--path", "path_", default=".", help="Path to agent project")
@click.option(
    "--level",
    "level",
    type=click.Choice(["static", "build", "install", "runtime", "integration"]),
    default="integration",
    help="Test level to run",
)
@click.option(
    "--category",
    "category",
    type=click.Choice(["security", "grpc", "rest", "env", "all"]),
    default="all",
    help="Test category to run",
)
@click.option("--json", "json_output", is_flag=True, help="Output JSON for CI/CD")
@click.option("--verbose", "verbose", is_flag=True, help="Verbose output")
def test_cmd(path_: str, level: str, category: str, json_output: bool, verbose: bool):
    """Test agent comprehensively before deployment."""
    import sys
    from pixell.test.test_runner import AgentTester, TestLevel

    project_dir = Path(path_)

    if not json_output:
        click.secho(f"\n🧪 Testing agent at: {project_dir}", fg="cyan", bold=True)
        click.secho("=" * 60, fg="cyan")

    # Currently category filtering is not implemented in runner; accept for future use
    _ = category  # placeholder to avoid linter warnings

    tester = AgentTester(project_dir, TestLevel(level), silent=json_output)
    result = asyncio.run(tester.run_all_tests())

    if json_output:
        import json as json_lib

        output = {
            "success": result.success,
            "passed": result.passed,
            "failed": result.failed,
            "warnings": result.warnings,
            "skipped": result.skipped,
        }
        click.echo(json_lib.dumps(output, indent=2))
    else:
        click.echo("\n")
        click.secho("=" * 60, fg="cyan")
        click.secho("📊 Test Results", fg="cyan", bold=True)
        click.secho("=" * 60, fg="cyan")

        for msg in result.passed:
            click.secho(msg, fg="green")
        for msg in result.warnings:
            click.secho(msg, fg="yellow")
        for msg in result.failed:
            click.secho(msg, fg="red")
        for msg in result.skipped:
            click.secho(msg, fg="blue")

        click.echo("\n")
        if result.success:
            click.secho("✅ All tests passed!", fg="green", bold=True)
            sys.exit(0)
        else:
            click.secho("❌ Tests failed", fg="red", bold=True)
            sys.exit(1)
