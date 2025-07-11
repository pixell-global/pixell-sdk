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
def build():
    """Build agent into APKG file."""
    click.echo("Building agent package...")
    click.echo("Not implemented yet")


@cli.command(name="run-dev")
def run_dev():
    """Run agent locally for development."""
    click.echo("Starting development server...")
    click.echo("Not implemented yet")


@cli.command()
@click.argument("package")
def inspect(package):
    """Inspect an APKG package."""
    click.echo(f"Inspecting package: {package}")
    click.echo("Not implemented yet")


@cli.command()
def validate():
    """Validate agent.yaml and package structure."""
    click.echo("Validating agent...")
    click.echo("Not implemented yet")


if __name__ == "__main__":
    cli()