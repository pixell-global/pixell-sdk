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

## Configuration

Pixell Kit supports flexible configuration management to avoid entering credentials repeatedly. You can configure API keys and app IDs at multiple levels with the following precedence order:

### 1. Environment Variables (Highest Priority)
```bash
export PIXELL_API_KEY=your-api-key
export PIXELL_APP_ID=your-app-id
export PIXELL_ENVIRONMENT=prod
```

### 2. Project-Level Configuration
Create `.pixell/config.json` in your project directory:
```json
{
  "api_key": "your-api-key",
  "app_id": "your-default-app-id",
  "default_environment": "prod",
  "environments": {
    "prod": {"app_id": "your-production-app-id"},
    "staging": {"app_id": "your-staging-app-id"},
    "local": {"app_id": "your-local-app-id"}
  }
}
```

### 3. Global Configuration
Create `~/.pixell/config.json` for user-wide settings:
```json
{
  "api_key": "your-api-key",
  "app_id": "your-default-app-id"
}
```

### Configuration Commands

```bash
# Interactive setup (recommended for first-time users)
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

### Simplified Deployment

Once configured, you can deploy without specifying credentials every time:

```bash
# Deploy to production (uses stored credentials)
pixell deploy --apkg-file my_agent-0.1.0.apkg

# Deploy to staging (uses environment-specific app ID)
pixell deploy --apkg-file my_agent-0.1.0.apkg --env staging

# Deploy to local development
pixell deploy --apkg-file my_agent-0.1.0.apkg --env local
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

This project is licensed under the [GNU Affero General Public License v3.0](LICENSE).

For organizations that do not wish to comply with AGPL-3.0 requirements,
commercial licensing options are available. Contact us at engineering@pixell.global .
