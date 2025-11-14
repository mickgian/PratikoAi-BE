# 🌐 PratikoAI Cross-Repository Deployment Orchestration System

A comprehensive deployment coordination system that ensures synchronized deployments between your Kotlin Multiplatform frontend and FastAPI+LangGraph backend repositories.

## 🎯 Overview

This system provides advanced cross-repository deployment orchestration with:

- **Workflow Coordination**: Triggers and coordinates workflows across multiple repositories
- **Dependency Management**: Ensures correct deployment sequencing (backend first, then frontend)
- **Health Validation**: Validates system health at each deployment step
- **Artifact Sharing**: Shares build artifacts and deployment information between repositories
- **Notification System**: Comprehensive notifications with actionable information
- **Rollback Capabilities**: Automated rollback on deployment failures
- **Multi-Channel Alerts**: Slack, email, GitHub issues, and webhook notifications

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                Cross-Repository Orchestration System                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │   Orchestrator  │    │   Notification  │    │    Artifact     │  │
│  │     Engine      │◄──►│     System      │◄──►│   Coordinator   │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│           │                       │                       │         │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │   Backend Repo  │    │   Frontend Repo │    │   Version       │  │
│  │   Workflows     │    │   Workflows     │    │   Registry      │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### 1. Configure Repository Secrets

Add these secrets to both repositories:

```bash
# Cross-repository coordination
CROSS_REPO_TOKEN=ghp_your_github_token_with_repo_access
ORCHESTRATOR_WEBHOOK_URL=https://your-orchestrator.com/webhook
ORCHESTRATOR_TOKEN=your_orchestrator_api_key

# Version management
VERSION_REGISTRY_URL=https://version-registry.pratiko.ai
VERSION_REGISTRY_TOKEN=your_version_registry_token
VERSION_REGISTRY_DB_URL=postgresql://user:pass@host/db  # pragma: allowlist secret

# Notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
SMTP_HOST=smtp.your-email-provider.com
SMTP_USERNAME=your_smtp_username
SMTP_PASSWORD=your_smtp_password

# Cloud storage (optional)
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
S3_ARTIFACT_BUCKET=pratiko-deployment-artifacts
```

### 2. Trigger Cross-Repository Deployment

#### Via GitHub Actions UI:
1. Go to Actions tab in the backend repository
2. Select "Cross-Repository Deployment Trigger"
3. Click "Run workflow"
4. Fill in the parameters:
   - **Environment**: staging/production
   - **Backend Version**: 1.2.0
   - **Frontend Versions**: `{"android": "2.1.0", "ios": "2.0.5", "web": "2.1.0"}`
   - **Strategy**: sequential/parallel/canary

#### Via API:
```bash
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/mickgian/PratikoAi-BE/actions/workflows/cross-repo-trigger.yml/dispatches \
  -d '{
    "ref": "main",
    "inputs": {
      "target_environment": "staging",
      "backend_version": "1.2.0",
      "frontend_versions": "{\"android\": \"2.1.0\", \"ios\": \"2.0.5\", \"web\": \"2.1.0\"}",
      "deployment_strategy": "sequential"
    }
  }'
```

#### Programmatically:
```python
from deployment_orchestration.orchestrator import CrossRepoOrchestrator
from deployment_orchestration.orchestrator import Environment

# Initialize orchestrator
orchestrator = CrossRepoOrchestrator(
    github_token="your_github_token"  # pragma: allowlist secret,
    webhook_url="https://your-webhook.com"
)

# Create deployment plan
plan = await orchestrator.create_deployment_plan(
    Environment.STAGING,
    backend_version="1.2.0",
    frontend_versions={"android": "2.1.0", "ios": "2.0.5", "web": "2.1.0"},
    created_by="api-user"
)

# Execute deployment
execution = await orchestrator.execute_deployment_plan(plan)
print(f"Deployment status: {execution.status}")
```

## 📋 System Components

### 1. Deployment Orchestrator (`orchestrator.py`)

The main coordination engine that:
- Creates deployment plans with dependency resolution
- Triggers workflows in correct sequence
- Monitors deployment progress
- Handles rollbacks on failure
- Coordinates health checks

**Key Features:**
- Support for sequential, parallel, and canary deployment strategies
- Automatic dependency resolution and ordering
- Health check validation after each deployment step
- Comprehensive error handling and rollback capabilities
- Integration with version management system

### 2. Notification System (`notification_system.py`)

