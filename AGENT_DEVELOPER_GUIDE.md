# Pixell Agent Kit - Developer Guide

This guide explains how to build and deploy AI agents using Pixell Agent Kit.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Agent Configuration](#agent-configuration)
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

1. **Initialize a new agent project**:
   ```bash
   pixell init my-agent
   cd my-agent
   ```

2. **Configure your agent** by editing `agent.yaml`

3. **Build your agent**:
   ```bash
   pixell build
   ```

4. **Test locally**:
   ```bash
   pixell run-dev
   ```

## Project Structure

A Pixell agent project should follow this structure:

```
my-agent/
├── agent.yaml           # Agent manifest (required)
├── src/                 # Agent source code (required)
│   ├── __init__.py
│   └── main.py         # Entry point
├── requirements.txt     # Python dependencies
├── tests/              # Test files (optional)
├── README.md           # Documentation (optional)
└── mcp.json            # MCP server config (optional)
```

## Agent Configuration

The `agent.yaml` file is the heart of your agent configuration:

```yaml
# agent.yaml
version: "1.0"
name: "my-agent"
display_name: "My AI Agent"
description: "A brief description of what your agent does"
author: "Your Name"
license: "MIT"

# Entry point for your agent
entry_point: "src.main:main"

# Agent capabilities
capabilities:
  - "text-generation"
  - "data-analysis"

# Runtime requirements
runtime:
  python_version: ">=3.8"
  memory: "512MB"
  timeout: 300  # seconds

# Environment variables (optional)
environment:
  API_KEY: "${API_KEY}"
  DEBUG: "false"

# Dependencies that will be installed
dependencies:
  - requests>=2.28.0
  - pandas>=1.5.0

# MCP server configuration (optional)
mcp:
  enabled: true
  config_file: "mcp.json"

# Metadata
metadata:
  version: "0.1.0"
  homepage: "https://github.com/username/my-agent"
  tags:
    - "automation"
    - "productivity"
```

## Building Your Agent

### 1. Create Your Agent Code

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

### 2. Define Dependencies

```txt
# requirements.txt
requests>=2.28.0
pandas>=1.5.0
numpy>=1.21.0
```

### 3. Validate Your Configuration

```bash
pixell validate
```

This checks:
- `agent.yaml` syntax and required fields
- Entry point accessibility
- Dependency conflicts
- File structure compliance

### 4. Build the Agent Package

```bash
pixell build
```

This creates an `.apkg` file containing:
- All source code
- Configuration files
- Dependencies list
- Metadata

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

### 1. Sign Your Package (Optional)

```bash
pixell sign my-agent.apkg --key-file private-key.pem
```

### 2. Deploy to Registry

```bash
# Configure registry
pixell config set registry.url s3://my-bucket/agents

# Deploy
pixell deploy my-agent.apkg
```

### 3. Install from Registry

Users can install your agent:

```bash
pixell install my-agent
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

entry_point: "src.main:main"

capabilities:
  - "text-summarization"
  - "natural-language-processing"

runtime:
  python_version: ">=3.8"
  memory: "256MB"
  timeout: 30

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

## Next Steps

1. Explore advanced features in the PRD
2. Join the developer community
3. Share your agents in the registry
4. Contribute to Pixell Kit development