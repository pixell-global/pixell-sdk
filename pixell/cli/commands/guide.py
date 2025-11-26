"""Guide command for pixell CLI."""

import click


BUILD_GUIDE = """
# Pixell Build Guide

## Quick Start

To build an agent package (.apkg file), you need:
1. An agent.yaml manifest file
2. Source code in a src/ directory
3. The pixell build command

## Commands

  pixell build                    # Build in current directory
  pixell build --output ./dist    # Custom output directory
  pixell build --path ./my-agent  # Build from specific directory
  pixell validate                 # Validate before building

## Project Structure (Required)

  my-agent/
  |-- agent.yaml          # REQUIRED: Agent manifest
  |-- src/                # REQUIRED: Agent source code
  |   |-- __init__.py
  |   |-- main.py         # Your agent implementation
  |-- .env                # REQUIRED: Environment variables (included in APKG)
  |-- requirements.txt    # Optional: Python dependencies
  |-- mcp.json           # Optional: MCP configuration
  |-- README.md          # Optional: Documentation
  |-- LICENSE            # Optional: License file

## agent.yaml - Required Fields

  version: "1.0"                         # Manifest version (always "1.0")
  name: "my-agent-name"                  # Package name (lowercase, hyphens only)
  display_name: "My Agent"               # Human-readable name
  description: "What your agent does"    # Short description
  author: "Your Name"                    # Author name
  license: "MIT"                         # License (MIT, Apache-2.0, etc.)
  entrypoint: "src.main:handler"         # Module:function entry point
  metadata:
    version: "1.0.0"                     # Your agent's version

## agent.yaml - Optional Fields

  capabilities:                          # What your agent can do
    - "text-generation"
    - "data-processing"

  runtime: "python3.11"                  # Runtime (python3.9, python3.11, node18, node20, go1.21)

  environment:                           # Environment variables
    API_KEY: "${API_KEY}"
    DEBUG: "false"

  dependencies:                          # Python packages (if no requirements.txt)
    - "requests>=2.28.0"
    - "pandas>=2.0.0"

  mcp:                                   # MCP configuration
    enabled: true
    config_file: "mcp.json"

## Entry Point Example

  # src/main.py
  def handler(context):
      '''Main entry point for the agent.'''
      # Your agent logic here
      return {"status": "success", "data": result}

## Validation Rules

  - Name: lowercase letters, numbers, hyphens only
  - Entrypoint: must be in module:function format
  - Runtime: must be a supported runtime
  - Dependencies: must follow pip format (package>=1.0.0)
  - Structure: agent.yaml and src/ directory must exist

## Common Errors

  "Required file missing: agent.yaml"
  -> Ensure agent.yaml exists in project root

  "Source directory 'src/' not found"
  -> Create a src/ directory with your code

  "Entrypoint module not found"
  -> Check that entrypoint path matches your file structure
  -> Example: src.main:handler needs src/main.py with handler function

  "Invalid dependency format"
  -> Use pip format: package>=1.0.0, package==2.1.3

  "Name must be lowercase letters, numbers, and hyphens only"
  -> Valid: my-agent, text-processor-2
  -> Invalid: My_Agent, agent.v1, AGENT

## Build Output

The build creates: {agent-name}-{version}.apkg

This ZIP archive contains:
  - agent.yaml
  - src/ directory (excluding __pycache__ and .pyc)
  - Optional files (requirements.txt, README.md, LICENSE)
  - Package metadata (.pixell/package.json)

## Next Steps

After building your .apkg file:
  - Test locally: pixell run-dev --path .
  - Deploy: pixell deploy -f my-agent-1.0.0.apkg -a <app-id>
  - Install: pixell install my-agent-1.0.0.apkg

For more information, visit: https://github.com/pixell-global/pixell-kit
"""


@click.command()
@click.option(
    "--topic",
    "-t",
    type=click.Choice(["build", "all"]),
    default="all",
    help="Specific topic to show guide for",
)
def guide_cmd(topic):
    """Display the agent development guide."""
    if topic == "build" or topic == "all":
        click.echo_via_pager(BUILD_GUIDE)

    if topic == "all":
        click.echo("\n" + "=" * 80 + "\n")
        click.echo("For specific topics, use: pixell guide --topic build")
