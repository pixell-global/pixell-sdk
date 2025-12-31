"""Config commands for pixell CLI."""

import click
import json
from pathlib import Path


@click.group()
def config():
    """Manage Pixell configuration."""
    pass


@config.command("set")
@click.option("--api-key", "-k", help="Set API key")
@click.option("--app-id", "-a", help="Set app ID")
@click.option("--environment", "-e", help="Set default environment")
@click.option("--env-app-id", help="Set app ID for specific environment (format: env:app-id)")
@click.option(
    "--global", "is_global", is_flag=True, help="Set global configuration (default: project-level)"
)
def config_set(api_key, app_id, environment, env_app_id, is_global):
    """Set configuration values."""
    # Determine config file location
    if is_global:
        config_dir = Path.home() / ".pixell"
        config_file = config_dir / "config.json"
    else:
        config_dir = Path(".pixell")
        config_file = config_dir / "config.json"

    # Create config directory if it doesn't exist
    config_dir.mkdir(parents=True, exist_ok=True)

    # Load existing config
    config_data = {}
    if config_file.exists():
        try:
            with open(config_file) as f:
                config_data = json.load(f)
        except Exception:
            pass

    # Update config values
    if api_key:
        config_data["api_key"] = api_key
        click.secho(f"✓ API key set in {config_file}", fg="green")

    if app_id:
        config_data["app_id"] = app_id
        click.secho(f"✓ App ID set in {config_file}", fg="green")

    if environment:
        config_data["default_environment"] = environment
        click.secho(f"✓ Default environment set to '{environment}' in {config_file}", fg="green")

    if env_app_id:
        if ":" not in env_app_id:
            click.secho("ERROR: env-app-id must be in format 'environment:app-id'", fg="red")
            return

        env_name, env_app_id_value = env_app_id.split(":", 1)
        if "environments" not in config_data:
            config_data["environments"] = {}
        config_data["environments"][env_name] = {"app_id": env_app_id_value}
        click.secho(f"✓ App ID for environment '{env_name}' set in {config_file}", fg="green")

    # Save config
    with open(config_file, "w") as f:
        json.dump(config_data, f, indent=2)

    if not any([api_key, app_id, environment, env_app_id]):
        click.secho("No values provided. Use --help to see available options.", fg="yellow")


@config.command("show")
@click.option(
    "--global", "is_global", is_flag=True, help="Show global configuration (default: project-level)"
)
def config_show(is_global):
    """Show current configuration."""
    # Determine config file location
    if is_global:
        config_file = Path.home() / ".pixell" / "config.json"
        config_type = "Global"
    else:
        config_file = Path(".pixell") / "config.json"
        config_type = "Project"

    if not config_file.exists():
        click.secho(f"No {config_type.lower()} configuration found at {config_file}", fg="yellow")
        return

    try:
        with open(config_file) as f:
            config_data = json.load(f)

        click.secho(f"{config_type} Configuration ({config_file}):", fg="cyan", bold=True)
        click.echo(json.dumps(config_data, indent=2))
    except Exception as e:
        click.secho(f"Error reading config file: {e}", fg="red")


@config.command("init")
@click.option("--api-key", "-k", prompt="API Key", help="Your Pixell API key")
@click.option("--app-id", "-a", prompt="App ID", help="Your default app ID")
@click.option("--environment", "-e", default="prod", help="Default environment")
@click.option(
    "--global",
    "is_global",
    is_flag=True,
    help="Initialize global configuration (default: project-level)",
)
def config_init(api_key, app_id, environment, is_global):
    """Initialize configuration with interactive setup."""
    # Determine config file location
    if is_global:
        config_dir = Path.home() / ".pixell"
        config_file = config_dir / "config.json"
    else:
        config_dir = Path(".pixell")
        config_file = config_dir / "config.json"

    # Create config directory if it doesn't exist
    config_dir.mkdir(parents=True, exist_ok=True)

    # Create initial config
    config_data = {"api_key": api_key, "app_id": app_id, "default_environment": environment}

    # Save config
    with open(config_file, "w") as f:
        json.dump(config_data, f, indent=2)

    click.secho(f"✓ Configuration initialized at {config_file}", fg="green")
    click.secho(
        "You can now deploy without specifying --api-key and --app-id every time!", fg="cyan"
    )
