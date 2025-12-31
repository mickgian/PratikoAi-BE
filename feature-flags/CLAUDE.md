# Feature Flag System Guidelines

This file contains specialized knowledge for the PratikoAI cross-repository feature flag management system.

## Core Concepts

- **Cross-repository flag management** between PratikoAI-BE (FastAPI backend) and PratikoAi-KMP (Kotlin Multiplatform frontend)
- **Shared evaluation logic** with platform-specific optimizations
- **Real-time flag updates** using WebSocket connections
- **Gradual rollout controls** with user targeting capabilities

## Architecture

- `feature_flag_service.py` - FastAPI backend service for flag management
- `python_sdk.py` - Python SDK for backend flag evaluation
- Platform-specific SDKs in KMP project for Android, iOS, and Web
- Admin web interface for flag management and rollout controls
- CI/CD integration for automated flag testing

## Key Components

- **Flag Service** - FastAPI backend with SQLAlchemy models
- **Python SDK** - Backend integration with caching and WebSocket updates
- **Kotlin SDK** - Multiplatform client with platform-specific implementations
- **Admin Interface** - Web-based management with real-time updates
- **Dependency Tracker** - Cross-repository dependency analysis

## Flag Naming Convention

Use format: `{component}_{feature}_{action}`

Examples:
- `dashboard_redesign_enabled`
- `payment_flow_optimized`
- `mobile_push_notifications_v2`

## Flag Types

- **Boolean flags** - Simple on/off switches
- **String flags** - Configuration values and feature variants
- **JSON flags** - Complex configuration objects
- **Number flags** - Numeric thresholds and limits

## User Targeting

Support multiple targeting operators:
- `equals`, `not_equals` - Exact matching
- `in`, `not_in` - List membership
- `contains`, `starts_with`, `ends_with` - String operations
- `greater_than`, `less_than` - Numeric comparisons
- `regex_match` - Pattern matching

## Evaluation Context

```python
context = EvaluationContext(
    user_id="user-123",
    user_attributes={
        "country": "US",
        "tier": "premium", 
        "beta_user": True,
        "signup_date": "2024-01-15"
    },
    request_attributes={
        "ip_address": "192.168.1.1",
        "user_agent": "Mozilla/5.0...",
        "platform": "web"
    }
)
```

## Flag Lifecycle

1. **Development** - Create flag and implement feature behind flag
2. **Testing** - Test both enabled/disabled states in all environments
3. **Staging** - Enable for internal team testing
4. **Production Rollout** - Gradual rollout starting at 1-5%
5. **Full Rollout** - Increase to 100% after monitoring
6. **Stabilization** - Monitor for 2-4 weeks
7. **Cleanup** - Remove flag and update code

## Cross-Repository Dependencies

Declare dependencies in `flag-dependencies.yaml`:

```yaml
dependencies:
  outgoing:
    - flag: "dashboard_api_v2_enabled"
      description: "New dashboard API endpoints"
      affects_repositories: ["PratikoAi-KMP"]
      
  incoming:
    - flag: "dashboard_redesign_enabled"
      repository: "PratikoAi-KMP"
      description: "Requires API v2"
      required: true
```

## Platform-Specific Implementation

### Python/FastAPI Backend

```python
# Simple flag evaluation
if await flag_client.is_enabled("dashboard_redesign_enabled", user_id=user_id):
    return await get_new_dashboard(user_id)
else:
    return await get_legacy_dashboard(user_id)

# Configuration flag
config = await flag_client.get_value(
    "search_algorithm_config",
    user_id=user_id,
    default={"algorithm": "standard", "boost_recent": False}
)
```

### Kotlin Multiplatform Frontend

```kotlin
// Boolean flag evaluation
val useNewDesign = flagClient.isEnabled(
    "dashboard_redesign_enabled",
    userId = userId,
    default = false
)

// Configuration flag
val searchConfig = flagClient.getValue<SearchConfig>(
    "search_algorithm_config", 
    userId = userId,
    default = SearchConfig.default()
)
```

## Admin Interface Features

- **Real-time flag status** across all environments
- **Gradual rollout controls** with percentage sliders
- **User targeting rules** with visual rule builder
- **Emergency flag toggling** across all environments
- **Flag analytics** with evaluation metrics and user impact
- **Audit logging** of all flag changes

## CI/CD Integration

- **Matrix testing** with different flag scenarios in GitHub Actions
- **Cross-repository coordination** through workflow dispatch
- **Automated flag validation** before deployment
- **Flag dependency checking** to prevent conflicts

## Performance Optimization

- **Client-side caching** with configurable TTL
- **Batch evaluation** for multiple flags
- **Request coalescing** to reduce API calls
- **WebSocket updates** for real-time flag changes
- **Platform-specific optimizations** for mobile and web

## Monitoring and Analytics

- **Flag evaluation metrics** - Count, latency, cache hit rates
- **Business impact tracking** - Conversion rates, engagement changes
- **Error monitoring** - Evaluation failures and fallback usage
- **Cross-repository sync status** - Dependency validation

## Testing Strategies

- **Unit tests** with mocked flag clients
- **Integration tests** with different flag scenarios
- **End-to-end tests** with flag state variations
- **Performance tests** measuring flag evaluation impact

## Security Considerations

- **API key management** through environment variables
- **User data privacy** with attribute sanitization
- **Audit logging** of all flag evaluations and changes
- **Access control** for admin interface operations

## Usage Examples

```python
# Python SDK usage
flag_client = FeatureFlagClient(
    api_url="https://flags.pratiko.ai",
    api_key=os.getenv("FEATURE_FLAG_API_KEY"),
    environment="production"
)

# Evaluate flag with user context
enabled = await flag_client.is_enabled(
    "new_payment_flow",
    user_id="user-123",
    user_attributes={"country": "US", "tier": "premium"}
)
```

```kotlin
// Kotlin SDK usage
val flagClient = FeatureFlagClient(
    apiUrl = "https://flags.pratiko.ai",
    apiKey = BuildConfig.FEATURE_FLAG_API_KEY,
    environment = "production"
)

// Evaluate flag with caching
val enabled = flagClient.isEnabled(
    "new_payment_flow",
    userId = "user-123",
    userAttributes = mapOf(
        "country" to JsonPrimitive("US"),
        "tier" to JsonPrimitive("premium")
    )
)
```

## Best Practices

- Test both flag states in all test scenarios
- Use descriptive flag names following naming conventions
- Document flag dependencies between repositories
- Plan flag lifecycle with clear removal timeline
- Monitor flag impact on system performance
- Coordinate rollouts across repositories
- Clean up unused flags regularly to prevent flag sprawl