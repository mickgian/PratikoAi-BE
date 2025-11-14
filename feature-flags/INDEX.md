# 🚀 PratikoAI Feature Flag System

A comprehensive feature flag management system that enables staggered feature releases across our Kotlin Multiplatform frontend and FastAPI backend with real-time updates, user targeting, and environment-specific configurations.

## 🎯 Overview

The PratikoAI Feature Flag System provides:

- **Cross-Platform Support**: Works seamlessly with KMP (Kotlin Multiplatform) and Python/FastAPI
- **Real-Time Updates**: Instant flag changes without deployments
- **User Targeting**: Sophisticated user segmentation and targeting rules
- **Environment Management**: Environment-specific flag configurations
- **Gradual Rollouts**: Percentage-based and criteria-based rollouts
- **Admin Interface**: Web-based management dashboard
- **CI/CD Integration**: Automated flag testing and deployment
- **Dependency Tracking**: Cross-repository feature dependencies

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                PratikoAI Feature Flag System                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │   Admin Web     │    │   Feature Flag  │    │   Real-time     │  │
│  │   Interface     │◄──►│   Service API   │◄──►│   Updates       │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│           │                       │                       │         │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │   Flag Storage  │    │   User Targeting│    │   Environment   │  │
│  │   (PostgreSQL)  │    │   Engine        │    │   Config        │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│           │                       │                       │         │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │   KMP Client    │    │   Python SDK    │    │   CI/CD         │  │
│  │   SDK           │    │   (FastAPI)     │    │   Integration   │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### 1. Backend Setup

```bash
# Install dependencies
cd feature-flags/
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the feature flag service
uvicorn feature_flag_service:app --host 0.0.0.0 --port 8001
```

### 2. Frontend Integration (KMP)

```kotlin
// Initialize the feature flag client
val featureFlagClient = FeatureFlagClient(
    apiUrl = "https://flags.pratiko.ai",
    apiKey = "your-api-key",  # pragma: allowlist secret
    environment = "production",
    userId = "user-123"
)

// Check feature flags
if (featureFlagClient.isEnabled("new_dashboard_ui")) {
    showNewDashboard()
} else {
    showLegacyDashboard()
}

// Get flag value with default
val maxItems = featureFlagClient.getValue("max_items_per_page", 20)
```

### 3. Backend Integration (FastAPI)

```python
from feature_flags.client import FeatureFlagClient

# Initialize client
flag_client = FeatureFlagClient(
    api_url="https://flags.pratiko.ai",
    api_key="your-api-key",  # pragma: allowlist secret
    environment="production"
)

# Use in endpoints
@app.get("/dashboard")
async def get_dashboard(user_id: str):
    if await flag_client.is_enabled("new_dashboard_api", user_id=user_id):
        return await get_new_dashboard(user_id)
    else:
        return await get_legacy_dashboard(user_id)
```

## 📋 Feature Flag Types

### 1. Boolean Flags

Simple on/off switches for features:

```json
{
  "flag_id": "new_payment_flow",
  "type": "boolean",
  "default_value": false,
  "environments": {
    "development": true,
    "staging": true,
    "production": false
  }
}
```

### 2. String/Numeric Flags

Configuration values:

```json
{
  "flag_id": "api_timeout_seconds",
  "type": "number",
  "default_value": 30,
  "environments": {
    "development": 60,
    "staging": 45,
    "production": 30
  }
}
```

### 3. JSON Configuration Flags

Complex configuration objects:

```json
{
  "flag_id": "ui_theme_config",
  "type": "json",
  "default_value": {"theme": "light", "sidebar": "expanded"},
  "environments": {
    "development": {"theme": "dark", "sidebar": "collapsed", "debug": true},
    "production": {"theme": "light", "sidebar": "expanded"}
  }
}
```

## 🎯 User Targeting

### Targeting Rules

Target specific users or groups:

