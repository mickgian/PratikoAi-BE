# 🔄 PratikoAI Rollback System

A comprehensive rollback system that provides automated recovery capabilities for both frontend and backend deployments when issues are detected, with zero-downtime operations and data preservation.

## 🎯 Overview

The PratikoAI Rollback System consists of three main components:

1. **Rollback Orchestrator** - Core rollback engine with support for multiple rollback strategies
2. **Health Monitor** - Automatic failure detection and monitoring system
3. **Integration Layer** - Seamless connection between monitoring and rollback systems

### Key Features

- **Automated Rollback Scripts** for frontend, backend, and database components
- **Zero-Downtime Operations** using blue-green and rolling deployment strategies
- **Data Preservation** with automatic database snapshots before rollbacks
- **Health Monitoring Integration** with configurable failure detection rules
- **Log Preservation** for comprehensive post-mortem analysis
- **Multi-Service Coordination** with dependency-aware rollback ordering
- **Comprehensive Documentation** with step-by-step troubleshooting guides

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PratikoAI Rollback System                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │   Health        │    │   Rollback      │    │   Integration   │  │
│  │   Monitor       │◄──►│   Orchestrator  │◄──►│   Layer         │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│           │                       │                       │         │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │   System        │    │   Database      │    │   Frontend      │  │
│  │   Monitoring    │    │   Rollback      │    │   Rollback      │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│           │                       │                       │         │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │   Log           │    │   Backend       │    │   Notification  │  │
│  │   Preservation  │    │   Rollback      │    │   System        │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

1. Python 3.9+ installed
2. Required dependencies installed:
   ```bash
   pip install -r requirements.txt
   ```
3. Access to deployment environments (staging/production)
4. Database access for snapshot operations
5. Container orchestration access (Docker/Kubernetes)

### Basic Setup

1. **Configure the System**:
   ```bash
   # Copy and customize configuration files
   cp health_monitor_config.yaml.example health_monitor_config.yaml
   cp rollback_config.yaml.example rollback_config.yaml

   # Edit configurations for your environment
   vim health_monitor_config.yaml
   vim rollback_config.yaml
   ```

2. **Start Integrated Monitoring**:
   ```bash
   python monitor_rollback_integration.py \
     --deployment-id deploy-prod-20240115 \
     --environment production \
     --services backend frontend database
   ```

3. **Manual Rollback** (when needed):
   ```bash
   python monitor_rollback_integration.py \
     --deployment-id deploy-prod-20240115 \
     --environment production \
     --manual-rollback "API response time degradation detected"
   ```

## 📋 System Components

### 1. Rollback Orchestrator (`rollback_orchestrator.py`)

The core rollback engine that coordinates rollback operations across multiple services.

**Key Features:**
- **Multiple Rollback Strategies**: Blue-green, rolling, and immediate rollback
- **Data Preservation**: Automatic database snapshots before rollbacks
- **Service Dependencies**: Intelligent rollback ordering based on service dependencies
- **Progress Tracking**: Real-time rollback progress monitoring
- **Error Recovery**: Comprehensive error handling and recovery mechanisms

**Usage:**
```python
from rollback_orchestrator import RollbackOrchestrator, RollbackTrigger, RollbackTarget

# Initialize orchestrator
orchestrator = RollbackOrchestrator()

# Create rollback trigger
trigger = RollbackTrigger(
    trigger_id="manual_rollback_001",
    reason=RollbackReason.PERFORMANCE_DEGRADATION,
    triggered_by="devops_team",
    deployment_id="deploy-prod-20240115",
    message="High response times detected"
)

# Define rollback targets
targets = [
    RollbackTarget(service="backend", environment="production"),
    RollbackTarget(service="frontend", environment="production")
]

# Execute rollback
execution = await orchestrator.initiate_rollback(trigger, targets)
```

### 2. Health Monitor (`health_monitor.py`)

Advanced health monitoring system with automatic failure detection capabilities.

**Key Features:**
- **Real-time Monitoring**: Continuous health checks with configurable intervals
- **Multiple Check Types**: HTTP endpoints, database connections, system resources, custom metrics
- **Configurable Rules**: Flexible monitoring rules with automatic actions
- **Log Preservation**: Automatic log collection before rollback operations
- **Escalation Rules**: Progressive alerting based on severity levels

