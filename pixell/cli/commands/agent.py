"""Agent commands for pixell CLI (init, build, validate, dev, run-dev, inspect)."""

import click
from pathlib import Path


@click.command()
@click.argument("name")
@click.option(
    "--surface",
    "surfaces",
    type=click.Choice(["a2a", "rest", "ui"], case_sensitive=False),
    multiple=True,
    help="Which surfaces to include (repeatable). Defaults to all.",
)
def init_cmd(name, surfaces):
    """Initialize a new agent project (Python) with optional A2A/REST/UI surfaces."""
    project_dir = Path(name).resolve()

    if project_dir.exists():
        click.secho(f"Directory already exists: {project_dir}", fg="red")
        ctx = click.get_current_context()
        ctx.exit(1)

    if not surfaces:
        surfaces = ("a2a", "rest", "ui")

    # Create directories
    (project_dir / "src").mkdir(parents=True)
    if "rest" in surfaces:
        (project_dir / "src" / "rest").mkdir(parents=True)
    if "a2a" in surfaces:
        (project_dir / "src" / "a2a").mkdir(parents=True)
    if "ui" in surfaces:
        (project_dir / "ui").mkdir(parents=True)

    # agent.yaml
    normalized_name = name.replace("_", "-").lower()
    display_name = name.replace("-", " ").replace("_", " ").title()

    agent_yaml = {
        "version": "1.0",
        "name": normalized_name,
        "display_name": display_name,
        "description": "A Pixell agent",
        "author": "Your Name",
        "license": "MIT",
        # Entrypoint optional when REST or A2A present, include a default sample
        "entrypoint": "src.main:handler",
        "runtime": "python3.11",
        "environment": {},
        "dependencies": [
            "fastapi>=0.112.0",
            "uvicorn>=0.30.0",
            "watchdog>=4.0.0",
        ],
        "metadata": {"version": "0.1.0"},
    }

    if "a2a" in surfaces:
        agent_yaml["a2a"] = {"service": "src.a2a.server:serve"}
    if "rest" in surfaces:
        agent_yaml["rest"] = {"entry": "src.rest.index:mount"}
    if "ui" in surfaces:
        agent_yaml["ui"] = {"path": "ui"}

    import yaml as _yaml

    (project_dir / "agent.yaml").write_text(_yaml.safe_dump(agent_yaml, sort_keys=False))

    # src/main.py
    (project_dir / "src" / "main.py").write_text(
        '''def handler(context):
    """Example entrypoint."""
    return {"message": "Hello from handler", "received": context}
'''
    )

    # REST scaffold
    if "rest" in surfaces:
        (project_dir / "src" / "rest" / "index.py").write_text(
            """from fastapi import FastAPI


def mount(app: FastAPI) -> None:
    @app.get("/api/hello")
    async def hello():
        return {"message": "Hello from REST"}
"""
        )

    # A2A scaffold (stub)
    if "a2a" in surfaces:
        (project_dir / "src" / "a2a" / "server.py").write_text(
            """def serve() -> None:
    # TODO: Implement gRPC server per A2A protocol
    print("A2A server stub - implement gRPC service here")
"""
        )

    # UI scaffold
    if "ui" in surfaces:
        (project_dir / "ui" / "index.html").write_text(
            """<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Pixell Agent UI</title>
    <style>body{font-family:system-ui, sans-serif; margin:40px}</style>
  </head>
  <body>
    <h1>Pixell Agent UI</h1>
    <p>Open <code>/api/hello</code> to test REST.</p>
  </body>
  </html>
"""
        )

    # requirements.txt
    (project_dir / "requirements.txt").write_text(
        "\n".join(
            [
                "fastapi>=0.112.0",
                "uvicorn>=0.30.0",
                "watchdog>=4.0.0",
            ]
        )
        + "\n"
    )

    # .env.example
    (project_dir / ".env.example").write_text(
        """# Environment Variables Template
# Copy this file to `.env` and set values.

# SECURITY: The `.env` file is included in your APKG package.
# Use safe defaults or placeholders if you do not want to embed real secrets.

# Example: OpenAI API Key
# OPENAI_API_KEY=your-api-key-here

# Example: Network bindings (use 0.0.0.0 in containers)
# API_HOST=0.0.0.0
# API_PORT=8080

# Example: Database connection (prefer service names in Docker)
# DB_HOST=database
# DB_PORT=5432
"""
    )

    # README
    (project_dir / "README.md").write_text(
        f"""# {agent_yaml["display_name"]}

Local dev:

- Install deps: `pip install -r requirements.txt`
- Run dev: `pixell dev -p . --port 8080` then open http://localhost:8080/ui/
- Try REST: http://localhost:8080/api/hello
"""
    )

    click.secho(f"✓ Initialized project at {project_dir}", fg="green")


