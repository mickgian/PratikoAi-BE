# PratikoAI Alert Management System

This document provides comprehensive runbooks for all PratikoAI monitoring alerts, including response procedures, escalation paths, and resolution steps.

## 🚨 Alert Overview

### Alert Classification
- **Critical**: Immediate action required, affects user experience or business revenue
- **Warning**: Attention needed within business hours, may impact performance  
- **Info**: Informational alerts for compliance or audit purposes

### Team Responsibilities
- **Finance Team**: Cost alerts, budget management
- **Business Team**: Revenue, payments, customer metrics
- **Engineering Team**: Performance, reliability, technical issues
- **Security Team**: Authentication, access, threat detection
- **Growth Team**: User acquisition, conversion metrics
- **Compliance Team**: GDPR, regulatory requirements

## 💰 COST ALERTS

### 🔴 CRITICAL: User Cost Exceeds €2.50 Target
**Alert ID**: `high_user_cost`  
**Threshold**: Average user cost >€2.50/month  
**Evaluation**: 2 minutes

**Immediate Actions**:
1. Check LLM usage patterns in cost dashboard
2. Identify high-cost users in user metrics
3. Review recent feature releases that might increase usage
4. Implement emergency cost controls if necessary

**Investigation Steps**:
```bash
# Check current user costs
curl 'http://localhost:9090/api/v1/query?query=user_monthly_cost_eur'

# Identify expensive operations
curl 'http://localhost:9090/api/v1/query?query=topk(10,sum by (user_id)(llm_cost_total_eur))'

# Check LLM provider breakdown
curl 'http://localhost:9090/api/v1/query?query=sum by (provider)(rate(llm_cost_total_eur[1h]))'
```

**Resolution**:
- Implement user-specific rate limiting
- Optimize expensive LLM operations
- Consider tiered pricing adjustments
- Review and update cost monitoring thresholds

**Escalation**: Finance Director if cost >€3.00/user

---

### 🟡 WARNING: Daily Cost Spike >50%
**Alert ID**: `daily_cost_spike`  
**Threshold**: Daily cost increase >50% vs previous day  
**Evaluation**: 5 minutes

**Investigation**:
1. Compare today's usage patterns with historical data
2. Check for unusual user behavior or bot activity
3. Review recent deployments or feature changes
4. Analyze LLM provider cost changes

**Resolution**:
- Investigate root cause of increased usage
- Implement temporary usage limits if needed
- Review pricing from LLM providers
- Document findings for future prevention

---

### 🟡 WARNING: Daily LLM Costs Exceed €100
**Alert ID**: `high_llm_daily_cost`  
**Threshold**: Daily LLM costs >€100  
**Evaluation**: 10 minutes

**Response**:
1. Check which providers are driving costs
2. Review high-volume users and their usage patterns
3. Analyze if costs are justified by user activity
4. Consider switching to cheaper models for non-critical operations

## 💼 BUSINESS ALERTS

### 🔴 CRITICAL: Payment Failure Rate >5%
**Alert ID**: `high_payment_failure_rate`  
**Threshold**: Payment failures >5% over 1 hour  
**Evaluation**: 10 minutes

**Immediate Actions**:
1. Check Stripe dashboard for payment processor issues
2. Review payment method distribution (card vs other)
3. Check for geographic patterns in failures
4. Verify webhook processing is working

**Investigation**:
```bash
# Check payment status breakdown
curl 'http://localhost:9090/api/v1/query?query=sum by (status)(rate(payment_operations_total[1h]))'

# Check payment methods
curl 'http://localhost:9090/api/v1/query?query=sum by (payment_method_type)(rate(payment_operations_total{status="failed"}[1h]))'
```

**Resolution**:
- Contact payment processor if widespread issues
- Review and update payment retry logic
- Check for expired payment methods requiring updates
- Implement backup payment processors if needed

**Escalation**: Business Director and Finance within 30 minutes

---

### 🟡 WARNING: MRR Below €20k Target
**Alert ID**: `low_mrr_progress`  
**Threshold**: Monthly revenue <€20k  
**Evaluation**: 30 minutes

**Analysis**:
1. Review subscription trends and churn rates
2. Check conversion rates from trials to paid
3. Analyze pricing tier distribution
4. Review recent marketing campaigns

