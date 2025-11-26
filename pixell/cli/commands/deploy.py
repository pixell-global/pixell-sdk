"""Deploy commands for pixell CLI (deploy, status)."""

import click
import time
from pathlib import Path


@click.command()
@click.argument("deployment_id")
@click.option(
    "--env",
    "-e",
    type=click.Choice(["local", "prod"]),
    default="prod",
    help="Deployment environment (local or prod)",
)
@click.option(
    "--api-key", "-k", help="API key for authentication (can also use PIXELL_API_KEY env var)"
)
@click.option("--follow", "-f", is_flag=True, help="Follow deployment progress in real-time")
@click.option("--json", "json_output", is_flag=True, help="Output status as JSON")
def status_cmd(deployment_id, env, api_key, follow, json_output):
    """Monitor deployment status."""
    from pixell.core.deployment import (
        DeploymentClient,
        DeploymentError,
        AuthenticationError,
        get_api_key,
    )
    import json as jsonlib

    # Get API key from parameter, environment, or config
    if not api_key:
        api_key = get_api_key()

    if not api_key:
        click.secho(
            "ERROR: No API key provided. Use --api-key, set PIXELL_API_KEY environment variable, or configure in ~/.pixell/config.json",
            fg="red",
        )
        ctx = click.get_current_context()
        ctx.exit(1)

    # Create deployment client
    try:
        client = DeploymentClient(environment=env, api_key=api_key)

        if follow:
            # Follow deployment progress
            click.echo(f"Following deployment {deployment_id}...")
            click.echo()

            last_step = None
            while True:
                try:
                    response = client.get_deployment_status(deployment_id)
                    deployment = response["deployment"]

                    # Check if deployment is complete
                    if deployment["status"] in ["completed", "failed"]:
                        # Show final status
                        if deployment["status"] == "completed":
                            click.secho(
                                "✓ Deployment completed successfully!", fg="green", bold=True
                            )
                        else:
                            click.secho("✗ Deployment failed!", fg="red", bold=True)
                            if "error" in deployment:
                                click.echo(f"  Error: {deployment['error']}")

                        if "completed_at" in deployment:
                            click.echo(f"  Completed at: {deployment['completed_at']}")
                        if "duration_seconds" in deployment:
                            click.echo(f"  Duration: {deployment['duration_seconds']} seconds")

                        break

                    # Show progress
                    if "progress" in deployment:
                        progress = deployment["progress"]
                        current_step = progress.get("current_step", "")

                        if current_step != last_step:
                            last_step = current_step
                            click.echo(f"Current step: {current_step}")

                            # Show step details
                            for step in progress.get("steps", []):
                                status_symbol = {
                                    "completed": "✓",
                                    "processing": "▶",
                                    "pending": "○",
                                    "failed": "✗",
                                }.get(step["status"], "?")

                                status_color = {
                                    "completed": "green",
                                    "processing": "yellow",
                                    "failed": "red",
                                }.get(step["status"], None)

                                step_text = f"  {status_symbol} {step['name']}"
                                if status_color:
                                    click.secho(step_text, fg=status_color)
                                else:
                                    click.echo(step_text)

                    time.sleep(3)

                except KeyboardInterrupt:
                    click.echo("\nMonitoring cancelled.")
                    break

        else:
            # Single status check
            response = client.get_deployment_status(deployment_id)

            if json_output:
                click.echo(jsonlib.dumps(response, indent=2))
            else:
                deployment = response["deployment"]

                # Basic info
                click.echo(f"Deployment ID: {deployment['id']}")
                click.echo(f"Status: {deployment['status']}")
                click.echo(f"Version: {deployment.get('version', 'N/A')}")
                click.echo(f"Created: {deployment.get('created_at', 'N/A')}")

                if deployment.get("started_at"):
                    click.echo(f"Started: {deployment['started_at']}")
                if deployment.get("completed_at"):
                    click.echo(f"Completed: {deployment['completed_at']}")

                # Progress information
                if "progress" in deployment:
                    progress = deployment["progress"]
                    click.echo()
                    click.echo(f"Current step: {progress.get('current_step', 'N/A')}")
                    click.echo("Steps:")

                    for step in progress.get("steps", []):
                        status_symbol = {
                            "completed": "✓",
                            "processing": "▶",
                            "pending": "○",
                            "failed": "✗",
                        }.get(step["status"], "?")

                        click.echo(f"  {status_symbol} {step['name']} [{step['status']}]")

                        if step.get("started_at"):
                            click.echo(f"    Started: {step['started_at']}")
                        if step.get("completed_at"):
                            click.echo(f"    Completed: {step['completed_at']}")

                # Error information
                if deployment["status"] == "failed" and "error" in deployment:
                    click.echo()
                    click.secho("Error:", fg="red", bold=True)
                    click.echo(f"  {deployment['error']}")

    except AuthenticationError as e:
        click.secho(f"AUTHENTICATION ERROR: {e}", fg="red")
        ctx = click.get_current_context()
        ctx.exit(1)
    except DeploymentError as e:
        click.secho(f"DEPLOYMENT ERROR: {e}", fg="red")
        ctx = click.get_current_context()
        ctx.exit(1)
    except Exception as e:
        click.secho(f"UNEXPECTED ERROR: {e}", fg="red")
        ctx = click.get_current_context()
        ctx.exit(1)


