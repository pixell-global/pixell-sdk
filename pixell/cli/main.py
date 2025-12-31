"""PixellSDK CLI - Build and deploy AI agent applications.

This is the main entry point for the pixell CLI.
All commands are defined in pixell.cli.commands modules.
"""

import click
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("pixell-sdk")
except PackageNotFoundError:
    __version__ = "0.4.12-dev"


@click.group()
@click.version_option(version=__version__, prog_name="pixell")
def cli():
    """PixellSDK - Build and deploy AI agent applications."""
    pass


# Import all commands from commands package
from pixell.cli.commands import (  # noqa: E402
    init_cmd,
    build_cmd,
    run_dev_cmd,
    dev_cmd,
    validate_cmd,
    inspect_cmd,
    deploy_cmd,
    status_cmd,
    config,
    secrets,
    ui,
    validate_intents_cmd,
    list_cmd,
    test_cmd,
    guide_cmd,
)

# Register top-level commands
cli.add_command(init_cmd, name="init")
cli.add_command(build_cmd, name="build")
cli.add_command(run_dev_cmd, name="run-dev")
cli.add_command(dev_cmd, name="dev")
cli.add_command(validate_cmd, name="validate")
cli.add_command(inspect_cmd, name="inspect")
cli.add_command(deploy_cmd, name="deploy")
cli.add_command(status_cmd, name="status")
cli.add_command(validate_intents_cmd, name="validate-intents")
cli.add_command(list_cmd, name="list")
cli.add_command(test_cmd, name="test")
cli.add_command(guide_cmd, name="guide")

# Register command groups
cli.add_command(config)
cli.add_command(secrets)
cli.add_command(ui)

if __name__ == "__main__":
    cli()
