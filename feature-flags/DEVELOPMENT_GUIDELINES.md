# 📋 PratikoAI Feature Flag Development Guidelines

Comprehensive guidelines for creating, managing, and maintaining feature flags across our KMP frontend and FastAPI backend, ensuring consistent practices and smooth feature rollouts.

## 🎯 Table of Contents

1. [Flag Creation Guidelines](#flag-creation-guidelines)
2. [Naming Conventions](#naming-conventions)
3. [Flag Implementation Patterns](#flag-implementation-patterns)
4. [Testing Strategies](#testing-strategies)
5. [Flag Lifecycle Management](#flag-lifecycle-management)
6. [Cross-Repository Dependencies](#cross-repository-dependencies)
7. [Performance Considerations](#performance-considerations)
8. [Security Best Practices](#security-best-practices)
9. [Monitoring and Metrics](#monitoring-and-metrics)
10. [Common Pitfalls and Solutions](#common-pitfalls-and-solutions)

---

## 🚀 Flag Creation Guidelines

### When to Create a Feature Flag

✅ **DO create flags for:**
- New features that need gradual rollout
- Experimental features for A/B testing
- High-risk changes that may need quick rollback
- Features with cross-team dependencies
- Configuration values that vary by environment
- Performance optimizations that need monitoring

❌ **DON'T create flags for:**
- Simple bug fixes
- Internal refactoring with no user impact
- Features that are guaranteed to be permanent
- Temporary development switches (use environment variables instead)

### Flag Planning Checklist

Before creating a flag, ensure you have:

- [ ] **Clear acceptance criteria** for the feature
- [ ] **Rollout strategy** (gradual, targeted users, etc.)
- [ ] **Success metrics** to measure impact
- [ ] **Rollback plan** if issues arise
- [ ] **Timeline** for flag removal
- [ ] **Cross-team communication** if dependencies exist

---

## 🏷️ Naming Conventions

### Flag ID Format

Use the following format for flag IDs:
```
{component}_{feature}_{action}
```

**Examples:**
```
dashboard_redesign_enabled
payment_flow_optimized
api_rate_limiting_strict
mobile_push_notifications_v2
search_algorithm_enhanced
user_preferences_personalized
```

### Component Prefixes

| Component | Prefix | Example |
|-----------|--------|---------|
| Dashboard | `dashboard_` | `dashboard_widgets_enabled` |
| Payment | `payment_` | `payment_apple_pay_enabled` |
| API | `api_` | `api_rate_limiting_enabled` |
| Mobile | `mobile_` | `mobile_biometric_auth_enabled` |
| Search | `search_` | `search_autocomplete_enabled` |
| User Management | `user_` | `user_profile_v2_enabled` |
| Analytics | `analytics_` | `analytics_realtime_enabled` |
| Notification | `notification_` | `notification_push_enhanced` |

### Action Suffixes

| Action | Suffix | Use Case |
|--------|--------|----------|
| Enable/Disable | `_enabled` | Boolean flags |
| Version | `_v2`, `_v3` | Version switches |
| Optimization | `_optimized` | Performance flags |
| Enhancement | `_enhanced` | Feature improvements |
| Configuration | `_config` | Config objects |
| Limit/Threshold | `_limit`, `_threshold` | Numeric values |

---

## 🛠️ Flag Implementation Patterns

### Python/FastAPI Backend

#### Simple Boolean Flag
```python
from feature_flags.client import FeatureFlagClient

flag_client = FeatureFlagClient(
    api_url="https://flags.pratiko.ai",
    api_key=os.getenv("FEATURE_FLAG_API_KEY"),
    environment=os.getenv("ENVIRONMENT", "production")
)

@app.get("/dashboard")
async def get_dashboard(user_id: str):
    if await flag_client.is_enabled("dashboard_redesign_enabled", user_id=user_id):
        return await get_new_dashboard(user_id)
    else:
        return await get_legacy_dashboard(user_id)
```

#### Configuration Flag
```python
@app.get("/api/search")
async def search(query: str, user_id: str):
    max_results = await flag_client.get_value(
        "search_max_results_limit",
        user_id=user_id,
        default=20
    )
    
    search_config = await flag_client.get_value(
        "search_algorithm_config",
        user_id=user_id,
        default={
            "algorithm": "standard",
            "boost_recent": False,
            "personalization": False
        }
    )
    
    return await perform_search(query, max_results, search_config)
```

#### Decorator Pattern
```python
from feature_flags.client import feature_flag

@feature_flag("new_payment_api_enabled", flag_client, default=False)
async def process_payment_v2(payment_data: dict, user_id: str):
    # New payment processing logic
    return await enhanced_payment_processing(payment_data)

async def process_payment(payment_data: dict, user_id: str):
    # Try new payment flow first
    result = await process_payment_v2(payment_data, user_id)
    if result is None:
        # Fall back to legacy flow
        return await legacy_payment_processing(payment_data)
    return result
```

#### Dependency Injection Pattern
```python
from fastapi import Depends

async def get_feature_flags(user_id: str = None) -> dict:
    """Dependency to inject feature flags into endpoints."""
    return await flag_client.get_all_flags(
        user_id=user_id,
        flag_ids=["dashboard_redesign_enabled", "api_rate_limiting_strict"]
    )

@app.get("/user/profile")
async def get_user_profile(
    user_id: str,
    flags: dict = Depends(get_feature_flags)
):
    if flags.get("dashboard_redesign_enabled"):
        return await get_enhanced_profile(user_id)
    else:
        return await get_standard_profile(user_id)
```

### Kotlin Multiplatform Frontend

#### Simple Boolean Flag
```kotlin
class DashboardViewModel(
    private val flagClient: FeatureFlagClient
) : ViewModel() {
    
    suspend fun loadDashboard(userId: String) {
        val useNewDesign = flagClient.isEnabled(
            "dashboard_redesign_enabled",
            userId = userId,
            default = false
        )
        
        if (useNewDesign) {
            loadNewDashboard()
        } else {
            loadLegacyDashboard()
        }
    }
}
```

#### Compose Integration
```kotlin
@Composable
fun DashboardScreen(
    userId: String,
    flagClient: FeatureFlagClient
) {
    val composeFlags = ComposeFeatureFlags(flagClient)
    val useNewDesign by composeFlags.rememberFlagState(
        "dashboard_redesign_enabled",
        userId = userId,
        default = false
    )
    
    if (useNewDesign) {
        NewDashboardUI()
    } else {
        LegacyDashboardUI()
    }
}
```

#### Configuration Flag
```kotlin
class SearchRepository(
    private val flagClient: FeatureFlagClient
) {
    suspend fun search(query: String, userId: String): SearchResults {
        val maxResults = flagClient.getIntValue(
            "search_max_results_limit",
            userId = userId,
            default = 20
        )
        
        val searchConfig = flagClient.getValue<SearchConfig>(
            "search_algorithm_config",
            userId = userId,
            default = SearchConfig.default()
        )
        
        return performSearch(query, maxResults, searchConfig)
    }
}
```

#### DSL Pattern
```kotlin
suspend fun handlePayment(paymentData: PaymentData, userId: String) {
    flagClient.withFlags {
        feature(
            "new_payment_flow_enabled",
            userId = userId,
            enabled = {
                processPaymentV2(paymentData)
            },
            disabled = {
                processPaymentLegacy(paymentData)
            }
        )
    }
}
```

#### Platform-Specific Flags
```kotlin
// Android-specific implementation
class AndroidMainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        lifecycleScope.launch {
            val enableMaterialYou = flagClient.isEnabledForDevice(
                "android_material_you_enabled",
                userId = getCurrentUserId(),
                additionalAttributes = mapOf(
                    "sdk_version" to JsonPrimitive(Build.VERSION.SDK_INT),
                    "device_type" to JsonPrimitive("phone")
                )
            )
            
            if (enableMaterialYou && Build.VERSION.SDK_INT >= 31) {
                enableMaterialYouTheme()
            }
        }
    }
}
```

---

## 🧪 Testing Strategies

### Unit Testing with Flags

#### Python Testing
```python
import pytest
from unittest.mock import AsyncMock
from feature_flags.client import FeatureFlagClient

@pytest.fixture
def mock_flag_client():
    client = AsyncMock(spec=FeatureFlagClient)
    return client

@pytest.mark.asyncio
async def test_dashboard_with_new_design(mock_flag_client):
    # Test with flag enabled
    mock_flag_client.is_enabled.return_value = True
    
    result = await get_dashboard("user-123")
    
    mock_flag_client.is_enabled.assert_called_with(
        "dashboard_redesign_enabled", 
        user_id="user-123"
    )
    assert result["version"] == "new"

@pytest.mark.asyncio
async def test_dashboard_with_legacy_design(mock_flag_client):
    # Test with flag disabled
    mock_flag_client.is_enabled.return_value = False
    
    result = await get_dashboard("user-123")
    
    assert result["version"] == "legacy"

@pytest.mark.parametrize("flag_enabled,expected_version", [
    (True, "new"),
    (False, "legacy")
])
async def test_dashboard_parametrized(mock_flag_client, flag_enabled, expected_version):
    mock_flag_client.is_enabled.return_value = flag_enabled
    
    result = await get_dashboard("user-123")
    
    assert result["version"] == expected_version
```

#### Kotlin Testing
```kotlin
class DashboardViewModelTest {
    
    @Mock
    private lateinit var mockFlagClient: FeatureFlagClient
    
    @Test
    fun `should load new dashboard when flag enabled`() = runTest {
        // Given
        coEvery { 
            mockFlagClient.isEnabled("dashboard_redesign_enabled", "user-123", any(), false) 
        } returns true
        
        val viewModel = DashboardViewModel(mockFlagClient)
        
        // When
        viewModel.loadDashboard("user-123")
        
        // Then
        coVerify { mockFlagClient.isEnabled("dashboard_redesign_enabled", "user-123") }
        assertTrue(viewModel.isNewDesignLoaded)
    }
    
    @Test
    fun `should load legacy dashboard when flag disabled`() = runTest {
        coEvery { 
            mockFlagClient.isEnabled("dashboard_redesign_enabled", "user-123", any(), false) 
        } returns false
        
        val viewModel = DashboardViewModel(mockFlagClient)
        
        viewModel.loadDashboard("user-123")
        
        assertTrue(viewModel.isLegacyDesignLoaded)
    }
}
```

### Integration Testing

#### Test with Different Flag Scenarios
```python
# test_flag_scenarios.py
import pytest
from httpx import AsyncClient

class TestFlagScenarios:
    
    @pytest.mark.asyncio
    async def test_all_flags_enabled(self, client: AsyncClient):
        """Test with all flags enabled."""
        # Set up flag scenario
        await setup_flag_scenario("all_flags_on")
        
        response = await client.get("/dashboard", headers={"user-id": "test-user"})
        assert response.status_code == 200
        assert response.json()["features"]["new_design"] is True
    
    @pytest.mark.asyncio
    async def test_all_flags_disabled(self, client: AsyncClient):
        """Test with all flags disabled."""
        await setup_flag_scenario("all_flags_off")
        
        response = await client.get("/dashboard", headers={"user-id": "test-user"})
        assert response.status_code == 200
        assert response.json()["features"]["new_design"] is False
    
    @pytest.mark.asyncio
    async def test_production_flag_config(self, client: AsyncClient):
        """Test with production flag configuration."""
        await setup_flag_scenario("production_config")
        
        response = await client.get("/dashboard", headers={"user-id": "test-user"})
        assert response.status_code == 200
        # Verify production-specific behavior
```

### End-to-End Testing

#### Playwright with Flags
```javascript
// e2e/flag-testing.spec.js
const { test, expect } = require('@playwright/test');

test.describe('Feature Flag E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Set up test user with specific attributes
    await page.addInitScript(() => {
      window.TEST_USER_ID = 'e2e-test-user';
      window.TEST_USER_ATTRIBUTES = {
        country: 'US',
        tier: 'premium',
        beta_user: true
      };
    });
  });

  test('should show new dashboard when flag enabled', async ({ page }) => {
    // Enable flag for test
    await page.route('**/api/v1/evaluate', (route) => {
      if (route.request().url().includes('dashboard_redesign_enabled')) {
        route.fulfill({
          json: {
            flag_id: 'dashboard_redesign_enabled',
            value: true,
            enabled: true,
            reason: 'test_scenario'
          }
        });
      }
    });

    await page.goto('/dashboard');
    
    // Verify new dashboard elements
    await expect(page.locator('[data-testid="new-dashboard"]')).toBeVisible();
    await expect(page.locator('[data-testid="legacy-dashboard"]')).not.toBeVisible();
  });

  test('should gracefully fallback when flag service unavailable', async ({ page }) => {
    // Simulate flag service failure
    await page.route('**/api/v1/evaluate', (route) => {
      route.abort('failed');
    });

    await page.goto('/dashboard');
    
    // Should show fallback/default behavior
    await expect(page.locator('[data-testid="legacy-dashboard"]')).toBeVisible();
  });
});
```

---

## 🔄 Flag Lifecycle Management

### Stage 1: Creation and Development

1. **Flag Creation**
   ```bash
   # Create flag via CLI
   feature-flags create-flag \
     --flag-id dashboard_redesign_enabled \
     --name "Dashboard Redesign" \
     --description "Enable new dashboard UI" \
     --type boolean \
     --default-value false
   ```

2. **Development Implementation**
   - Implement feature behind flag
   - Add comprehensive tests for both states
   - Document flag usage and dependencies

3. **Code Review Checklist**
   - [ ] Flag name follows conventions
   - [ ] Both enabled/disabled paths tested
   - [ ] Proper fallback handling
   - [ ] Performance impact considered
   - [ ] Dependencies documented

### Stage 2: Testing and Staging

1. **Feature Branch Testing**
   ```yaml
   # In CI/CD pipeline
   test_scenarios:
     - name: "flag_enabled"
       flags:
         dashboard_redesign_enabled: true
     - name: "flag_disabled"
       flags:
         dashboard_redesign_enabled: false
   ```

2. **Staging Environment**
   - Enable flag for internal team
   - Gather feedback and metrics
   - Test rollout scenarios

### Stage 3: Production Rollout

1. **Initial Rollout (1-5%)**
   ```bash
   # Set gradual rollout
   feature-flags update-rollout \
     --flag-id dashboard_redesign_enabled \
     --environment production \
     --percentage 5
   ```

2. **Targeted Rollout**
   ```bash
   # Target specific user segments
   feature-flags update-targeting \
     --flag-id dashboard_redesign_enabled \
     --environment production \
     --rule "beta_users" \
     --condition "user_type=beta" \
     --percentage 100
   ```

3. **Full Rollout**
   ```bash
   # Gradually increase to 100%
   feature-flags update-rollout \
     --flag-id dashboard_redesign_enabled \
     --environment production \
     --percentage 100
   ```

### Stage 4: Stabilization and Cleanup

1. **Monitor Metrics** (2-4 weeks)
   - Performance impact
   - Error rates
   - User engagement
   - Business metrics

2. **Code Cleanup**
   ```python
   # Before cleanup
   if await flag_client.is_enabled("dashboard_redesign_enabled"):
       return await get_new_dashboard(user_id)
   else:
       return await get_legacy_dashboard(user_id)
   
   # After cleanup (remove flag)
   return await get_new_dashboard(user_id)  # New becomes default
   ```

3. **Flag Removal**
   ```bash
   # Remove flag after cleanup
   feature-flags delete-flag \
     --flag-id dashboard_redesign_enabled \
     --confirm
   ```

### Flag Lifecycle Tracking

| Stage | Duration | Responsibilities | Exit Criteria |
|-------|----------|------------------|---------------|
| Development | 1-2 weeks | Engineer | Code merged, tests pass |
| Testing | 3-5 days | QA + Engineer | All scenarios tested |
| Staging | 1 week | Product + Engineering | Internal approval |
| Initial Rollout | 3-7 days | Product + DevOps | No critical issues |
| Full Rollout | 1-2 weeks | Product | Success metrics met |
| Stabilization | 2-4 weeks | Engineering | Performance validated |
| Cleanup | 1 week | Engineering | Code cleaned, flag removed |

---

## 🔗 Cross-Repository Dependencies

### Dependency Declaration

Create `flag-dependencies.yaml` in each repository:

```yaml
# Backend repository (PratikoAi-BE)
dependencies:
  outgoing:
    - flag: "dashboard_api_v2_enabled"
      description: "New dashboard API endpoints"
      affects_repositories: ["PratikoAi-KMP"]
      required_for:
        - flag: "dashboard_redesign_enabled"
          repository: "PratikoAi-KMP"
      
  incoming:
    - flag: "dashboard_redesign_enabled"
      repository: "PratikoAi-KMP"
      description: "New dashboard UI that requires API v2"

# Frontend repository (PratikoAi-KMP)
dependencies:
  outgoing:
    - flag: "dashboard_redesign_enabled"
      description: "New dashboard UI"
      affects_repositories: ["PratikoAi-BE"]
      
  incoming:
    - flag: "dashboard_api_v2_enabled"
      repository: "PratikoAi-BE"
      description: "Required API for new dashboard"
      required: true
```

### Dependency Validation

```python
# ci_cd/dependency_checker.py
class FlagDependencyChecker:
    
    async def validate_cross_repo_dependencies(self, repository: str, flag_changes: List[str]):
        """Validate flag dependencies across repositories."""
        dependencies = await self.load_dependencies(repository)
        
        for flag_id in flag_changes:
            # Check outgoing dependencies
            outgoing_deps = dependencies.get("outgoing", [])
            for dep in outgoing_deps:
                if dep["flag"] == flag_id:
                    await self.verify_dependent_repositories(dep)
            
            # Check incoming dependencies
            incoming_deps = dependencies.get("incoming", [])
            for dep in incoming_deps:
                if dep.get("required", False):
                    await self.verify_dependency_available(dep)
    
    async def verify_dependent_repositories(self, dependency: dict):
        """Verify that dependent repositories are ready for flag changes."""
        for repo in dependency["affects_repositories"]:
            # Check if dependent flags exist and are properly configured
            dependent_flags = dependency.get("required_for", [])
            for dep_flag in dependent_flags:
                await self.check_flag_exists(dep_flag["flag"], repo)
```

### Coordination Workflows

#### Pre-deployment Coordination
```yaml
# .github/workflows/pre-deploy-coordination.yml
name: Pre-deployment Flag Coordination

on:
  workflow_dispatch:
    inputs:
      target_environment:
        required: true
        type: choice
        options: [staging, production]

jobs:
  coordinate_flags:
    runs-on: ubuntu-latest
    steps:
      - name: Check Cross-Repo Dependencies
        run: |
          python ci_cd/dependency_checker.py \
            --repository "${{ github.repository }}" \
            --environment "${{ inputs.target_environment }}" \
            --validate-dependencies
      
      - name: Coordinate with Dependent Repos
        run: |
          # Trigger dependency validation in other repos
          gh workflow run flag-dependency-check.yml \
            --repo mickgian/PratikoAi-KMP \
            --field source_repo="${{ github.repository }}" \
            --field environment="${{ inputs.target_environment }}"
```

#### Synchronized Rollout
```python
# synchronized_rollout.py
class SynchronizedFlagRollout:
    
    async def coordinate_rollout(self, primary_flag: str, dependent_flags: List[dict]):
        """Coordinate rollout across multiple repositories."""
        rollout_plan = await self.create_rollout_plan(primary_flag, dependent_flags)
        
        for step in rollout_plan.steps:
            logger.info(f"Executing rollout step: {step.name}")
            
            # Execute all flags in this step simultaneously
            tasks = []
            for flag_config in step.flags:
                task = self.update_flag_rollout(
                    flag_config["repository"],
                    flag_config["flag_id"],
                    flag_config["environment"],
                    step.percentage
                )
                tasks.append(task)
            
            # Wait for all updates to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check for failures
            failures = [r for r in results if isinstance(r, Exception)]
            if failures:
                logger.error(f"Rollout step failed: {failures}")
                await self.rollback_step(step)
                raise Exception(f"Synchronized rollout failed at step {step.name}")
            
            # Wait before next step
            await asyncio.sleep(step.wait_time)
```

---

## ⚡ Performance Considerations

### Client-Side Caching

```kotlin
// Implement smart caching strategy
class FeatureFlagCache(
    private val cacheSize: Int = 100,
    private val ttlMinutes: Int = 5
) {
    private val cache = LRUCache<String, CachedFlag>(cacheSize)
    
    suspend fun getFlag(key: String, fetcher: suspend () -> FlagEvaluation): FlagEvaluation {
        val cached = cache[key]
        
        if (cached != null && !cached.isExpired()) {
            return cached.evaluation
        }
        
        val evaluation = fetcher()
        cache.put(key, CachedFlag(evaluation, Clock.System.now() + ttlMinutes.minutes))
        
        return evaluation
    }
}
```

### Batch Flag Evaluation

```python
# Batch multiple flag evaluations
async def get_user_flags(user_id: str, flag_ids: List[str]) -> Dict[str, Any]:
    """Get multiple flags in a single API call."""
    return await flag_client.get_all_flags(
        user_id=user_id,
        flag_ids=flag_ids
    )

# Use in request handler
@app.get("/user/dashboard")
async def get_dashboard(user_id: str):
    # Get all required flags at once
    flags = await get_user_flags(user_id, [
        "dashboard_redesign_enabled",
        "analytics_realtime_enabled",
        "user_preferences_v2_enabled"
    ])
    
    return await build_dashboard(user_id, flags)
```

### Flag Evaluation Optimization

```kotlin
// Pre-load flags for better performance
class UserSessionManager(
    private val flagClient: FeatureFlagClient
) {
    private val userFlags = mutableMapOf<String, Map<String, JsonElement>>()
    
    suspend fun initializeUserSession(userId: String) {
        // Pre-load all flags for user
        val flags = flagClient.getAllFlags(userId = userId)
        userFlags[userId] = flags
        
        // Set up real-time updates
        flagClient.addFlagUpdateCallback { flagId, _ ->
            // Refresh specific flag
            refreshFlagForUser(userId, flagId)
        }
    }
    
    fun getFlagValue(userId: String, flagId: String, default: Boolean): Boolean {
        return userFlags[userId]?.get(flagId)?.booleanOrNull ?: default
    }
}
```

### Network Optimization

```python
# Implement request coalescing
class FlagRequestCoalescer:
    def __init__(self, batch_window_ms: int = 100):
        self.batch_window_ms = batch_window_ms
        self.pending_requests: Dict[str, List[asyncio.Future]] = {}
    
    async def get_flag(self, flag_id: str, context: dict) -> Any:
        """Coalesce similar requests into batches."""
        cache_key = self._get_cache_key(flag_id, context)
        
        if cache_key not in self.pending_requests:
            self.pending_requests[cache_key] = []
        
        # Create future for this request
        future = asyncio.Future()
        self.pending_requests[cache_key].append(future)
        
        # Start batch timer if this is the first request
        if len(self.pending_requests[cache_key]) == 1:
            asyncio.create_task(self._process_batch(cache_key))
        
        return await future
```

---

## 🔒 Security Best Practices

### API Key Management

```python
# Secure API key handling
class SecureFeatureFlagClient:
    def __init__(self, api_url: str):
        self.api_url = api_url
        # Load API key from secure source
        self.api_key = self._load_api_key()
    
    def _load_api_key(self) -> str:
        # Priority order: environment variable > secret manager > config file
        if api_key := os.getenv("FEATURE_FLAG_API_KEY"):
            return api_key
        
        # Load from secret manager (AWS Secrets Manager, etc.)
        if secret_manager_url := os.getenv("SECRET_MANAGER_URL"):
            return self._load_from_secret_manager(secret_manager_url)
        
        raise ValueError("Feature flag API key not found")
```

### User Data Privacy

```kotlin
// Ensure user data privacy in flag evaluation
class PrivacyAwareFeatureFlagClient(
    private val flagClient: FeatureFlagClient,
    private val privacyManager: PrivacyManager
) {
    suspend fun isEnabled(
        flagId: String,
        userId: String,
        userAttributes: Map<String, JsonElement> = emptyMap()
    ): Boolean {
        // Filter out sensitive attributes
        val sanitizedAttributes = privacyManager.sanitizeAttributes(userAttributes)
        
        // Use hashed user ID for targeting if privacy required
        val evaluationUserId = if (privacyManager.shouldHashUserId(flagId)) {
            privacyManager.hashUserId(userId)
        } else {
            userId
        }
        
        return flagClient.isEnabled(flagId, evaluationUserId, sanitizedAttributes)
    }
}
```

### Audit Logging

```python
# Comprehensive audit logging
class AuditedFeatureFlagClient:
    def __init__(self, base_client: FeatureFlagClient, audit_logger: AuditLogger):
        self.base_client = base_client
        self.audit_logger = audit_logger
    
    async def is_enabled(self, flag_id: str, user_id: str = None, **kwargs) -> bool:
        start_time = datetime.now(timezone.utc)
        
        try:
            result = await self.base_client.is_enabled(flag_id, user_id, **kwargs)
            
            # Log successful evaluation
            await self.audit_logger.log_flag_evaluation(
                flag_id=flag_id,
                user_id=user_id,
                result=result,
                duration=datetime.now(timezone.utc) - start_time,
                success=True
            )
            
            return result
            
        except Exception as e:
            # Log failed evaluation
            await self.audit_logger.log_flag_evaluation(
                flag_id=flag_id,
                user_id=user_id,
                error=str(e),
                duration=datetime.now(timezone.utc) - start_time,
                success=False
            )
            raise
```

---

## 📊 Monitoring and Metrics

### Key Metrics to Track

1. **Flag Evaluation Metrics**
   - Evaluation count per flag
   - Evaluation latency
   - Cache hit/miss rates
   - Error rates

2. **Business Impact Metrics**
   - Conversion rates by flag state
   - User engagement changes
   - Performance impact
   - Revenue attribution

3. **Operational Metrics**
   - Flag service availability
   - API response times
   - Client SDK performance
   - Cross-repository sync status

### Custom Metrics Implementation

```python
# Custom metrics collection
class FeatureFlagMetrics:
    def __init__(self, metrics_client):
        self.metrics = metrics_client
    
    async def record_flag_evaluation(self, flag_id: str, user_id: str, 
                                   value: Any, duration_ms: float):
        """Record flag evaluation metrics."""
        # Counter metrics
        self.metrics.increment(
            "feature_flag.evaluations.total",
            tags={"flag_id": flag_id, "value": str(value)}
        )
        
        # Timing metrics
        self.metrics.timing(
            "feature_flag.evaluation.duration",
            duration_ms,
            tags={"flag_id": flag_id}
        )
        
        # Unique user tracking
        self.metrics.set(
            "feature_flag.users.unique",
            user_id,
            tags={"flag_id": flag_id}
        )
    
    async def record_business_metric(self, flag_id: str, metric_name: str, 
                                   value: float, user_id: str):
        """Record business impact metrics."""
        self.metrics.gauge(
            f"feature_flag.business.{metric_name}",
            value,
            tags={"flag_id": flag_id, "user_group": self._get_user_group(user_id)}
        )
```

### Alerting Setup

```yaml
# alerting_rules.yaml
groups:
  - name: feature_flags
    rules:
      - alert: FeatureFlagServiceDown
        expr: up{job="feature-flag-service"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Feature flag service is down"
          
      - alert: FeatureFlagHighErrorRate
        expr: rate(feature_flag_errors_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate in feature flag evaluations"
          
      - alert: FeatureFlagSlowResponse
        expr: histogram_quantile(0.95, rate(feature_flag_duration_seconds_bucket[5m])) > 0.5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Feature flag evaluations are slow"
```

---

## ⚠️ Common Pitfalls and Solutions

### 1. Flag Sprawl

**Problem**: Too many flags that never get cleaned up

**Solution**:
```python
# Automated flag lifecycle tracking
class FlagLifecycleManager:
    async def audit_stale_flags(self):
        """Find flags that haven't been updated in months."""
        cutoff_date = datetime.now() - timedelta(days=90)
        
        stale_flags = await self.get_flags_older_than(cutoff_date)
        
        for flag in stale_flags:
            # Check if flag is still being evaluated
            recent_evaluations = await self.get_recent_evaluations(flag.id, days=30)
            
            if not recent_evaluations:
                # Flag is not being used - candidate for removal
                await self.mark_for_cleanup(flag.id)
```

### 2. Flag Dependencies

**Problem**: Flags depend on each other, causing confusion

**Solution**:
```python
# Explicit dependency management
@dataclass
class FlagDependency:
    parent_flag: str
    child_flag: str
    relationship: str  # "requires", "conflicts", "enhances"

class DependencyAwareFlagClient:
    async def is_enabled(self, flag_id: str, user_id: str) -> bool:
        # Check dependencies first
        dependencies = await self.get_dependencies(flag_id)
        
        for dep in dependencies:
            if dep.relationship == "requires":
                if not await self.base_client.is_enabled(dep.parent_flag, user_id):
                    return False
            elif dep.relationship == "conflicts":
                if await self.base_client.is_enabled(dep.parent_flag, user_id):
                    return False
        
        return await self.base_client.is_enabled(flag_id, user_id)
```

### 3. Performance Impact

**Problem**: Too many flag evaluations impact performance

**Solution**:
```kotlin
// Implement flag bundling
class BundledFeatureFlagClient(
    private val baseClient: FeatureFlagClient
) {
    // Pre-load commonly used flags
    private val commonFlags = setOf(
        "dashboard_redesign_enabled",
        "new_navigation_enabled",
        "performance_tracking_enabled"
    )
    
    suspend fun initializeUserSession(userId: String) {
        // Load all common flags at once
        val flags = baseClient.getAllFlags(userId, commonFlags.toList())
        // Cache them for the session
        SessionCache.storeFlagsForUser(userId, flags)
    }
}
```

### 4. Inconsistent Behavior

**Problem**: Different flag values across services

**Solution**:
```python
# Consistency checker
class FlagConsistencyChecker:
    async def verify_cross_service_consistency(self, user_id: str, flag_ids: List[str]):
        """Verify flags return consistent values across services."""
        
        # Get flags from each service
        backend_flags = await self.get_flags_from_service("backend", user_id, flag_ids)
        frontend_flags = await self.get_flags_from_service("frontend", user_id, flag_ids)
        
        inconsistencies = []
        for flag_id in flag_ids:
            backend_value = backend_flags.get(flag_id)
            frontend_value = frontend_flags.get(flag_id)
            
            if backend_value != frontend_value:
                inconsistencies.append({
                    "flag_id": flag_id,
                    "backend_value": backend_value,
                    "frontend_value": frontend_value
                })
        
        if inconsistencies:
            await self.alert_inconsistencies(inconsistencies)
        
        return inconsistencies
```

### 5. Testing Complexity

**Problem**: Complex testing with multiple flag combinations

**Solution**:
```python
# Automated test scenario generation
class FlagTestScenarioGenerator:
    def generate_test_matrix(self, flags: List[str], max_combinations: int = 20):
        """Generate reasonable test scenarios for flag combinations."""
        
        scenarios = [
            # Base scenarios
            {"name": "all_flags_off", "flags": {flag: False for flag in flags}},
            {"name": "all_flags_on", "flags": {flag: True for flag in flags}},
        ]
        
        # Add high-impact combinations
        important_flags = self.identify_important_flags(flags)
        for flag in important_flags:
            scenarios.append({
                "name": f"only_{flag}_enabled",
                "flags": {f: (f == flag) for f in flags}
            })
        
        # Add random combinations up to max_combinations
        while len(scenarios) < max_combinations:
            random_scenario = self.generate_random_scenario(flags)
            if random_scenario not in scenarios:
                scenarios.append(random_scenario)
        
        return scenarios
```

---

## 📚 Additional Resources

### Documentation Templates

- [Flag Creation Template](templates/flag_creation.md)
- [Testing Checklist](templates/testing_checklist.md)
- [Rollout Plan Template](templates/rollout_plan.md)
- [Post-Mortem Template](templates/flag_postmortem.md)

### Tools and Scripts

- [Flag Dependency Analyzer](scripts/dependency_analyzer.py)
- [Performance Impact Calculator](scripts/performance_calculator.py)
- [Cleanup Automation](scripts/flag_cleanup.py)
- [Migration Assistant](scripts/flag_migration.py)

### Team Resources

- **Slack Channels**: `#feature-flags`, `#deployment-coordination`
- **Documentation Wiki**: Internal feature flag knowledge base
- **Office Hours**: Weekly flag management Q&A sessions
- **Training Materials**: Video tutorials and best practices guides

---

**Document Version**: 1.0.0  
**Last Updated**: January 15, 2024  
**Next Review**: April 15, 2024  
**Maintained by**: Platform Engineering Team

For questions or suggestions, contact the team at `#feature-flags` or create an issue in the repository.