**Configuration Example:**
```yaml
health_checks:
  - check_id: backend_health
    service: backend
    name: Backend Health Check
    check_type: http_response
    endpoint_url: "https://api.pratiko.ai/health"
    interval_seconds: 30
    threshold_critical: 500

monitoring_rules:
  - rule_id: critical_failure_rollback
    name: Critical Service Failure Rollback
    condition: "get_failure_count('backend', 5) >= 3"
    action: rollback
    priority: 1
    cooldown_minutes: 30
```

### 3. Integration Layer (`monitor_rollback_integration.py`)

Seamless integration between health monitoring and rollback systems.

**Key Features:**
- **Automatic Coordination**: Seamless integration between monitoring and rollback
- **Post-Rollback Verification**: Validates system health after rollback operations
- **Manual Overrides**: Support for manual rollback triggers
- **Audit Trails**: Comprehensive logging of all rollback activities
- **Status Reporting**: Real-time status and progress reporting

## 📖 Rollback Strategies

### 1. Blue-Green Rollback

**Use Case**: Zero-downtime rollback for backend services

**How it Works**:
1. Maintains two identical production environments (blue/green)
2. Routes traffic back to the previous stable environment
3. Validates health before completing the rollback
4. Preserves the failed environment for debugging

**Configuration**:
```python
rollback_target = RollbackTarget(
    service="backend",
    environment="production",
    strategy=RollbackStrategy.BLUE_GREEN,
    options={
        "health_check_url": "https://api.pratiko.ai/health",
        "validation_timeout": 300,
        "preserve_failed_environment": True
    }
)
```

### 2. Rolling Rollback

**Use Case**: Gradual rollback of backend services with multiple instances

**How it Works**:
1. Identifies all running instances of the service
2. Gradually replaces instances with previous stable version
3. Monitors health during each instance replacement
4. Stops rollback if issues are detected

**Configuration**:
```python
rollback_target = RollbackTarget(
    service="backend",
    environment="production",
    strategy=RollbackStrategy.ROLLING,
    options={
        "batch_size": 2,
        "batch_delay_seconds": 30,
        "health_check_interval": 10
    }
)
```

### 3. Database Rollback with Data Preservation

**Use Case**: Rollback database migrations while preserving data

**How it Works**:
1. Creates a complete data snapshot before rollback
2. Rolls back schema changes to target version
3. Preserves data integrity during the process
4. Provides recovery options if rollback fails

**Configuration**:
```python
rollback_target = RollbackTarget(
    service="database",
    environment="production",
    strategy=RollbackStrategy.DATABASE_MIGRATION,
    options={
        "target_migration": "0045_previous_stable",
        "preserve_data": True,
        "snapshot_tables": ["user_data", "transactions", "logs"],
        "backup_location": "s3://pratiko-db-backups/rollback/"
    }
)
```

### 4. Frontend Rollback

**Use Case**: Rollback frontend deployments across multiple platforms

**How it Works**:
1. Identifies previous stable versions for each platform
2. Reverts CDN and static asset deployments
3. Updates mobile app store deployments
4. Validates frontend health endpoints

**Configuration**:
```python
rollback_target = RollbackTarget(
    service="frontend",
    environment="production",
    strategy=RollbackStrategy.FRONTEND,
    options={
        "platforms": ["web", "android", "ios"],
        "cdn_invalidation": True,
        "app_store_rollback": True,
        "health_check_urls": [
            "https://pratiko.ai/health",
            "https://mobile-api.pratiko.ai/health"
        ]
    }
)
```

## 🔧 Configuration

### Health Monitor Configuration

The health monitor uses a YAML configuration file to define monitoring behavior:

```yaml
# health_monitor_config.yaml
monitoring_interval_seconds: 30
metrics_retention_minutes: 60
rollback_enabled: true
log_preservation_enabled: true

system_resource_thresholds:
  cpu_warning: 80
  cpu_critical: 95
  memory_warning: 80
  memory_critical: 95

health_checks:
  - check_id: backend_health
    service: backend
    name: Backend Health Check
    check_type: http_response
    endpoint_url: "https://api.pratiko.ai/health"
    interval_seconds: 30
    timeout_seconds: 10
    threshold_critical: 500

monitoring_rules:
  - rule_id: critical_failure_rollback
    name: Critical Service Failure Rollback
    condition: "get_failure_count('backend', 5) >= 3"
    action: rollback
    priority: 1
    cooldown_minutes: 30
```

