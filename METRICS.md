# PratikoAI Prometheus Metrics Documentation

This document lists all available Prometheus metrics for the PratikoAI monitoring dashboard. Metrics are organized by category for easier navigation.

## 📊 Cost Metrics
Track LLM provider costs and user spending to maintain profitability.

### `llm_cost_total_eur`
- **Type**: Counter
- **Description**: Total LLM API costs in EUR by provider and model
- **Labels**: `provider`, `model`, `user_id`
- **Target**: Monitor to keep cost per user <€2/month

### `user_monthly_cost_eur`
- **Type**: Gauge
- **Description**: Current monthly cost per user in EUR (target <2.00)
- **Labels**: `user_id`, `plan_type`
- **Target**: <€2.00 per user per month

### `api_calls_total`
- **Type**: Counter
- **Description**: Total API calls by provider and success status
- **Labels**: `provider`, `model`, `status`

## ⚡ Performance Metrics
Track response times and system efficiency.

### `http_request_duration_seconds`
- **Type**: Histogram
- **Description**: HTTP request latency in seconds
- **Labels**: `method`, `endpoint`, `status_code`
- **Buckets**: 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, +Inf

### `cache_hit_ratio`
- **Type**: Gauge
- **Description**: Cache hit ratio (0.0-1.0, target >0.8)
- **Labels**: `cache_type` (`llm_responses`, `conversations`, `embeddings`)
- **Target**: >0.8 hit ratio

### `active_users_total`
- **Type**: Gauge
- **Description**: Number of currently active users
- **Labels**: `time_window` (`5m`, `1h`, `24h`)

## 💰 Business Metrics
Track revenue and growth toward €25k ARR target.

### `active_subscriptions_total`
- **Type**: Gauge
- **Description**: Number of active paid subscriptions (target 50)
- **Labels**: `subscription_type`, `status` (`active`, `trial`, `cancelled`)
- **Target**: 50 active subscriptions for €25k ARR

### `monthly_revenue_eur`
- **Type**: Gauge
- **Description**: Monthly Recurring Revenue in EUR (target 25000)
- **Labels**: `currency` (always `EUR`)
- **Target**: €25,000 MRR

### `trial_conversions_total`
- **Type**: Counter
- **Description**: Number of trial to paid conversions
- **Labels**: `conversion_type`, `plan_type`

## 🔧 System Metrics
Track infrastructure health and resource usage.

### `database_connections_active`
- **Type**: Gauge
- **Description**: Number of active database connections
- **Labels**: `database_type`, `status`

### `redis_memory_usage_bytes`
- **Type**: Gauge
- **Description**: Redis memory usage in bytes
- **Labels**: `instance`

### `llm_errors_total`
- **Type**: Counter
- **Description**: LLM provider errors by type
- **Labels**: `provider`, `error_type`, `model`

### `process_memory_bytes`
- **Type**: Gauge
- **Description**: Process memory usage in bytes
- **Labels**: `type` (`rss`, `vms`, `shared`)

### `cpu_usage_percent`
- **Type**: Gauge
- **Description**: CPU usage percentage

## 🇮🇹 Italian Tax Operations
Business-specific metrics for PratikoAI/NormoAI tax calculations.

### `italian_tax_calculations_total`
- **Type**: Counter
- **Description**: Total Italian tax calculations performed
- **Labels**: `calculation_type`, `status`, `user_id`
- **Usage**: Track tax calculation volume and success rates

### `italian_tax_amount_calculated_eur`
- **Type**: Counter
- **Description**: Total tax amounts calculated in EUR
- **Labels**: `calculation_type`, `tax_year`
- **Usage**: Monitor financial impact of tax calculations

## 📄 Document Processing
Track document processing operations and performance.

### `document_processing_operations_total`
- **Type**: Counter
- **Description**: Total document processing operations
- **Labels**: `operation_type`, `document_type`, `status`

### `document_processing_duration_seconds`
- **Type**: Histogram
- **Description**: Document processing duration in seconds
- **Labels**: `operation_type`, `document_type`
- **Buckets**: 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, +Inf

## 🔍 Knowledge Base Queries
Monitor knowledge base performance and search effectiveness.

### `knowledge_base_queries_total`
- **Type**: Counter
- **Description**: Total knowledge base queries
- **Labels**: `query_type`, `source`, `status`

### `knowledge_base_query_duration_seconds`
- **Type**: Histogram
- **Description**: Knowledge base query duration in seconds
- **Labels**: `query_type`, `source`
- **Buckets**: 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, +Inf