**Actions**:
- Accelerate growth initiatives
- Review pricing strategy
- Implement customer retention campaigns
- Analyze competitive positioning

---

### 🟡 WARNING: High Subscription Churn >10%
**Alert ID**: `high_subscription_churn`  
**Threshold**: Churn rate >10% over 24 hours  
**Evaluation**: 1 hour

**Investigation**:
1. Identify which subscription tiers have highest churn
2. Review recent user feedback and support tickets
3. Check for technical issues affecting user experience
4. Analyze churn timing patterns

**Response**:
- Implement customer retention outreach
- Review product roadmap priorities
- Analyze exit interviews and feedback
- Consider targeted discounts or feature updates

---

### 🟡 WARNING: No New Signups for 48 Hours
**Alert ID**: `no_new_signups`  
**Threshold**: Zero new users for 48 hours  
**Evaluation**: 2 hours

**Checks**:
1. Verify signup flow is working correctly
2. Check marketing campaign status
3. Review website analytics and traffic sources
4. Test registration process end-to-end

**Actions**:
- Fix any technical issues in signup flow
- Review and restart marketing campaigns
- Check for SEO or advertising issues
- Analyze competitive landscape changes

## ⚡ PERFORMANCE ALERTS

### 🔴 CRITICAL: API Response Time >5 Seconds
**Alert ID**: `high_api_response_time`  
**Threshold**: 95th percentile >5 seconds  
**Evaluation**: 2 minutes

**Immediate Response**:
1. Check system resource usage (CPU, memory, disk)
2. Review slow query logs in database
3. Check LLM provider response times
4. Verify cache performance

**Investigation**:
```bash
# Check slowest endpoints
curl 'http://localhost:9090/api/v1/query?query=topk(5,histogram_quantile(0.95,rate(http_request_duration_seconds_bucket[5m])))'

# Check database performance
curl 'http://localhost:9090/api/v1/query?query=pg_stat_activity_count'

# Check cache hit ratios
curl 'http://localhost:9090/api/v1/query?query=cache_hit_ratio'
```

**Resolution**:
- Scale application instances if needed
- Optimize slow database queries
- Implement caching for expensive operations
- Review and optimize LLM calls

**Escalation**: Engineering Manager within 15 minutes if not resolved

---

### 🟡 WARNING: Cache Hit Ratio <70%
**Alert ID**: `low_cache_hit_ratio`  
**Threshold**: Cache efficiency <70%  
**Evaluation**: 5 minutes

**Analysis**:
1. Check which cache types are underperforming
2. Review cache key patterns and TTL settings
3. Analyze cache memory usage and eviction rates
4. Check for cache invalidation issues

**Resolution**:
- Adjust cache TTL settings
- Increase cache memory allocation
- Optimize cache key strategies
- Review cache warming procedures

---

### 🟡 WARNING: High Database Connections >80%
**Alert ID**: `high_database_connections`  
**Threshold**: >80% of connection pool  
**Evaluation**: 5 minutes

**Actions**:
1. Check for connection leaks in application code
2. Review long-running queries
3. Analyze connection pool configuration
4. Check for database deadlocks or blocking

**Resolution**:
- Increase connection pool size if appropriate
- Fix connection leaks in application
- Optimize long-running queries
- Implement connection monitoring

---

### 🔴 CRITICAL: API Error Rate >5%
**Alert ID**: `high_error_rate`  
**Threshold**: Error rate >5% over 5 minutes  
**Evaluation**: 2 minutes

**Response**:
1. Check error types and affected endpoints
2. Review application logs for error details
3. Check database connectivity and health
4. Verify external service dependencies

**Investigation**:
```bash
# Check error breakdown
curl 'http://localhost:9090/api/v1/query?query=sum by (error_category)(rate(api_errors_total[5m]))'

# Check affected endpoints
curl 'http://localhost:9090/api/v1/query?query=sum by (endpoint)(rate(api_errors_total[5m]))'
```

## 🔒 SECURITY ALERTS

### 🔴 CRITICAL: Multiple Failed Authentication Attempts
**Alert ID**: `multiple_failed_auth`  
**Threshold**: Auth failures >0.1/sec over 5 minutes  
**Evaluation**: 1 minute

