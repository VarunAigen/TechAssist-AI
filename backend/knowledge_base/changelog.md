# CloudNexus — Changelog

## Version 4.2.0 (June 2026)
### New Features
- **AI-Powered Monitoring**: Introduced machine learning-based anomaly detection for application metrics. Automatically identifies unusual patterns and alerts teams before issues impact users.
- **Team Workspaces**: New collaborative workspaces where team members can share configurations, dashboards, and deployment pipelines.
- **Custom Domains with Auto-SSL**: Simplified custom domain setup with automatic Let's Encrypt SSL certificate provisioning and renewal.

### Improvements
- Dashboard load time reduced by 40%
- API response times improved by 25% across all endpoints
- Search functionality now supports fuzzy matching

### Bug Fixes
- Fixed an issue where deployment logs were truncated for builds exceeding 30 minutes
- Resolved WebSocket disconnection issue during rolling deployments
- Fixed timezone display in analytics charts

## Version 4.1.0 (April 2026)
### New Features
- **Preview Deployments**: Automatically create preview environments for pull requests. Each PR gets a unique URL for testing.
- **Secrets Manager**: Centralized secrets management with rotation policies and access controls.
- **Cost Explorer**: New tool to analyze and optimize cloud spending with recommendations.

### Improvements
- Container startup time reduced by 50%
- Added support for Node.js 22 LTS
- Improved error messages for failed deployments

## Version 4.0.0 (January 2026)
### Major Release
- **New Dashboard UI**: Complete redesign of the CloudNexus dashboard with improved navigation, dark mode, and customizable layouts.
- **Edge Functions**: Deploy serverless functions to edge locations for sub-10ms latency worldwide.
- **Database Branching**: Create database branches for development and testing without affecting production data.
- **GraphQL API**: New GraphQL API endpoint in addition to the existing REST API.

### Breaking Changes
- API v1 endpoints have been deprecated. Please migrate to v2 endpoints by March 2026.
- Minimum Node.js version updated from 16 to 18.