@click.command()
@click.option(
    "--apkg-file",
    "-f",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to the APKG file to deploy",
)
@click.option(
    "--env",
    "-e",
    type=click.Choice(["local", "prod"]),
    default="prod",
    help="Deployment environment (local or prod)",
)
@click.option(
    "--app-id",
    "-a",
    help="Agent app ID to deploy to (can also use PIXELL_APP_ID env var or config file)",
)
@click.option(
    "--version", "-v", help="Version string (optional, will extract from package if not provided)"
)
@click.option("--release-notes", "-r", help="Release notes for this deployment")
@click.option(
    "--signature",
    "-s",
    type=click.Path(exists=True, path_type=Path),
    help="Path to signature file for signed packages",
)
@click.option(
    "--api-key", "-k", help="API key for authentication (can also use PIXELL_API_KEY env var)"
)
@click.option("--wait", is_flag=True, help="Wait for deployment to complete")
@click.option("--timeout", default=300, help="Timeout in seconds when waiting for deployment")
@click.option("--force", is_flag=True, help="Force overwrite existing version")
@click.option(
    "--runtime-env",
    multiple=True,
    help="Runtime environment variables in KEY=VALUE format (can specify multiple times)",
)
def deploy_cmd(
    apkg_file,
    env,
    app_id,
    version,
    release_notes,
    signature,
    api_key,
    wait,
    timeout,
    force,
    runtime_env,
):
    """Deploy an APKG file to Pixell Agent Cloud."""
    from pixell.core.deployment import (
        DeploymentClient,
        DeploymentError,
        AuthenticationError,
        InsufficientCreditsError,
        ValidationError,
        get_api_key,
        get_app_id,
    )

    # Get API key from parameter, environment, or config
    if not api_key:
        api_key = get_api_key()

    if not api_key:
        click.secho(
            "ERROR: No API key provided. Use --api-key, set PIXELL_API_KEY environment variable, or configure in ~/.pixell/config.json",
            fg="red",
        )
        ctx = click.get_current_context()
        ctx.exit(1)

    # Get app ID from parameter, environment, or config
    if not app_id:
        app_id = get_app_id(env)

    if not app_id:
        click.secho(
            f"ERROR: No app ID provided for environment '{env}'. Use --app-id, set PIXELL_APP_ID environment variable, or configure in ~/.pixell/config.json",
            fg="red",
        )
        click.secho(
            "Example config file structure:",
            fg="yellow",
        )
        click.secho(
            '{\n  "api_key": "your-api-key",\n  "environments": {\n    "prod": {"app_id": "your-prod-app-id"},\n    "local": {"app_id": "your-local-app-id"}\n  }\n}',
            fg="yellow",
        )
        ctx = click.get_current_context()
        ctx.exit(1)

    # Parse runtime environment variables
    runtime_env_dict = {}
    if runtime_env:
        for env_var in runtime_env:
            if "=" not in env_var:
                click.secho(
                    f"ERROR: Invalid runtime environment variable format: '{env_var}'. Use KEY=VALUE format.",
                    fg="red",
                )
                ctx = click.get_current_context()
                ctx.exit(1)
            key, value = env_var.split("=", 1)
            runtime_env_dict[key] = value

    # Create deployment client
    try:
        client = DeploymentClient(environment=env, api_key=api_key)

        click.echo(f"Deploying {apkg_file.name} to {client.ENVIRONMENTS[env]['name']}...")
        click.echo(f"Target: {client.base_url}")
        click.echo(f"App ID: {app_id}")

        if version:
            click.echo(f"Version: {version}")
        if release_notes:
            click.echo(f"Release notes: {release_notes}")
        if force:
            click.echo(click.style("Force overwrite: ENABLED", fg="yellow", bold=True))
        if runtime_env_dict:
            click.echo(f"Runtime environment variables: {len(runtime_env_dict)} variable(s)")

        # Start deployment
        response = client.deploy(
            app_id=app_id,
            apkg_file=apkg_file,
            version=version,
            release_notes=release_notes,
            signature_file=signature,
            force_overwrite=force,
            runtime_env=runtime_env_dict if runtime_env_dict else None,
        )

        deployment = response["deployment"]
        package = response["package"]
        tracking = response["tracking"]

        # Show deployment info
        click.echo()
        click.secho("✓ Deployment initiated successfully!", fg="green", bold=True)
        click.echo(f"  Deployment ID: {deployment['id']}")
        click.echo(f"  Package ID: {package['id']}")
        click.echo(f"  Status: {deployment['status']}")
        click.echo(f"  Version: {package['version']}")
        click.echo(f"  Size: {package['size_bytes'] / (1024 * 1024):.1f} MB")
        click.echo(f"  Queued at: {deployment['queued_at']}")

        if "estimated_duration_seconds" in deployment:
            click.echo(f"  Estimated duration: {deployment['estimated_duration_seconds']} seconds")

        click.echo()
        click.echo(f"Track deployment status: {tracking['status_url']}")

        # Wait for completion if requested
        if wait:
            click.echo()
            click.echo("Waiting for deployment to complete...")

            try:
                with click.progressbar(length=timeout, label="Deploying") as bar:
                    start_time = time.time()
                    while time.time() - start_time < timeout:
                        status = client.get_deployment_status(deployment["id"])
                        deployment_status = status["deployment"]["status"]

                        if deployment_status == "completed":
                            bar.update(timeout)  # Complete the progress bar
                            click.echo()
                            click.secho(
                                "✓ Deployment completed successfully!", fg="green", bold=True
                            )

                            # Show final status
                            final_deployment = status["deployment"]
                            if "completed_at" in final_deployment:
                                click.echo(f"  Completed at: {final_deployment['completed_at']}")

                            return
                        elif deployment_status == "failed":
                            bar.update(timeout)  # Complete the progress bar
                            click.echo()
                            click.secho("✗ Deployment failed!", fg="red", bold=True)
                            error_msg = status["deployment"].get("error", "Unknown error")
                            click.echo(f"  Error: {error_msg}")
                            ctx = click.get_current_context()
                            ctx.exit(1)

                        # Update progress
                        elapsed = int(time.time() - start_time)
                        bar.update(min(elapsed, timeout))
                        time.sleep(5)

                # Timeout reached
                click.echo()
                click.secho("⚠ Deployment timed out", fg="yellow", bold=True)
                click.echo(f"  Check status manually: {tracking['status_url']}")

            except KeyboardInterrupt:
                click.echo()
                click.echo("Deployment monitoring cancelled. Check status manually:")
                click.echo(f"  {tracking['status_url']}")

    except AuthenticationError as e:
        click.secho(f"AUTHENTICATION ERROR: {e}", fg="red")
        ctx = click.get_current_context()
        ctx.exit(1)
    except InsufficientCreditsError as e:
        click.secho(f"INSUFFICIENT CREDITS: {e}", fg="red")
        ctx = click.get_current_context()
        ctx.exit(1)
    except ValidationError as e:
        click.secho(f"VALIDATION ERROR: {e}", fg="red")
        ctx = click.get_current_context()
        ctx.exit(1)
    except DeploymentError as e:
        click.secho(f"DEPLOYMENT ERROR: {e}", fg="red")
        ctx = click.get_current_context()
        ctx.exit(1)
    except Exception as e:
        click.secho(f"UNEXPECTED ERROR: {e}", fg="red")
        ctx = click.get_current_context()
        ctx.exit(1)
