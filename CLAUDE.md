# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Pixell Kit is a CLI tool for packaging AI agents into portable, standardized APKG files. The project is in its initial development phase with a comprehensive Product Requirements Document in `pak_prd.md`.

## Key Project Goals

- Create a CLI tool (`pixell`) for building and managing AI agent packages
- Support `agent.yaml` manifest files that define agent metadata and dependencies
- Provide local development server for testing agents before packaging
- Enable package validation, signing, and distribution via S3-based registry

## Development Setup

Since this is a new Python project, initial setup will involve:

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (once requirements.txt is created)
pip install -r requirements.txt

# Install in development mode (once setup.py is created)
pip install -e .
```

## Planned CLI Commands

According to the PRD, the following commands should be implemented:

- `pixell init` - Initialize new agent project with template
- `pixell build` - Build agent into APKG file
- `pixell run-dev` - Run agent locally for development
- `pixell validate` - Validate agent.yaml and package structure
- `pixell install` - Install agent from APKG file or registry
- `pixell list` - List installed agents

## Project Structure (Planned)

Based on the PRD, the project should follow this structure:

```
pixell-kit/
├── pixell/           # Main package directory
│   ├── cli/          # CLI command implementations
│   ├── core/         # Core functionality (building, packaging)
│   ├── models/       # Data models for manifest, packages
│   └── utils/        # Utility functions
├── tests/            # Test suite
└── docs/             # Documentation
```

## Agent Package Format

Agents are packaged as `.apkg` files (ZIP archives) containing:
- `agent.yaml` - Manifest file with metadata
- `src/` - Agent source code
- `requirements.txt` - Python dependencies
- Optional: `mcp.json` for MCP server configuration

## Key Files

- `pak_prd.md` - Product Requirements Document with detailed specifications
- `agent.yaml` - Agent manifest format (see PRD for schema)

## Testing Strategy

The PRD specifies unit tests for all major components and integration tests for CLI commands. Use pytest as the testing framework.

## Important Conventions

1. Follow Python PEP 8 style guidelines
2. Use type hints for all function signatures
3. Implement proper error handling with descriptive messages
4. Validate all user inputs, especially in manifest files
5. Use Click framework for CLI implementation (as specified in PRD)