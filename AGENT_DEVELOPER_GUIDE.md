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
entry_point: "src.main:main"
capabilities:
  - "document-processing"
  - "format-conversion"
  - "text-extraction"

runtime:
  python_version: ">=3.8"
  memory: "1GB"
  timeout: 600

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