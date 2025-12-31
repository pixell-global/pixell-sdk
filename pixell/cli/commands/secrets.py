"""Secrets commands for pixell CLI."""

import click
from pathlib import Path


@click.group()
def secrets():
    """Manage environment variables/secrets for agent apps.

    Exit codes:
        0 - Success
        1 - General error (validation, file parsing, etc.)
        2 - Authentication error (invalid API key)
        3 - Not found error (secret or app not found)
    """
    pass


@secrets.command(name="list")
@click.option(
    "--app-id",
    "-a",
    help="Agent app ID (can also use PIXELL_APP_ID env var)",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format (table or json)",
)
@click.option(
    "--api-key",
    "-k",
    help="API key for authentication (can also use PIXELL_API_KEY env var)",
)
@click.option(
    "--env",
    "-e",
    type=click.Choice(["local", "prod"]),
    default="prod",
    help="Environment (local or prod)",
)
def secrets_list(app_id, format, api_key, env):
    """List all secrets for an agent app."""
    from pixell.core.secrets import SecretsClient, SecretsError, SecretNotFoundError
    from pixell.core.secrets_utils import format_secrets_table
    from pixell.core.deployment import get_app_id, get_api_key, AuthenticationError
    import json as jsonlib

    # Get app ID from parameter or environment
    if not app_id:
        app_id = get_app_id(env)

    if not app_id:
        click.secho(
            "ERROR: No app ID provided. Use --app-id, set PIXELL_APP_ID environment variable, or configure in ~/.pixell/config.json",
            fg="red",
        )
        ctx = click.get_current_context()
        ctx.exit(1)

    # Get API key
    if not api_key:
        api_key = get_api_key()

    if not api_key:
        click.secho(
            "ERROR: No API key provided. Use --api-key, set PIXELL_API_KEY environment variable, or configure in ~/.pixell/config.json",
            fg="red",
        )
        ctx = click.get_current_context()
        ctx.exit(1)

    try:
        client = SecretsClient(environment=env, api_key=api_key)
        secrets_data = client.list_secrets(app_id)

        if format == "json":
            click.echo(jsonlib.dumps({"secrets": secrets_data}, indent=2))
        else:
            if secrets_data:
                table = format_secrets_table(secrets_data, mask=True)
                click.echo(table)
            else:
                click.echo("No secrets found.")

    except AuthenticationError as e:
        click.secho(f"AUTHENTICATION ERROR: {e}", fg="red")
        ctx = click.get_current_context()
        ctx.exit(2)
    except SecretNotFoundError as e:
        click.secho(f"NOT FOUND: {e}", fg="red")
        ctx = click.get_current_context()
        ctx.exit(3)
    except SecretsError as e:
        click.secho(f"ERROR: {e}", fg="red")
        ctx = click.get_current_context()
        ctx.exit(1)


@secrets.command(name="get")
@click.argument("key")
@click.option(
    "--app-id",
    "-a",
    help="Agent app ID (can also use PIXELL_APP_ID env var)",
)
@click.option(
    "--api-key",
    "-k",
    help="API key for authentication (can also use PIXELL_API_KEY env var)",
)
@click.option(
    "--env",
    "-e",
    type=click.Choice(["local", "prod"]),
    default="prod",
    help="Environment (local or prod)",
)
def secrets_get(key, app_id, api_key, env):
    """Get a single secret value (unmasked).

    This command outputs only the secret value, making it suitable for scripting.
    """
    from pixell.core.secrets import SecretsClient, SecretsError, SecretNotFoundError
    from pixell.core.deployment import get_app_id, get_api_key, AuthenticationError

    # Get app ID from parameter or environment
    if not app_id:
        app_id = get_app_id(env)

    if not app_id:
        click.secho(
            "ERROR: No app ID provided. Use --app-id, set PIXELL_APP_ID environment variable, or configure in ~/.pixell/config.json",
            fg="red",
        )
        ctx = click.get_current_context()
        ctx.exit(1)

    # Get API key
    if not api_key:
        api_key = get_api_key()

    if not api_key:
        click.secho(
            "ERROR: No API key provided. Use --api-key, set PIXELL_API_KEY environment variable, or configure in ~/.pixell/config.json",
            fg="red",
        )
        ctx = click.get_current_context()
        ctx.exit(1)

    try:
        client = SecretsClient(environment=env, api_key=api_key)
        value = client.get_secret(app_id, key)
        click.echo(value)

    except AuthenticationError as e:
        click.secho(f"AUTHENTICATION ERROR: {e}", fg="red")
        ctx = click.get_current_context()
        ctx.exit(2)
    except SecretNotFoundError as e:
        click.secho(f"NOT FOUND: {e}", fg="red")
        ctx = click.get_current_context()
        ctx.exit(3)
    except SecretsError as e:
        click.secho(f"ERROR: {e}", fg="red")
        ctx = click.get_current_context()
        ctx.exit(1)


