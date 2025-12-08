# Pixell Agent Kit

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

## Environment and Secrets

### Phase 1: Required .env in APKG
- Every agent package must include a `.env` at the project root.
- Builds fail if `.env` is missing.
- The builder always includes `.env` in the APKG.
- The validator warns on potential secrets and non-portable absolute paths.

Scaffold:
- `pixell init` generates a `.env.example`. Copy to `.env` and fill values.

Notes:
- Treat `.env` as sensitive; it is packaged. Use placeholders for shared artifacts.

### Phase 2: Runtime Environment Injection (Dev parity)
- The dev server automatically loads `.env` and applies variables to the process environment.
- Precedence (dev): `.env` > base environment.
- Logs show variable keys only, never values.

### Phase 3: Service-Bound Secrets (Dev parity)
- Optional secrets providers can inject runtime secrets without baking them into `.env`.
- Provider selection is controlled by environment variables:
  - `PIXELL_SECRETS_PROVIDER=static` with `PIXELL_SECRETS_JSON` (JSON object)
  - `PIXELL_SECRETS_PROVIDER=env` to pass-through current process env
  - `PIXELL_SECRETS_PROVIDER=aws` to use AWS Secrets Manager with:
    - `PIXELL_AWS_SECRETS` (comma-separated secret names/ARNs)
    - optional `PIXELL_AWS_REGION`
- Precedence (dev): provider > `.env` > base env.

Example (static):
```bash
export PIXELL_SECRETS_PROVIDER=static
export PIXELL_SECRETS_JSON='{"OPENAI_API_KEY":"runtime","DB_HOST":"database"}'
```

Example (AWS):
```bash
export PIXELL_SECRETS_PROVIDER=aws
export PIXELL_AWS_SECRETS=my/app/secrets,another/secret
export PIXELL_AWS_REGION=us-east-1
```

### Best Practices
- Use `0.0.0.0` for bind addresses inside containers (not `localhost`).
- Avoid absolute, machine-specific paths in `.env`.
- Never log secret values; only keys. The kit adheres to this.

### PAR Guidance (separate runtime)
- Apply precedence in the agent subprocess:
  1) Runtime deployment env (highest)
  2) `.env` from APKG
  3) Base runtime environment (lowest)
- Optionally add service-bound providers per deployment context.

## Features

- 📦 Package any AI agent into portable APKG files
- 🚀 Local development server with hot-reload
- ✅ Manifest validation and package integrity
- 🔐 Optional package signing with GPG
- 🐍 Python 3.11+ support (TypeScript coming soon)

---

## SDK Runtime

The Pixell SDK provides runtime infrastructure for agent execution, including task queue processing, user context management, and progress reporting.

### Installation

```bash
pip install pixell-sdk
```

### Quick Start

```python
import asyncio
from pixell.sdk import UserContext, TaskConsumer

async def handle_task(ctx: UserContext, payload: dict) -> dict:
    # Report progress
    await ctx.report_progress("starting", percent=0)

    # Access user data
    profile = await ctx.get_user_profile()

    # Call OAuth APIs on behalf of the user
    events = await ctx.call_oauth_api(
        provider="google",
        method="GET",
        path="/calendar/v3/calendars/primary/events"
    )

    await ctx.report_progress("completed", percent=100)
    return {"status": "success", "events": len(events.get("items", []))}

async def main():
    consumer = TaskConsumer(
        agent_id="my-agent",
        redis_url="redis://localhost:6379",
        pxui_base_url="https://api.pixell.global",
        handler=handle_task,
    )

    async with consumer:
        await consumer.start()

if __name__ == "__main__":
    asyncio.run(main())
```

### Core Components

| Component | Description |
|-----------|-------------|
| `TaskConsumer` | Redis task queue consumer with concurrency control |
| `UserContext` | Execution context with access to user data and OAuth APIs |
| `ProgressReporter` | Real-time progress updates via Redis pub/sub |
| `PXUIDataClient` | HTTP client for PXUI platform API |

### UserContext Methods

```python
# OAuth API calls (Google, GitHub, Slack, TikTok, etc.)
result = await ctx.call_oauth_api(provider, method, path, body?, headers?)

# User data access
profile = await ctx.get_user_profile()
files = await ctx.get_files(filter?, limit?)
content = await ctx.get_file_content(file_id)
conversations = await ctx.get_conversations(limit?, since?)
history = await ctx.get_task_history(agent_id?, limit?)

# Progress reporting
await ctx.report_progress(status, percent?, message?)
await ctx.report_error(error_type, message, recoverable?)
```

### Error Handling

```python
from pixell.sdk import (
    AuthenticationError,  # Invalid/expired token
    RateLimitError,       # Rate limit exceeded (check retry_after)
    APIError,             # API error response
    ConnectionError,      # Network failure
    TaskTimeoutError,     # Task exceeded timeout
)

try:
    result = await ctx.call_oauth_api(...)
except RateLimitError as e:
    retry_after = e.details.get("retry_after", 60)
    await asyncio.sleep(retry_after)
except AuthenticationError:
    # Token invalid - cannot retry
    raise
```

### Configuration Options

```python
consumer = TaskConsumer(
    agent_id="my-agent",
    redis_url="redis://localhost:6379",
    pxui_base_url="https://api.pixell.global",
    handler=handle_task,
    concurrency=10,        # Max concurrent tasks (default: 10)
    poll_interval=1.0,     # Queue poll interval in seconds
    task_timeout=300.0,    # Task timeout in seconds (default: 5 min)
)
```

### Redis Queue Keys

- `pixell:agents:{agent_id}:tasks` - Main task queue
- `pixell:agents:{agent_id}:processing` - Tasks being processed
- `pixell:agents:{agent_id}:dead_letter` - Failed tasks
- `pixell:tasks:{task_id}:progress` - Progress pub/sub channel

---

## Documentation

See the [full documentation](https://docs.pixell.global/pixell) for detailed usage.

For SDK tutorials and advanced patterns, see [SDK_TUTORIAL.md](https://github.com/pixell-global/pixell-kit/blob/main/docs/SDK_TUTORIAL.md).

## License

This project is licensed under the [GNU Affero General Public License v3.0](LICENSE).

For organizations that do not wish to comply with AGPL-3.0 requirements,
commercial licensing options are available. Contact us at engineering@pixell.global .
# Trigger publish workflow
