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