```json
{
  "flag_id": "beta_features",
  "targeting_rules": [
    {
      "name": "beta_users",
      "conditions": [
        {"attribute": "user_type", "operator": "equals", "value": "beta"},
        {"attribute": "country", "operator": "in", "value": ["US", "CA", "UK"]}
      ],
      "value": true,
      "percentage": 100
    },
    {
      "name": "gradual_rollout",
      "conditions": [
        {"attribute": "user_type", "operator": "equals", "value": "standard"}
      ],
      "value": true,
      "percentage": 25
    }
  ],
  "default_value": false
}
```

### User Attributes

Support for various user attributes:

- **Built-in**: `user_id`, `email`, `country`, `platform`, `app_version`
- **Custom**: Any application-specific attributes
- **Computed**: Derived attributes like `user_tier`, `subscription_status`

## 🔧 Environment Management

### Environment Hierarchy

```yaml
environments:
  development:
    parent: null
    description: "Local development environment"
    auto_sync: false

  staging:
    parent: development
    description: "Staging environment for testing"
    auto_sync: true

  production:
    parent: staging
    description: "Production environment"
    auto_sync: false
    approval_required: true
```

### Environment-Specific Features

- **Auto-sync**: Automatically inherit changes from parent environment
- **Approval Required**: Require manual approval for flag changes
- **Change Windows**: Restrict when changes can be made
- **Rollback Protection**: Prevent accidental production changes

## 📊 Admin Interface Features

### Dashboard Overview

- **Flag Status**: Quick overview of all flags across environments
- **Recent Changes**: Audit log of flag modifications
- **Usage Metrics**: Flag evaluation statistics
- **Health Monitoring**: System health and performance metrics

### Flag Management

- **Visual Flag Editor**: Easy-to-use interface for flag configuration
- **Bulk Operations**: Update multiple flags simultaneously
- **Import/Export**: Backup and restore flag configurations
- **Version History**: Track all changes with rollback capability

### Rollout Controls

- **Gradual Rollout**: Percentage-based feature rollouts
- **Kill Switch**: Emergency flag disabling
- **Scheduled Changes**: Plan flag changes in advance
- **A/B Testing**: Built-in experimentation framework

## 🔄 CI/CD Integration

### GitHub Actions Integration

Automated flag testing and deployment:

```yaml
name: Feature Flag Testing
on: [push, pull_request]

jobs:
  test-with-flags:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        flag_scenario:
          - all_flags_off
          - all_flags_on
          - production_flags
    steps:
      - uses: actions/checkout@v4
      - name: Setup Feature Flags
        uses: ./feature-flags/actions/setup-flags
        with:
          scenario: ${{ matrix.flag_scenario }}
      - name: Run Tests
        run: npm test
```

### Deployment Automation

Automatically enable/disable flags during deployments:

```yaml
deployment:
  pre_deploy:
    - enable_flag: "maintenance_mode"
    - disable_flag: "new_feature_beta"
  post_deploy:
    - disable_flag: "maintenance_mode"
    - enable_flag: "new_feature_beta"
    - verify_flags: ["critical_feature", "payment_system"]
```

## 📈 Monitoring and Analytics

### Flag Usage Metrics

- **Evaluation Count**: How often flags are checked
- **Value Distribution**: What values are returned
- **Performance Impact**: Latency introduced by flag checks
- **Error Rates**: Failed flag evaluations

### Business Metrics Integration

- **Conversion Tracking**: Measure impact of feature flags on business KPIs
- **A/B Test Results**: Statistical analysis of feature experiments
- **User Behavior**: How flag changes affect user engagement
- **Revenue Impact**: Financial impact of feature rollouts

## 🛠️ Development Guidelines

### Flag Naming Conventions

```
Format: {component}_{feature}_{action}
Examples:
- dashboard_redesign_enabled
- payment_flow_optimized
- api_rate_limiting_strict
- mobile_push_notifications_v2
```

### Flag Lifecycle

1. **Creation**: Define flag with clear description and acceptance criteria
2. **Development**: Use flag in code with proper fallbacks
3. **Testing**: Test both enabled and disabled states
4. **Rollout**: Gradual rollout with monitoring
5. **Stabilization**: Monitor metrics and user feedback
6. **Cleanup**: Remove flag code once feature is stable

