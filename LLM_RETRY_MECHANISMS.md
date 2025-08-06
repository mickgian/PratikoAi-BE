# LLM Retry Mechanisms for PratikoAI

This document provides comprehensive documentation for the robust retry mechanisms implemented for LLM API calls in PratikoAI, ensuring production reliability by gracefully handling transient failures, rate limits, and timeouts from OpenAI and Anthropic APIs.

## Overview

The LLM retry mechanisms prevent single API failures from resulting in customer-facing errors while maintaining cost control and performance. The system implements exponential backoff with jitter, circuit breaker patterns, provider fallback, and cost-aware retry budgets.

### Key Features

- **Exponential Backoff with Jitter**: Prevents thundering herd problems
- **Circuit Breaker Protection**: Prevents cascade failures
- **Multi-Provider Fallback**: Automatic failover between OpenAI and Anthropic
- **Cost-Aware Retry Budgets**: Prevents budget overruns
- **Comprehensive Monitoring**: Real-time metrics and health monitoring
- **Configurable Retry Policies**: Provider-specific configurations

## Architecture

### Core Components

1. **RetryHandler**: Core retry logic with exponential backoff
2. **CircuitBreaker**: Failure protection and recovery
3. **ResilientLLMService**: High-level service with provider fallback
4. **CostTracker**: Cost monitoring and budget enforcement
5. **QueryService**: Main interface integrating with existing LLM factory

### Component Relationships

```
QueryService
    ├── ResilientLLMService
    │   ├── RetryHandler (per provider)
    │   ├── CircuitBreaker (per provider)
    │   ├── OpenAIProvider
    │   └── AnthropicProvider
    ├── CostTracker
    └── RetryMetrics
```

## Configuration

### Provider-Specific Configurations

The system uses different retry configurations for each provider:

#### OpenAI Configuration
```python
OPENAI = RetryConfig(
    max_attempts=3,
    initial_delay=2.0,          # seconds
    timeout=30.0,
    max_retry_cost=0.10,        # EUR
    circuit_breaker_threshold=5
)
```

#### Anthropic Configuration
```python
ANTHROPIC = RetryConfig(
    max_attempts=3,
    initial_delay=1.5,          # seconds
    timeout=25.0,
    max_retry_cost=0.08,        # EUR
    circuit_breaker_threshold=5
)
```

#### Fallback Configuration (Cheap Model)
```python
OPENAI_CHEAP = RetryConfig(
    max_attempts=2,
    initial_delay=1.0,          # seconds
    timeout=20.0,
    max_retry_cost=0.02,        # EUR
    circuit_breaker_threshold=3
)
```

### Environment Variables

```bash
# Required for retry mechanisms
LLM_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
REDIS_URL=redis://localhost:6379/0

# Optional configuration
COST_TRACKING_ENABLED=true
RETRY_METRICS_ENABLED=true
CIRCUIT_BREAKER_TIMEOUT=60.0
MAX_RETRY_BUDGET_PER_USER=1.00
```

## Usage

### Basic Query Processing

```python
from app.services.query_service import get_query_service
from app.models.query import QueryRequest, QueryType

# Create query request
request = QueryRequest(
    prompt="Explain quantum computing",
    user_id="user123",
    query_type=QueryType.CHAT,
    preferred_provider="openai",
    allow_fallback=True,
    max_tokens=150,
    temperature=0.7
)

# Process with retry mechanisms
query_service = await get_query_service()
result = await query_service.process_query(request, use_retry_mechanisms=True)
```

### Direct Resilient LLM Service

```python
from app.services.resilient_llm_service import get_llm_service

# Get resilient LLM service
llm_service = await get_llm_service()

# Execute with automatic retries and fallback
result = await llm_service.complete(
    prompt="Analyze this financial document",
    user_id="user123",
    preferred_provider="openai",
    allow_fallback=True,
    max_tokens=500
)
```

### Manual Provider Control

```python
from app.services.resilient_llm_service import get_llm_service

llm_service = await get_llm_service()

# Disable problematic provider
await llm_service.disable_provider("openai")

# Reset circuit breaker
await llm_service.reset_circuit_breaker("anthropic")

# Re-enable provider
await llm_service.enable_provider("openai")
```

## API Endpoints

### Submit Query with Retry Mechanisms

```http
POST /api/v1/llm-retry/query
Content-Type: application/json

{
  "query_request": {
    "prompt": "Explain machine learning",
    "user_id": "user123",
    "query_type": "chat",
    "preferred_provider": "openai",
    "allow_fallback": true,
    "max_tokens": 200,
    "temperature": 0.7
  },
  "use_retry_mechanisms": true
}
```

### Get Query Status

```http
GET /api/v1/llm-retry/query/{query_id}
```

### Get Retry Statistics

