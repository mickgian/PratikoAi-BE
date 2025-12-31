# MCP Servers Infrastructure Guidelines

This file contains specialized knowledge for the PratikoAI AWS-optimized MCP (Model Context Protocol) server infrastructure deployment and management.

## Core Infrastructure Strategy

- Use **AWS-native services** for maximum cost optimization and scalability
- Implement **3-phase deployment approach**: Local development (FREE) → AWS Free Tier staging ($0 first year) → Serverless production ($2.30/month)
- Achieve **92% cost reduction** compared to traditional infrastructure ($2.30/month vs $29/month in first year)
- Maximize **AWS Free Tier usage** for 12-month startup runway with strategic service selection
- Use **serverless-first architecture** for production to minimize operational overhead

## Architecture Decisions and Rationale

- **Production**: Lambda + DynamoDB + API Gateway + CloudFront for cost efficiency and auto-scaling
- **Staging**: EC2 + RDS + ALB for team learning, debugging capabilities, and traditional deployment testing
- **Development**: Local Docker + AWS service integration for zero cloud costs during development
- **Database Strategy**: DynamoDB for production (serverless, pay-per-use) and PostgreSQL for staging (familiar, free tier)
- **Storage**: S3 with CloudFront CDN for global performance and cost optimization

## Deployment Tools and Scripts

- Use `provision-aws-startup.sh` as the primary interactive deployment script for all environments
- Execute CloudFormation templates for Infrastructure as Code with version control and rollback capabilities
- Deploy serverless applications using SAM (Serverless Application Model) templates for Lambda functions
- Monitor costs using AWS billing alerts and CloudWatch metrics to prevent unexpected charges
- Implement health checks using comprehensive `health-check.sh` script across all environments

## Cost Optimization Strategies

- **Free Tier Maximization**: Lambda (1M requests/month), DynamoDB (25GB + 25 RCU/WCU), S3 (5GB), CloudFront (1TB transfer)
- **Reserved Capacity Planning**: Use reserved instances for predictable workloads after growth validation
- **Intelligent Storage Tiering**: Implement S3 lifecycle policies to transition data to cheaper storage classes
- **Resource Right-Sizing**: Monitor CloudWatch metrics to optimize instance sizes and Lambda memory allocation
- **Auto-Scaling Configuration**: Set appropriate scaling policies to avoid over-provisioning during low usage periods

## Performance and Scaling Characteristics

- **Lambda Cold Starts**: 100-1000ms initial latency, mitigated with provisioned concurrency ($24/month for 100 concurrent)
- **DynamoDB Performance**: <10ms read/write latency with virtually unlimited throughput on-demand
- **CloudFront CDN**: Global edge locations provide <50ms latency worldwide for static content
- **API Gateway Limits**: 10,000 RPS default (increasable to 100,000+ with AWS support tickets)
- **Scaling Projections**: 10 RPS (cold) → 1000 RPS (warm) → 5000+ RPS (optimized with provisioned concurrency)

## Security Implementation

- **Multi-Layer Security**: CloudFront (DDoS) → API Gateway (rate limiting) → Lambda Authorizer (JWT) → IAM roles (resource access)
- **Encryption Standards**: AES-256 at rest for all storage, TLS 1.2+ in transit for all communications
- **IAM Best Practices**: Least-privilege access with resource-specific policies and condition-based access control
- **Secrets Management**: AWS Secrets Manager with automatic rotation for sensitive configuration values
- **Network Security**: VPC isolation for staging environment with private subnets for databases

## Monitoring and Observability

- **CloudWatch Integration**: Native AWS metrics collection with custom metrics for business KPIs
- **Grafana Dashboards**: Visual monitoring setup with pre-configured dashboards for system health
- **Cost Monitoring**: Billing alerts at $50 monthly threshold with detailed cost attribution by service
- **Performance Tracking**: Response time P95 <500ms target with automated alerting for threshold breaches
- **Error Rate Monitoring**: Target <1% error rate with immediate Slack notifications for critical issues

## Environment-Specific Configuration