Multi-channel notification system that provides:
- **Slack Integration**: Rich messages with action buttons
- **Email Notifications**: HTML and text formats with deployment details
- **GitHub Issues**: Automatic issue creation on failures
- **Webhook Support**: Generic webhook for custom integrations
- **Escalation Rules**: Progressive notifications based on severity

**Notification Types:**
- Deployment started/completed/failed
- Rollback events
- Health check failures
- Compatibility warnings
- Manual intervention required

### 3. Artifact Coordinator (`artifact_coordinator.py`)

Manages build artifacts and deployment information:
- **Cross-Repository Sharing**: Share artifacts between workflows
- **Multiple Storage Backends**: GitHub, S3, local filesystem
- **Version Manifests**: Complete deployment metadata
- **Rollback Artifacts**: Preserve artifacts for rollback operations

**Supported Artifacts:**
- Build information and metadata
- Deployment configurations
- Health check reports
- Compatibility reports
- Performance metrics
- Test results

### 4. GitHub Actions Workflows

#### Backend Repository (`orchestrated-deployment.yml`):
- Pre-deployment validation and compatibility checks
- Docker image building and testing
- Environment-specific deployment with health validation
- Cross-repository trigger for frontend deployment
- Rollback capabilities

#### Frontend Repository (`orchestrated-frontend-deployment.yml`):
- Multi-platform KMP builds (Android, iOS, Web, Desktop)
- Backend dependency validation
- Platform-specific deployment strategies
- Coordinated deployment reporting

#### Cross-Repository Trigger (`cross-repo-trigger.yml`):
- Master workflow for initiating coordinated deployments
- Support for different deployment strategies
- Dry-run capabilities for validation
- Comprehensive reporting and notifications

## 🔧 Configuration

### Deployment Strategies

#### Sequential Deployment (Recommended)
```yaml
deployment_strategy: sequential
```
- Backend deploys first
- Frontend platforms deploy after backend is healthy
- Safest approach with minimal risk

#### Parallel Deployment
```yaml
deployment_strategy: parallel
```
- All services deploy simultaneously
- Faster deployment but higher risk
- Suitable for well-tested environments

#### Canary Deployment
```yaml
deployment_strategy: canary
```
- Backend + one frontend platform first
- Other platforms deploy after canary validation
- Best for production deployments

### Environment Configuration

```yaml
environments:
  development:
    backend_url: "http://localhost:8000"
    frontend_url: "http://localhost:3000"
    health_check_timeout: 30

  staging:
    backend_url: "https://api-staging.pratiko.ai"
    frontend_url: "https://staging.pratiko.ai"
    health_check_timeout: 60

  production:
    backend_url: "https://api.pratiko.ai"
    frontend_url: "https://pratiko.ai"
    health_check_timeout: 120
    rollback_enabled: true
```

### Notification Rules

```python
# Custom notification configuration
notification_rules = [
    {
        "event_types": ["deployment_failed", "rollback_failed"],
        "severity_levels": ["critical"],
        "channels": ["slack", "email", "github_issue"],
        "recipients": [
            {"name": "DevOps Team", "channel": "slack", "address": "#alerts"},
            {"name": "Engineering Manager", "channel": "email", "address": "manager@pratiko.ai"}
        ],
        "conditions": {"environment": "production"},
        "escalation_delay_minutes": 5
    }
]
```

## 📊 Monitoring and Observability

### Deployment Metrics

The system tracks:
- Deployment success/failure rates
- Average deployment duration
- Rollback frequency
- Health check pass rates
- Cross-repository coordination latency

### Health Checks

Automated health validation:
- Service availability
- API responsiveness
- Database connectivity
- External service dependencies
- Version compatibility

### Logging and Tracing

Comprehensive logging:
- Deployment orchestration events
- Cross-repository workflow triggers
- Notification delivery status
- Artifact sharing operations
- Error tracking and debugging

## 🛠️ Advanced Usage

### Custom Deployment Steps

Add custom steps to the orchestration:

```python
from deployment_orchestration.orchestrator import DeploymentStep, ServiceType

# Add custom validation step
custom_step = DeploymentStep(
    service=ServiceType.BACKEND,
    version="1.2.0",
    environment=Environment.PRODUCTION,
    repository="mickgian/PratikoAi-BE",
    workflow_name="custom-validation.yml",
    depends_on=["backend-deploy"],
    health_check_url="https://api.pratiko.ai/health",
    timeout_minutes=15
)
```

### Artifact Sharing Between Repositories

