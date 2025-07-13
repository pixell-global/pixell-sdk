import click
import time
from pathlib import Path
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
        click.secho("SUCCESS: Build successful!", fg='green', bold=True)
        click.echo(f"  [Package] {output_path.name}")
        click.echo(f"  [Location] {output_path.parent}")
        click.echo(f"  [Size] {size_mb:.2f} MB")
        
    except BuildError as e:
        click.secho(f"FAILED: Build failed: {e}", fg='red')
        ctx = click.get_current_context()
        ctx.exit(1)
    except Exception as e:
        click.secho(f"ERROR: Unexpected error: {e}", fg='red')
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
        click.echo("\nShutting down development server...")
    except Exception as e:
        click.secho(f"ERROR: Server error: {e}", fg='red')
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
        click.secho("FAILED: Validation failed:", fg='red', bold=True)
        for error in errors:
            click.echo(f"  - {error}")
    
    if warnings:
        click.echo()
        click.secho("WARNING: Warnings:", fg='yellow', bold=True)
        for warning in warnings:
            click.echo(f"  - {warning}")
    
    if is_valid:
        click.echo()
        click.secho("SUCCESS: Validation passed!", fg='green', bold=True)
        ctx = click.get_current_context()
        ctx.exit(0)
    else:
        ctx = click.get_current_context()
        ctx.exit(1)


@cli.command()
@click.option('--format', '-f', type=click.Choice(['table', 'json', 'detailed']), default='table', 
              help='Output format (table, json, or detailed)')
@click.option('--search', '-s', help='Search for agents by name, description, or tags')
@click.option('--show-sub-agents', is_flag=True, help='Show sub-agents in table view')
def list(format, search, show_sub_agents):
    """List installed agents with detailed information."""
    from pixell.core.registry import Registry
    import json
    
    registry = Registry()
    
    # Get agents based on search
    if search:
        agents = registry.search_agents(search)
        if not agents:
            click.echo(f"No agents found matching '{search}'")
            return
    else:
        agents = registry.list_agents(detailed=(format == 'detailed' or show_sub_agents))
    
    if format == 'table':
        # Table format with basic info
        if not agents:
            click.echo("No agents installed.")
            click.echo("\nUse 'pixell install <package>' to install an agent.")
            return
        
        # Calculate column widths
        name_width = max(20, max(len(a.display_name) for a in agents) + 2)
        version_width = 10
        author_width = max(15, max(len(a.author) for a in agents) + 2)
        
        # Header
        click.echo()
        header = f"{'Name':<{name_width}} {'Version':<{version_width}} {'Author':<{author_width}} Description"
        click.echo(header)
        click.echo("-" * len(header))
        
        # Agent rows
        for agent in agents:
            desc = agent.description[:50] + "..." if len(agent.description) > 50 else agent.description
            click.echo(f"{agent.display_name:<{name_width}} {agent.version:<{version_width}} {agent.author:<{author_width}} {desc}")
            
            # Show sub-agents if requested
            if show_sub_agents and agent.sub_agents:
                for sub in agent.sub_agents:
                    sub_desc = sub.description[:40] + "..." if len(sub.description) > 40 else sub.description
                    public_tag = "[public]" if sub.public else "[private]"
                    click.echo(f"  └─ {sub.name:<{name_width-3}} {'':<{version_width}} {public_tag:<{author_width}} {sub_desc}")
        
        click.echo()
        click.echo(f"Total: {len(agents)} agent(s)")
        click.echo("\nUse 'pixell list --format detailed' for full information")
        click.echo("Use 'pixell list --show-sub-agents' to see sub-agents")
        
    elif format == 'json':
        # JSON format with all details
        agents_data = [agent.to_dict() for agent in registry.list_agents(detailed=True)]
        click.echo(json.dumps(agents_data, indent=2))
        
    else:  # detailed format
        # Detailed format with extensive information
        for i, agent in enumerate(agents):
            if i > 0:
                click.echo("\n" + "="*80 + "\n")
            
            # Basic info
            click.secho(f"{agent.display_name} v{agent.version}", fg='green', bold=True)
            click.echo(f"Package name: {agent.name}")
            click.echo(f"Author: {agent.author}")
            click.echo(f"License: {agent.license}")
            if agent.homepage:
                click.echo(f"Homepage: {agent.homepage}")
            
            # Description
            click.echo(f"\n{agent.description}")
            
            # Extensive description
            if agent.extensive_description:
                click.echo("\nDetailed Description:")
                for line in agent.extensive_description.strip().split('\n'):
                    click.echo(f"  {line}")
            
            # Capabilities and tags
            if agent.capabilities:
                click.echo(f"\nCapabilities: {', '.join(agent.capabilities)}")
            if agent.tags:
                click.echo(f"Tags: {', '.join(agent.tags)}")
            
            # Sub-agents
            if agent.sub_agents:
                click.echo("\nSub-agents:")
                for sub in agent.sub_agents:
                    status = "PUBLIC" if sub.public else "PRIVATE"
                    click.echo(f"  • {sub.name} [{status}]")
                    click.echo(f"    Description: {sub.description}")
                    click.echo(f"    Endpoint: {sub.endpoint}")
                    click.echo(f"    Capabilities: {', '.join(sub.capabilities)}")
            
            # Usage guide
            if agent.usage_guide:
                click.echo("\nUsage Guide:")
                for line in agent.usage_guide.strip().split('\n'):
                    click.echo(f"  {line}")
            
            # Examples
            if agent.examples:
                click.echo("\nExamples:")
                for example in agent.examples:
                    click.echo(f"  {example['title']}:")
                    click.echo(f"    {example['code']}")
            
            # Technical details
            click.echo("\nTechnical Details:")
            if agent.runtime_requirements:
                click.echo(f"  Runtime: {agent.runtime_requirements}")
            if agent.dependencies:
                click.echo(f"  Dependencies: {', '.join(agent.dependencies)}")
            if agent.install_date:
                click.echo(f"  Installed: {agent.install_date.strftime('%Y-%m-%d %H:%M:%S')}")
            if agent.install_path:
                click.echo(f"  Location: {agent.install_path}")
            if agent.package_size:
                size_mb = agent.package_size / (1024 * 1024)
                click.echo(f"  Size: {size_mb:.1f} MB")