### Environment Variables

Set these environment variables for proper system operation:

```bash
# Database connections
export DATABASE_URL="postgresql://user:pass@localhost/pratiko"  # pragma: allowlist secret
export REDIS_URL="redis://localhost:6379"

# Container orchestration
export DOCKER_HOST="unix:///var/run/docker.sock"
export KUBECONFIG="/path/to/kubeconfig"

# Cloud storage
export AWS_ACCESS_KEY_ID="your_aws_key"
export AWS_SECRET_ACCESS_KEY="your_aws_secret"  # pragma: allowlist secret
export S3_BACKUP_BUCKET="pratiko-rollback-backups"

# Notifications
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
export EMAIL_SMTP_HOST="smtp.gmail.com"
export EMAIL_SMTP_USER="rollback@pratiko.ai"
export EMAIL_SMTP_PASSWORD="your_email_password"  # pragma: allowlist secret

# GitHub integration
export GITHUB_TOKEN="your_github_token"  # pragma: allowlist secret
export GITHUB_REPO="mickgian/PratikoAi-BE"
```

## 🔍 Monitoring and Alerting

### Real-time Monitoring

The system provides real-time monitoring through multiple channels:

1. **Console Logs**: Real-time status updates in the console
2. **Log Files**: Detailed logs stored in `/var/log/pratiko-rollback/`
3. **Metrics Dashboard**: System metrics and health indicators
4. **Slack Notifications**: Real-time alerts to your Slack channels
5. **Email Alerts**: Critical alerts via email notifications

### Health Check Types

1. **HTTP Response Checks**:
   ```yaml
   - check_id: api_health
     check_type: http_response
     endpoint_url: "https://api.pratiko.ai/health"
     expected_status: 200
     timeout_seconds: 10
   ```

2. **Database Connection Checks**:
   ```yaml
   - check_id: db_health
     check_type: database_connection
     endpoint_url: "postgresql://user:pass@localhost/db"  # pragma: allowlist secret
     query: "SELECT 1"
   ```

3. **System Resource Checks**:
   ```yaml
   - check_id: cpu_usage
     check_type: system_resource
     threshold_warning: 80
     threshold_critical: 95
     metadata:
       resource: cpu
   ```

4. **Custom Metric Checks**:
   ```yaml
   - check_id: custom_metric
     check_type: custom
     command: "curl -s https://api.pratiko.ai/metrics | jq '.response_time'"
     threshold_critical: 5000
   ```

### Monitoring Rules

Define custom rules for automatic actions:

```yaml
monitoring_rules:
  # Automatic rollback on critical failures
  - rule_id: auto_rollback
    condition: "get_failure_count('backend', 5) >= 3"
    action: rollback
    priority: 1
    cooldown_minutes: 30

  # Alert on resource exhaustion
  - rule_id: resource_alert
    condition: "get_latest_metric('system').value > 90"
    action: alert
    priority: 2
    cooldown_minutes: 15

  # Log preservation on multiple failures
  - rule_id: preserve_logs
    condition: "len([s for s, m in metrics.items() if get_failure_count(s, 3) >= 2]) >= 2"
    action: preserve_logs
    priority: 2
    cooldown_minutes: 5
```

## 📊 Status and Reporting

### Getting System Status

Check the current status of the rollback system:

```bash
python monitor_rollback_integration.py \
  --deployment-id deploy-prod-20240115 \
  --environment production \
  --status
```

Example output:
```json
{
  "integration_running": true,
  "deployment_id": "deploy-prod-20240115",
  "environment": "production",
  "health_status": "healthy",
  "active_rollbacks": 0,
  "total_rollbacks": 3,
  "auto_rollback_enabled": true,
  "last_report_time": "2024-01-15T14:30:22Z"
}
```

### Health Reports

Generate comprehensive health reports:

```python
# Generate health report
health_report = await health_monitor.generate_health_report(deployment_id)

print(f"Overall Status: {health_report.overall_status}")
print(f"Failed Checks: {health_report.failed_checks}")
print(f"Warnings: {health_report.warnings}")
print(f"Recommendations: {health_report.recommendations}")
```

### Rollback History

View rollback execution history:

