# PratikoAI Metrics Glossary

Comprehensive reference for all metrics collected by the PratikoAI monitoring system. This glossary defines every metric, its purpose, calculation method, and business significance.

## 📊 Metric Categories

- [💰 Business & Financial Metrics](#-business--financial-metrics)
- [⚡ Performance & Technical Metrics](#-performance--technical-metrics)
- [🔒 Security & Compliance Metrics](#-security--compliance-metrics)
- [💾 System Resource Metrics](#-system-resource-metrics)
- [🤖 LLM & AI Metrics](#-llm--ai-metrics)
- [📈 Growth & User Metrics](#-growth--user-metrics)

---

## 💰 Business & Financial Metrics

### `user_monthly_cost_eur`
**Definition**: Average monthly cost per active user in Euros  
**Type**: Gauge  
**Unit**: EUR (Euros)  
**Target**: €2.00/month  
**Critical Threshold**: >€2.50/month  

**Calculation**: 
```
sum(llm_cost_total_eur + infrastructure_cost_eur + support_cost_eur) / count(active_users)
```

**Business Impact**: 
- Primary profitability indicator
- Direct correlation to business sustainability
- Key metric for pricing strategy decisions

**PromQL Queries**:
```promql
# Current average user cost
avg(user_monthly_cost_eur)

# Top 10 expensive users
topk(10, user_monthly_cost_eur)

# Users exceeding target cost
count(user_monthly_cost_eur > 2.0)
```

**Labels**: `user_id`, `plan_type`, `region`

---

### `monthly_revenue_eur`
**Definition**: Monthly recurring revenue in Euros  
**Type**: Gauge  
**Unit**: EUR (Euros)  
**Target**: €25,000/month  
**Warning Threshold**: <€20,000/month  

**Calculation**:
```
sum(subscription_value_eur{status="active"})
```

**Business Impact**:
- Growth tracking and financial planning
- Investor reporting and valuation
- Resource allocation decisions

**PromQL Queries**:
```promql
# Current MRR
sum(monthly_revenue_eur)

# MRR growth rate (month over month)
(sum(monthly_revenue_eur) / sum(monthly_revenue_eur offset 30d) - 1) * 100

# Revenue by plan type
sum by (plan_type) (monthly_revenue_eur)
```

**Labels**: `plan_type`, `billing_cycle`, `currency`

---

### `payment_operations_total`
**Definition**: Total count of payment operations  
**Type**: Counter  
**Unit**: Count  
**Target Success Rate**: >95%  
**Critical Threshold**: <95% success rate  

**Calculation**:
```
count(payment_attempts) labeled by status
```

**Business Impact**:
- Revenue collection efficiency
- Customer experience quality
- Financial operations health

**PromQL Queries**:
```promql
# Payment success rate (last hour)
rate(payment_operations_total{status="succeeded"}[1h]) / rate(payment_operations_total[1h]) * 100

# Payment failures by type
sum by (error_type) (rate(payment_operations_total{status="failed"}[1h]))

# Daily payment volume
increase(payment_operations_total[24h])
```

**Labels**: `status` (succeeded/failed), `payment_method`, `error_type`, `currency`

---

### `llm_cost_total_eur`
**Definition**: Cumulative LLM API costs in Euros  
**Type**: Counter  
**Unit**: EUR (Euros)  
**Warning Threshold**: >€100/day  

**Calculation**:
```
sum(api_call_cost * token_count * model_rate)
```

**Business Impact**:
- Major component of user cost calculation
- Direct impact on profit margins
- Technology spend optimization

**PromQL Queries**:
```promql
# Daily LLM costs
increase(llm_cost_total_eur[24h])

# Cost by provider
sum by (provider) (increase(llm_cost_total_eur[24h]))

# Cost by model
sum by (model) (increase(llm_cost_total_eur[24h]))

# Cost per API call
increase(llm_cost_total_eur[1h]) / increase(llm_calls_total[1h])
```

**Labels**: `provider` (openai/anthropic), `model`, `user_id`, `endpoint`

---

### `active_subscriptions_total`
**Definition**: Number of active paid subscriptions  
**Type**: Gauge  
**Unit**: Count  
**Target**: 50 active subscriptions  

**Calculation**:
```
count(subscriptions{status="active", expiry_date > now()})
```

**Business Impact**:
- Revenue predictability indicator
- Growth trajectory measurement
- Customer retention tracking

**PromQL Queries**:
```promql
# Active subscriptions
sum(active_subscriptions_total{status="active"})

# Subscription churn rate (24h)
rate(subscription_churn_total[24h]) / rate(active_subscriptions_total[24h]) * 100

# Subscriptions by plan
sum by (plan_type) (active_subscriptions_total{status="active"})
```

**Labels**: `status`, `plan_type`, `billing_cycle`, `region`

---

## ⚡ Performance & Technical Metrics

### `http_request_duration_seconds`
**Definition**: HTTP request duration histogram  
**Type**: Histogram  
**Unit**: Seconds  
**Target**: <2 seconds (95th percentile)  
**SLA Threshold**: <5 seconds (95th percentile)  

**Calculation**:
```
histogram of request processing times from start to response
```

**Technical Impact**:
- User experience quality
- System performance indicator
- Scalability assessment

**PromQL Queries**:
```promql
# 95th percentile response time
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Average response time
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])

# Slowest endpoints
topk(5, histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])))
```

**Labels**: `method`, `endpoint`, `status_code`, `user_id`

---

### `cache_hit_ratio`
**Definition**: Percentage of requests served from cache  
**Type**: Gauge  
**Unit**: Ratio (0-1)  
**Target**: >0.80 (80%)  
**Warning Threshold**: <0.70 (70%)  

**Calculation**:
```
cache_hits / (cache_hits + cache_misses)
```

**Technical Impact**:
- Performance optimization indicator
- Cost reduction through reduced LLM calls
- System efficiency measurement

**PromQL Queries**:
```promql
# Overall cache hit ratio
avg(cache_hit_ratio)

# Cache performance by type
avg by (cache_type) (cache_hit_ratio)

# Cache hit trend
rate(cache_hits_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m]))
```

**Labels**: `cache_type`, `endpoint`, `user_id`

---

### `api_errors_total`
**Definition**: Total count of API errors  
**Type**: Counter  
**Unit**: Count  
**Target**: <1% error rate  
**Critical Threshold**: >5% error rate  

**Calculation**:
```
count(http_responses{status_code >= 400})
```

**Technical Impact**:
- System reliability indicator
- User experience quality
- Debugging and maintenance priority

**PromQL Queries**:
```promql
# Error rate percentage
rate(api_errors_total[5m]) / rate(http_request_duration_seconds_count[5m]) * 100

# Errors by endpoint
sum by (endpoint) (rate(api_errors_total[5m]))

# Error types distribution
sum by (error_type) (rate(api_errors_total[5m]))
```

**Labels**: `endpoint`, `status_code`, `error_type`, `method`

---

### `database_connections_active`
**Definition**: Number of active database connections  
**Type**: Gauge  
**Unit**: Count  
**Warning Threshold**: >80% of max connections  

**Calculation**:
```
count(active_database_sessions)
```

**Technical Impact**:
- Database performance indicator
- Resource utilization monitoring
- Scalability bottleneck detection

**PromQL Queries**:
```promql
# Connection pool utilization
database_connections_active / database_connections_total * 100

# Connection usage trend
rate(database_connections_active[5m])

# Idle vs active connections
database_connections_active - database_connections_idle
```

**Labels**: `database`, `pool_name`, `connection_type`

---

## 🔒 Security & Compliance Metrics

### `auth_failures_total`
**Definition**: Total count of authentication failures  
**Type**: Counter  
**Unit**: Count  
**Critical Threshold**: >0.1/second (potential attack)  

**Calculation**:
```
count(login_attempts{status="failed"})
```

**Security Impact**:
- Brute force attack detection
- System security monitoring
- User account protection

**PromQL Queries**:
```promql
# Authentication failure rate
rate(auth_failures_total[5m])

# Failures by source (if IP tracking available)
sum by (source_ip) (increase(auth_failures_total[1h]))

# Failed vs successful authentications
rate(auth_failures_total[5m]) / rate(auth_attempts_total[5m]) * 100
```

**Labels**: `endpoint`, `source_ip`, `user_agent`, `failure_reason`

---

### `gdpr_requests_total`
**Definition**: Total count of GDPR data requests  
**Type**: Counter  
**Unit**: Count  

**Calculation**:
```
count(data_export_requests + data_deletion_requests)
```

**Compliance Impact**:
- Regulatory compliance tracking
- Privacy rights fulfillment
- Legal audit requirements

**PromQL Queries**:
```promql
# GDPR requests by type
sum by (request_type) (increase(gdpr_requests_total[30d]))

# Monthly GDPR request volume
increase(gdpr_requests_total[30d])

# Request processing time
histogram_quantile(0.95, rate(gdpr_processing_duration_seconds_bucket[24h]))
```

**Labels**: `request_type` (export/deletion), `user_id`, `status`

---

### `security_events_total`
**Definition**: Total count of security events  
**Type**: Counter  
**Unit**: Count  

**Calculation**:
```
count(suspicious_activities + blocked_requests + security_violations)
```

**Security Impact**:
- Threat detection and response
- Security posture assessment
- Incident tracking and analysis

**PromQL Queries**:
```promql
# Security events by severity
sum by (severity) (increase(security_events_total[24h]))

# Events by type
sum by (event_type) (increase(security_events_total[24h]))

# Security trend analysis
increase(security_events_total[7d])
```

**Labels**: `event_type`, `severity`, `source_ip`, `user_id`

---

## 💾 System Resource Metrics

### `redis_memory_usage_bytes`
**Definition**: Redis memory consumption in bytes  
**Type**: Gauge  
**Unit**: Bytes  

**Calculation**:
```
redis_info.used_memory
```

**Technical Impact**:
- Cache performance optimization
- Resource allocation planning
- Cost optimization opportunities

**PromQL Queries**:
```promql
# Redis memory usage in MB
redis_memory_usage_bytes / 1024 / 1024

# Memory usage trend
rate(redis_memory_usage_bytes[5m])

# Memory efficiency
redis_memory_usage_bytes / redis_memory_max_bytes * 100
```

**Labels**: `instance`, `database`

---

### `postgres_connections_total`
**Definition**: Total PostgreSQL connections  
**Type**: Gauge  
**Unit**: Count  

**Calculation**:
```
count(pg_stat_activity.pid)
```

**Technical Impact**:
- Database performance monitoring
- Connection pool optimization
- Resource utilization tracking

**PromQL Queries**:
```promql
# Connection utilization
postgres_connections_active / postgres_connections_max * 100

# Connections by state
sum by (state) (postgres_connections_total)

# Idle connection ratio
postgres_connections_idle / postgres_connections_total * 100
```

**Labels**: `state`, `database`, `user`

---

### `system_cpu_usage_percent`
**Definition**: System CPU utilization percentage  
**Type**: Gauge  
**Unit**: Percentage (0-100)  
**Warning Threshold**: >80%  

**Calculation**:
```
(1 - idle_cpu_time / total_cpu_time) * 100
```

**Technical Impact**:
- System performance monitoring
- Scaling decision support
- Resource optimization guidance

**PromQL Queries**:
```promql
# Current CPU usage
avg(system_cpu_usage_percent)

# CPU usage by core
system_cpu_usage_percent by (cpu)

# CPU trend over time
rate(system_cpu_usage_percent[5m])
```

**Labels**: `cpu`, `mode` (user/system/idle)

---

### `system_memory_usage_bytes`
**Definition**: System memory consumption in bytes  
**Type**: Gauge  
**Unit**: Bytes  
**Warning Threshold**: >85% of total memory  

**Calculation**:
```
total_memory - available_memory
```

**Technical Impact**:
- System stability monitoring
- Performance optimization
- Capacity planning support

**PromQL Queries**:
```promql
# Memory usage percentage
system_memory_usage_bytes / system_memory_total_bytes * 100

# Available memory
system_memory_total_bytes - system_memory_usage_bytes

# Memory usage trend
rate(system_memory_usage_bytes[5m])
```

**Labels**: `type` (used/free/cached/buffered)

---

## 🤖 LLM & AI Metrics

### `llm_calls_total`
**Definition**: Total count of LLM API calls  
**Type**: Counter  
**Unit**: Count  

**Calculation**:
```
count(api_requests_to_llm_providers)
```

**Technical Impact**:
- Usage pattern analysis
- Cost prediction and optimization
- Performance bottleneck identification

**PromQL Queries**:
```promql
# LLM calls per minute
rate(llm_calls_total[1m]) * 60

# Calls by provider
sum by (provider) (increase(llm_calls_total[24h]))

# Calls by model
sum by (model) (increase(llm_calls_total[24h]))

# Average calls per user
increase(llm_calls_total[24h]) / count(active_users)
```

**Labels**: `provider`, `model`, `user_id`, `endpoint`, `status`

---

### `llm_request_duration_seconds`
**Definition**: LLM API request duration histogram  
**Type**: Histogram  
**Unit**: Seconds  

**Calculation**:
```
histogram of time from LLM request start to completion
```

**Technical Impact**:
- LLM provider performance comparison
- User experience optimization
- Timeout configuration guidance

**PromQL Queries**:
```promql
# Average LLM response time
rate(llm_request_duration_seconds_sum[5m]) / rate(llm_request_duration_seconds_count[5m])

# 95th percentile by provider
histogram_quantile(0.95, rate(llm_request_duration_seconds_bucket[5m])) by (provider)

# Slowest LLM models
topk(5, histogram_quantile(0.95, rate(llm_request_duration_seconds_bucket[5m])) by (model))
```

**Labels**: `provider`, `model`, `endpoint`, `status`

---

### `llm_tokens_total`
**Definition**: Total count of LLM tokens processed  
**Type**: Counter  
**Unit**: Count  

**Calculation**:
```
sum(input_tokens + output_tokens)
```

**Technical Impact**:
- Cost calculation accuracy
- Usage optimization opportunities
- Model efficiency comparison

**PromQL Queries**:
```promql
# Token usage rate
rate(llm_tokens_total[1h])

# Tokens by type
sum by (token_type) (increase(llm_tokens_total[24h]))

# Average tokens per request
increase(llm_tokens_total[24h]) / increase(llm_calls_total[24h])

# Token cost efficiency
increase(llm_cost_total_eur[24h]) / increase(llm_tokens_total[24h])
```

**Labels**: `provider`, `model`, `token_type` (input/output), `user_id`

---

## 📈 Growth & User Metrics

### `active_users_total`
**Definition**: Number of active users in specified time window  
**Type**: Gauge  
**Unit**: Count  

**Calculation**:
```
count(distinct users with activity in time_window)
```

**Business Impact**:
- Growth tracking and forecasting
- User engagement monitoring
- Market penetration analysis

**PromQL Queries**:
```promql
# Daily active users
active_users_total{time_window="24h"}

# Weekly active users
active_users_total{time_window="7d"}

# Monthly active users
active_users_total{time_window="30d"}

# User growth rate
(active_users_total{time_window="30d"} / active_users_total{time_window="30d"} offset 30d - 1) * 100
```

**Labels**: `time_window`, `plan_type`, `region`

---

### `user_registrations_total`
**Definition**: Total count of user registrations  
**Type**: Counter  
**Unit**: Count  

**Calculation**:
```
count(successful_user_signups)
```

**Business Impact**:
- Growth funnel analysis
- Marketing campaign effectiveness
- Acquisition cost calculation

**PromQL Queries**:
```promql
# Daily registrations
increase(user_registrations_total[24h])

# Registration trend
rate(user_registrations_total[7d])

# Registrations by source
sum by (acquisition_source) (increase(user_registrations_total[24h]))
```

**Labels**: `acquisition_source`, `plan_type`, `region`

---

### `session_duration_seconds`
**Definition**: User session duration histogram  
**Type**: Histogram  
**Unit**: Seconds  

**Calculation**:
```
histogram of time from session start to end
```

**Business Impact**:
- User engagement measurement
- Product stickiness indicator
- Feature usage optimization

**PromQL Queries**:
```promql
# Average session duration
rate(session_duration_seconds_sum[1h]) / rate(session_duration_seconds_count[1h])

# 90th percentile session length
histogram_quantile(0.90, rate(session_duration_seconds_bucket[1h]))

# Session duration by user type
histogram_quantile(0.50, rate(session_duration_seconds_bucket[1h])) by (plan_type)
```

**Labels**: `user_id`, `plan_type`, `device_type`

---

### `feature_usage_total`
**Definition**: Total count of feature usage events  
**Type**: Counter  
**Unit**: Count  

**Calculation**:
```
count(feature_interaction_events)
```

**Business Impact**:
- Feature adoption tracking
- Product development priorities
- User behavior analysis

**PromQL Queries**:
```promql
# Most used features
topk(10, sum by (feature_name) (increase(feature_usage_total[24h])))

# Feature usage by user type
sum by (plan_type) (increase(feature_usage_total[24h]))

# Feature adoption rate
increase(feature_usage_total[7d]) / active_users_total{time_window="7d"}
```

**Labels**: `feature_name`, `user_id`, `plan_type`

---

## 🎯 Key Performance Indicators (KPIs)

### Business KPIs
- **Customer Acquisition Cost (CAC)**: `marketing_spend / new_customers`
- **Customer Lifetime Value (CLV)**: `average_revenue_per_user * average_customer_lifespan`
- **Monthly Recurring Revenue Growth**: `(current_mrr - previous_mrr) / previous_mrr * 100`
- **Churn Rate**: `churned_customers / total_customers * 100`
- **Net Revenue Retention**: `(starting_mrr + expansion - churn - contraction) / starting_mrr * 100`

### Technical KPIs
- **System Availability**: `uptime / total_time * 100`
- **Mean Time to Recovery (MTTR)**: `total_downtime / number_of_incidents`
- **API Success Rate**: `successful_requests / total_requests * 100`
- **Cache Efficiency**: `cache_hits / (cache_hits + cache_misses) * 100`
- **Cost per Request**: `total_infrastructure_cost / total_requests`

### Operational KPIs
- **Alert Response Time**: Time from alert to acknowledgment
- **Incident Resolution Time**: Time from incident start to resolution
- **Deployment Frequency**: Number of deployments per time period
- **Change Failure Rate**: Failed deployments / total deployments * 100

---

## 📊 Metric Collection Architecture

### Collection Methods
- **Application Metrics**: Custom Prometheus metrics from FastAPI app
- **System Metrics**: Node Exporter for system-level metrics
- **Database Metrics**: PostgreSQL Exporter for database performance
- **Cache Metrics**: Redis Exporter for cache performance
- **LLM Metrics**: Custom integration with LLM provider APIs

### Storage and Retention
- **Prometheus Storage**: 30 days retention with 15-second scrape interval
- **Aggregation Rules**: Pre-calculated aggregations for dashboard performance
- **Backup Strategy**: Daily exports for long-term storage and compliance

### Query Performance
- **Dashboards**: Optimized queries with appropriate time ranges
- **Alerting**: Efficient queries with minimal evaluation overhead
- **Automation**: Batch queries for report generation

---

*This metrics glossary ensures consistent understanding and usage of all monitoring data in the PratikoAI system. Regular updates reflect system evolution and business requirement changes.*