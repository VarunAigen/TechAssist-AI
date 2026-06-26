# CloudNexus — Frequently Asked Questions

## General

**Q: What is CloudNexus?**
A: CloudNexus is an enterprise cloud platform that provides scalable infrastructure, deployment tools, and monitoring for businesses of all sizes. Think of it as your complete cloud operations platform.

**Q: How is CloudNexus different from AWS/Azure/GCP?**
A: CloudNexus is built on top of major cloud providers but abstracts away the complexity. You get enterprise-grade infrastructure without needing a dedicated DevOps team. We handle scaling, security, compliance, and monitoring automatically.

**Q: Can I try CloudNexus before purchasing?**
A: Yes! Our Free tier is available permanently with no credit card required. You can also request a 14-day trial of the Professional plan.

## Technical

**Q: What programming languages does CloudNexus support?**
A: CloudNexus supports any language that can run in a Docker container. We have first-class support (auto-detection, optimized builds) for Node.js, Python, Go, Ruby, and Java. For other languages, use our Docker deployment option.

**Q: How does auto-scaling work?**
A: CloudNexus monitors your application's CPU usage, memory, and request queue depth. When metrics exceed configured thresholds (default: 70% CPU), we automatically provision additional instances within 30 seconds. Scaling down happens after a 5-minute cooldown period.

**Q: What is the maximum file upload size?**
A: The default maximum upload size is 100 MB per file. This can be increased to 5 GB on Enterprise plans by contacting support.

**Q: Do you support WebSocket connections?**
A: Yes, CloudNexus fully supports WebSocket connections on all plans. WebSocket connections are load-balanced using sticky sessions to ensure connection persistence.

**Q: What database options are available?**
A: CloudNexus offers managed databases including PostgreSQL, MySQL, MongoDB, and Redis. All databases include automated backups, point-in-time recovery, and read replicas (Professional and Enterprise plans).

## Security

**Q: Is my data encrypted?**
A: Yes, all data is encrypted both in transit (TLS 1.3) and at rest (AES-256). Enterprise customers can use their own encryption keys (CMEK).

**Q: Do you have a bug bounty program?**
A: Yes, we run a bug bounty program through HackerOne. Responsible disclosure of security vulnerabilities is rewarded with bounties ranging from $100 to $10,000.

**Q: Where can I find your security documentation?**
A: Detailed security documentation is available at https://cloudnexus.io/security. SOC 2 reports are available to customers under NDA.

## Billing

**Q: Can I switch between plans?**
A: Yes, you can upgrade or downgrade at any time. Upgrades take effect immediately and are prorated. Downgrades take effect at the start of the next billing cycle.

**Q: Do you offer refunds?**
A: We offer a 30-day money-back guarantee for new customers. After 30 days, remaining prepaid time is credited to your account.

**Q: What happens if I exceed my bandwidth limit?**
A: You'll receive a notification at 80% usage. Beyond the limit, additional bandwidth is charged at $0.10/GB. We never throttle or cut off your service.
