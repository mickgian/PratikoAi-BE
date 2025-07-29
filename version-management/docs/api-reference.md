# 🔗 API Reference

Complete reference for the PratikoAI Version Management System REST API.

## Base URL

```
http://localhost:8001/api/v1
```

## Authentication

The API uses Bearer token authentication:

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://version-registry.your-domain.com/api/v1/versions
```

## Rate Limiting

- **Rate Limit**: 1000 requests per hour per token
- **Burst Limit**: 50 requests per minute
- **Headers**: `X-RateLimit-Remaining`, `X-RateLimit-Reset`

## Error Responses

All errors follow this format:

```json
{
  "error": "error_code",
  "message": "Human readable error message",
  "details": {
    "field": "specific error details"
  },
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req_123abc"
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict |
| 422 | Validation Error |
| 429 | Rate Limited |
| 500 | Internal Server Error |

---

## Endpoints

### Health Check

#### GET /health

Check API health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0",
  "database": "connected",
  "services": {
    "registry": "healthy",
    "compatibility_checker": "healthy"
  }
}
```

---

## Version Management

### Register Version

#### POST /versions/register

Register a new service version.

**Request Body:**
```json
{
  "service_type": "backend",
  "version": "1.2.0",
  "git_commit": "abc123def456",
  "git_branch": "main",
  "change_type": "minor",
  "release_notes": "Added user authentication API",
  "breaking_changes": [
    "Changed user ID format from integer to UUID"
  ],
  "new_features": [
    "OAuth2 authentication",
    "Role-based permissions"
  ],
  "bug_fixes": [
    "Fixed memory leak in user session handling"
  ],
  "dependencies": [
    {
      "service_type": "database",
      "min_version": "13.0",
      "reason": "Requires UUID extension"
    }
  ],
  "api_contract": {
    "openapi_spec": {...},
    "endpoints": [...],
    "schemas": {...}
  },
  "feature_flags": {
    "new_auth_flow": true,
    "legacy_login": false
  },
  "created_by": "john.doe"
}
```

**Response:**
```json
{
  "version_id": "550e8400-e29b-41d4-a716-446655440000",
  "service_type": "backend",
  "version": "1.2.0",
  "created_at": "2024-01-15T10:30:00Z",
  "status": "registered"
}
```

### Get Version

#### GET /versions/{service_type}/{version}

Get details of a specific version.

**Parameters:**
- `service_type`: Service type (backend, frontend-android, etc.)
- `version`: Version identifier

**Response:**
```json
{
  "version_id": "550e8400-e29b-41d4-a716-446655440000",
  "service_type": "backend",
  "version": "1.2.0",
  "git_commit": "abc123def456",
  "git_branch": "main",
  "change_type": "minor",
  "release_notes": "Added user authentication API",
  "breaking_changes": ["Changed user ID format"],
  "new_features": ["OAuth2 authentication"],
  "bug_fixes": ["Fixed memory leak"],
  "dependencies": [...],
  "deployments": {
    "development": "2024-01-15T10:30:00Z",
    "staging": "2024-01-15T11:00:00Z"
  },
  "created_at": "2024-01-15T10:30:00Z",
  "created_by": "john.doe"
}
```

### List Versions

#### GET /versions/{service_type}

List versions for a service.

**Query Parameters:**
- `limit` (optional): Maximum number of versions (default: 20)
- `offset` (optional): Number of versions to skip (default: 0)
- `order` (optional): Sort order - "asc" or "desc" (default: "desc")

**Response:**
```json
{
  "versions": [
    {
      "version": "1.2.0",
      "change_type": "minor",
      "created_at": "2024-01-15T10:30:00Z",
      "breaking_changes": true,
      "deployments": ["development", "staging"]
    },
    {
      "version": "1.1.5",
      "change_type": "patch",
      "created_at": "2024-01-14T15:20:00Z",
      "breaking_changes": false,
      "deployments": ["development", "staging", "production"]
    }
  ],
  "total": 45,
  "limit": 20,
  "offset": 0
}
```

### Get Latest Version

#### GET /versions/{service_type}/latest

Get the latest version for a service.

**Response:**
```json
{
  "version": "1.2.0",
  "version_id": "550e8400-e29b-41d4-a716-446655440000",
  "change_type": "minor",
  "created_at": "2024-01-15T10:30:00Z",
  "deployments": ["development", "staging"]
}
```

### Delete Version

#### DELETE /versions/{service_type}/{version}

Delete a version (admin only).

**Response:**
```json
{
  "message": "Version backend v1.2.0 deleted successfully",
  "deleted_at": "2024-01-15T12:00:00Z"
}
```

---

## Compatibility Management

### Check Compatibility

#### POST /compatibility/check

Check compatibility between two service versions.

**Request Body:**
```json
{
  "source_service": "frontend-android",
  "source_version": "2.1.0",
  "target_service": "backend",
  "target_version": "1.2.0"
}
```

**Response:**
```json
{
  "compatible": true,
  "compatibility_level": "fully_compatible",
  "issues": [],
  "warnings": [
    "Using deprecated endpoint /api/v1/login"
  ],
  "recommendations": [
    "Update to use /api/v2/auth/login"
  ],
  "checked_at": "2024-01-15T10:30:00Z"
}
```

### Get Compatibility Matrix

#### GET /compatibility/{service_type}/{version}

Get compatibility matrix for a version.

**Response:**
```json
{
  "service_type": "backend",
  "version": "1.2.0",
  "compatibility_matrix": {
    "frontend-android:2.1.0": "fully_compatible",
    "frontend-android:2.0.5": "backward_compatible",
    "frontend-ios:1.9.2": "fully_compatible",
    "frontend-web:1.8.0": "limited_compatible"
  },
  "dependencies": [
    {
      "service_type": "database",
      "min_version": "13.0",
      "max_version": null,
      "optional": false,
      "reason": "Requires UUID extension"
    }
  ],
  "generated_at": "2024-01-15T10:30:00Z"
}
```

### Validate Deployment

#### POST /validate-deployment

Validate if a deployment is safe.

**Request Body:**
```json
{
  "service_type": "backend",
  "version": "1.2.0",
  "environment": "production"
}
```

**Response:**
```json
{
  "can_deploy": true,
  "compatibility_level": "fully_compatible",
  "blocking_issues": [],
  "warnings": [
    "This version has not been tested in production"
  ],
  "dependency_checks": [
    {
      "service_type": "database",
      "min_version": "13.0",
      "deployed_version": "13.2",
      "satisfied": true
    }
  ],
  "recommendations": [
    "Deploy to staging first for additional testing"
  ],
  "validated_at": "2024-01-15T10:30:00Z"
}
```

---

## Deployment Management

### Record Deployment

#### POST /deployments

Record a deployment event.

**Request Body:**
```json
{
  "service_type": "backend",
  "version": "1.2.0",
  "environment": "production",
  "deployed_by": "john.doe",
  "deployment_id": "deploy_123",
  "deployment_strategy": "blue-green",
  "metadata": {
    "rollback_version": "1.1.5",
    "health_check_url": "https://api.example.com/health"
  }
}
```

**Response:**
```json
{
  "deployment_id": "550e8400-e29b-41d4-a716-446655440000",
  "service_type": "backend",
  "version": "1.2.0",
  "environment": "production",
  "deployed_at": "2024-01-15T10:30:00Z",
  "status": "deployed"
}
```

### Get Deployment Status

#### GET /deployments/{environment}

Get current deployment status for an environment.

**Response:**
```json
{
  "environment": "production",
  "services": {
    "backend": {
      "version": "1.2.0",
      "deployed_at": "2024-01-15T10:30:00Z",
      "deployed_by": "john.doe",
      "status": "healthy",
      "health_check_passed": true,
      "rollback_version": "1.1.5"
    },
    "frontend-android": {
      "version": "2.1.0",
      "deployed_at": "2024-01-15T09:45:00Z",
      "deployed_by": "jane.smith",
      "status": "healthy",
      "health_check_passed": true
    }
  },
  "last_updated": "2024-01-15T10:30:00Z"
}
```

### Get Deployment History

#### GET /deployments/{environment}/history

Get deployment history for an environment.

**Query Parameters:**
- `limit` (optional): Maximum number of deployments (default: 50)
- `service_type` (optional): Filter by service type

**Response:**
```json
{
  "deployments": [
    {
      "deployment_id": "550e8400-e29b-41d4-a716-446655440000",
      "service_type": "backend",
      "version": "1.2.0",
      "deployed_at": "2024-01-15T10:30:00Z",
      "deployed_by": "john.doe",
      "status": "success",
      "duration_minutes": 12
    },
    {
      "deployment_id": "450e8400-e29b-41d4-a716-446655440001",
      "service_type": "backend",
      "version": "1.1.5",
      "deployed_at": "2024-01-14T15:20:00Z",
      "deployed_by": "jane.smith",
      "status": "success",
      "duration_minutes": 8
    }
  ],
  "total": 127,
  "environment": "production"
}
```

---

## Statistics and Monitoring

### Get System Statistics

#### GET /stats

Get overall system statistics.

**Response:**
```json
{
  "versions": {
    "total": 342,
    "by_service": {
      "backend": 89,
      "frontend-android": 85,
      "frontend-ios": 78,
      "frontend-web": 90
    },
    "by_change_type": {
      "major": 12,
      "minor": 98,
      "patch": 232
    }
  },
  "deployments": {
    "total": 1205,
    "successful": 1156,
    "failed": 49,
    "success_rate": 0.959
  },
  "compatibility_checks": {
    "total": 2847,
    "passed": 2698,
    "failed": 149,
    "pass_rate": 0.948
  },
  "environments": {
    "development": 156,
    "staging": 124,
    "production": 89
  },
  "generated_at": "2024-01-15T10:30:00Z"
}
```

### Get Service Statistics

#### GET /stats/{service_type}

Get statistics for a specific service.

**Query Parameters:**
- `days` (optional): Number of days to include (default: 30)

**Response:**
```json
{
  "service_type": "backend",
  "versions": {
    "total": 89,
    "recent": 12,
    "breaking_changes": 3
  },
  "deployments": {
    "successful": 278,
    "failed": 12,
    "success_rate": 0.959,
    "avg_duration_minutes": 8.5
  },
  "compatibility": {
    "checks": 456,
    "issues_found": 23,
    "most_incompatible_with": "frontend-web"
  },
  "period_days": 30,
  "generated_at": "2024-01-15T10:30:00Z"
}
```

---

## Webhook Management

### Register Webhook

#### POST /webhooks

Register a webhook for version events.

**Request Body:**
```json
{
  "url": "https://your-app.com/webhooks/versions",
  "events": [
    "version.registered",
    "deployment.completed",
    "compatibility.failed"
  ],
  "secret": "your-webhook-secret",
  "active": true
}
```

**Response:**
```json
{
  "webhook_id": "550e8400-e29b-41d4-a716-446655440000",
  "url": "https://your-app.com/webhooks/versions",
  "events": ["version.registered", "deployment.completed"],
  "created_at": "2024-01-15T10:30:00Z",
  "active": true
}
```

### List Webhooks

#### GET /webhooks

List registered webhooks.

**Response:**
```json
{
  "webhooks": [
    {
      "webhook_id": "550e8400-e29b-41d4-a716-446655440000",
      "url": "https://your-app.com/webhooks/versions",
      "events": ["version.registered"],
      "active": true,
      "created_at": "2024-01-15T10:30:00Z",
      "last_delivery": "2024-01-15T11:15:00Z",
      "delivery_status": "success"
    }
  ]
}
```

---

## Webhook Events

### Event Types

| Event | Description |
|-------|-------------|
| `version.registered` | New version registered |
| `version.updated` | Version metadata updated |
| `deployment.started` | Deployment initiated |
| `deployment.completed` | Deployment finished |
| `deployment.failed` | Deployment failed |
| `compatibility.checked` | Compatibility check performed |
| `compatibility.failed` | Compatibility issues found |

### Event Payload

```json
{
  "event": "version.registered",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "service_type": "backend",
    "version": "1.2.0",
    "version_id": "550e8400-e29b-41d4-a716-446655440000",
    "created_by": "john.doe",
    "change_type": "minor",
    "breaking_changes": true
  },
  "webhook_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## SDK Examples

