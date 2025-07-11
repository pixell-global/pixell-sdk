# Pixell Kit

A lightweight developer kit for packaging AI agents into portable, standardized APKG files.

## Installation

### Using pipx (Recommended)
```bash
pipx install pixell-kit
```

### Using Homebrew
```bash
brew install pixell-kit
```

### Using pip
```bash
pip install pixell-kit
```

## Quick Start

```bash
# Create a new agent project
pixell init my_agent

# Run locally for development
cd my_agent
pixell run-dev

# Build into APKG package
pixell build

# Inspect the package
pixell inspect my_agent-0.1.0.apkg
```

## Features

- 📦 Package any AI agent into portable APKG files
- 🚀 Local development server with hot-reload
- ✅ Manifest validation and package integrity
- 🔐 Optional package signing with GPG
- 🐍 Python 3.11+ support (TypeScript coming soon)

## Documentation

See the [full documentation](https://docs.pixell.global/pixell) for detailed usage.

## License

Apache License 2.0