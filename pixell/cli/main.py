import click
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("pixell-kit")
except PackageNotFoundError:
    __version__ = "0.1.0-dev"


@click.group()
@click.version_option(version=__version__, prog_name="pixell")
def cli():
    """Pixell Kit - Package AI agents into portable APKG files."""
    pass


@cli.command()
@click.argument("name")
def init(name):
    """Initialize a new agent project."""
    click.echo(f"Initializing agent project: {name}")
    click.echo("Not implemented yet")


@cli.command()
@click.option('--path', '-p', default='.', help='Path to agent project directory')
@click.option('--output', '-o', help='Output directory for APKG file')
def build(path, output):
    """Build agent into APKG file."""
    from pathlib import Path
    from pixell.core.builder import AgentBuilder, BuildError
    
    project_dir = Path(path).resolve()
    click.echo(f"Building agent from {project_dir}...")
    
    try:
        builder = AgentBuilder(project_dir)
        output_path = builder.build(output_dir=Path(output) if output else None)
        
        # Show build info
        size_mb = output_path.stat().st_size / (1024 * 1024)
        click.echo()
        click.secho("✅ Build successful!", fg='green', bold=True)
        click.echo(f"  📦 Package: {output_path.name}")
        click.echo(f"  📁 Location: {output_path.parent}")
        click.echo(f"  📏 Size: {size_mb:.2f} MB")
        
    except BuildError as e:
        click.secho(f"❌ Build failed: {e}", fg='red')
        ctx = click.get_current_context()
        ctx.exit(1)
    except Exception as e:
        click.secho(f"❌ Unexpected error: {e}", fg='red')
        ctx = click.get_current_context()
        ctx.exit(1)


@cli.command(name="run-dev")
@click.option('--path', '-p', default='.', help='Path to agent project directory')
@click.option('--port', default=8080, help='Port to run the server on')
def run_dev(path, port):
    """Run agent locally for development."""
    from pathlib import Path
    from pixell.dev_server.server import DevServer
    
    project_dir = Path(path).resolve()
    
    try:
        server = DevServer(project_dir, port=port)
        server.run()
    except KeyboardInterrupt:
        click.echo("\n👋 Shutting down development server...")
    except Exception as e:
        click.secho(f"❌ Server error: {e}", fg='red')
        ctx = click.get_current_context()
        ctx.exit(1)


@cli.command()
@click.argument("package")
def inspect(package):
    """Inspect an APKG package."""
    click.echo(f"Inspecting package: {package}")
    click.echo("Not implemented yet")


@cli.command()
@click.option('--path', '-p', default='.', help='Path to agent project directory')
def validate(path):
    """Validate agent.yaml and package structure."""
    from pathlib import Path
    from pixell.core.validator import AgentValidator
    
    project_dir = Path(path).resolve()
    click.echo(f"Validating agent in {project_dir}...")
    
    validator = AgentValidator(project_dir)
    is_valid, errors, warnings = validator.validate()
    
    # Display results
    if errors:
        click.secho("❌ Validation failed:", fg='red', bold=True)
        for error in errors:
            click.echo(f"  • {error}")
    
    if warnings:
        click.echo()
        click.secho("⚠️  Warnings:", fg='yellow', bold=True)
        for warning in warnings:
            click.echo(f"  • {warning}")
    
    if is_valid:
        click.echo()
        click.secho("✅ Validation passed!", fg='green', bold=True)
        ctx = click.get_current_context()
        ctx.exit(0)
    else:
        ctx = click.get_current_context()
        ctx.exit(1)


if __name__ == "__main__":
    cli()