```python
# Get rollback history
history = await rollback_orchestrator.get_rollback_history(deployment_id)

for execution in history:
    print(f"Execution: {execution.execution_id}")
    print(f"Status: {execution.status}")
    print(f"Duration: {execution.duration_minutes} minutes")
    print(f"Services: {[t.service for t in execution.targets]}")
```

## 🚨 Troubleshooting

### Common Issues and Solutions

#### 1. Rollback Fails to Start

**Symptom**: Rollback initiation fails with connection errors

**Possible Causes**:
- Database connection issues
- Container orchestration access problems
- Missing environment variables
- Permission issues

**Solutions**:
```bash
# Check database connectivity
python -c "import asyncpg; asyncpg.connect('postgresql://user:pass@host/db')"  # pragma: allowlist secret

# Verify container access
docker ps
kubectl get pods

# Check environment variables
echo $DATABASE_URL
echo $KUBECONFIG

# Verify permissions
ls -la /var/run/docker.sock
kubectl auth can-i get pods
```

#### 2. Health Checks Failing

**Symptom**: Health checks consistently report failures for healthy services

**Possible Causes**:
- Incorrect health check URLs
- Network connectivity issues
- Authentication problems
- Timeout settings too strict

**Solutions**:
```bash
# Test health endpoints manually
curl -v https://api.pratiko.ai/health
curl -v https://pratiko.ai/health

# Check network connectivity
ping api.pratiko.ai
nslookup api.pratiko.ai

# Review health check configuration
cat health_monitor_config.yaml | grep -A 10 "health_checks"

# Increase timeout values
sed -i 's/timeout_seconds: 10/timeout_seconds: 30/g' health_monitor_config.yaml
```

#### 3. Database Rollback Issues

**Symptom**: Database rollback fails or causes data loss

**Possible Causes**:
- Insufficient database permissions
- Migration conflicts
- Data integrity constraints
- Backup storage issues

**Solutions**:
```bash
# Check database permissions
psql -c "SELECT current_user, session_user;"
psql -c "SELECT has_database_privilege('pratiko', 'CREATE');"

# Verify migration state
python manage.py showmigrations
python manage.py migrate --plan

# Test backup storage
aws s3 ls s3://pratiko-rollback-backups/
aws s3 cp /tmp/test.txt s3://pratiko-rollback-backups/test.txt

# Manual data verification
psql -c "SELECT COUNT(*) FROM critical_table;"
```

#### 4. Frontend Rollback Problems

**Symptom**: Frontend rollback doesn't revert to previous version

**Possible Causes**:
- CDN caching issues
- Asset deployment problems
- Mobile app store policies
- Version registry inconsistencies

**Solutions**:
```bash
# Clear CDN cache
aws cloudfront create-invalidation --distribution-id E123456 --paths "/*"

# Check asset versions
curl -I https://cdn.pratiko.ai/app.js
curl -I https://cdn.pratiko.ai/manifest.json

# Verify version registry
curl -s https://version-registry.pratiko.ai/api/v1/versions/frontend/web

# Manual asset rollback
aws s3 sync s3://pratiko-assets/v2.0.5/ s3://pratiko-assets/current/
```

#### 5. System Resource Issues

**Symptom**: System resource checks trigger false alarms

**Possible Causes**:
- Incorrect threshold configuration
- System monitoring agent issues
- Resource spike during normal operations
- Insufficient system capacity

**Solutions**:
```bash
# Check actual system resources
top
htop
iostat
free -h
df -h

# Review resource thresholds
grep -A 5 "system_resource_thresholds" health_monitor_config.yaml

# Adjust thresholds if needed
sed -i 's/cpu_warning: 80/cpu_warning: 90/g' health_monitor_config.yaml

# Monitor resource patterns
sar -u 1 60  # CPU usage
sar -r 1 60  # Memory usage
```

#### 6. Integration Communication Issues

**Symptom**: Health monitor and rollback orchestrator lose communication

**Possible Causes**:
- Process crashes
- Network connectivity issues
- Resource exhaustion
- Configuration mismatches

**Solutions**:
```bash
# Check process status
ps aux | grep "health_monitor\|rollback"
systemctl status pratiko-rollback

# Review integration logs
tail -f /var/log/pratiko-integration.log
journalctl -u pratiko-rollback -f

# Test component connectivity
python -c "from health_monitor import HealthMonitor; print('Health monitor OK')"
python -c "from rollback_orchestrator import RollbackOrchestrator; print('Rollback orchestrator OK')"

# Restart integration
sudo systemctl restart pratiko-rollback
```