@secrets.command(name="set")
@click.option(
    "--app-id",
    "-a",
    help="Agent app ID (can also use PIXELL_APP_ID env var)",
)
@click.option(
    "--file",
    "-f",
    type=click.Path(exists=True, path_type=Path),
    help="Path to JSON or .env file containing secrets",
)
@click.option(
    "--secret",
    "-s",
    multiple=True,
    help="Secret in KEY=VALUE format (can specify multiple times)",
)
@click.option(
    "--api-key",
    "-k",
    help="API key for authentication (can also use PIXELL_API_KEY env var)",
)
@click.option(
    "--env",
    "-e",
    type=click.Choice(["local", "prod"]),
    default="prod",
    help="Environment (local or prod)",
)
def secrets_set(app_id, file, secret, api_key, env):
    """Set/replace all secrets for an agent app (bulk operation).

    WARNING: This replaces ALL secrets with the provided values.
    Existing secrets not in the request will be deleted.

    Examples:
        pixell secrets set -a app-123 --file secrets.json
        pixell secrets set -a app-123 -s OPENAI_API_KEY=sk-xxx -s DEBUG=false
    """
    from pixell.core.secrets import SecretsClient, SecretsError, SecretNotFoundError
    from pixell.core.secrets_utils import parse_json_file, parse_env_file, validate_secret_key
    from pixell.core.deployment import get_app_id, get_api_key, AuthenticationError

    # Get app ID from parameter or environment
    if not app_id:
        app_id = get_app_id(env)

    if not app_id:
        click.secho(
            "ERROR: No app ID provided. Use --app-id, set PIXELL_APP_ID environment variable, or configure in ~/.pixell/config.json",
            fg="red",
        )
        ctx = click.get_current_context()
        ctx.exit(1)

    # Get API key
    if not api_key:
        api_key = get_api_key()

    if not api_key:
        click.secho(
            "ERROR: No API key provided. Use --api-key, set PIXELL_API_KEY environment variable, or configure in ~/.pixell/config.json",
            fg="red",
        )
        ctx = click.get_current_context()
        ctx.exit(1)

    # Parse secrets from file or command line
    secrets_data = {}

    if file:
        try:
            if file.suffix == ".json":
                secrets_data = parse_json_file(file)
            elif file.suffix == ".env" or file.name == ".env":
                secrets_data = parse_env_file(file)
            else:
                click.secho(
                    f"ERROR: Unsupported file format: {file.suffix}. Use .json or .env files.",
                    fg="red",
                )
                ctx = click.get_current_context()
                ctx.exit(1)
        except SecretsError as e:
            click.secho(f"ERROR: Failed to parse file: {e}", fg="red")
            ctx = click.get_current_context()
            ctx.exit(1)

    if secret:
        for s in secret:
            if "=" not in s:
                click.secho(
                    f"ERROR: Invalid secret format: '{s}'. Use KEY=VALUE format.",
                    fg="red",
                )
                ctx = click.get_current_context()
                ctx.exit(1)
            key, value = s.split("=", 1)
            secrets_data[key] = value

    if not secrets_data:
        click.secho(
            "ERROR: No secrets provided. Use --file or --secret to specify secrets.",
            fg="red",
        )
        ctx = click.get_current_context()
        ctx.exit(1)

    # Validate all keys
    for key in secrets_data.keys():
        if not validate_secret_key(key):
            click.secho(
                f"ERROR: Invalid secret key '{key}'. Keys must contain only uppercase letters, numbers, and underscores.",
                fg="red",
            )
            ctx = click.get_current_context()
            ctx.exit(1)

    # Confirm operation
    click.echo(
        f"This will replace ALL secrets for app {app_id} with {len(secrets_data)} secret(s)."
    )
    click.echo("Existing secrets not in this list will be deleted.")
    if not click.confirm("Do you want to continue?"):
        click.echo("Cancelled.")
        ctx = click.get_current_context()
        ctx.exit(0)

    try:
        client = SecretsClient(environment=env, api_key=api_key)
        result = client.set_secrets(app_id, secrets_data)

        click.secho("✓ Secrets saved successfully!", fg="green", bold=True)
        click.echo(f"  Total secrets: {result.get('secretCount', len(secrets_data))}")

    except AuthenticationError as e:
        click.secho(f"AUTHENTICATION ERROR: {e}", fg="red")
        ctx = click.get_current_context()
        ctx.exit(2)
    except SecretNotFoundError as e:
        click.secho(f"NOT FOUND: {e}", fg="red")
        ctx = click.get_current_context()
        ctx.exit(3)
    except SecretsError as e:
        click.secho(f"ERROR: {e}", fg="red")
        ctx = click.get_current_context()
        ctx.exit(1)