**Immediate Actions**:
1. Check source IPs for failed attempts
2. Review authentication logs for patterns
3. Implement IP-based rate limiting if needed
4. Check for credential stuffing attacks

**Investigation**:
```bash
# Check authentication error rate
curl 'http://localhost:9090/api/v1/query?query=rate(api_errors_total{error_category="authentication"}[5m])'

# Check user patterns
curl 'http://localhost:9090/api/v1/query?query=topk(10,sum by (user_id)(rate(api_errors_total{error_category="authentication"}[5m])))'
```

**Response**:
- Implement temporary IP blocking for suspicious sources
- Enable additional authentication monitoring
- Review and strengthen password policies
- Consider implementing CAPTCHA or MFA

**Escalation**: Security team lead immediately

---

### 🟡 WARNING: Unusual API Usage Pattern
**Alert ID**: `unusual_api_usage`  
**Threshold**: Request rate >100 req/sec  
**Evaluation**: 5 minutes

**Analysis**:
1. Check request patterns by endpoint and user
2. Review geographic distribution of requests
3. Analyze user agent strings for bot activity
4. Check for legitimate traffic spikes vs attacks

**Actions**:
- Implement rate limiting if needed
- Block suspicious traffic patterns
- Review legitimate high-usage customers
- Update monitoring thresholds if needed

---

### ℹ️ INFO: GDPR Data Export Request
**Alert ID**: `gdpr_data_export_request`  
**Threshold**: Any data export request  
**Evaluation**: Immediate

**Compliance Actions**:
1. Log the request for audit purposes
2. Initiate 30-day compliance timeline
3. Gather all user data across systems
4. Prepare data export package

**Process**:
- Acknowledge request within 48 hours
- Complete data export within 30 days
- Verify user identity before processing
- Document completion for compliance records

## 🔧 ALERT TESTING

### Test Scenarios

#### Cost Alert Testing
```bash
# Simulate high user cost (development only)
curl -X POST http://localhost:8000/test/metrics \
  -d '{"metric": "user_monthly_cost_eur", "value": 3.0}'

# Expected: Email alert within 2 minutes
```

#### Performance Alert Testing
```bash
# Test high API response time
curl -X POST http://localhost:8000/test/slow \
  -d '{"delay_seconds": 6}'

# Expected: Critical alert within 2 minutes
```

#### Security Alert Testing
```bash
# Test failed authentication
for i in {1..20}; do
  curl -X POST http://localhost:8000/auth/login \
    -d '{"username": "test", "password": "wrong"}'
done

# Expected: Security alert within 1 minute
```

## 📊 ALERT DASHBOARD ACCESS

### Grafana Dashboards
- **Alert Management**: http://localhost:3000/d/alerts
- **Cost Monitoring**: http://localhost:3000/d/costs  
- **Business KPIs**: http://localhost:3000/d/business
- **Performance**: http://localhost:3000/d/performance

### Alert Channels
- **Email**: admin@pratikoai.com, alerts@pratikoai.com
- **Slack**: #pratikoai-alerts channel
- **Webhook**: Custom integrations via http://localhost:3001/alerts
- **PagerDuty**: Critical alerts only

## 📞 ESCALATION PROCEDURES

### Critical Alerts (Immediate Response)
1. **Engineering**: On-call engineer via PagerDuty
2. **Business**: Business Director + Finance Director
3. **Security**: Security team lead + Engineering Manager

### Warning Alerts (Business Hours)
1. **First Response**: Responsible team lead
2. **Escalation**: Department manager if not resolved in 2 hours
3. **Executive**: C-level if customer impact or revenue loss

### Response Time SLAs
- **Critical**: 15 minutes acknowledgment, 1 hour resolution
- **Warning**: 2 hours acknowledgment, 1 business day resolution
- **Info**: 1 business day acknowledgment, as needed resolution

## 📝 ALERT MAINTENANCE

### Weekly Review
- Review alert frequency and accuracy
- Update thresholds based on business growth
- Check notification channel effectiveness
- Review resolution time metrics

### Monthly Optimization
- Analyze false positive rates
- Update runbooks based on new scenarios
- Review team response procedures
- Update escalation contacts

### Quarterly Assessment
- Review business threshold alignment
- Update cost targets based on growth
- Assess monitoring coverage gaps
- Plan monitoring system improvements