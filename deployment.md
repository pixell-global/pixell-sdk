### 5. Packages

#### POST /api/agent-apps/:id/packages
Upload a new package.

**Request:**
```bash
curl -X POST http://localhost:4000/api/agent-apps/app-uuid/packages \
  -H "Cookie: sb-xxx-auth-token=..." \
  -F "file=@agent.apkg" \
  -F "version=1.0.1"
```

**Response:**
```json
{
  "package": {
    "id": "uuid",
    "version": "1.0.1",
    "s3_url": "https://s3.amazonaws.com/...",
    "size": 2048000,
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

#### POST /api/agent-apps/:id/packages/deploy
Deploy a package to the runtime (with validation and credit deduction).

**Request:**
```bash
# Using session authentication
curl -X POST http://localhost:4000/api/agent-apps/app-uuid/packages/deploy \
  -H "Cookie: sb-xxx-auth-token=..." \
  -F "file=@agent.apkg" \
  -F "version=1.2.0" \
  -F "release_notes=Fixed bugs and improved performance" \
  -F "signature=@agent.apkg.sig"

# Using API key authentication
curl -X POST http://localhost:4000/api/agent-apps/app-uuid/packages/deploy \
  -H "Authorization: Bearer pac_your_api_key_here" \
  -F "file=@agent.apkg" \
  -F "version=1.2.0"
```

**Response (202 Accepted):**
```json
{
  "deployment": {
    "id": "deployment-uuid",
    "status": "queued",
    "message": "Deployment queued successfully",
    "queued_at": "2024-01-01T00:00:00Z",
    "estimated_duration_seconds": 120
  },
  "package": {
    "id": "package-uuid",
    "version": "1.2.0",
    "size_bytes": 2048000,
    "status": "uploading"
  },
  "tracking": {
    "status_url": "https://your-app.com/api/deployments/deployment-uuid",
    "webhook_url": "https://your-app.com/api/agent-apps/app-uuid/webhooks"
  }
}
```

**Error Responses:**

400 Bad Request - Package validation failed:
```json
{
  "error": "Package validation failed",
  "details": [
    "Invalid APKG format",
    "Missing required manifest.json",
    "Version already exists"
  ]
}
```

401 Unauthorized - Authentication failed:
```json
{
  "error": "Invalid API key or session"
}
```

402 Payment Required - Insufficient credits:
```json
{
  "error": "Insufficient credits",
  "required": 10,
  "available": 5
}
```

**Notes:**
- File size is used to calculate credit cost (1 credit per MB)
- Package is validated before deployment
- Credits are reserved during deployment and refunded if deployment fails
- Use the status URL to track deployment progress

#### GET /api/agent-apps/:id/packages
List all packages for an agent app.

**Request:**
```bash
curl http://localhost:4000/api/agent-apps/app-uuid/packages \
  -H "Cookie: sb-xxx-auth-token=..."
