# Pixell Agent Kit (PAK) - Architecture & Implementation Steps

## Architecture Overview

### Component Architecture
```
pixell-agent-kit/
├── pixell/                 # Main package directory
│   ├── __init__.py
│   ├── cli/               # CLI command implementations
│   │   ├── __init__.py
│   │   ├── init.py        # pixell init command
│   │   ├── build.py       # pixell build command
│   │   ├── run_dev.py     # pixell run-dev command
│   │   ├── inspect.py     # pixell inspect command
│   │   ├── validate.py    # pixell validate command
│   │   └── main.py        # CLI entry point using Click
│   ├── core/              # Core functionality
│   │   ├── __init__.py
│   │   ├── packager.py    # APKG creation logic
│   │   ├── validator.py   # Manifest & package validation
│   │   ├── loader.py      # APKG loading for runtime
│   │   └── signer.py      # Package signing/verification
│   ├── models/            # Data models
│   │   ├── __init__.py
│   │   ├── manifest.py    # Agent manifest model
│   │   └── package.py     # APKG package model
│   ├── utils/             # Utility functions
│   │   ├── __init__.py
│   │   ├── hash.py        # SHA-256 hash utilities
│   │   ├── file_ops.py    # File operations
│   │   └── templates.py   # Agent templates
│   └── dev_server/        # Local development server
│       ├── __init__.py
│       └── server.py      # FastAPI dev server
├── tests/                 # Test suite
│   ├── __init__.py
│   ├── test_cli/
│   ├── test_core/
│   └── test_models/
├── setup.py               # Package setup
├── requirements.txt       # Dependencies
├── README.md             # Project documentation
└── .gitignore            # Git ignore file
```

## Implementation Steps

### Step 1: Project Foundation (Can be built independently)
**Goal**: Set up basic project structure and dependencies

1. Create project directory structure
2. Create setup.py with basic metadata
3. Create requirements.txt with core dependencies
4. Create .gitignore file
5. Verify: `pip install -e .` works

### Step 2: Data Models (Can be built independently)
**Goal**: Define core data structures for manifest and packages

1. Create manifest.py with Pydantic models for agent.yaml
2. Create package.py with APKG package model
3. Add JSON Schema generation for manifest validation
4. Write unit tests for models
5. Verify: Models can be instantiated and validated

### Step 3: CLI Foundation (Depends on Step 1)
**Goal**: Set up Click-based CLI structure

1. Create main.py with Click group
2. Add basic command stubs (init, build, run-dev, etc.)
3. Set up console_scripts entry point in setup.py
4. Add --version and --help support
5. Verify: `pixell --help` shows all commands

### Step 4: Init Command (Depends on Steps 2, 3)
**Goal**: Implement agent project scaffolding

1. Create templates directory with sample agent.yaml
2. Implement init.py with project creation logic
3. Add Python agent template with main.py
4. Add .apkgignore template
5. Verify: `pixell init test_agent` creates working project

### Step 5: Validation Logic (Depends on Step 2)
**Goal**: Implement manifest and structure validation

1. Create validator.py with schema validation
2. Add manifest version compatibility checks
3. Implement file structure validation
4. Add size limit checks
5. Verify: Validation catches invalid manifests

### Step 6: Build Command (Depends on Steps 2, 4, 5)
**Goal**: Create APKG packaging functionality

1. Create packager.py with zip creation logic
2. Implement deterministic file ordering
3. Add SHA-256 hash generation
4. Implement .apkgignore handling
5. Verify: `pixell build` creates valid .apkg file

### Step 7: Inspect Command (Depends on Step 6)
**Goal**: Enable APKG inspection

1. Implement inspect.py with package reading
2. Add manifest extraction and display
3. Show package contents and metadata
4. Add JSON output format option
5. Verify: `pixell inspect file.apkg` shows package info

### Step 8: Loader API (Depends on Step 6)
**Goal**: Enable runtime package loading

1. Create loader.py with APKG extraction
2. Implement dynamic module loading
3. Add FastAPI router generation
4. Handle version conflicts
5. Verify: load_apkg() returns working router