@secrets.command(name="update")
@click.argument("key")
@click.argument("value")
@click.option(
    "--app-id",
    "-a",
    help="Agent app ID (can also use PIXELL_APP_ID env var)",
)
@click.option(
    "--api-key",
    "-k",
    help="API key for authentication (can also use PIXELL_API_KEY env var)",
)
@click.option(
    "--env",
    "-e",
    type=click.Choice(["local", "prod"]),
    default="prod",
    help="Environment (local or prod)",
)
def secrets_update(key, value, app_id, api_key, env):
    """Update or create a single secret.

    Does not affect other secrets.

    Example:
        pixell secrets update -a app-123 OPENAI_API_KEY sk-new-key
    """
    from pixell.core.secrets import SecretsClient, SecretsError, SecretNotFoundError
    from pixell.core.secrets_utils import validate_secret_key
    from pixell.core.deployment import get_app_id, get_api_key, AuthenticationError

    # Get app ID from parameter or environment
    if not app_id:
        app_id = get_app_id(env)

    if not app_id:
        click.secho(
            "ERROR: No app ID provided. Use --app-id, set PIXELL_APP_ID environment variable, or configure in ~/.pixell/config.json",
            fg="red",
        )
        ctx = click.get_current_context()
        ctx.exit(1)

    # Get API key
    if not api_key:
        api_key = get_api_key()

    if not api_key:
        click.secho(
            "ERROR: No API key provided. Use --api-key, set PIXELL_API_KEY environment variable, or configure in ~/.pixell/config.json",
            fg="red",
        )
        ctx = click.get_current_context()
        ctx.exit(1)

    # Validate key format
    if not validate_secret_key(key):
        click.secho(
            f"ERROR: Invalid secret key '{key}'. Keys must contain only uppercase letters, numbers, and underscores.",
            fg="red",
        )
        ctx = click.get_current_context()
        ctx.exit(1)

    try:
        client = SecretsClient(environment=env, api_key=api_key)
        client.update_secret(app_id, key, value)

        click.secho(f"✓ Secret '{key}' updated successfully!", fg="green", bold=True)

    except AuthenticationError as e:
        click.secho(f"AUTHENTICATION ERROR: {e}", fg="red")
        ctx = click.get_current_context()
        ctx.exit(2)
    except SecretNotFoundError as e:
        click.secho(f"NOT FOUND: {e}", fg="red")
        ctx = click.get_current_context()
        ctx.exit(3)
    except SecretsError as e:
        click.secho(f"ERROR: {e}", fg="red")
        ctx = click.get_current_context()
        ctx.exit(1)