@cli.command()
@click.argument('deployment_id')
@click.option('--env', '-e', type=click.Choice(['local', 'prod']), default='prod',
              help='Deployment environment (local or prod)')
@click.option('--api-key', '-k', help='API key for authentication (can also use PIXELL_API_KEY env var)')
@click.option('--follow', '-f', is_flag=True, help='Follow deployment progress in real-time')
@click.option('--json', 'json_output', is_flag=True, help='Output status as JSON')
def status(deployment_id, env, api_key, follow, json_output):
    """Monitor deployment status."""
    from pixell.core.deployment import DeploymentClient, DeploymentError, AuthenticationError, get_api_key
    import json as jsonlib
    
    # Get API key from parameter, environment, or config
    if not api_key:
        api_key = get_api_key()
    
    if not api_key:
        click.secho("ERROR: No API key provided. Use --api-key, set PIXELL_API_KEY environment variable, or configure in ~/.pixell/config.json", fg='red')
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
                    deployment = response['deployment']
                    
                    # Check if deployment is complete
                    if deployment['status'] in ['completed', 'failed']:
                        # Show final status
                        if deployment['status'] == 'completed':
                            click.secho("✓ Deployment completed successfully!", fg='green', bold=True)
                        else:
                            click.secho("✗ Deployment failed!", fg='red', bold=True)
                            if 'error' in deployment:
                                click.echo(f"  Error: {deployment['error']}")
                        
                        if 'completed_at' in deployment:
                            click.echo(f"  Completed at: {deployment['completed_at']}")
                        if 'duration_seconds' in deployment:
                            click.echo(f"  Duration: {deployment['duration_seconds']} seconds")
                        
                        break
                    
                    # Show progress
                    if 'progress' in deployment:
                        progress = deployment['progress']
                        current_step = progress.get('current_step', '')
                        
                        if current_step != last_step:
                            last_step = current_step
                            click.echo(f"Current step: {current_step}")
                            
                            # Show step details
                            for step in progress.get('steps', []):
                                status_symbol = {
                                    'completed': '✓',
                                    'processing': '▶',
                                    'pending': '○',
                                    'failed': '✗'
                                }.get(step['status'], '?')
                                
                                status_color = {
                                    'completed': 'green',
                                    'processing': 'yellow',
                                    'failed': 'red'
                                }.get(step['status'], None)
                                
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
                deployment = response['deployment']
                
                # Basic info
                click.echo(f"Deployment ID: {deployment['id']}")
                click.echo(f"Status: {deployment['status']}")
                click.echo(f"Version: {deployment.get('version', 'N/A')}")
                click.echo(f"Created: {deployment.get('created_at', 'N/A')}")
                
                if deployment.get('started_at'):
                    click.echo(f"Started: {deployment['started_at']}")
                if deployment.get('completed_at'):
                    click.echo(f"Completed: {deployment['completed_at']}")
                
                # Progress information
                if 'progress' in deployment:
                    progress = deployment['progress']
                    click.echo()
                    click.echo(f"Current step: {progress.get('current_step', 'N/A')}")
                    click.echo("Steps:")
                    
                    for step in progress.get('steps', []):
                        status_symbol = {
                            'completed': '✓',
                            'processing': '▶',
                            'pending': '○',
                            'failed': '✗'
                        }.get(step['status'], '?')
                        
                        click.echo(f"  {status_symbol} {step['name']} [{step['status']}]")
                        
                        if step.get('started_at'):
                            click.echo(f"    Started: {step['started_at']}")
                        if step.get('completed_at'):
                            click.echo(f"    Completed: {step['completed_at']}")
                
                # Error information
                if deployment['status'] == 'failed' and 'error' in deployment:
                    click.echo()
                    click.secho("Error:", fg='red', bold=True)
                    click.echo(f"  {deployment['error']}")
                    
    except AuthenticationError as e:
        click.secho(f"AUTHENTICATION ERROR: {e}", fg='red')
        ctx = click.get_current_context()
        ctx.exit(1)
    except DeploymentError as e:
        click.secho(f"DEPLOYMENT ERROR: {e}", fg='red')
        ctx = click.get_current_context()
        ctx.exit(1)
    except Exception as e:
        click.secho(f"UNEXPECTED ERROR: {e}", fg='red')
        ctx = click.get_current_context()
        ctx.exit(1)


