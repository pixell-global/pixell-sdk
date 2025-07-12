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
    from pixell.core.registry import Registry, create_sample_agents
    import json
    
    registry = Registry()
    
    # For demo purposes, register sample agents if registry is empty
    if not registry.list_agents():
        click.echo("No agents found. Loading sample agents for demonstration...")
        for agent in create_sample_agents():
            registry.register_agent(agent)
    
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


if __name__ == "__main__":
    cli()