```

**Response:**
```json
{
  "packages": [
    {
      "id": "uuid",
      "version": "1.0.1",
      "s3_url": "https://s3.amazonaws.com/...",
      "size": 2048000,
      "created_at": "2024-01-01T00:00:00Z"
    },
    {
      "id": "uuid",
      "version": "1.0.0",
      "s3_url": "https://s3.amazonaws.com/...",
      "size": 1024000,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### DELETE /api/agent-apps/:id/packages/:packageId
Delete a package.

**Request:**
```bash
curl -X DELETE http://localhost:4000/api/agent-apps/app-uuid/packages/package-uuid \
  -H "Cookie: sb-xxx-auth-token=..."
```

**Response:**
```json
{
  "message": "Package deleted successfully"
}
```


### 9. Deployments


#### GET /api/deployments/:id
Get deployment status and details.

**Request:**
```bash
curl http://localhost:4000/api/deployments/deployment-uuid \
  -H "Authorization: Bearer pac_your_api_key_here"
```

**Response:**
```json
{
  "deployment": {
    "id": "deployment-uuid",
    "status": "processing",
    "package_id": "package-uuid",
    "agent_app_id": "app-uuid",
    "version": "1.2.0",
    "created_at": "2024-01-01T00:00:00Z",
    "started_at": "2024-01-01T00:01:00Z",
    "progress": {
      "current_step": "upload_to_s3",
      "steps": [
        {
          "name": "validate_package",
          "status": "completed",
          "started_at": "2024-01-01T00:01:00Z",
          "completed_at": "2024-01-01T00:01:10Z"
        },
        {
          "name": "upload_to_s3",
          "status": "processing",
          "started_at": "2024-01-01T00:01:10Z"
        },
        {
          "name": "generate_metadata",
          "status": "pending"
        },
        {
          "name": "notify_runtime",
          "status": "pending"
        },
        {
          "name": "finalize",
          "status": "pending"
        }
      ]
    }
  }
}
```

**Status Values:**
- `queued` - Deployment is waiting to be processed
- `processing` - Deployment is being processed
- `completed` - Deployment completed successfully
- `failed` - Deployment failed

#### GET /api/deployments/queue/stats
Get deployment queue statistics.

**Request:**
```bash
curl http://localhost:4000/api/deployments/queue/stats
```

**Response:**
```json
{
  "stats": {
    "queued": 3,
    "processing": 1,
    "completed": 156,
    "failed": 2,
    "total": 162
  },
  "health": {
    "status": "healthy",
    "message": "Queue is operating normally"
  },
  "metrics": {
    "avgProcessingTimeSeconds": 45,
    "lastUpdated": "2024-01-01T00:00:00Z"
  }
}
```

**Health Status Values:**
- `healthy` - Queue operating normally
- `warning` - High queue depth or failure rate
- `critical` - Too many jobs stuck in processing

## Environment Variables & Secrets

### Packaging Requirements
- `.env` at project root is REQUIRED. Build fails without it.
- `.env` is included in APKG; treat it as sensitive. Use placeholders for shared packages.

### Validation
- Presence check for `.env`.
- Warnings for secret-like values (e.g., `sk-`, `AWS_SECRET_ACCESS_KEY`, `-----BEGIN`).
- Warnings for absolute paths that harm portability.

### Runtime Injection (PAR guidance)
Recommended precedence when starting the agent subprocess:
1. Runtime deployment environment (from deployment request) [highest]
2. `.env` from APKG
3. Base runtime environment [lowest]

This lets you override packaged placeholders at deploy time.

### Service-Bound Secrets (optional)
If your runtime supports secret providers, inject secrets without storing them in the package.

- Static JSON provider:
  - `PIXELL_SECRETS_PROVIDER=static`
  - `PIXELL_SECRETS_JSON` set to a JSON object mapping env keys to values
- AWS Secrets Manager provider:
  - `PIXELL_SECRETS_PROVIDER=aws`
  - `PIXELL_AWS_SECRETS` = comma-separated secret names/ARNs
  - `PIXELL_AWS_REGION` = region (optional)

Precedence recommendation: provider > `.env` > base env.

### Dev Server Parity
The dev server mirrors the behavior for local runs:
- Loads `.env` automatically.
- Optionally loads secrets via provider (static/env/aws) using the same environment variables.
- Logs show counts and keys, never values.

### Examples
Static JSON override:
```bash
export PIXELL_SECRETS_PROVIDER=static
export PIXELL_SECRETS_JSON='{"OPENAI_API_KEY":"runtime","DB_HOST":"database"}'
```

AWS Secrets Manager:
```bash
export PIXELL_SECRETS_PROVIDER=aws
export PIXELL_AWS_SECRETS=my/app/secrets,another/secret
export PIXELL_AWS_REGION=us-east-1
```

Network and Path Hygiene:
- Use `0.0.0.0` for bind addresses in containers.
- Prefer service DNS names over IPs.
- Avoid absolute local filesystem paths in env vars; use relative paths or `/tmp`.