@cli.command()
@click.option('--apkg-file', '-f', required=True, type=click.Path(exists=True, path_type=Path), 
              help='Path to the APKG file to deploy')
@click.option('--env', '-e', type=click.Choice(['local', 'prod']), default='prod',
              help='Deployment environment (local or prod)')
@click.option('--app-id', '-a', required=True, help='Agent app ID to deploy to')
@click.option('--version', '-v', help='Version string (optional, will extract from package if not provided)')
@click.option('--release-notes', '-r', help='Release notes for this deployment')
@click.option('--signature', '-s', type=click.Path(exists=True, path_type=Path),
              help='Path to signature file for signed packages')
@click.option('--api-key', '-k', help='API key for authentication (can also use PIXELL_API_KEY env var)')
@click.option('--wait', is_flag=True, help='Wait for deployment to complete')
@click.option('--timeout', default=300, help='Timeout in seconds when waiting for deployment')
@click.option('--force', is_flag=True, help='Force overwrite existing version')
def deploy(apkg_file, env, app_id, version, release_notes, signature, api_key, wait, timeout, force):
    """Deploy an APKG file to Pixell Agent Cloud."""
    from pixell.core.deployment import DeploymentClient, DeploymentError, AuthenticationError, InsufficientCreditsError, ValidationError, get_api_key
    
    # Get API key from parameter, environment, or config
    if not api_key:
        api_key = get_api_key()
    
    if not api_key:
        click.secho("ERROR: No API key provided. Use --api-key, set PIXELL_API_KEY environment variable, or configure in ~/.pixell/config.json", fg='red')
        ctx = click.get_current_context()
        ctx.exit(1)
    
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
            click.echo(click.style("Force overwrite: ENABLED", fg='yellow', bold=True))
        
        # Start deployment
        response = client.deploy(
            app_id=app_id,
            apkg_file=apkg_file,
            version=version,
            release_notes=release_notes,
            signature_file=signature,
            force_overwrite=force
        )
        
        deployment = response['deployment']
        package = response['package']
        tracking = response['tracking']
        
        # Show deployment info
        click.echo()
        click.secho("✓ Deployment initiated successfully!", fg='green', bold=True)
        click.echo(f"  Deployment ID: {deployment['id']}")
        click.echo(f"  Package ID: {package['id']}")
        click.echo(f"  Status: {deployment['status']}")
        click.echo(f"  Version: {package['version']}")
        click.echo(f"  Size: {package['size_bytes'] / (1024*1024):.1f} MB")
        click.echo(f"  Queued at: {deployment['queued_at']}")
        
        if 'estimated_duration_seconds' in deployment:
            click.echo(f"  Estimated duration: {deployment['estimated_duration_seconds']} seconds")
        
        click.echo()
        click.echo(f"Track deployment status: {tracking['status_url']}")
        
        # Wait for completion if requested
        if wait:
            click.echo()
            click.echo("Waiting for deployment to complete...")
            
            try:
                with click.progressbar(length=timeout, label='Deploying') as bar:
                    start_time = time.time()
                    while time.time() - start_time < timeout:
                        status = client.get_deployment_status(deployment['id'])
                        deployment_status = status['deployment']['status']
                        
                        if deployment_status == 'completed':
                            bar.update(timeout)  # Complete the progress bar
                            click.echo()
                            click.secho("✓ Deployment completed successfully!", fg='green', bold=True)
                            
                            # Show final status
                            final_deployment = status['deployment']
                            if 'completed_at' in final_deployment:
                                click.echo(f"  Completed at: {final_deployment['completed_at']}")
                            
                            return
                        elif deployment_status == 'failed':
                            bar.update(timeout)  # Complete the progress bar
                            click.echo()
                            click.secho("✗ Deployment failed!", fg='red', bold=True)
                            error_msg = status['deployment'].get('error', 'Unknown error')
                            click.echo(f"  Error: {error_msg}")
                            ctx = click.get_current_context()
                            ctx.exit(1)
                        
                        # Update progress
                        elapsed = int(time.time() - start_time)
                        bar.update(min(elapsed, timeout))
                        time.sleep(5)
                
                # Timeout reached
                click.echo()
                click.secho("⚠ Deployment timed out", fg='yellow', bold=True)
                click.echo(f"  Check status manually: {tracking['status_url']}")
                
            except KeyboardInterrupt:
                click.echo()
                click.echo("Deployment monitoring cancelled. Check status manually:")
                click.echo(f"  {tracking['status_url']}")
        
    except AuthenticationError as e:
        click.secho(f"AUTHENTICATION ERROR: {e}", fg='red')
        ctx = click.get_current_context()
        ctx.exit(1)
    except InsufficientCreditsError as e:
        click.secho(f"INSUFFICIENT CREDITS: {e}", fg='red')
        ctx = click.get_current_context()
        ctx.exit(1)
    except ValidationError as e:
        click.secho(f"VALIDATION ERROR: {e}", fg='red')
        ctx = click.get_current_context()
        ctx.exit(1)
    except DeploymentError as e:
        click.secho(f"DEPLOYMENT ERROR: {e}", fg='red')
        ctx = click.get_current_context()
        ctx.exit(1)
    except Exception as e:
        click.secho(f"UNEXPECTED ERROR: {e}", fg='red')
        ctx = click.get_current_context()
        ctx.exit(1)


if __name__ == "__main__":
    cli()