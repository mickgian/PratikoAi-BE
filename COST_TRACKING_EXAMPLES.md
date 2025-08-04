# Cost Tracking Examples

## How Cost Tracking Works with Single API Key

### Current Implementation Flow

```python
# 1. User makes request to /api/v1/chatbot/query
async def query_chatbot(
    request: ChatRequest,
    session: UserSession = Depends(get_current_session)  # ✅ user_id from JWT
):
    # 2. Pass user_id to LangGraph agent
    result = await agent.get_response(
        processed_messages, 
        session.id, 
        user_id=session.user_id  # ✅ User attribution
    )

# 3. LangGraph stores user context
self._current_user_id = user_id
self._current_session_id = session_id

# 4. LLM call with shared API key (user_id NOT sent to OpenAI)
response = await openai_client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
    # Uses OPENAI_API_KEY - no user identification here
)

# 5. Cost attributed to user AFTER call
await usage_tracker.track_llm_usage(
    user_id=self._current_user_id,  # ✅ User gets charged
    provider="openai",
    model="gpt-4o-mini", 
    llm_response=response,  # Contains token count & cost
    cost_eur=response.cost_estimate,  # Cost calculated from tokens
    cache_hit=False
)
```

### Database Schema for Cost Tracking

```sql
-- Individual usage events (every LLM call)
CREATE TABLE usage_events (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR NOT NULL,           -- ✅ Links cost to specific user
    session_id VARCHAR,
    event_type VARCHAR NOT NULL,        -- 'llm_query', 'cache_hit', 'api_request'
    timestamp TIMESTAMP DEFAULT NOW(),
    
    -- LLM Details
    provider VARCHAR,                   -- 'openai', 'anthropic'  
    model VARCHAR,                      -- 'gpt-4o-mini', 'claude-3-haiku'
    input_tokens INTEGER,               -- Tokens sent to API
    output_tokens INTEGER,              -- Tokens received from API
    total_tokens INTEGER,               -- Sum of input + output
    
    -- Cost Attribution  
    cost_eur DECIMAL(10,6),            -- ✅ Cost in EUR for this user
    cost_category VARCHAR,              -- 'llm_inference', 'storage', etc.
    
    -- Performance
    response_time_ms INTEGER,
    cache_hit BOOLEAN DEFAULT FALSE,    -- Zero cost if true
    
    -- Error tracking
    error_occurred BOOLEAN DEFAULT FALSE,
    error_type VARCHAR
);

-- Daily summaries per user (efficient querying)  
CREATE TABLE user_usage_summaries (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR NOT NULL,           -- ✅ Per-user daily rollup
    date DATE NOT NULL,
    
    -- Usage counts
    total_requests INTEGER DEFAULT 0,
    llm_requests INTEGER DEFAULT 0,
    cache_hits INTEGER DEFAULT 0,
    cache_misses INTEGER DEFAULT 0,
    
    -- Token usage
    total_input_tokens INTEGER DEFAULT 0,
    total_output_tokens INTEGER DEFAULT 0, 
    total_tokens INTEGER DEFAULT 0,
    
    -- Cost tracking
    total_cost_eur DECIMAL(10,6) DEFAULT 0.0,  -- ✅ Daily cost per user
    llm_cost_eur DECIMAL(10,6) DEFAULT 0.0,
    
    -- Performance metrics
    avg_response_time_ms DECIMAL(8,2),
    cache_hit_rate DECIMAL(4,3) DEFAULT 0.0,
    error_rate DECIMAL(4,3) DEFAULT 0.0,
    
    UNIQUE(user_id, date)
);

-- User quotas and limits
CREATE TABLE usage_quotas (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR UNIQUE NOT NULL,    -- ✅ Individual user limits
    
    -- Limits
    daily_requests_limit INTEGER DEFAULT 100,
    daily_cost_limit_eur DECIMAL(6,3) DEFAULT 0.10,     -- €0.10/day
    monthly_cost_limit_eur DECIMAL(6,2) DEFAULT 2.00,   -- €2.00/month
    daily_token_limit INTEGER DEFAULT 50000,
    monthly_token_limit INTEGER DEFAULT 1000000,
    
    -- Current usage (auto-reset)
    current_daily_requests INTEGER DEFAULT 0,
    current_daily_cost_eur DECIMAL(6,3) DEFAULT 0.0,    -- ✅ Today's cost
    current_monthly_cost_eur DECIMAL(6,2) DEFAULT 0.0,  -- ✅ This month's cost
    current_daily_tokens INTEGER DEFAULT 0,
    current_monthly_tokens INTEGER DEFAULT 0,
    
    -- Reset tracking
    daily_reset_at TIMESTAMP DEFAULT NOW(),
    monthly_reset_at TIMESTAMP DEFAULT NOW(),
    
    is_active BOOLEAN DEFAULT TRUE
);
```

## Example Queries

### 1. Get Cost Per User This Month

```sql
-- Option A: From daily summaries (faster)
SELECT 
    user_id,
    SUM(total_cost_eur) as monthly_cost_eur,
    SUM(total_requests) as total_requests,
    SUM(llm_requests) as llm_requests,
    SUM(total_tokens) as total_tokens,
    AVG(cache_hit_rate) as avg_cache_hit_rate
FROM user_usage_summaries 
WHERE date >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY user_id
ORDER BY monthly_cost_eur DESC;

-- Option B: From individual events (more detailed)
SELECT 
    user_id,
    SUM(cost_eur) as monthly_cost_eur,
    COUNT(*) as total_requests,
    COUNT(*) FILTER (WHERE event_type = 'llm_query') as llm_requests,
    SUM(total_tokens) as total_tokens,
    SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END)::FLOAT / 
        COUNT(*) FILTER (WHERE event_type = 'llm_query') as cache_hit_rate
FROM usage_events 
WHERE timestamp >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY user_id
ORDER BY monthly_cost_eur DESC;
```