```http
GET /api/v1/llm-retry/statistics?hours=24
```

### Service Health Check

```http
GET /api/v1/llm-retry/health
```

### Admin Provider Control

```http
POST /api/v1/llm-retry/admin/provider/control
Content-Type: application/json

{
  "provider": "openai",
  "action": "reset_circuit_breaker",
  "reason": "Clearing temporary issues"
}
```

## Retry Strategies

### Exponential Backoff

The system uses exponential backoff with jitter to prevent thundering herd problems:

```python
delay = initial_delay * (exponential_base ** attempt)
delay = min(delay, max_delay)

# Add jitter (50-100% of calculated delay)
if jitter:
    jitter_factor = 0.5 + (random.random() * 0.5)
    delay *= jitter_factor
```

**Example delays for OpenAI:**
- Attempt 1: 2.0s (±1.0s jitter)
- Attempt 2: 4.0s (±2.0s jitter)  
- Attempt 3: 8.0s (±4.0s jitter)

### Circuit Breaker States

1. **Closed**: Normal operation, requests pass through
2. **Open**: Circuit breaker is open, requests fail immediately
3. **Half-Open**: Testing if service has recovered

**Failure Threshold**: 5 consecutive failures opens the circuit
**Timeout**: 60 seconds before transitioning to half-open

### Provider Fallback Order

1. **Primary**: User's preferred provider (default: OpenAI)
2. **Secondary**: Alternative provider (Anthropic)
3. **Fallback**: Cheap model (GPT-3.5-turbo) for cost control

## Error Handling

### Retryable Errors

The system automatically retries on:
- **HTTP 429**: Rate limit exceeded
- **HTTP 5xx**: Server errors
- **Timeout errors**: Request timeouts
- **Connection errors**: Network issues
- **Overloaded errors**: Service temporarily unavailable

### Non-Retryable Errors

The system does not retry on:
- **HTTP 400**: Bad request
- **HTTP 401**: Unauthorized (invalid API key)
- **HTTP 403**: Forbidden
- **Malformed request errors**
- **Authentication failures**

### Cost Budget Exceeded

When a user exceeds their retry budget:
1. System attempts the request once without retries
2. If that fails, returns `CostBudgetExceededError`
3. User must wait for budget window to reset

## Monitoring and Metrics

### Key Metrics

- **Success Rate**: Percentage of successful requests
- **Retry Rate**: Average retries per request
- **Fallback Rate**: Percentage using fallback providers
- **Circuit Breaker State**: Provider availability
- **Cost per Request**: Average cost including retries
- **Response Time**: Including retry delays

### Health Scores

Provider health scores (0-100) based on:
- Success rate in the last hour
- Circuit breaker state
- Average response time
- Error frequency

**Health Score Calculation:**
- 90-100: Excellent
- 70-89: Good  
- 50-69: Degraded
- 25-49: Poor
- 0-24: Critical

### Prometheus Metrics

```python
# Success counter
llm_retry_success_total{provider="openai"} 1250

# Failure counter  
llm_retry_failure_total{provider="anthropic",error_type="timeout"} 23

# Duration histogram
llm_retry_duration_seconds{provider="openai"} 2.34

# Fallback counter
llm_provider_fallback_total{from_provider="openai",to_provider="anthropic"} 45

# Circuit breaker state
llm_circuit_breaker_state{provider="openai"} 0
```

## Cost Control

### Retry Budgets

Each user has a retry budget to prevent cost overruns:
- **Default Budget**: €0.10 per hour sliding window
- **Budget Tracking**: Redis-based with automatic cleanup
- **Budget Exceeded**: Single attempt without retries

### Cost Calculation

```python
# OpenAI GPT-4 pricing example
input_cost = (input_tokens / 1000) * 0.03   # €0.03 per 1K tokens
output_cost = (output_tokens / 1000) * 0.06 # €0.06 per 1K tokens
total_cost = input_cost + output_cost
```

### Cost Optimization

1. **Fallback to Cheaper Models**: GPT-3.5-turbo for cost control
2. **Provider Cost Multipliers**: Anthropic typically 20% cheaper
3. **Budget Enforcement**: Prevents unlimited retries
4. **Cost-Aware Routing**: Consider cost in provider selection

## Troubleshooting

### Common Issues

#### High Failure Rate

1. Check provider API status
2. Verify API keys are valid
3. Review rate limits
4. Check network connectivity

```bash
# Check provider health
curl -X GET "http://localhost:8000/api/v1/llm-retry/admin/providers/health"
```

#### Circuit Breaker Constantly Open

1. Review error logs for root cause
2. Check provider service status
3. Consider increasing failure threshold
4. Manually reset if needed