@secrets.command(name="delete")
@click.argument("key")
@click.option(
    "--app-id",
    "-a",
    help="Agent app ID (can also use PIXELL_APP_ID env var)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Skip confirmation prompt",
)
@click.option(
    "--api-key",
    "-k",
    help="API key for authentication (can also use PIXELL_API_KEY env var)",
)
@click.option(
    "--env",
    "-e",
    type=click.Choice(["local", "prod"]),
    default="prod",
    help="Environment (local or prod)",
)
def secrets_delete(key, app_id, force, api_key, env):
    """Delete a single secret.

    Example:
        pixell secrets delete -a app-123 DEBUG
        pixell secrets delete -a app-123 TEMP_KEY --force
    """
    from pixell.core.secrets import SecretsClient, SecretsError, SecretNotFoundError
    from pixell.core.deployment import get_app_id, get_api_key, AuthenticationError

    # Get app ID from parameter or environment
    if not app_id:
        app_id = get_app_id(env)

    if not app_id:
        click.secho(
            "ERROR: No app ID provided. Use --app-id, set PIXELL_APP_ID environment variable, or configure in ~/.pixell/config.json",
            fg="red",
        )
        ctx = click.get_current_context()
        ctx.exit(1)

    # Get API key
    if not api_key:
        api_key = get_api_key()

    if not api_key:
        click.secho(
            "ERROR: No API key provided. Use --api-key, set PIXELL_API_KEY environment variable, or configure in ~/.pixell/config.json",
            fg="red",
        )
        ctx = click.get_current_context()
        ctx.exit(1)

    # Confirm deletion
    if not force:
        if not click.confirm(f"Are you sure you want to delete secret '{key}'?"):
            click.echo("Cancelled.")
            ctx = click.get_current_context()
            ctx.exit(0)

    try:
        client = SecretsClient(environment=env, api_key=api_key)
        client.delete_secret(app_id, key)

        click.secho(f"✓ Secret '{key}' deleted successfully!", fg="green", bold=True)

    except AuthenticationError as e:
        click.secho(f"AUTHENTICATION ERROR: {e}", fg="red")
        ctx = click.get_current_context()
        ctx.exit(2)
    except SecretNotFoundError as e:
        click.secho(f"NOT FOUND: {e}", fg="red")
        ctx = click.get_current_context()
        ctx.exit(3)
    except SecretsError as e:
        click.secho(f"ERROR: {e}", fg="red")
        ctx = click.get_current_context()
        ctx.exit(1)


@secrets.command(name="delete-all")
@click.option(
    "--app-id",
    "-a",
    help="Agent app ID (can also use PIXELL_APP_ID env var)",
)
@click.option(
    "--confirm",
    is_flag=True,
    help="Confirm deletion (required)",
)
@click.option(
    "--api-key",
    "-k",
    help="API key for authentication (can also use PIXELL_API_KEY env var)",
)
@click.option(
    "--env",
    "-e",
    type=click.Choice(["local", "prod"]),
    default="prod",
    help="Environment (local or prod)",
)
def secrets_delete_all(app_id, confirm, api_key, env):
    """Delete all secrets for an agent app.

    WARNING: This will delete ALL secrets for the agent app.

    Example:
        pixell secrets delete-all -a app-123 --confirm
    """
    from pixell.core.secrets import SecretsClient, SecretsError, SecretNotFoundError
    from pixell.core.deployment import get_app_id, get_api_key, AuthenticationError

    # Get app ID from parameter or environment
    if not app_id:
        app_id = get_app_id(env)

    if not app_id:
        click.secho(
            "ERROR: No app ID provided. Use --app-id, set PIXELL_APP_ID environment variable, or configure in ~/.pixell/config.json",
            fg="red",
        )
        ctx = click.get_current_context()
        ctx.exit(1)

    # Get API key
    if not api_key:
        api_key = get_api_key()

    if not api_key:
        click.secho(
            "ERROR: No API key provided. Use --api-key, set PIXELL_API_KEY environment variable, or configure in ~/.pixell/config.json",
            fg="red",
        )
        ctx = click.get_current_context()
        ctx.exit(1)

    # Require explicit confirmation
    if not confirm:
        click.secho(
            "ERROR: This command requires --confirm flag to proceed.",
            fg="red",
        )
        click.echo("This will delete ALL secrets for the agent app.")
        ctx = click.get_current_context()
        ctx.exit(1)

    # Double confirmation
    click.secho(f"WARNING: This will delete ALL secrets for app {app_id}", fg="yellow", bold=True)
    if not click.confirm("Are you absolutely sure?"):
        click.echo("Cancelled.")
        ctx = click.get_current_context()
        ctx.exit(0)

    try:
        client = SecretsClient(environment=env, api_key=api_key)
        client.delete_all_secrets(app_id)

        click.secho("✓ All secrets deleted successfully!", fg="green", bold=True)

    except AuthenticationError as e:
        click.secho(f"AUTHENTICATION ERROR: {e}", fg="red")
        ctx = click.get_current_context()
        ctx.exit(2)
    except SecretNotFoundError as e:
        click.secho(f"NOT FOUND: {e}", fg="red")
        ctx = click.get_current_context()
        ctx.exit(3)
    except SecretsError as e:
        click.secho(f"ERROR: {e}", fg="red")
        ctx = click.get_current_context()
        ctx.exit(1)