### Cross-Repository Dependencies

```yaml
# flag-dependencies.yaml
dependencies:
  - flag: "new_dashboard_ui"
    depends_on:
      - repository: "PratikoAi-BE"
        flag: "dashboard_api_v2"
        required_value: true
      - repository: "PratikoAi-BE"
        flag: "user_preferences_api"
        required_value: true
```

## 🔒 Security and Compliance

### API Security

- **API Key Authentication**: Secure client authentication
- **Rate Limiting**: Prevent abuse and ensure availability
- **Encryption**: All data encrypted in transit and at rest
- **Audit Logging**: Complete audit trail of all changes

### Compliance Features

- **GDPR Compliance**: User data handling and right to be forgotten
- **SOX Compliance**: Change approval workflows for financial features
- **HIPAA Compliance**: Healthcare data protection for relevant features
- **Access Controls**: Role-based permissions for flag management

## 📚 Best Practices

### Code Implementation

```python
# ✅ Good: Use feature flags with proper fallbacks
async def get_user_dashboard(user_id: str):
    if await flag_client.is_enabled("new_dashboard", user_id=user_id):
        try:
            return await get_new_dashboard_data(user_id)
        except Exception as e:
            logger.error(f"New dashboard failed: {e}")
            return await get_legacy_dashboard_data(user_id)
    else:
        return await get_legacy_dashboard_data(user_id)

# ❌ Bad: No fallback handling
async def get_user_dashboard(user_id: str):
    if await flag_client.is_enabled("new_dashboard", user_id=user_id):
        return await get_new_dashboard_data(user_id)  # Could fail!
```

### Flag Management

```kotlin
// ✅ Good: Descriptive flag names and defaults
class FeatureFlags {
    companion object {
        const val ENHANCED_SEARCH_ENABLED = "search_enhanced_algorithm_v2"
        const val MAX_SEARCH_RESULTS = "search_max_results_per_page"
        const val SEARCH_TIMEOUT_MS = "search_timeout_milliseconds"
    }
}

// ❌ Bad: Generic names and magic values
if (flags.isEnabled("feature1")) {
    // What does feature1 do?
}
```

### Testing Strategy

1. **Unit Tests**: Test both flag states in unit tests
2. **Integration Tests**: Test flag interactions between services
3. **E2E Tests**: Test complete user flows with different flag states
4. **Performance Tests**: Measure flag evaluation overhead
5. **Chaos Testing**: Test system behavior when flag service is unavailable

## 🚨 Emergency Procedures

### Kill Switch Activation

For immediate feature disabling:

```bash
# Emergency disable via CLI
feature-flags emergency-disable --flag payment_processing_v2 --environment production

# Emergency disable via API
curl -X POST "https://flags.pratiko.ai/api/v1/emergency/disable" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"flag_id": "payment_processing_v2", "environment": "production"}'
```

### Rollback Procedures

```bash
# Rollback to previous flag state
feature-flags rollback --flag new_checkout_flow --environment production --to-version 1.2.3

# Bulk rollback after deployment issues
feature-flags rollback --deployment-id deploy-20240115 --environment production
```

## 📞 Support and Troubleshooting

### Common Issues

1. **Flag Not Updating**: Check cache TTL and force refresh
2. **Performance Issues**: Review flag evaluation frequency
3. **Inconsistent Behavior**: Verify user targeting rules
4. **Service Unavailable**: Check fallback mechanisms

### Monitoring Dashboards

- **Grafana Dashboard**: Real-time metrics and alerts
- **Admin Interface**: Flag status and health monitoring
- **Application Logs**: Detailed flag evaluation logging
- **Error Tracking**: Sentry integration for flag-related errors

### Support Channels

- **Slack**: #feature-flags for general questions
- **GitHub Issues**: Bug reports and feature requests
- **Documentation**: Comprehensive guides and API references
- **On-call**: 24/7 support for production issues

---

**Version**: 1.0.0
**Last Updated**: January 15, 2024
**Maintained by**: PratikoAI Platform Team