### Local Development (FREE)
- **Docker Compose**: Multi-container setup with MCP server, PostgreSQL, Redis, and monitoring stack
- **AWS Integration**: S3 bucket creation for testing file uploads and storage functionality
- **Hot Reloading**: Development server with automatic restart on code changes
- **Local Monitoring**: Prometheus at localhost:9091 for metrics collection and analysis

### AWS Free Tier Staging ($0 first year, $29.50 after)
- **EC2 Instance**: t3.micro (750 hours/month free) with Auto Scaling Group for high availability
- **RDS Database**: db.t3.micro PostgreSQL (750 hours/month free) with automated backups
- **Load Balancer**: Application Load Balancer with health checks and SSL termination
- **Monitoring**: CloudWatch metrics with basic alerting for system health

### Serverless Production ($2.30/month first year, $32 after)
- **Lambda Functions**: Main application logic with automatic scaling and pay-per-invocation pricing
- **API Gateway**: RESTful API management with built-in throttling and request validation
- **DynamoDB**: NoSQL database with on-demand billing and single-digit millisecond latency
- **CloudFront**: Global CDN with 1TB free monthly transfer and automatic HTTPS

## Operational Procedures

- **Daily Health Checks**: Run `./scripts/health-check.sh all report` to verify system status across environments
- **Cost Review**: Weekly AWS cost analysis using `aws ce get-cost-and-usage` CLI commands
- **Performance Monitoring**: Monitor P95 response times and scale Lambda memory allocation as needed
- **Security Audits**: Monthly review of IAM policies, security groups, and access logs
- **Backup Verification**: Validate S3 versioning, DynamoDB backups, and disaster recovery procedures

## Scaling Decision Points

### Upgrade to Growth Phase ($75/month)
- **Trigger Conditions**: Monthly revenue >$500, active users >100, monthly requests >500K
- **Actions**: Upgrade RDS to db.t3.small, increase Lambda provisioned concurrency, enable CloudFront paid features
- **Timeline**: 4-hour migration window with zero-downtime deployment

### Upgrade to Scale Phase ($200/month)
- **Trigger Conditions**: Monthly revenue >$2000, active users >1000, monthly requests >5M
- **Actions**: Deploy EKS cluster, implement Aurora Serverless, add ElastiCache Redis, enable multi-region
- **Timeline**: 1-week migration project with comprehensive testing and rollback procedures

## Emergency Response Procedures

### Service Outage Response
1. **Assessment** (0-5 min): Run health check scripts and verify AWS service status
2. **Traffic Diversion** (5-10 min): Activate maintenance page or redirect to staging environment
3. **Root Cause Analysis** (10-30 min): Check recent deployments, system events, and infrastructure changes
4. **Recovery Actions** (30+ min): Rollback deployments, restore from backups, or scale resources

### Cost Spike Response
1. **Immediate**: Check billing dashboard and identify cost spike source service
2. **Short-term**: Implement temporary throttling or disable non-critical features
3. **Long-term**: Optimize resource allocation and implement better cost controls

## Key File References

- `aws-resource-allocation.yaml` - Detailed cost and technical specifications for all phases
- `AWS_DEPLOYMENT_GUIDE.md` - Comprehensive deployment walkthrough with troubleshooting steps
- `ADR-001-AWS-DEPLOYMENT-ARCHITECTURE.md` - Architectural decision record with failure analysis
- `provision-aws-startup.sh` - Interactive deployment script with environment selection menu
- `health-check.sh` - Comprehensive health monitoring across all environments and services

## Best Practices and Guidelines

- **Deploy backend before frontend** to ensure API compatibility during cross-repository deployments
- **Use semantic versioning** for infrastructure changes that affect other systems or repositories
- **Test in staging environment** before production deployment with comprehensive integration testing
- **Maintain cost discipline** by monitoring spending weekly and setting up proactive billing alerts
- **Document all changes** in ADR format for future reference and team knowledge sharing
- **Plan for disaster recovery** with regular backup testing and documented recovery procedures