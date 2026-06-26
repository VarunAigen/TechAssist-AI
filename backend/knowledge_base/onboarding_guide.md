# CloudNexus — Onboarding Guide

## Getting Started with CloudNexus

Welcome to CloudNexus! This guide will help you set up your account and deploy your first application in under 15 minutes.

## Step 1: Create Your Account

1. Visit https://dashboard.cloudnexus.io/signup
2. Enter your work email and create a password
3. Verify your email address
4. Complete your profile (company name, team size, primary use case)

No credit card required for the Free tier.

## Step 2: Set Up Your Workspace

After signup, you'll be guided through workspace setup:

1. **Name your workspace**: This is your team's namespace (e.g., "acme-corp")
2. **Invite team members**: Add colleagues by email. They'll receive an invitation link.
3. **Choose your region**: Select the primary region closest to your users

## Step 3: Connect Your Repository

CloudNexus integrates with major Git providers:

1. Navigate to Settings → Git Integration
2. Click "Connect" for your provider (GitHub, GitLab, Bitbucket)
3. Authorize CloudNexus to access your repositories
4. Select the repository you want to deploy

## Step 4: Deploy Your First Application

### Automatic Framework Detection
CloudNexus will automatically detect your framework and suggest optimal build settings:

| Framework | Build Command | Output Directory |
|-----------|--------------|-----------------|
| Next.js | `npm run build` | `.next` |
| React (Vite) | `npm run build` | `dist` |
| Django | `pip install -r requirements.txt` | N/A (server) |
| FastAPI | `pip install -r requirements.txt` | N/A (server) |
| Express | `npm install` | N/A (server) |

### Manual Configuration
If automatic detection doesn't work, create a `cloudnexus.yaml` file:
```yaml
name: my-app
build:
  command: npm run build
  output: dist
runtime:
  command: npm start
  port: 3000
```

## Step 5: Configure Environment Variables

1. Go to your project → Settings → Environment
2. Add required environment variables (database URLs, API keys, etc.)
3. Use "Production" and "Preview" environments to separate configs

## Step 6: Set Up Custom Domain

1. Go to Settings → Domains
2. Click "Add Domain" and enter your domain
3. Add the provided CNAME record to your DNS provider
4. SSL certificate is automatically provisioned (usually within 5 minutes)

## Step 7: Enable Monitoring

CloudNexus includes built-in monitoring:
1. **Application logs**: Available immediately in the Logs tab
2. **Performance metrics**: CPU, memory, and response time charts
3. **Alerts**: Set up alerts for downtime, high error rates, or resource limits

## Next Steps

- Read the [API Reference](api_reference.md) to integrate programmatically
- Set up [Slack/Teams notifications](integration_guide.md) for deployment updates
- Configure [auto-scaling](deployment_guide.md) for production workloads
- Review [security settings](auth_security_spec.md) and enable MFA

## Getting Help

- **Documentation**: https://docs.cloudnexus.io
- **Community forum**: https://community.cloudnexus.io
- **Support email**: support@cloudnexus.io
- **Live chat**: Available in-dashboard (Professional & Enterprise plans)