### `knowledge_base_results_found`
- **Type**: Histogram
- **Description**: Number of results found in knowledge base queries
- **Labels**: `query_type`, `source`
- **Buckets**: 0, 1, 5, 10, 25, 50, 100, +Inf

## 💳 Payment Operations
Track payment processing and financial transactions.

### `payment_operations_total`
- **Type**: Counter
- **Description**: Total payment operations
- **Labels**: `operation_type`, `payment_method`, `status`

### `payment_amount_processed_eur`
- **Type**: Counter
- **Description**: Total payment amounts processed in EUR
- **Labels**: `operation_type`, `currency`

### `payment_operation_duration_seconds`
- **Type**: Histogram
- **Description**: Payment operation duration in seconds
- **Labels**: `operation_type`, `payment_method`
- **Buckets**: 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, +Inf

## ❌ Error Tracking
Categorized API error monitoring for better debugging.

### `api_errors_total`
- **Type**: Counter
- **Description**: Total API errors by category and type
- **Labels**: `error_category`, `error_type`, `endpoint`, `status_code`
- **Usage**: Identify error patterns and failure points

## 👥 User Activity
Track user engagement and feature usage.

### `user_actions_total`
- **Type**: Counter
- **Description**: Total user actions performed
- **Labels**: `action_type`, `feature`, `user_type`
- **Usage**: Monitor feature adoption and user engagement

## ℹ️ System Information
Static system information for context.

### `pratikoai_system_info`
- **Type**: Info
- **Description**: System information
- **Labels**: `version`, `environment`, `python_version`, `project_name`

## 📈 Key Performance Indicators (KPIs)

### Financial KPIs
- **Target MRR**: €25,000 (tracked via `monthly_revenue_eur`)
- **Target Active Subscriptions**: 50 (tracked via `active_subscriptions_total`)
- **Target Cost per User**: <€2/month (tracked via `user_monthly_cost_eur`)
- **Revenue per User**: €69/month (calculated from active subscriptions)

### Performance KPIs
- **Cache Hit Ratio**: >80% (tracked via `cache_hit_ratio`)
- **API Response Time**: <2s p95 (tracked via `http_request_duration_seconds`)
- **System Uptime**: >99.9% (tracked via health checks)

### Business KPIs
- **Trial Conversion Rate**: Track via `trial_conversions_total` vs trial starts
- **Monthly Active Users**: Track via `active_users_total` with 24h window
- **Document Processing Success**: >95% success rate via `document_processing_operations_total`

## 🔧 Metric Collection Integration

### Automatic Collection
Most metrics are automatically collected via:
- **PrometheusMiddleware**: HTTP request metrics
- **System metrics**: Memory, CPU usage updated on every metrics export
- **Business metrics**: Updated by StripeService for subscription/revenue data

### Manual Tracking
Use these helper functions in your code:

```python
from app.core.monitoring.metrics import (
    track_llm_cost, track_italian_tax_calculation,
    track_document_processing, track_knowledge_base_query,
    track_payment_operation, track_api_error, track_user_action
)

# Example usage
track_llm_cost("openai", "gpt-4o-mini", user_id, 0.02)
track_italian_tax_calculation("income_tax", "success", user_id, 1250.0, "2024")
track_payment_operation("subscription", "card", "success", 69.0, 2.1)
```

## 📊 Grafana Dashboard Recommendations

### Dashboard 1: Business Overview
- Monthly Revenue vs Target (€25k)
- Active Subscriptions vs Target (50)
- Trial Conversion Funnel
- Cost per User vs Target (€2)

### Dashboard 2: System Performance
- HTTP Request Duration Percentiles
- Cache Hit Ratios by Type
- Active Users Timeline
- Error Rates by Endpoint

### Dashboard 3: Financial Monitoring
- LLM Costs by Provider/Model
- Payment Processing Volume
- Revenue Trends
- Cost Optimization Opportunities

### Dashboard 4: Italian Tax Operations
- Tax Calculation Volume
- Processing Success Rates
- Average Calculation Values
- User Engagement with Tax Features

## 🚨 Alerting Rules

### Critical Alerts
- Monthly cost per user >€2.50
- API error rate >5%
- System memory usage >80%
- Database connection failures

### Warning Alerts  
- Cache hit ratio <70%
- API response time p95 >5s
- LLM error rate >2%
- Failed payment operations

### Business Alerts
- MRR growth stalled for 7 days
- Trial conversion rate <10%
- Active subscription churn >5%

## 📍 Metrics Endpoint

Access all metrics at: `GET /metrics`

The endpoint combines both default Prometheus metrics and PratikoAI custom metrics for comprehensive monitoring coverage.