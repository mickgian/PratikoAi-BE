# PratikoAI MCP Server Infrastructure

This directory contains the complete infrastructure configuration for PratikoAI's AWS-optimized MCP (Model Context Protocol) server deployment across development, staging, and production environments with a focus on startup-friendly cost optimization.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    PratikoAI MCP Infrastructure             │
├─────────────────────────────────────────────────────────────┤
│  Development     │    Staging       │    Production         │
│  ┌─────────────┐ │  ┌─────────────┐ │  ┌─────────────────┐   │
│  │ MCP Dev     │ │  │ MCP Staging │ │  │ MCP Production  │   │
│  │ - 2 CPU     │ │  │ - 4 CPU     │ │  │ - 8 CPU         │   │
│  │ - 4GB RAM   │ │  │ - 8GB RAM   │ │  │ - 16GB RAM      │   │
│  │ - 50GB SSD  │ │  │ - 100GB SSD │ │  │ - 500GB SSD     │   │
│  │ - 1 replica │ │  │ - 2 replicas│ │  │ - 3+ replicas   │   │
│  └─────────────┘ │  └─────────────┘ │  └─────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

1. **Prerequisites Setup**:
   ```bash
   # Install required tools
   ./scripts/install-prerequisites.sh

   # Configure environment
   cp config/env.example config/.env.development
   ```

2. **Deploy Development Environment**:
   ```bash
   ./scripts/provision-dev.sh
   ```

3. **Deploy Staging Environment**:
   ```bash
   ./scripts/provision-staging.sh
   ```

4. **Deploy Production Environment**:
   ```bash
   ./scripts/provision-production.sh
   ```

## Directory Structure

```
mcp-servers/
├── INDEX.md                       # This file
├── config/                        # Configuration files
│   ├── env.example               # Environment template
│   ├── development.yaml          # Dev environment config
│   ├── staging.yaml              # Staging environment config
│   ├── production.yaml           # Production environment config
│   └── security/                 # Security configurations
├── scripts/                       # Provisioning and management scripts
│   ├── provision-dev.sh          # Development provisioning
│   ├── provision-staging.sh      # Staging provisioning
│   ├── provision-production.sh   # Production provisioning
│   ├── install-prerequisites.sh  # Prerequisites installer
│   ├── backup-restore.sh         # Backup and restore utilities
│   └── health-check.sh           # Health monitoring
├── kubernetes/                    # Kubernetes manifests
│   ├── base/                     # Base configurations
│   ├── overlays/                 # Environment overlays
│   └── monitoring/               # Monitoring stack
├── docker/                        # Docker configurations
│   ├── mcp-server/               # MCP server images
│   ├── monitoring/               # Monitoring containers
│   └── security/                 # Security tools
└── monitoring/                    # Monitoring and alerting
    ├── prometheus/               # Prometheus configuration
    ├── grafana/                  # Grafana dashboards
    └── alerts/                   # Alert rules
```

## Environment Specifications

### Development Environment
- **Purpose**: Local development and testing
- **Resources**: 2 CPU, 4GB RAM, 50GB SSD
- **Replicas**: 1
- **Uptime**: Business hours only
- **Cost**: ~$50/month

### Staging Environment
- **Purpose**: Pre-production testing and validation
- **Resources**: 4 CPU, 8GB RAM, 100GB SSD
- **Replicas**: 2 (high availability)
- **Uptime**: 24/7
- **Cost**: ~$200/month

### Production Environment
- **Purpose**: Live production workloads
- **Resources**: 8+ CPU, 16+ GB RAM, 500GB+ SSD
- **Replicas**: 3+ (auto-scaling)
- **Uptime**: 99.9% SLA
- **Cost**: ~$800/month (base), scales with usage

## Security Features

- **Authentication**: OAuth 2.0 with JWT tokens
- **Authorization**: RBAC with environment-specific permissions
- **Network Security**: VPN, firewalls, and network segmentation
- **Data Encryption**: TLS 1.3 in transit, AES-256 at rest
- **Secret Management**: HashiCorp Vault integration
- **Audit Logging**: Comprehensive audit trails

## Monitoring and Alerting

- **Health Monitoring**: Real-time server health checks
- **Performance Metrics**: CPU, memory, network, and disk utilization
- **Application Metrics**: MCP protocol metrics and response times
- **Log Aggregation**: Centralized logging with ELK stack
- **Alerting**: PagerDuty integration for critical alerts

## Cost Optimization

- **Auto-scaling**: Horizontal scaling based on load
- **Resource Right-sizing**: Regular resource utilization analysis
- **Spot Instances**: Non-critical workloads on spot instances
- **Reserved Capacity**: Long-term reservations for predictable workloads
- **Monitoring**: Cost tracking and budget alerts

## Support and Troubleshooting

For issues and support:
1. Check the [Troubleshooting Guide](docs/troubleshooting.md)
2. Review [Monitoring Dashboards](monitoring/grafana/)
3. Contact the Platform Engineering team
4. Create an issue in the repository

## Next Steps

1. Review the configuration files in `config/`
2. Customize environment variables for your setup
3. Run the provisioning scripts for your target environment
4. Set up monitoring and alerting
5. Configure backup and disaster recovery procedures
