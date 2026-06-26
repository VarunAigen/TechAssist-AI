# CloudNexus — Deployment Guide

## Deployment Options

### 1. CloudNexus Managed (Recommended)
The simplest option — deploy directly to CloudNexus managed infrastructure.

**Steps:**
1. Push your code to a connected Git repository (GitHub, GitLab, Bitbucket)
2. CloudNexus automatically detects your framework and configures the build
3. Click "Deploy" or set up automatic deployments on push

**Supported frameworks:**
- Node.js (Express, Next.js, Fastify)
- Python (Django, Flask, FastAPI)
- Go
- Ruby (Rails, Sinatra)
- Java (Spring Boot)
- Docker containers (any language)

### 2. Docker Deployment
Bring your own Docker container and deploy it to CloudNexus.

**Steps:**
1. Build your Docker image locally
2. Push to CloudNexus Container Registry: `docker push registry.cloudnexus.io/your-app`
3. Configure deployment settings (replicas, health checks, environment variables)
4. Deploy via dashboard or CLI

### 3. Kubernetes (Enterprise)
Enterprise customers can deploy to managed Kubernetes clusters.

**Features:**
- Managed control plane
- Auto-scaling node pools
- Integrated monitoring and logging
- Helm chart support

## Deployment Configuration

### Environment Variables
Set environment variables via:
- Dashboard: Settings → Environment
- CLI: `cloudnexus env set KEY=value`
- `.env` files (not recommended for production secrets)

### Health Checks
Configure health checks for automatic restart and load balancing:
- **HTTP check**: GET request to a specified endpoint
- **TCP check**: Port connectivity check
- **Command check**: Custom health check script

Default: HTTP GET to `/health` every 30 seconds.

### Scaling Configuration
```yaml
scaling:
  min_instances: 2
  max_instances: 20
  target_cpu: 70%
  scale_up_cooldown: 60s
  scale_down_cooldown: 300s
```

## Rollbacks
Every deployment creates a snapshot. To rollback:
- Dashboard: Deployments → Select version → "Rollback"
- CLI: `cloudnexus rollback --to=v42`
- API: `POST /deployments/{id}/rollback`

Rollbacks complete within 30 seconds.

## Zero-Downtime Deployments
CloudNexus uses rolling deployments by default:
1. New version is deployed alongside the old version
2. Health checks pass on new version
3. Traffic gradually shifts to new version
4. Old version is terminated

Blue-green and canary deployments available on Professional and Enterprise plans.
