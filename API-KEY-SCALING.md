# API Key Scaling Strategy

## Current Setup (1-10 users)
- Single API key per provider (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`)
- Cost tracking via `user_id` in application layer
- Rate limiting handled in application layer with cost middleware
- €2.00/user/month target with daily €0.10 limits

## Scaling Trigger: 10+ Active Users

When we hit 10 active users, implement multiple API key strategy to:
- Distribute load across multiple keys
- Avoid hitting rate limits
- Improve reliability with failover
- Maintain granular cost tracking per user

### Implementation Plan

#### 1. **Multiple API Keys Configuration**

```python
# app/core/config.py
OPENAI_API_KEYS = [
    os.getenv("OPENAI_API_KEY_1"),
    os.getenv("OPENAI_API_KEY_2"), 
    os.getenv("OPENAI_API_KEY_3"),
]

ANTHROPIC_API_KEYS = [
    os.getenv("ANTHROPIC_API_KEY_1"),
    os.getenv("ANTHROPIC_API_KEY_2"),
]

# Fallback to single key for backward compatibility
if not any(OPENAI_API_KEYS):
    OPENAI_API_KEYS = [os.getenv("OPENAI_API_KEY")]
```

#### 2. **Load Balancing Logic**

```python
# app/core/llm/key_manager.py
class APIKeyManager:
    """Manages multiple API keys with load balancing and failover."""
    
    def __init__(self, keys: List[str], provider: str):
        self.keys = [key for key in keys if key]  # Filter None values
        self.provider = provider
        self.current_index = 0
        self.key_usage = {key: 0 for key in self.keys}
        self.key_errors = {key: 0 for key in self.keys}
        self.key_last_used = {key: datetime.utcnow() for key in self.keys}
    
    def get_next_key(self) -> str:
        """Get next key using round-robin with error avoidance."""
        if not self.keys:
            raise ValueError(f"No valid API keys configured for {self.provider}")
        
        # Simple round-robin
        key = self.keys[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.keys)
        
        # Track usage
        self.key_usage[key] += 1
        self.key_last_used[key] = datetime.utcnow()
        
        return key
    
    def mark_key_error(self, key: str, error_type: str):
        """Mark key as having errors for monitoring."""
        if key in self.key_errors:
            self.key_errors[key] += 1
            
        logger.warning(
            "api_key_error",
            provider=self.provider,
            key_prefix=key[:8] + "...",
            error_type=error_type,
            total_errors=self.key_errors[key]
        )
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for all keys."""
        return {
            "provider": self.provider,
            "total_keys": len(self.keys),
            "key_usage": {
                f"{key[:8]}...": {
                    "requests": self.key_usage[key],
                    "errors": self.key_errors[key],
                    "last_used": self.key_last_used[key].isoformat(),
                    "error_rate": self.key_errors[key] / max(1, self.key_usage[key])
                }
                for key in self.keys
            }
        }
```

#### 3. **LLM Provider Integration**

```python
# app/core/llm/openai_provider.py
class OpenAIProvider:
    def __init__(self):
        self.key_manager = APIKeyManager(settings.OPENAI_API_KEYS, "openai")
    
    async def generate_response(self, messages: List[Message]) -> LLMResponse:
        """Generate response with automatic key rotation and retry."""
        max_retries = min(3, len(self.key_manager.keys))
        
        for attempt in range(max_retries):
            try:
                api_key = self.key_manager.get_next_key()
                client = openai.AsyncOpenAI(api_key=api_key)
                
                # Make API call
                response = await client.chat.completions.create(...)
                
                return self._parse_response(response)
                
            except openai.RateLimitError as e:
                self.key_manager.mark_key_error(api_key, "rate_limit")
                if attempt == max_retries - 1:
                    raise
                continue
                
            except openai.AuthenticationError as e:
                self.key_manager.mark_key_error(api_key, "auth_error")
                if attempt == max_retries - 1:
                    raise
                continue
                
            except Exception as e:
                self.key_manager.mark_key_error(api_key, str(e))
                if attempt == max_retries - 1:
                    raise
                continue
```

#### 4. **Monitoring & Alerting**

```python
# app/services/api_key_monitor.py
class APIKeyMonitor:
    """Monitor API key usage and health."""
    
    async def check_key_health(self):
        """Check all API keys for issues."""
        for provider in ["openai", "anthropic"]:
            key_manager = get_key_manager(provider)
            stats = key_manager.get_usage_stats()
            
            for key_stats in stats["key_usage"].values():
                # Alert if error rate > 20%
                if key_stats["error_rate"] > 0.2:
                    await self._send_alert(
                        f"High error rate for {provider} key",
                        key_stats
                    )
                
                # Alert if key hasn't been used in 24h but others have
                last_used = datetime.fromisoformat(key_stats["last_used"])
                if datetime.utcnow() - last_used > timedelta(hours=24):
                    if any(s["requests"] > 0 for s in stats["key_usage"].values()):
                        await self._send_alert(
                            f"Unused {provider} key detected", 
                            key_stats
                        )
    
    async def get_rate_limit_status(self, provider: str) -> Dict[str, Any]:
        """Check rate limit status for all keys."""
        # Implementation would check remaining quotas via API headers
        # or provider-specific endpoints
        pass
```

#### 5. **Cost Tracking Preservation**

The existing usage tracking system **already handles this perfectly**:

```python
# Current tracking in usage_tracker.py - NO CHANGES NEEDED
await usage_tracker.track_llm_usage(
    user_id=user_id,           # ✅ User attribution preserved
    session_id=session_id,     # ✅ Session tracking preserved  
    provider=provider,         # ✅ Provider tracking preserved
    model=model,              # ✅ Model tracking preserved
    llm_response=response,    # ✅ Cost from response.cost_estimate
    # ... rest of tracking
)
```

**Key insight**: Cost tracking is done **after** the API call using the response data, so it doesn't matter which specific API key was used. The cost is still attributed to the correct user.

### Deployment Configuration

#### Environment Variables
```bash
# Production
OPENAI_API_KEY_1=sk-...
OPENAI_API_KEY_2=sk-...
OPENAI_API_KEY_3=sk-...

ANTHROPIC_API_KEY_1=sk-ant-...
ANTHROPIC_API_KEY_2=sk-ant-...

# Monitoring
API_KEY_HEALTH_CHECK_INTERVAL=300  # 5 minutes
RATE_LIMIT_ALERT_THRESHOLD=0.8     # Alert at 80%
```

#### Docker Compose Updates
```yaml
services:
  app:
    environment:
      - OPENAI_API_KEY_1=${OPENAI_API_KEY_1}
      - OPENAI_API_KEY_2=${OPENAI_API_KEY_2}
      - OPENAI_API_KEY_3=${OPENAI_API_KEY_3}
      - ANTHROPIC_API_KEY_1=${ANTHROPIC_API_KEY_1}
      - ANTHROPIC_API_KEY_2=${ANTHROPIC_API_KEY_2}
```

### Implementation Checklist

#### Phase 1: Foundation
- [ ] Create `APIKeyManager` class with round-robin selection
- [ ] Add multiple key support to LLM providers
- [ ] Update configuration to support key arrays
- [ ] Test failover scenarios in development

#### Phase 2: Monitoring  
- [ ] Implement `APIKeyMonitor` service
- [ ] Add Prometheus metrics for key usage
- [ ] Create alerting rules for high error rates
- [ ] Add health check endpoints

#### Phase 3: Production
- [ ] Deploy with multiple keys in staging
- [ ] Test load distribution and failover
- [ ] Monitor key usage patterns
- [ ] Update deployment documentation

#### Phase 4: Optimization
- [ ] Implement intelligent key selection (avoid recently failed keys)
- [ ] Add rate limit awareness (check remaining quotas)
- [ ] Create key usage dashboard
- [ ] Automated key rotation capabilities

## Why Scale at 10 Users?

### Traffic Analysis
- **10 active users** × **100 requests/day** = **1,000 requests/day**
- **Peak hour**: ~200 requests/hour = **3.3 requests/minute**
- **Current OpenAI limits**: 3 requests/minute on Tier 1
- **Risk**: Getting close to rate limit concerns

### Benefits of Early Implementation
1. **Proactive**: Implement before hitting issues
2. **Reliability**: Better uptime with failover
3. **Scalability**: Smooth growth to 50+ users
4. **Monitoring**: Early detection of API issues
5. **Cost Control**: Maintained per-user tracking

### Cost Impact
- **Additional Keys**: $0/month (same usage, distributed)
- **Implementation**: ~8 hours development time
- **Monitoring**: Minimal overhead, high value
- **ROI**: Prevents service disruptions worth > €1000/incident

## Future Scaling Considerations

### 50+ Users
- Consider usage-based key selection
- Implement key-specific rate limiting
- Add geographic key distribution
- Monitor provider-specific quotas

### 100+ Users  
- Implement key pooling strategies
- Add intelligent routing based on model/task type
- Consider enterprise API tier upgrades
- Implement automated key procurement