### 2. Get Total Cost for Specific User This Month

```sql
-- Quick query using quota table
SELECT 
    user_id,
    current_monthly_cost_eur as monthly_cost,
    monthly_cost_limit_eur as monthly_limit,
    (current_monthly_cost_eur / monthly_cost_limit_eur * 100) as usage_percentage
FROM usage_quotas 
WHERE user_id = 'user_12345';

-- Detailed breakdown by day
SELECT 
    date,
    total_cost_eur as daily_cost,
    total_requests,
    cache_hit_rate,
    error_rate
FROM user_usage_summaries 
WHERE user_id = 'user_12345' 
  AND date >= DATE_TRUNC('month', CURRENT_DATE)
ORDER BY date;
```

### 3. Cost Dashboard Query (All Users)

```sql
WITH monthly_stats AS (
    SELECT 
        user_id,
        SUM(total_cost_eur) as monthly_cost,
        SUM(total_requests) as monthly_requests,
        AVG(cache_hit_rate) as avg_cache_hit_rate
    FROM user_usage_summaries 
    WHERE date >= DATE_TRUNC('month', CURRENT_DATE)
    GROUP BY user_id
),
quota_info AS (
    SELECT 
        user_id,
        monthly_cost_limit_eur,
        current_monthly_cost_eur,
        is_active
    FROM usage_quotas
)
SELECT 
    ms.user_id,
    ms.monthly_cost,
    qi.monthly_cost_limit_eur as limit,
    (ms.monthly_cost / qi.monthly_cost_limit_eur * 100) as usage_percent,
    ms.monthly_requests,
    ms.avg_cache_hit_rate,
    qi.is_active,
    CASE 
        WHEN ms.monthly_cost > qi.monthly_cost_limit_eur THEN 'OVER_LIMIT'
        WHEN ms.monthly_cost > qi.monthly_cost_limit_eur * 0.8 THEN 'WARNING'
        ELSE 'OK'
    END as status
FROM monthly_stats ms
JOIN quota_info qi ON ms.user_id = qi.user_id
ORDER BY usage_percent DESC;
```

### 4. Model Usage and Cost Breakdown

```sql
-- Cost by model for all users this month
SELECT 
    model,
    provider,
    COUNT(*) as requests,
    SUM(total_tokens) as total_tokens,
    SUM(cost_eur) as total_cost_eur,
    AVG(cost_eur) as avg_cost_per_request,
    AVG(total_tokens) as avg_tokens_per_request
FROM usage_events 
WHERE timestamp >= DATE_TRUNC('month', CURRENT_DATE)
  AND event_type = 'llm_query'
  AND NOT cache_hit
GROUP BY model, provider
ORDER BY total_cost_eur DESC;

-- Cost by model for specific user
SELECT 
    model,
    COUNT(*) as requests,
    SUM(cost_eur) as total_cost,
    AVG(response_time_ms) as avg_response_time
FROM usage_events 
WHERE user_id = 'user_12345'
  AND timestamp >= DATE_TRUNC('month', CURRENT_DATE)
  AND event_type = 'llm_query'
GROUP BY model
ORDER BY total_cost DESC;
```

### 5. API Endpoints for Cost Data

The application provides these endpoints for users to access their cost data:

```python
# GET /api/v1/analytics/usage/current
{
    "user_id": "user_12345",
    "current_period": {
        "daily_cost": 0.05,
        "daily_limit": 0.10,
        "monthly_cost": 1.25,
        "monthly_limit": 2.00,
        "requests_today": 15,
        "tokens_today": 12500
    },
    "usage_percentage": {
        "daily": 50.0,
        "monthly": 62.5
    },
    "status": "OK"  # OK, WARNING, OVER_LIMIT
}

# GET /api/v1/analytics/usage/breakdown?period=month
{
    "period": "month",
    "user_id": "user_12345", 
    "breakdown": {
        "by_category": {
            "llm_inference": 1.20,
            "storage": 0.03,
            "compute": 0.02,
            "total": 1.25
        },
        "by_model": {
            "gpt-4o-mini": {"requests": 45, "cost": 0.85},
            "claude-3-haiku": {"requests": 12, "cost": 0.40}
        },
        "by_day": [
            {"date": "2024-01-01", "cost": 0.08, "requests": 12},
            {"date": "2024-01-02", "cost": 0.12, "requests": 18}
        ]
    }
}
```

## Key Points

### ✅ What Works Well
1. **Single API Key**: All LLM calls use shared `OPENAI_API_KEY`
2. **User Attribution**: Cost tracked per user via `user_id` from session
3. **Granular Tracking**: Every API call logged with full context
4. **Budget Control**: €0.10 daily, €2.00 monthly limits enforced
5. **Cache Optimization**: Cache hits tracked with zero cost
6. **Real-time Quotas**: Limits checked before each request

### 🔄 How Multiple API Keys Will Work
- **Same Cost Tracking**: No changes needed to usage tracking
- **Key Selection**: Round-robin selection of available keys
- **User Attribution**: Still tracked via `user_id` after API call
- **Cost Calculation**: Same token-based cost calculation
- **Failover**: Automatic retry with different key on rate limits

### 📊 Cost Dashboard Available At
- `/api/v1/analytics/usage/current` - Current usage
- `/api/v1/analytics/usage/breakdown` - Detailed breakdown
- `/api/v1/analytics/usage/history` - Historical data
- Admin dashboard at `/api/v1/admin/usage/system` - System-wide metrics