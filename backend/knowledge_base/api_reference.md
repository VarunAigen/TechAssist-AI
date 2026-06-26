# CloudNexus — API Reference

## API Overview

The CloudNexus API is a RESTful API that allows programmatic access to all platform features. All API endpoints use HTTPS and return JSON responses.

**Base URL**: `https://api.cloudnexus.io/v2`

**Rate Limits**:
- Free tier: 100 requests/minute
- Professional: 1,000 requests/minute
- Enterprise: 10,000 requests/minute (customizable)

## Authentication

All API requests require authentication via API keys or OAuth 2.0 bearer tokens.

### API Key Authentication
Include your API key in the request header:
```
Authorization: Bearer cn_live_xxxxxxxxxxxxxxxxxxxx
```

API keys can be generated from the CloudNexus Dashboard under Settings → API Keys. Each key can be scoped to specific permissions (read-only, read-write, admin).

### OAuth 2.0
For user-facing applications, CloudNexus supports OAuth 2.0 authorization code flow. Register your application at https://dashboard.cloudnexus.io/oauth/apps to receive a client_id and client_secret.

## Core Endpoints

### Resources
- `GET /resources` — List all cloud resources
- `POST /resources` — Create a new resource
- `GET /resources/{id}` — Get resource details
- `PUT /resources/{id}` — Update a resource
- `DELETE /resources/{id}` — Delete a resource

### Deployments
- `GET /deployments` — List all deployments
- `POST /deployments` — Create a new deployment
- `GET /deployments/{id}/status` — Check deployment status
- `POST /deployments/{id}/rollback` — Rollback a deployment

### Analytics
- `GET /analytics/overview` — Get analytics summary
- `GET /analytics/metrics` — Get detailed metrics
- `GET /analytics/events` — Get event stream

### Users & Teams
- `GET /team/members` — List team members
- `POST /team/invite` — Invite a team member
- `PUT /team/members/{id}/role` — Update member role
- `DELETE /team/members/{id}` — Remove team member

## Webhooks

CloudNexus supports webhooks for real-time event notifications. Configure webhooks at Dashboard → Settings → Webhooks.

Supported events:
- `deployment.started`, `deployment.completed`, `deployment.failed`
- `resource.created`, `resource.deleted`, `resource.alert`
- `team.member_added`, `team.member_removed`
- `billing.invoice_generated`, `billing.payment_failed`

Webhook payloads are signed with HMAC-SHA256 for verification.

## SDKs

Official SDKs are available for:
- **Python**: `pip install cloudnexus-sdk`
- **JavaScript/Node.js**: `npm install @cloudnexus/sdk`
- **Go**: `go get github.com/cloudnexus/go-sdk`
- **Java**: Available via Maven Central
- **Ruby**: `gem install cloudnexus`

## Error Handling

All errors follow a standard format:
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "The requested resource does not exist",
    "status": 404
  }
}
```

Common error codes: UNAUTHORIZED (401), FORBIDDEN (403), RATE_LIMITED (429), INTERNAL_ERROR (500).
