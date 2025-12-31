# Deployment Orchestration Guidelines

This file contains specialized knowledge for the PratikoAI cross-repository deployment orchestration system.

## Core Concepts

- **Cross-repository coordination** between PratikoAI-BE (backend) and PratikoAi-KMP (frontend)
- **Sequential deployment** pattern: backend deploys first, then frontend
- **Artifact sharing** through GitHub Actions for version synchronization
- **Health validation** at each deployment step with abort capabilities

## Architecture

- `orchestrator.py` - Main coordination engine with `CrossRepoOrchestrator` class
- `notification_system.py` - Multi-channel alerts (Slack, Teams, Email, Webhook)
- `artifact_coordinator.py` - Cross-repository artifact sharing and version management
- GitHub Actions workflows for automated deployment triggering

## Key Classes

- `CrossRepoOrchestrator` - Main orchestration engine
- `DeploymentConfig` - Deployment configuration management
- `DeploymentStatus` - Status tracking with states: pending, running, success, failed, aborted
- `NotificationSystem` - Multi-channel notification management
- `ArtifactCoordinator` - Cross-repository artifact coordination

## Deployment Flow

1. **Backend Deployment**:
   - Trigger backend deployment in PratikoAI-BE
   - Wait for successful completion
   - Share build artifacts and version info

2. **Health Validation**:
   - Validate backend health endpoints
   - Check database migration status
   - Verify API functionality

3. **Frontend Deployment**:
   - Trigger frontend deployment in PratikoAi-KMP
   - Use backend artifacts for version coordination
   - Validate cross-repository compatibility

4. **System Validation**:
   - End-to-end system health checks
   - Integration testing between frontend and backend
   - Rollback if any validation fails

## Configuration

```python
config = DeploymentConfig(
    backend_repo="mickgian/PratikoAi-BE",
    frontend_repo="mickgian/PratikoAi-KMP",
    environments=["staging", "production"],
    deployment_strategy="sequential",
    health_check_timeout=300,
    rollback_on_failure=True
)
```

## GitHub Actions Integration

- Use `trigger_cross_repo_deployment` workflow to coordinate deployments
- Share artifacts using `upload-artifact` and `download-artifact` actions
- Implement workflow status checking with GitHub API
- Use repository dispatch events for cross-repository triggering

## Notification Channels

- **Slack**: Real-time deployment status updates
- **Microsoft Teams**: Team collaboration notifications
- **Email**: Critical alerts and deployment summaries
- **Webhook**: Custom integrations with external systems

## Health Checks

- API endpoint availability checks
- Database connectivity validation
- Service dependency verification
- Performance threshold validation
- Cross-repository communication testing

## Error Handling

- **Automatic retries** with exponential backoff
- **Circuit breaker** pattern for external service calls
- **Graceful degradation** when non-critical services fail
- **Comprehensive logging** with correlation IDs for troubleshooting

## Monitoring

- Track deployment duration and success rates
- Monitor cross-repository coordination timing
- Alert on deployment failures or extended durations
- Generate deployment reports with metrics and insights

## Usage Examples

```python
# Initialize orchestrator
orchestrator = CrossRepoOrchestrator(
    github_token=os.getenv("GITHUB_TOKEN"),
    webhook_url=os.getenv("WEBHOOK_URL")
)

# Execute coordinated deployment
result = await orchestrator.deploy_coordinated(
    config=deployment_config,
    triggered_by="automated-pipeline"
)
```

## Best Practices

- Always deploy backend before frontend to ensure API compatibility
- Use semantic versioning for cross-repository coordination
- Implement comprehensive health checks at each step
- Maintain deployment rollback capabilities
- Log all deployment events with detailed context
- Test deployment flows in staging before production