```bash
# Reset circuit breaker
curl -X POST "http://localhost:8000/api/v1/llm-retry/admin/provider/control" \
  -H "Content-Type: application/json" \
  -d '{"provider": "openai", "action": "reset_circuit_breaker"}'
```

#### Cost Budget Issues

1. Check user retry costs in Redis
2. Review retry frequency
3. Adjust budget limits if needed
4. Monitor for abuse patterns

```bash
# Check Redis for user costs
redis-cli ZRANGE retry_costs:user123 0 -1 WITHSCORES
```

### Debugging Commands

```python
# Get detailed service status
from app.services.resilient_llm_service import get_llm_service_status
status = await get_llm_service_status()
print(status)

# Get provider health
from app.services.resilient_llm_service import get_llm_service
service = await get_llm_service()
health = await service.get_provider_health()
print(health)

# Get retry statistics
stats = await service.get_retry_statistics(hours=24)
print(stats)
```

## Performance Considerations

### Scalability

- **Stateless Design**: All services are completely stateless
- **Redis Caching**: Distributed state management
- **Connection Pooling**: Efficient HTTP client management
- **Async Processing**: Non-blocking I/O throughout

### Latency Optimization

- **Jitter**: Prevents thundering herd problems
- **Circuit Breakers**: Fast-fail for unhealthy providers
- **Provider Selection**: Route to fastest available provider
- **Timeout Management**: Prevent hanging requests

### Memory Usage

- **Bounded Queues**: Limited retry attempt storage
- **TTL Expiration**: Automatic cleanup of old data
- **Metrics Aggregation**: Efficient time-series storage
- **Connection Reuse**: HTTP connection pooling

## Security Considerations

### API Key Management

- Store API keys in environment variables
- Use separate keys for different environments
- Rotate keys regularly
- Monitor for key usage anomalies

### Rate Limit Compliance

- Respect provider rate limits
- Implement back-pressure mechanisms
- Monitor for abuse patterns
- Use cost budgets to prevent overuse

### Data Protection

- No logging of sensitive prompt content
- Secure Redis connections
- Encrypt data in transit
- Audit access patterns

## Testing

### Unit Tests

```bash
# Run retry mechanism tests
pytest tests/test_llm_retry_mechanisms.py -v

# Run integration tests
pytest tests/test_query_service.py -v

# Run with coverage
pytest --cov=app/services tests/ --cov-report=html
```

### Load Testing

```python
# Test concurrent requests
import asyncio
import aiohttp

async def load_test():
    tasks = []
    for i in range(100):
        task = submit_test_query(f"Query {i}")
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

### Manual Testing

```bash
# Test retry mechanisms
curl -X POST "http://localhost:8000/api/v1/llm-retry/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query_request": {
      "prompt": "Test query",
      "user_id": "test_user",
      "preferred_provider": "openai"
    },
    "use_retry_mechanisms": true
  }'
```

## Migration Guide

### From Direct LLM Calls

1. **Replace direct provider calls** with `QueryService`
2. **Update error handling** to handle retry-specific exceptions
3. **Add cost tracking** to monitor usage
4. **Configure retry policies** per your requirements

```python
# Before
provider = OpenAIProvider(api_key=key, model="gpt-4")
response = await provider.chat_completion(messages)

# After  
query_service = await get_query_service()
request = QueryRequest(prompt=prompt, user_id=user_id)
response = await query_service.process_query(request)
```

### Gradual Rollout

1. **Phase 1**: Deploy with `use_retry_mechanisms=False`
2. **Phase 2**: Enable for specific users/endpoints
3. **Phase 3**: Enable for all traffic
4. **Phase 4**: Remove legacy fallback code

## Support and Maintenance

### Log Analysis

```bash
# Search for retry-related logs
grep "retry_" /var/log/pratikoai/app.log

# Monitor circuit breaker events
grep "Circuit breaker" /var/log/pratikoai/app.log

# Check cost budget issues
grep "budget exceeded" /var/log/pratikoai/app.log
```

### Metrics Dashboard

Key metrics to monitor:
- Overall success rate (target: >99%)
- Average retry count (target: <0.1)
- Circuit breaker state changes
- Cost per request trends
- Response time percentiles

### Emergency Procedures

#### All Providers Failing

1. Check provider status pages
2. Verify API keys and quotas
3. Review recent configuration changes
4. Consider temporary fallback to cached responses

#### Cost Budget Overruns

1. Review retry patterns for anomalies
2. Check for potential abuse
3. Temporarily increase budgets if legitimate
4. Implement additional rate limiting

#### Performance Degradation

1. Monitor provider response times
2. Check circuit breaker states
3. Review retry frequency
4. Consider provider rebalancing

---

**Last Updated**: 2024-12-05  
**Version**: 1.0  
**Authors**: Claude Code Assistant

For additional support or questions, please refer to the PratikoAI documentation or contact the development team.