# Pixell Agent Kit - Developer Guide

This guide explains how to build and deploy AI agents using Pixell Agent Kit.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Agent Configuration (agent.yaml)](#agent-configuration-agentyaml)
- [Building Your Agent](#building-your-agent)
- [Testing Locally](#testing-locally)
- [Deployment](#deployment)
- [Best Practices](#best-practices)

## Prerequisites

1. **Install Pixell Kit**:
   ```bash
   pipx install pixell-kit
   ```

2. **Python Requirements**:
   - Python 3.8 or higher
   - pip for dependency management

## Quick Start

To build an agent package (.apkg file), you need:
1. An `agent.yaml` manifest file
2. Source code in a `src/` directory
3. The `pixell build` command

```bash
# Build your agent (outputs to current directory)
pixell build

# Build with custom output directory
pixell build --output ./dist

# Build from specific directory
pixell build --path ./my-agent

# Validate before building
pixell validate
```

## Project Structure

Your agent project MUST follow this structure:

```
my-agent/
├── agent.yaml          # REQUIRED: Agent manifest
├── src/                # REQUIRED: Agent source code
│   ├── __init__.py
│   └── main.py         # Your agent implementation
├── requirements.txt    # Optional: Python dependencies
├── mcp.json           # Optional: MCP configuration
├── README.md          # Optional: Documentation
└── LICENSE            # Optional: License file
```

## Agent Configuration (agent.yaml)

The `agent.yaml` file defines your agent's metadata and configuration. This file is REQUIRED for building your agent.

### Required Fields

Every `agent.yaml` MUST include these fields:

```yaml
# Manifest version (always "1.0")
version: "1.0"

# Package name (lowercase, numbers, hyphens only)
name: "my-agent-name"

# Human-readable display name
display_name: "My Agent"

# Short description of what your agent does
description: "An AI agent that helps with specific tasks"

# Author name
author: "Your Name"

# License identifier (e.g., MIT, Apache-2.0, GPL-3.0)
license: "MIT"

# Python module:function entry point
# Format: "module.path:function_name"
entrypoint: "src.main:handler"

# Required metadata section
metadata:
  # Semantic version of your agent
  version: "1.0.0"
```

### Optional Fields

You can include these optional fields for additional functionality:

```yaml
# Agent capabilities (what your agent can do)
capabilities:
  - "text-generation"
  - "code-analysis"
  - "data-processing"

# Runtime environment (default: python3.11)
# Valid options: python3.9, python3.11, node18, node20, go1.21
runtime: "python3.11"

# Environment variables
environment:
  API_KEY: "${API_KEY}"
  DEBUG: "false"

# Python dependencies (same format as requirements.txt)
# These will be used if requirements.txt is not present
dependencies:
  - "requests>=2.28.0"
  - "numpy>=1.24.0"
  - "pandas>=2.0.0"

# MCP (Model Context Protocol) configuration
mcp:
  enabled: true
  config_file: "mcp.json"

# Extended metadata
metadata:
  version: "1.0.0"
  homepage: "https://github.com/username/my-agent"
  repository: "https://github.com/username/my-agent"
  tags:
    - "automation"
    - "productivity"
    - "ai-assistant"

# UI specification (for agents with custom UI)
ui_spec_version: "1.0"
required_ui_capabilities:
  - "forms"
  - "charts"
```

### Complete Example

Here's a complete `agent.yaml` example:

```yaml
version: "1.0"
name: "weather-assistant"
display_name: "Weather Assistant"
description: "AI agent that provides weather forecasts and alerts"
author: "Jane Developer"
license: "MIT"
entrypoint: "src.weather_agent:main"

capabilities:
  - "weather-forecast"
  - "alert-generation"
  - "data-visualization"

runtime: "python3.11"

environment:
  WEATHER_API_KEY: "${WEATHER_API_KEY}"
  DEFAULT_LOCATION: "San Francisco"

dependencies:
  - "requests>=2.31.0"
  - "python-dateutil>=2.8.0"
  - "pytz>=2023.3"

mcp:
  enabled: false

metadata:
  version: "2.1.0"
  homepage: "https://weatherassistant.ai"
  repository: "https://github.com/janedev/weather-assistant"
  tags:
    - "weather"
    - "forecast"
    - "alerts"
    - "api-integration"
```

## Building Your Agent

### 1. Entry Point Implementation

Your entry point function (specified in `agent.yaml`) should follow this pattern:

```python
# src/main.py

def handler(context):
    """
    Main entry point for the agent.
    
    Args:
        context: Agent execution context with request data
        
    Returns:
        Agent response
    """
    # Your agent logic here
    return {"status": "success", "data": result}
```

Or for a more complete example:

```python
# src/main.py
import json
import sys

def main():
    """Main entry point for the agent."""
    # Read input
    input_data = json.loads(sys.stdin.read())
    
    # Process the request
    response = process_request(input_data)
    
    # Write output
    print(json.dumps(response))

def process_request(data):
    """Process the incoming request."""
    action = data.get('action')
    
    if action == 'generate':
        return {'result': 'Generated content'}
    elif action == 'analyze':
        return {'result': 'Analysis complete'}
    else:
        return {'error': 'Unknown action'}

if __name__ == '__main__':
    main()
```

### 2. Dependencies

You can specify dependencies in two ways:

**Option 1: requirements.txt** (takes precedence)
```txt
# requirements.txt
requests>=2.28.0
pandas>=1.5.0
numpy>=1.21.0
```

**Option 2: In agent.yaml** (used if requirements.txt doesn't exist)
```yaml
dependencies:
  - "requests>=2.28.0"
  - "pandas>=1.5.0"
  - "numpy>=1.21.0"
```

### 3. Validation

Before building, validate your agent:

```bash
pixell validate

# Validate specific directory
pixell validate --path ./my-agent
```

The validation checks:
- **Project Structure**: `agent.yaml` and `src/` directory exist
- **Manifest Validation**: All required fields present and valid
- **Name Format**: Lowercase letters, numbers, and hyphens only
- **Entrypoint Format**: Must be in `module:function` format
- **Entrypoint Exists**: The specified module and function exist
- **Runtime**: Must be a supported runtime (python3.9, python3.11, node18, node20, go1.21)
- **Dependencies**: Must follow pip requirement format (e.g., `package>=1.0.0`)
- **MCP Config**: If MCP is enabled, config file must exist

### 4. Build Process

Run the build command:

```bash
# Basic build (outputs to current directory)
pixell build

# Build from specific directory
pixell build --path ./my-agent

# Specify output directory
pixell build --output ./dist
```

The build process:
1. **Validates** your project structure and manifest
2. **Copies** files to build directory:
   - `agent.yaml` (required)
   - `src/` directory (required, excludes `__pycache__` and `.pyc`)
   - `requirements.txt` (optional)
   - `README.md` (optional)
   - `LICENSE` (optional)
   - MCP config file (if specified)
3. **Creates** package metadata in `.pixell/package.json`
4. **Generates** `requirements.txt` from manifest dependencies if not present
5. **Packages** everything into a `.apkg` file (ZIP archive)

Output filename: `{agent-name}-{version}.apkg`

### Common Build Errors and Solutions

**"Validation failed"**
- Run `pixell validate` to see specific errors
- Fix all validation errors before building

**"Required file missing: agent.yaml"**
- Ensure `agent.yaml` exists in your project root

**"Source directory 'src/' not found"**
- Create a `src/` directory with your agent code

**"Entrypoint module not found"**
- Check that your entrypoint path matches your file structure
- Example: `src.main:handler` requires `src/main.py` with a `handler` function

**"Invalid dependency format"**
- Use pip requirement specifiers: `package>=1.0.0`, `package==2.1.3`, `package<3.0.0`

**"Name must be lowercase letters, numbers, and hyphens only"**
- Fix your agent name in `agent.yaml`
- Valid: `my-agent`, `text-processor-2`
- Invalid: `My_Agent`, `agent.v1`, `AGENT`

## Testing Locally

### Run Development Server

```bash
pixell run-dev
```

This starts a local server that:
- Loads your agent
- Provides a testing interface
- Shows real-time logs
- Hot-reloads on code changes

### Test Your Agent

```bash
# Send a test request
curl -X POST http://localhost:8080/invoke \
  -H "Content-Type: application/json" \
  -d '{"action": "generate", "prompt": "Hello"}'
```

### Run Unit Tests

```bash
python -m pytest tests/
```

## Deployment

### Deploy to Pixell Agent Cloud

Pixell Kit provides a built-in deployment command to deploy your agents to Pixell Agent Cloud:

```bash
# Deploy to production
pixell deploy --apkg-file my-agent.apkg --app-id your-app-id

# Deploy to local development environment  
pixell deploy --apkg-file my-agent.apkg --app-id your-app-id --env local

# Deploy with version and release notes
pixell deploy --apkg-file my-agent.apkg --app-id your-app-id \
  --version 1.2.0 --release-notes "Fixed bugs and improved performance"

# Deploy with signature for signed packages
pixell deploy --apkg-file my-agent.apkg --app-id your-app-id \
  --signature my-agent.apkg.sig

# Deploy and wait for completion
pixell deploy --apkg-file my-agent.apkg --app-id your-app-id --wait
```

#### Environment Configuration

The deploy command supports two environments:

- **Production** (`--env prod`): `https://main.d2o02924ohm5pe.amplifyapp.com/` (default)
- **Local Development** (`--env local`): `http://localhost:4000`

#### Authentication & Configuration

You can provide your API key and app ID in several ways, with the following order of precedence:

1. **Command line parameters** (highest priority):
   ```bash
   pixell deploy --apkg-file my-agent.apkg --app-id your-app-id --api-key your-api-key
   ```

2. **Environment variables**:
   ```bash
   export PIXELL_API_KEY=your-api-key
   export PIXELL_APP_ID=your-app-id
   export PIXELL_ENVIRONMENT=prod
   pixell deploy --apkg-file my-agent.apkg
   ```

3. **Project-level configuration** (`.pixell/config.json`):
   ```json
   {
     "api_key": "your-api-key",
     "app_id": "your-default-app-id",
     "default_environment": "prod",
     "environments": {
       "prod": {"app_id": "your-prod-app-id"},
       "staging": {"app_id": "your-staging-app-id"},
       "local": {"app_id": "your-local-app-id"}
     }
   }
   ```

4. **Global configuration** (`~/.pixell/config.json`):
   ```json
   {
     "api_key": "your-api-key",
     "app_id": "your-default-app-id"
   }
   ```

#### Configuration Management

Use the built-in configuration commands to manage your credentials:

```bash
# Initialize configuration interactively
pixell config init

# Set individual values
pixell config set --api-key your-api-key
pixell config set --app-id your-app-id
pixell config set --env-app-id prod:your-prod-app-id
pixell config set --env-app-id staging:your-staging-app-id

# Set global configuration (affects all projects)
pixell config set --global --api-key your-api-key

# View current configuration
pixell config show
pixell config show --global
```

#### Simplified Deployment

Once configured, you can deploy without specifying credentials every time:

```bash
# Deploy to production (uses stored credentials)
pixell deploy --apkg-file my-agent.apkg

# Deploy to staging (uses environment-specific app ID)
pixell deploy --apkg-file my-agent.apkg --env staging

# Deploy to local development
pixell deploy --apkg-file my-agent.apkg --env local
```

#### Deployment Process

The deployment process includes:

1. **Package Upload**: Your APKG file is uploaded to the cloud
2. **Validation**: Package format and manifest are validated
3. **Credit Deduction**: Credits are deducted based on package size (1 credit per MB)
4. **Runtime Deployment**: Agent is deployed to the runtime environment
5. **Finalization**: Deployment is marked as complete

You can track deployment progress with the `--wait` flag or use the tracking URL provided in the response.

#### Error Handling

The deploy command handles various error scenarios:

- **Authentication Error**: Invalid API key or session
- **Insufficient Credits**: Not enough credits for deployment  
- **Validation Error**: Package format or content issues
- **Network Errors**: Connection or timeout issues

#### Complete Example

```bash
# Build your agent
pixell build

# Deploy to production with monitoring
pixell deploy \
  --apkg-file dist/my-agent-1.0.0.apkg \
  --app-id app-uuid-here \
  --version 1.0.0 \
  --release-notes "Initial production release" \
  --wait \
  --timeout 600
```

### Alternative Deployment Methods

#### 1. Manual API Deployment

You can also deploy directly using the API:

```bash
curl -X POST https://main.d2o02924ohm5pe.amplifyapp.com/api/agent-apps/your-app-id/packages/deploy \
  -H "Authorization: Bearer your-api-key" \
  -F "file=@my-agent.apkg" \
  -F "version=1.0.0" \
  -F "release_notes=Initial release"
```

#### 2. Sign Your Package (Optional)

```bash
pixell sign my-agent.apkg --key-file private-key.pem
```

## Best Practices

### 1. **Input/Output Format**
- Use JSON for all input/output
- Define clear schemas
- Handle errors gracefully

```python
# Good practice
try:
    result = process_data(input_data)
    return {'status': 'success', 'data': result}
except Exception as e:
    return {'status': 'error', 'message': str(e)}
```

### 2. **Resource Management**
- Set appropriate timeouts
- Limit memory usage
- Clean up resources

```yaml
runtime:
  memory: "256MB"  # Be conservative
  timeout: 60       # Reasonable timeout
```

### 3. **Security**
- Never hardcode credentials
- Use environment variables
- Validate all inputs

```python
# Use environment variables
api_key = os.environ.get('API_KEY')
if not api_key:
    raise ValueError("API_KEY not configured")
```

### 4. **Versioning**
- Use semantic versioning
- Update version for each release
- Document changes

```yaml
metadata:
  version: "1.2.3"  # major.minor.patch
```

### 5. **Documentation**
- Include a README.md
- Document API endpoints
- Provide usage examples

### 6. **Testing**
- Write unit tests
- Test edge cases
- Validate with `pixell validate`

## Example: Complete Agent

Here's a complete example of a text summarization agent:

```python
# src/main.py
import json
import sys
import os
from typing import Dict, Any

def main():
    """Main entry point."""
    try:
        # Read JSON input
        input_text = sys.stdin.read()
        data = json.loads(input_text)
        
        # Process request
        result = handle_request(data)
        
        # Output result
        print(json.dumps(result))
    except Exception as e:
        error_response = {
            'status': 'error',
            'message': str(e)
        }
        print(json.dumps(error_response))
        sys.exit(1)

def handle_request(data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle incoming requests."""
    action = data.get('action')
    
    if action == 'summarize':
        text = data.get('text', '')
        max_length = data.get('max_length', 100)
        return summarize_text(text, max_length)
    else:
        return {
            'status': 'error',
            'message': f'Unknown action: {action}'
        }

def summarize_text(text: str, max_length: int) -> Dict[str, Any]:
    """Summarize the given text."""
    # Simple summarization logic (replace with your implementation)
    sentences = text.split('. ')
    summary = '. '.join(sentences[:2]) + '.'
    
    return {
        'status': 'success',
        'summary': summary[:max_length],
        'original_length': len(text),
        'summary_length': len(summary)
    }

if __name__ == '__main__':
    main()
```

```yaml
# agent.yaml
version: "1.0"
name: "text-summarizer"
display_name: "Text Summarizer Agent"
description: "Summarizes long text into concise summaries"
author: "Example Corp"
license: "MIT"

entrypoint: "src.main:main"

capabilities:
  - "text-summarization"
  - "natural-language-processing"

runtime: "python3.11"

metadata:
  version: "1.0.0"
  homepage: "https://github.com/example/text-summarizer"
  tags:
    - "nlp"
    - "summarization"
    - "text-processing"
```

## Troubleshooting

### Common Issues

1. **Build Fails**
   - Check `agent.yaml` syntax
   - Verify entry point exists
   - Ensure all files are present

2. **Agent Won't Start**
   - Check Python version compatibility
   - Verify dependencies are installed
   - Review error logs

3. **Performance Issues**
   - Profile your code
   - Optimize resource usage
   - Consider async operations

### Getting Help

- Check the [Pixell Kit Documentation](https://docs.pixell.ai)
- Join the community forum
- Report issues on GitHub

## Agent Registry

### Discovering Agents

Pixell Kit includes a powerful registry system for discovering and managing installed agents:

```bash
# List all installed agents
pixell list

# Search for specific agents
pixell list --search "text"
pixell list --search "nlp"

# View detailed information about all agents
pixell list --format detailed

# Export agent list as JSON
pixell list --format json > agents.json

# Show sub-agents in table view
pixell list --show-sub-agents
```

### Agent Information Structure

Each registered agent provides extensive metadata:

#### Basic Information
- **Name**: Technical package name (e.g., `text-summarizer`)
- **Display Name**: Human-friendly name (e.g., "Text Summarizer Pro")
- **Version**: Semantic version number
- **Author**: Creator or organization
- **License**: Distribution license
- **Description**: Brief one-line description

#### Extended Information
- **Extensive Description**: Detailed explanation of capabilities and features
- **Capabilities**: List of agent capabilities (e.g., `["text-generation", "multi-language"]`)
- **Tags**: Searchable keywords for discovery
- **Homepage**: Project website or repository URL

#### Sub-Agents

Agents can expose sub-agents for specific functionalities:

```yaml
sub_agents:
  - name: "extractive-summarizer"
    description: "Extract key sentences from text"
    endpoint: "/summarize/extractive"
    capabilities: ["sentence-ranking", "key-phrase-extraction"]
    public: true  # Accessible without authentication
  
  - name: "security-scanner"
    description: "Scan for vulnerabilities"
    endpoint: "/analyze/security"
    capabilities: ["vulnerability-detection", "SAST"]
    public: false  # Requires authentication
```

Sub-agents allow you to:
- Provide specialized endpoints for different tasks
- Control access with public/private flags
- Organize complex functionality
- Enable microservice-like architecture

#### Usage Information

Include comprehensive usage guides:

```yaml
usage_guide: |
  Basic usage:
  ```bash
  echo '{"action": "summarize", "text": "..."}' | pixell run text-summarizer
  ```
  
  Advanced usage with sub-agents:
  ```bash
  curl -X POST http://localhost:8080/summarize/extractive \
    -H "Content-Type: application/json" \
    -d '{"text": "...", "num_sentences": 3}'
  ```

examples:
  - title: "Basic Summarization"
    code: '{"action": "summarize", "text": "...", "max_length": 150}'
  - title: "Extract Keywords"
    code: '{"action": "keywords", "text": "...", "num_keywords": 10}'
```

### Registering Your Agent

When you install an agent, it's automatically registered with metadata from the APKG package:

```bash
# Install and register an agent
pixell install my-agent.apkg

# Install from registry
pixell install text-summarizer
```

The registry stores:
- Complete agent metadata
- Installation date and location
- Package size
- Runtime requirements
- Dependencies

### Registry Storage

Agent metadata is stored in:
- **Unix/Linux/macOS**: `~/.pixell/registry/`
- **Windows**: `%USERPROFILE%\.pixell\registry\`

Structure:
```
~/.pixell/registry/
├── agents/          # Installed agent files
└── metadata/        # JSON metadata files
    ├── text-summarizer.json
    ├── code-analyzer.json
    └── ...
```

### Best Practices for Agent Metadata

1. **Comprehensive Descriptions**
   - Provide both brief and extensive descriptions
   - Explain unique features and use cases
   - List supported languages/formats

2. **Clear Sub-Agent Documentation**
   - Document each endpoint's purpose
   - Specify authentication requirements
   - Include example requests/responses

3. **Practical Examples**
   - Show real-world use cases
   - Include both simple and advanced examples
   - Demonstrate sub-agent usage

4. **Accurate Capabilities**
   - Use standard capability names when possible
   - Be specific about what your agent can do
   - Update capabilities as features are added

5. **Helpful Tags**
   - Include relevant technology tags
   - Add use-case tags (e.g., "productivity", "automation")
   - Consider language/framework tags

### Example: Complete Agent Manifest

```yaml
# agent.yaml with full metadata
version: "1.0"
name: "doc-processor"
display_name: "Document Processor Suite"
description: "All-in-one document processing and analysis"
author: "DocTools Inc."
license: "Apache-2.0"

# Extended metadata for registry
metadata:
  version: "2.0.1"
  homepage: "https://github.com/doctools/doc-processor"
  extensive_description: |
    Document Processor Suite provides comprehensive document handling:
    
    - Format conversion (PDF, Word, HTML, Markdown)
    - Text extraction with layout preservation
    - Metadata extraction and indexing
    - OCR for scanned documents
    - Document comparison and diff
    - Batch processing capabilities
    
    Supports 50+ file formats and 20+ languages.
  
  tags:
    - "document-processing"
    - "pdf"
    - "ocr"
    - "text-extraction"
    - "file-conversion"
  
  sub_agents:
    - name: "pdf-converter"
      description: "Convert PDFs to other formats"
      endpoint: "/convert/pdf"
      capabilities: ["pdf-to-text", "pdf-to-html", "pdf-to-docx"]
      public: true
    
    - name: "ocr-engine"
      description: "Extract text from images and scanned docs"
      endpoint: "/ocr/extract"
      capabilities: ["optical-character-recognition", "layout-analysis"]
      public: true
    
    - name: "doc-comparer"
      description: "Compare and diff documents"
      endpoint: "/compare"
      capabilities: ["diff-generation", "change-tracking"]
      public: false
  
  usage_guide: |
    # Basic PDF to text conversion
    curl -X POST http://localhost:8080/convert/pdf \
      -F "file=@document.pdf" \
      -F "format=text"
    
    # OCR with language specification
    curl -X POST http://localhost:8080/ocr/extract \
      -F "file=@scan.jpg" \
      -F "language=eng+fra"
    
    # Document comparison (requires auth)
    curl -X POST http://localhost:8080/compare \
      -H "Authorization: Bearer YOUR_TOKEN" \
      -F "original=@v1.docx" \
      -F "modified=@v2.docx"
  
  examples:
    - title: "Convert PDF to Markdown"
      code: |
        curl -X POST http://localhost:8080/convert/pdf \
          -F "file=@report.pdf" \
          -F "format=markdown" \
          -F "preserve_layout=true"
    
    - title: "Batch OCR Processing"
      code: |
        echo '{"files": ["scan1.jpg", "scan2.jpg"], "language": "eng"}' | \
        pixell run doc-processor --action batch-ocr

# Standard configuration continues...
entrypoint: "src.main:main"
capabilities:
  - "document-processing"
  - "format-conversion"
  - "text-extraction"

runtime: "python3.11"

dependencies:
  - pypdf2>=3.0
  - python-docx>=0.8
  - pytesseract>=0.3
  - pillow>=9.0
```

## Next Steps

1. Explore advanced features in the PRD
2. Join the developer community
3. Share your agents in the registry
4. Contribute to Pixell Kit development