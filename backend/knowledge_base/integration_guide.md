# CloudNexus — Integration Guide

## Overview

CloudNexus integrates with a wide range of third-party tools and platforms. This guide covers the most commonly requested integrations.

## CRM Integrations

### Salesforce
CloudNexus offers a native Salesforce integration that syncs deployment data, resource usage, and billing information directly to your Salesforce CRM.

**Setup:**
1. Install the "CloudNexus Connector" from the Salesforce AppExchange
2. Navigate to CloudNexus Dashboard → Integrations → Salesforce
3. Click "Connect" and authorize with your Salesforce admin account
4. Configure field mappings for Account, Opportunity, and Custom Objects

**Synced data:**
- Resource utilization → Custom fields on Account
- Deployment status → Activity feed
- Billing data → Opportunity amounts
- Usage alerts → Salesforce Tasks

**Sync frequency:** Real-time for critical events, batch sync every 15 minutes for metrics.

### HubSpot
HubSpot integration is currently in beta. It supports basic contact syncing and deal tracking. Full feature parity with the Salesforce integration is planned for Q3 2026.

## Communication Integrations

### Slack
The CloudNexus Slack app sends real-time notifications to your channels:
- Deployment notifications (started, completed, failed)
- Alert notifications (resource limits, downtime)
- Weekly summary reports

**Setup:** Install from the Slack App Directory and connect your CloudNexus workspace.

**Commands:**
- `/cloudnexus status` — Check current system status
- `/cloudnexus deploy [service]` — Trigger a deployment
- `/cloudnexus resources` — View resource summary

### Microsoft Teams
Teams integration is available on Professional and Enterprise plans. Features mirror the Slack integration.

## CI/CD Integrations

### GitHub Actions
CloudNexus provides official GitHub Actions for:
- `cloudnexus/deploy-action` — Deploy from GitHub workflow
- `cloudnexus/preview-action` — Create preview deployments for PRs

### GitLab CI
Use the CloudNexus CLI in your `.gitlab-ci.yml`:
```yaml
deploy:
  script:
    - cloudnexus deploy --env production
```

### Jenkins
A CloudNexus Jenkins plugin is available for automated deployments.

## Monitoring Integrations

### Datadog
CloudNexus metrics can be forwarded to Datadog for unified monitoring. Enable via Integrations → Datadog in the dashboard.

### PagerDuty
Connect CloudNexus alerts to PagerDuty for incident management. Supports custom escalation policies and service mappings.

### Grafana
Export CloudNexus metrics to Grafana using our Prometheus-compatible metrics endpoint at `/metrics`.

## Custom Integrations

For integrations not listed here, use the CloudNexus API (see API Reference) or webhooks to build custom integrations. Our Professional Services team can also assist with custom integration development for Enterprise customers.