### Step 9: Dev Server (Depends on Steps 7, 8)
**Goal**: Local development environment

1. Create dev_server/server.py with FastAPI app
2. Implement hot-reload with watchdog
3. Add environment variable injection
4. Add debug endpoints
5. Verify: `pixell run-dev` starts local server

### Step 10: Package Signing (Optional, Depends on Step 6)
**Goal**: Add security features

1. Create signer.py with GPG integration
2. Implement sign command
3. Implement verify command
4. Add signature to package metadata
5. Verify: Signed packages can be verified

### Step 11: Test Suite (Throughout all steps)
**Goal**: Comprehensive test coverage

1. Unit tests for each module
2. Integration tests for CLI commands
3. End-to-end test scenarios
4. Add CI/CD configuration
5. Verify: >80% test coverage

### Step 12: Documentation & Polish
**Goal**: Production-ready release

1. Write comprehensive README
2. Add CLI command examples
3. Create sample agents (Python)
4. Add error handling improvements
5. Performance optimization

## Testing Strategy for Each Step

Each step should be tested to ensure it builds correctly:

### Step 1 Test:
```bash
python -m venv test_env
source test_env/bin/activate
pip install -e .
pixell --version  # Should show version
```

### Step 2 Test:
```python
from pixell.models.manifest import AgentManifest
manifest = AgentManifest(
    id="test.agent",
    version="0.1.0",
    entrypoint="main:app"
)
print(manifest.model_dump())  # Should print valid manifest
```

### Step 3 Test:
```bash
pixell --help  # Should list all commands
pixell init --help  # Should show init help
```

### Step 4 Test:
```bash
pixell init my_test_agent
cd my_test_agent
ls -la  # Should show agent.yaml, src/, etc.
```

### Step 5 Test:
```bash
pixell validate  # In agent directory, should pass
echo "invalid: yaml" > agent.yaml
pixell validate  # Should fail with error
```

### Step 6 Test:
```bash
pixell build  # Should create .apkg file
unzip -l *.apkg  # Should show package contents
```

### Step 7 Test:
```bash
pixell inspect my_agent-0.1.0.apkg  # Should display manifest
```

### Step 8 Test:
```python
from pixell.loader import load_apkg
router = load_apkg("my_agent-0.1.0.apkg")
# Should return FastAPI router
```

### Step 9 Test:
```bash
pixell run-dev  # Should start server on http://localhost:8000
curl http://localhost:8000/health  # Should return OK
```

### Step 10 Test:
```bash
pixell sign --key mykey.gpg my_agent-0.1.0.apkg
pixell verify my_agent-0.1.0.apkg.sig
```

### Step 11 Test:
```bash
pytest tests/  # Should run all tests
pytest --cov=pixell  # Should show coverage report
```

## Dependencies by Step

- **Step 1**: Python 3.11+, pip
- **Step 2**: pydantic>=2.0, jsonschema
- **Step 3**: click>=8.0
- **Step 4**: pyyaml, jinja2
- **Step 5**: jsonschema
- **Step 6**: zipfile (stdlib), hashlib (stdlib)
- **Step 7**: tabulate
- **Step 8**: fastapi>=0.100, importlib (stdlib)
- **Step 9**: uvicorn, watchdog, python-dotenv
- **Step 10**: python-gnupg (optional)
- **Step 11**: pytest, pytest-cov, pytest-asyncio

## Key Design Decisions

1. **Pydantic for Models**: Type safety and automatic validation
2. **Click for CLI**: Industry standard, extensible
3. **FastAPI for Dev Server**: Async support, automatic docs
4. **Deterministic Packaging**: Reproducible builds
5. **Plugin Architecture**: Extensible for future registry backends
6. **Minimal Dependencies**: Keep core lightweight

## Success Criteria

- Each step can be built and tested independently
- Total implementation time: ~2 weeks for core features
- Performance: `pixell build` < 2s for 100-file repo
- Developer experience: Init to running agent < 60s