### Debugging Tools

#### 1. Log Analysis

```bash
# View comprehensive logs
tail -f /var/log/pratiko-rollback/*.log

# Search for specific errors
grep -r "ERROR\|CRITICAL" /var/log/pratiko-rollback/

# Analyze rollback execution logs
grep -A 10 -B 10 "rollback.*failed" /var/log/pratiko-rollback/rollback.log
```

#### 2. Health Check Testing

```bash
# Test individual health checks
python -c "
import asyncio
from health_monitor import HealthMonitor
async def test():
    monitor = HealthMonitor()
    report = await monitor.generate_health_report('test-deployment')
    print(report)
asyncio.run(test())
"
```

#### 3. Rollback Simulation

```bash
# Simulate rollback without execution
python rollback_orchestrator.py \
  --deployment-id test \
  --dry-run \
  --service backend \
  --reason "test simulation"
```

#### 4. Database State Verification

```bash
# Check migration state
python manage.py showmigrations --list

# Verify data integrity
python manage.py check --database default

# Test database rollback
python -c "
from rollback_orchestrator import DatabaseRollback
import asyncio
async def test():
    db = DatabaseRollback()
    snapshot = await db.create_data_snapshot('test-snapshot')
    print(f'Snapshot created: {snapshot}')
asyncio.run(test())
"
```

### Log Locations

- **Integration Logs**: `/var/log/pratiko-integration.log`
- **Health Monitor Logs**: `/var/log/pratiko-rollback/health_monitor.log`
- **Rollback Execution Logs**: `/var/log/pratiko-rollback/rollback_execution.log`
- **System Logs**: `/var/log/pratiko-rollback/system.log`
- **Preserved Logs**: `/var/log/pratiko-rollback-logs/{deployment_id}/`

### Emergency Procedures

#### 1. Emergency Stop

If rollback is causing issues, stop it immediately:

```bash
# Stop all rollback processes
sudo pkill -f "rollback_orchestrator"
sudo pkill -f "health_monitor"
sudo pkill -f "monitor_rollback_integration"

# Stop systemd service
sudo systemctl stop pratiko-rollback

# Emergency database connection kill
sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE application_name LIKE '%rollback%';"
```

#### 2. Manual Recovery

If automatic rollback fails, perform manual recovery:

```bash
# Manual database rollback
python manage.py migrate app_name 0044_previous_migration

# Manual container rollback
docker tag pratiko-backend:v1.2.0 pratiko-backend:latest
docker-compose up -d backend

# Manual frontend rollback
aws s3 sync s3://pratiko-assets/v2.0.5/ s3://pratiko-assets/current/
aws cloudfront create-invalidation --distribution-id E123456 --paths "/*"
```

#### 3. System Recovery

If the entire system needs recovery:

```bash
# Restore from backup
aws s3 sync s3://pratiko-rollback-backups/latest/ /opt/pratiko/

# Restart all services
sudo systemctl restart postgresql
sudo systemctl restart redis
sudo systemctl restart nginx
sudo systemctl restart pratiko-backend
sudo systemctl restart pratiko-rollback

# Verify system health
curl https://api.pratiko.ai/health
curl https://pratiko.ai/health
```

## 🤝 Support and Maintenance

### Regular Maintenance Tasks

1. **Weekly**:
   - Review rollback execution logs
   - Check system resource usage trends
   - Verify backup integrity
   - Update health check endpoints

2. **Monthly**:
   - Clean up old log files
   - Review and update monitoring thresholds
   - Test rollback procedures in staging
   - Update documentation

3. **Quarterly**:
   - Full system testing
   - Performance optimization
   - Security audit
   - Disaster recovery testing

### Getting Help

1. **Documentation**: Check this README and inline code documentation
2. **Logs**: Review system logs for detailed error information
3. **GitHub Issues**: Create an issue in the repository
4. **Team Chat**: Contact the DevOps team in Slack (#deployment-alerts)
5. **Emergency**: Contact the on-call engineer for production issues

---

**Version**: 1.0.0
**Last Updated**: January 15, 2024
**Maintained by**: PratikoAI DevOps Team