```python
from deployment_orchestration.artifact_coordinator import CrossRepoArtifactCoordinator

# Initialize coordinator
coordinator = CrossRepoArtifactCoordinator()

# Store build artifact
artifact = await coordinator.store_artifact(
    deployment_id="deploy-prod-123",
    service="backend",
    artifact_type=ArtifactType.BUILD_INFO,
    content={"version": "1.2.0", "image": "pratiko-backend:1.2.0"}
)

# Share with frontend repository
sharing_result = await coordinator.share_artifact_cross_repo(
    deployment_id="deploy-prod-123",
    artifact_id=artifact.artifact_id,
    target_repo="mickgian/PratikoAi-KMP",
    target_workflow="orchestrated-frontend-deployment.yml"
)
```

### Custom Notifications

```python
from deployment_orchestration.notification_system import NotificationManager, NotificationType

# Send custom notification
await notification_manager.send_notification(
    NotificationType.DEPLOYMENT_SUCCESS,
    deployment_context,
    Severity.INFO,
    "Custom deployment completed successfully with additional validations"
)
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Cross-Repository Workflow Not Triggered
```bash
# Check token permissions
curl -H "Authorization: token $CROSS_REPO_TOKEN" \
  https://api.github.com/repos/mickgian/PratikoAi-KMP

# Verify workflow dispatch permissions
```

#### 2. Deployment Stuck in Progress
```bash
# Check orchestrator logs
python -c "
from deployment_orchestration.orchestrator import CrossRepoOrchestrator
orchestrator = CrossRepoOrchestrator('$GITHUB_TOKEN')
status = await orchestrator.get_deployment_status('deployment-id')
print(status)
"
```

#### 3. Notification Delivery Failures
```bash
# Test Slack webhook
curl -X POST $SLACK_WEBHOOK_URL \
  -H "Content-Type: application/json" \
  -d '{"text": "Test notification"}'

# Check email configuration
python -c "
import smtplib
smtp = smtplib.SMTP('$SMTP_HOST', 587)
smtp.ehlo()
print('SMTP connection successful')
"
```

### Debug Mode

Enable verbose logging:

```bash
export LOG_LEVEL=DEBUG
export ORCHESTRATOR_DEBUG=true

# Run deployment with debug output
python deployment_orchestration/orchestrator.py --debug
```

### Health Check Validation

```bash
# Manual health check
curl -f https://api.pratiko.ai/health
curl -f https://pratiko.ai/health

# Check service dependencies
python deployment_orchestration/health_checker.py \
  --deployment-id deploy-prod-123 \
  --environment production
```

## 📚 Examples

### Production Deployment with Rollback

```yaml
# .github/workflows/production-deploy.yml
name: Production Deployment
on:
  schedule:
    - cron: '0 2 * * 1'  # Monday 2 AM
  workflow_dispatch:

jobs:
  deploy:
    uses: ./.github/workflows/cross-repo-trigger.yml
    with:
      target_environment: production
      backend_version: ${{ needs.get-versions.outputs.backend_version }}
      frontend_versions: ${{ needs.get-versions.outputs.frontend_versions }}
      deployment_strategy: canary
      rollback_on_failure: true
      notification_channels: "slack,email,github"
    secrets: inherit
```

### Staging Environment Testing

```bash
# Quick staging deployment
curl -X POST "https://api.github.com/repos/mickgian/PratikoAi-BE/dispatches" \
  -H "Authorization: token $GITHUB_TOKEN" \
  -d '{
    "event_type": "trigger-cross-repo-deployment",
    "client_payload": {
      "environment": "staging",
      "backend_version": "develop-latest",
      "frontend_versions": {"android": "develop-latest", "web": "develop-latest"},
      "strategy": "parallel"
    }
  }'
```

### Custom Integration

```python
# Custom deployment integration
import asyncio
from deployment_orchestration.orchestrator import CrossRepoOrchestrator
from deployment_orchestration.notification_system import NotificationManager

async def custom_deployment():
    # Initialize systems
    orchestrator = CrossRepoOrchestrator(github_token="...")
    notifier = NotificationManager()

    # Create and execute deployment
    plan = await orchestrator.create_deployment_plan(...)
    execution = await orchestrator.execute_deployment_plan(plan)

    # Send custom notifications
    if execution.status == "success":
        await notifier.send_notification(...)

    return execution.status

# Run deployment
status = asyncio.run(custom_deployment())
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Update documentation
5. Submit a pull request

## 📄 License

This cross-repository orchestration system is part of the PratikoAI project.

---

**Need Help?** Check the [troubleshooting section](#troubleshooting) or create an issue with the `orchestration` label.