### Python SDK

```python
import httpx
from typing import Dict, Any

class VersionManagementClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip('/')
        self.headers = {"Authorization": f"Bearer {token}"}
    
    async def register_version(self, version_data: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/versions/register",
                json=version_data,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def check_compatibility(self, source_service: str, source_version: str,
                                target_service: str, target_version: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/compatibility/check",
                json={
                    "source_service": source_service,
                    "source_version": source_version,
                    "target_service": target_service,
                    "target_version": target_version
                },
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

# Usage
client = VersionManagementClient("http://localhost:8001", "your-token")
result = await client.register_version({
    "service_type": "backend",
    "version": "1.2.0",
    "git_commit": "abc123",
    "change_type": "minor"
})
```

### JavaScript SDK

```javascript
class VersionManagementClient {
  constructor(baseUrl, token) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.headers = {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  }

  async registerVersion(versionData) {
    const response = await fetch(`${this.baseUrl}/api/v1/versions/register`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify(versionData)
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }
    
    return response.json();
  }

  async checkCompatibility(sourceService, sourceVersion, targetService, targetVersion) {
    const response = await fetch(`${this.baseUrl}/api/v1/compatibility/check`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({
        source_service: sourceService,
        source_version: sourceVersion,
        target_service: targetService,
        target_version: targetVersion
      })
    });
    
    return response.json();
  }
}

// Usage
const client = new VersionManagementClient('http://localhost:8001', 'your-token');
const result = await client.registerVersion({
  service_type: 'frontend-android',
  version: '2.1.0',
  git_commit: 'def456',
  change_type: 'minor'
});
```

---

## OpenAPI Specification

The complete OpenAPI 3.0 specification is available at:

```
GET /api/v1/openapi.json
GET /api/v1/docs  # Swagger UI
GET /api/v1/redoc # ReDoc UI
```

## Rate Limiting Headers

All API responses include rate limiting information:

- `X-RateLimit-Limit`: Requests allowed per window
- `X-RateLimit-Remaining`: Requests remaining in current window
- `X-RateLimit-Reset`: Unix timestamp when window resets
- `X-RateLimit-Retry-After`: Seconds to wait if rate limited

---

This API reference provides complete coverage of all endpoints and their usage. For implementation examples, see the [Developer Guide](developer-guide.md).