@click.command()
@click.option("--path", "-p", default=".", help="Path to agent project directory")
@click.option("--output", "-o", help="Output directory for APKG file")
def build_cmd(path, output):
    """Build agent into APKG file."""
    from pixell.core.builder import AgentBuilder, BuildError

    project_dir = Path(path).resolve()
    click.echo(f"Building agent from {project_dir}...")

    try:
        builder = AgentBuilder(project_dir)
        output_path = builder.build(output_dir=Path(output) if output else None)

        # Show build info
        size_mb = output_path.stat().st_size / (1024 * 1024)
        click.echo()
        click.secho("SUCCESS: Build successful!", fg="green", bold=True)
        click.echo(f"  [Package] {output_path.name}")
        click.echo(f"  [Location] {output_path.parent}")
        click.echo(f"  [Size] {size_mb:.2f} MB")

    except BuildError as e:
        click.secho(f"FAILED: Build failed: {e}", fg="red")
        ctx = click.get_current_context()
        ctx.exit(1)
    except Exception as e:
        click.secho(f"ERROR: Unexpected error: {e}", fg="red")
        ctx = click.get_current_context()
        ctx.exit(1)


@click.command(name="run-dev")
@click.option("--path", "-p", default=".", help="Path to agent project directory")
@click.option("--port", default=8080, help="Port to run the server on")
def run_dev_cmd(path, port):
    """Run agent locally for development."""
    from pixell.dev_server.server import DevServer

    project_dir = Path(path).resolve()

    try:
        server = DevServer(project_dir, port=port)
        server.run()
    except KeyboardInterrupt:
        click.echo("\nShutting down development server...")
    except Exception as e:
        click.secho(f"ERROR: Server error: {e}", fg="red")
        ctx = click.get_current_context()
        ctx.exit(1)


@click.command(name="dev")
@click.option("--path", "-p", default=".", help="Path to agent project directory")
@click.option("--port", default=8080, help="Port to run the server on")
def dev_cmd(path, port):
    """Alias for run-dev."""
    return run_dev_cmd.callback(path, port)  # type: ignore[attr-defined]


@click.command()
@click.option("--path", "-p", default=".", help="Path to agent project directory")
def validate_cmd(path):
    """Validate agent.yaml and package structure."""
    from pixell.core.validator import AgentValidator

    project_dir = Path(path).resolve()
    click.echo(f"Validating agent in {project_dir}...")

    validator = AgentValidator(project_dir)
    is_valid, errors, warnings = validator.validate()

    # Display results
    if errors:
        click.secho("FAILED: Validation failed:", fg="red", bold=True)
        for error in errors:
            click.echo(f"  - {error}")

    if warnings:
        click.echo()
        click.secho("WARNING: Warnings:", fg="yellow", bold=True)
        for warning in warnings:
            click.echo(f"  - {warning}")

    if is_valid:
        click.echo()
        click.secho("SUCCESS: Validation passed!", fg="green", bold=True)
        ctx = click.get_current_context()
        ctx.exit(0)
    else:
        ctx = click.get_current_context()
        ctx.exit(1)


@click.command()
@click.argument("package")
def inspect_cmd(package):
    """Inspect an APKG package."""
    click.echo(f"Inspecting package: {package}")
    click.echo("Not implemented yet")
