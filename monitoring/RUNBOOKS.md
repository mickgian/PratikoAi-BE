# PratikoAI Monitoring Runbooks

Detailed response procedures for each alert in the PratikoAI monitoring system. Each runbook provides investigation steps, resolution procedures, and escalation paths.

## 📋 Runbook Index

### 💰 Cost Alerts
- [High User Cost (>€2.50/month)](#high-user-cost-250month)
- [Daily Cost Spike (>50% increase)](#daily-cost-spike-50-increase)
- [High LLM Daily Cost (>€100/day)](#high-llm-daily-cost-100day)

### 💼 Business Alerts
- [High Payment Failure Rate (>5%)](#high-payment-failure-rate-5)
- [Low MRR Progress (<€20k/month)](#low-mrr-progress-20kmonth)
- [High Subscription Churn (>10%/24h)](#high-subscription-churn-1024h)
- [No New Signups (48 hours)](#no-new-signups-48-hours)

### ⚡ Performance Alerts
- [High API Response Time (>5s)](#high-api-response-time-5s)
- [Low Cache Hit Ratio (<70%)](#low-cache-hit-ratio-70)
- [High Database Connections (>80%)](#high-database-connections-80)
- [High API Error Rate (>5%)](#high-api-error-rate-5)

### 🔒 Security Alerts
- [Multiple Failed Authentication (>0.1/sec)](#multiple-failed-authentication-01sec)
- [Unusual API Usage Pattern](#unusual-api-usage-pattern)
- [GDPR Data Export Request](#gdpr-data-export-request)

---

## 💰 Cost Alerts

### High User Cost (>€2.50/month)

**Alert Severity**: 🔴 Critical  
**Evaluation Time**: 2 minutes  
**Response Time**: Immediate (within 5 minutes)  
**Responsible Team**: Finance + Engineering

#### What This Means
Individual users are costing more than €2.50 per month, exceeding our €2.00 target and threatening profitability. This is a critical business metric that requires immediate attention.

#### Immediate Investigation (5 minutes)

1. **Access Cost Analysis Dashboard**:
   - URL: http://localhost:3000/d/costs/pratikoai-cost-analysis
   - Look for "High Cost Users" table
   - Identify users exceeding €2.50/month

2. **Get Current Cost Data**:
   ```bash
   # Check current average user cost
   curl "http://localhost:9090/api/v1/query?query=avg(user_monthly_cost_eur)"
   
   # Identify top 10 expensive users
   curl "http://localhost:9090/api/v1/query?query=topk(10, user_monthly_cost_eur)"
   
   # Check cost trend over last 24 hours
   curl "http://localhost:9090/api/v1/query_range?query=avg(user_monthly_cost_eur)&start=$(date -d '24 hours ago' +%s)&end=$(date +%s)&step=3600"
   ```

3. **Identify Cost Drivers**:
   ```bash
   # LLM costs by provider for expensive users
   curl "http://localhost:9090/api/v1/query?query=sum by (provider, user_id) (increase(llm_cost_total_eur{user_monthly_cost_eur>2.5}[24h]))"
   
   # API call volume for expensive users  
   curl "http://localhost:9090/api/v1/query?query=sum by (user_id) (increase(http_request_duration_seconds_count{user_monthly_cost_eur>2.5}[24h]))"
   ```

#### Detailed Analysis (15 minutes)

4. **Run Automated Cost Analysis**:
   ```bash
   # Generate detailed cost optimization report
   make monitoring-costs
   
   # Export results for analysis
   python monitoring/scripts/optimize_costs.py --detailed --export cost_crisis_$(date +%Y%m%d_%H%M).json
   ```

5. **Investigate Usage Patterns**:
   - Check for API abuse or excessive usage
   - Review LLM model selection (expensive vs cheap models)
   - Analyze cache hit ratios for expensive users
   - Look for failed requests causing wasteful retries

6. **Business Context Review**:
   - Check if expensive users are on premium plans
   - Review recent feature releases that might increase costs
   - Determine if cost increase is expected (new features) or unexpected (inefficiency)

#### Resolution Steps

**Immediate Actions (if cost >€5/user)**:
1. **Emergency Cost Controls**:
   ```bash
   # Implement temporary usage limits (requires application changes)
   # This is a business decision - contact CEO immediately
   
   # Check if specific users need immediate limits
   curl "http://localhost:9090/api/v1/query?query=user_monthly_cost_eur > 5"
   ```

2. **Contact High-Usage Users**:
   - Send usage optimization recommendations
   - Offer consultation on efficient API usage
   - Consider upgrading to higher-tier plans

**Short-term Fixes (within 1 hour)**:
1. **Optimize LLM Usage**:
   - Switch expensive calls to cheaper models where possible
   - Implement better caching for repeated queries
   - Review prompt engineering for efficiency

2. **Technical Optimizations**:
   ```bash
   # Check cache performance for expensive users
   curl "http://localhost:9090/api/v1/query?query=cache_hit_ratio{user_id=~\"expensive_user_pattern\"}"
   
   # Review error rates (failed requests waste money)
   curl "http://localhost:9090/api/v1/query?query=rate(api_errors_total{user_id=~\"expensive_user_pattern\"}[1h])"
   ```

**Long-term Solutions (within 24 hours)**:
1. **Implement Usage Analytics**:
   - Add per-user cost tracking dashboards
   - Implement usage warnings for users
   - Create cost prediction models

2. **Business Model Adjustments**:
   - Review pricing tiers
   - Implement usage-based billing
   - Add cost-aware feature flags

#### Escalation Path

**Level 1** (0-5 minutes): Finance Team
- Immediate cost analysis
- Contact high-usage users

**Level 2** (5-15 minutes): Engineering + Finance Manager
- Technical optimization implementation
- Emergency cost controls if needed

**Level 3** (15-30 minutes): CEO + CTO
- Business model adjustments
- Strategic decision on cost controls

**Level 4** (30+ minutes): Board notification
- If costs threaten company viability

#### Prevention

1. **Monitoring Improvements**:
   - Lower alert threshold to €2.25 for earlier warning
   - Add predictive cost alerts
   - Implement user-level cost budgets

2. **Technical Improvements**:
   - Better caching strategies
   - More efficient LLM model selection
   - Improved error handling to reduce waste

3. **Business Process**:
   - Regular cost review meetings
   - User education on efficient usage
   - Proactive outreach to high-usage users

---

### Daily Cost Spike (>50% increase)

**Alert Severity**: 🟡 Warning  
**Evaluation Time**: 5 minutes  
**Response Time**: Within 15 minutes  
**Responsible Team**: Finance + Engineering

#### What This Means
Daily LLM costs have increased by more than 50% compared to the previous day, indicating potential inefficiency, increased usage, or system issues.

#### Investigation Steps

1. **Compare Daily Costs**:
   ```bash
   # Today's cost vs yesterday
   curl "http://localhost:9090/api/v1/query?query=increase(llm_cost_total_eur[24h])"
   curl "http://localhost:9090/api/v1/query?query=increase(llm_cost_total_eur[24h] offset 24h)"
   
   # Cost by provider today vs yesterday
   curl "http://localhost:9090/api/v1/query?query=sum by (provider) (increase(llm_cost_total_eur[24h]))"
   ```

2. **Identify Spike Causes**:
   - Check for unusual user activity patterns
   - Review recent deployments or feature releases
   - Look for failed requests causing retries
   - Analyze LLM model usage changes

3. **Usage Pattern Analysis**:
   ```bash
   # API call volume increase
   curl "http://localhost:9090/api/v1/query?query=increase(http_request_duration_seconds_count[24h]) / increase(http_request_duration_seconds_count[24h] offset 24h)"
   
   # New user activity
   curl "http://localhost:9090/api/v1/query?query=increase(active_users_total[24h])"
   ```

#### Resolution
- Determine if spike is justified (more users, new features)
- Implement optimizations if inefficiency detected  
- Monitor trend over next 24 hours
- Adjust alert threshold if new baseline established

---

### High LLM Daily Cost (>€100/day)

**Alert Severity**: 🟡 Warning  
**Evaluation Time**: 10 minutes  
**Response Time**: Within 30 minutes  
**Responsible Team**: Engineering + Finance

#### Investigation Steps
1. **Daily Cost Breakdown**:
   ```bash
   # Total daily LLM costs
   curl "http://localhost:9090/api/v1/query?query=sum(increase(llm_cost_total_eur[24h]))"
   
   # Cost by provider
   curl "http://localhost:9090/api/v1/query?query=sum by (provider) (increase(llm_cost_total_eur[24h]))"
   
   # Cost by model
   curl "http://localhost:9090/api/v1/query?query=sum by (model) (increase(llm_cost_total_eur[24h]))"
   ```

2. **Usage Analysis**:
   - Review LLM call volume and patterns
   - Check for expensive model usage (GPT-4 vs GPT-3.5)
   - Analyze prompt lengths and complexity

#### Resolution
- Optimize expensive LLM calls
- Consider model downgrading for suitable use cases
- Implement better prompt engineering
- Review caching effectiveness

---

## 💼 Business Alerts

### High Payment Failure Rate (>5%)

**Alert Severity**: 🔴 Critical  
**Evaluation Time**: 10 minutes  
**Response Time**: Immediate (within 5 minutes)  
**Responsible Team**: Business + Engineering

#### What This Means
More than 5% of payment transactions are failing, directly impacting revenue collection and customer experience. This requires immediate investigation and resolution.

#### Immediate Investigation (5 minutes)

1. **Check Current Payment Metrics**:
   ```bash
   # Current payment success rate
   curl "http://localhost:9090/api/v1/query?query=rate(payment_operations_total{status=\"succeeded\"}[1h]) / rate(payment_operations_total[1h]) * 100"
   
   # Payment failure rate by type
   curl "http://localhost:9090/api/v1/query?query=sum by (error_type) (rate(payment_operations_total{status=\"failed\"}[1h]))"
   
   # Failed payment volume
   curl "http://localhost:9090/api/v1/query?query=increase(payment_operations_total{status=\"failed\"}[1h])"
   ```

2. **Identify Failure Patterns**:
   - Check failure types (declined, timeout, network)
   - Review affected payment methods
   - Analyze geographic patterns if available
   - Look for time-based patterns

#### Detailed Analysis (15 minutes)

3. **Payment Provider Status**:
   - Check Stripe/payment provider status page
   - Review recent payment processing changes
   - Verify API connectivity and authentication

4. **System Health Check**:
   ```bash
   # Check payment service health
   curl http://localhost:8000/health/payments
   
   # Review payment-related error logs
   docker logs app_container | grep -i payment | tail -50
   
   # Database connectivity for payment records
   docker exec postgres_container psql -U postgres -c "SELECT COUNT(*) FROM payment_transactions WHERE created_at > NOW() - INTERVAL '1 hour';"
   ```

#### Resolution Steps

**Immediate Actions**:
1. **Payment Provider Issues**:
   - Contact payment provider support
   - Switch to backup payment method if available
   - Communicate with customers about payment issues

2. **System Issues**:
   ```bash
   # Restart payment service if unhealthy
   docker restart app_container
   
   # Check database connection pool
   curl "http://localhost:9090/api/v1/query?query=database_connections_active / database_connections_total"
   ```

**Short-term Fixes**:
1. **Implement Retry Logic**:
   - Add automatic retries for transient failures
   - Implement exponential backoff
   - Queue failed payments for retry

2. **Customer Communication**:
   - Notify affected customers
   - Provide alternative payment methods
   - Offer payment support assistance

#### Escalation
- **5 minutes**: Business team + payment processor contact
- **15 minutes**: Engineering team for system issues
- **30 minutes**: Management notification for revenue impact
- **1 hour**: CEO notification if issue persists

---

### Low MRR Progress (<€20k/month)

**Alert Severity**: 🟡 Warning  
**Evaluation Time**: 30 minutes  
**Response Time**: Within 1 hour  
**Responsible Team**: Business + Marketing

#### Investigation Steps
1. **Revenue Analysis**:
   ```bash
   # Current MRR
   curl "http://localhost:9090/api/v1/query?query=sum(monthly_revenue_eur)"
   
   # MRR trend over last 30 days
   curl "http://localhost:9090/api/v1/query_range?query=sum(monthly_revenue_eur)&start=$(date -d '30 days ago' +%s)&end=$(date +%s)&step=86400"
   
   # Active subscriptions
   curl "http://localhost:9090/api/v1/query?query=sum(active_subscriptions_total{status=\"active\"})"
   ```

2. **Growth Factor Analysis**:
   - New subscription rate
   - Churn rate impact
   - Average revenue per user
   - Upgrade/downgrade patterns

#### Resolution
- Review marketing campaigns effectiveness
- Analyze conversion funnel performance
- Implement growth initiatives
- Consider pricing adjustments

---

### High Subscription Churn (>10%/24h)

**Alert Severity**: 🟡 Warning  
**Evaluation Time**: 1 hour  
**Response Time**: Within 2 hours  
**Responsible Team**: Business + Customer Success

#### Investigation Steps
1. **Churn Analysis**:
   ```bash
   # Churn rate calculation
   curl "http://localhost:9090/api/v1/query?query=rate(subscription_churn_total[24h]) / rate(active_subscriptions_total[24h]) * 100"
   
   # Churn reasons if available
   curl "http://localhost:9090/api/v1/query?query=sum by (churn_reason) (increase(subscription_churn_total[24h]))"
   ```

2. **Customer Feedback Review**:
   - Recent support tickets
   - Cancellation feedback
   - Product usage patterns before churn

#### Resolution
- Contact churned customers for feedback
- Implement retention campaigns
- Address common churn reasons
- Improve onboarding and engagement

---

### No New Signups (48 hours)

**Alert Severity**: 🟡 Warning  
**Evaluation Time**: 48 hours  
**Response Time**: Within 4 hours  
**Responsible Team**: Marketing + Growth

#### Investigation Steps
1. **Signup Funnel Analysis**:
   ```bash
   # Signup tracking
   curl "http://localhost:9090/api/v1/query?query=increase(user_registrations_total[48h])"
   
   # Website traffic if available
   curl "http://localhost:9090/api/v1/query?query=increase(website_visits_total[48h])"
   ```

2. **Marketing Channel Review**:
   - Check marketing campaign status
   - Review SEO performance
   - Analyze social media engagement
   - Verify signup form functionality

#### Resolution
- Test signup process end-to-end
- Review marketing spend and targeting
- Check for technical issues in signup flow
- Implement promotional campaigns if needed

---

## ⚡ Performance Alerts

### High API Response Time (>5s)

**Alert Severity**: 🔴 Critical  
**Evaluation Time**: 2 minutes  
**Response Time**: Immediate (within 2 minutes)  
**Responsible Team**: Engineering

#### What This Means
API response times exceed our 5-second SLA, directly impacting user experience and potentially causing timeouts or customer dissatisfaction.

#### Immediate Investigation (2 minutes)

1. **Check Current Response Times**:
   ```bash
   # Current 95th percentile response time
   curl "http://localhost:9090/api/v1/query?query=histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"
   
   # Slowest endpoints
   curl "http://localhost:9090/api/v1/query?query=topk(5, histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])))"
   
   # Error rate correlation
   curl "http://localhost:9090/api/v1/query?query=rate(api_errors_total[5m]) / rate(http_request_duration_seconds_count[5m]) * 100"
   ```

2. **System Resource Check**:
   ```bash
   # CPU usage
   curl "http://localhost:9090/api/v1/query?query=rate(process_cpu_seconds_total[5m]) * 100"
   
   # Memory usage
   curl "http://localhost:9090/api/v1/query?query=process_resident_memory_bytes"
   
   # Database connections
   curl "http://localhost:9090/api/v1/query?query=database_connections_active / database_connections_total * 100"
   ```

#### Detailed Analysis (10 minutes)

3. **Database Performance**:
   ```bash
   # Check database slow queries
   docker exec postgres_container psql -U postgres -c "
   SELECT query, mean_time, calls, total_time 
   FROM pg_stat_statements 
   ORDER BY mean_time DESC 
   LIMIT 10;"
   
   # Active database connections
   docker exec postgres_container psql -U postgres -c "
   SELECT count(*), state 
   FROM pg_stat_activity 
   GROUP BY state;"
   ```

4. **Application Analysis**:
   ```bash
   # Check application logs for errors
   docker logs app_container --tail=100 | grep -i error
   
   # LLM provider response times
   curl "http://localhost:9090/api/v1/query?query=histogram_quantile(0.95, rate(llm_request_duration_seconds_bucket[5m]))"
   ```

#### Resolution Steps

**Immediate Actions (if response time >30s)**:
1. **Emergency Restart**:
   ```bash
   # Restart application
   docker restart app_container
   
   # Verify restart
   curl http://localhost:8000/health
   ```

2. **Load Balancing** (if available):
   - Route traffic to healthy instances
   - Scale horizontally if possible

**Short-term Fixes**:
1. **Database Optimization**:
   ```bash
   # Kill long-running queries if safe
   docker exec postgres_container psql -U postgres -c "
   SELECT pg_terminate_backend(pid) 
   FROM pg_stat_activity 
   WHERE state = 'active' 
   AND query_start < NOW() - INTERVAL '5 minutes';"
   ```

2. **Cache Optimization**:
   ```bash
   # Check Redis performance
   docker exec redis_container redis-cli info stats
   
   # Clear cache if corrupted
   docker exec redis_container redis-cli flushdb
   ```

**Long-term Solutions**:
1. **Query Optimization**:
   - Add database indexes for slow queries
   - Optimize N+1 query problems
   - Implement database connection pooling

2. **Caching Improvements**:
   - Add application-level caching
   - Implement CDN for static content
   - Optimize cache key strategies

#### Escalation
- **2 minutes**: Engineering team immediate response
- **10 minutes**: Senior engineering if not resolved
- **30 minutes**: CTO notification
- **1 hour**: Customer communication if ongoing

---

### Low Cache Hit Ratio (<70%)

**Alert Severity**: 🟡 Warning  
**Evaluation Time**: 5 minutes  
**Response Time**: Within 15 minutes  
**Responsible Team**: Engineering

#### Investigation Steps
1. **Cache Performance Analysis**:
   ```bash
   # Current cache hit ratio
   curl "http://localhost:9090/api/v1/query?query=cache_hit_ratio * 100"
   
   # Cache operations volume
   curl "http://localhost:9090/api/v1/query?query=rate(cache_operations_total[5m])"
   
   # Cache by type
   curl "http://localhost:9090/api/v1/query?query=sum by (cache_type) (cache_hit_ratio)"
   ```

2. **Redis Health Check**:
   ```bash
   # Redis memory usage
   curl "http://localhost:9090/api/v1/query?query=redis_memory_usage_bytes"
   
   # Redis connection info
   docker exec redis_container redis-cli info clients
   ```

#### Resolution
- Analyze cache key patterns
- Optimize TTL settings
- Increase cache memory if needed
- Review cache invalidation strategy

---

### High Database Connections (>80%)

**Alert Severity**: 🟡 Warning  
**Evaluation Time**: 5 minutes  
**Response Time**: Within 10 minutes  
**Responsible Team**: Engineering

#### Investigation Steps
1. **Connection Pool Analysis**:
   ```bash
   # Current connection usage
   curl "http://localhost:9090/api/v1/query?query=database_connections_active / database_connections_total * 100"
   
   # Connection pool settings
   docker exec postgres_container psql -U postgres -c "SHOW max_connections;"
   ```

2. **Active Connection Review**:
   ```bash
   # Active connections by state
   docker exec postgres_container psql -U postgres -c "
   SELECT state, count(*) 
   FROM pg_stat_activity 
   GROUP BY state;"
   
   # Long-running connections
   docker exec postgres_container psql -U postgres -c "
   SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
   FROM pg_stat_activity 
   WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';"
   ```

#### Resolution
- Kill idle connections if safe
- Optimize connection pool settings
- Review application connection handling
- Consider connection pooling improvements

---

### High API Error Rate (>5%)

**Alert Severity**: 🔴 Critical  
**Evaluation Time**: 2 minutes  
**Response Time**: Immediate (within 5 minutes)  
**Responsible Team**: Engineering

#### Investigation Steps
1. **Error Analysis**:
   ```bash
   # Current error rate
   curl "http://localhost:9090/api/v1/query?query=rate(api_errors_total[5m]) / rate(http_request_duration_seconds_count[5m]) * 100"
   
   # Errors by endpoint
   curl "http://localhost:9090/api/v1/query?query=sum by (endpoint) (rate(api_errors_total[5m]))"
   
   # Error types
   curl "http://localhost:9090/api/v1/query?query=sum by (error_type) (rate(api_errors_total[5m]))"
   ```

2. **Log Analysis**:
   ```bash
   # Recent error logs
   docker logs app_container --tail=100 | grep -i error
   
   # Error patterns
   docker logs app_container | grep "$(date +'%Y-%m-%d %H:')" | grep -c ERROR
   ```

#### Resolution
- Identify error patterns and root causes
- Fix application bugs causing errors
- Implement better error handling
- Add circuit breakers for external services

---

## 🔒 Security Alerts

### Multiple Failed Authentication (>0.1/sec)

**Alert Severity**: 🔴 Critical  
**Evaluation Time**: 1 minute  
**Response Time**: Immediate (within 2 minutes)  
**Responsible Team**: Security + Engineering

#### What This Means
Authentication failures are occurring at a rate that suggests a brute force attack or system issue requiring immediate security response.

#### Immediate Investigation (2 minutes)

1. **Authentication Failure Analysis**:
   ```bash
   # Current failure rate
   curl "http://localhost:9090/api/v1/query?query=rate(auth_failures_total[5m])"
   
   # Failure patterns by endpoint
   curl "http://localhost:9090/api/v1/query?query=sum by (endpoint) (rate(auth_failures_total[5m]))"
   
   # If source IP tracking available
   curl "http://localhost:9090/api/v1/query?query=topk(10, sum by (source_ip) (increase(auth_failures_total[1h])))"
   ```

2. **Attack Pattern Detection**:
   - Check for distributed vs single-source attacks
   - Analyze timing patterns
   - Review attempted usernames/emails
   - Look for user enumeration attempts

#### Resolution Steps

**Immediate Actions**:
1. **IP Blocking** (if single source):
   ```bash
   # Block suspicious IPs at firewall level
   # This requires infrastructure access
   iptables -A INPUT -s SUSPICIOUS_IP -j DROP
   ```

2. **Rate Limiting Enhancement**:
   - Implement stricter rate limits
   - Add CAPTCHA for repeated failures
   - Temporary account lockouts

**Investigation**:
1. **Log Analysis**:
   ```bash
   # Authentication logs
   docker logs app_container | grep -i "auth" | grep -i "fail" | tail -50
   
   # Pattern analysis
   docker logs app_container | grep "$(date +'%Y-%m-%d %H:')" | grep -c "auth.*fail"
   ```

2. **System Health**:
   - Verify authentication service is functioning
   - Check for recent security updates
   - Review user account status

#### Escalation
- **2 minutes**: Security team notification
- **5 minutes**: Engineering team if system issue
- **15 minutes**: Management notification
- **30 minutes**: Consider public security advisory

---

### Unusual API Usage Pattern

**Alert Severity**: 🟡 Warning  
**Evaluation Time**: 10 minutes  
**Response Time**: Within 30 minutes  
**Responsible Team**: Security + Engineering

#### Investigation Steps
1. **Usage Pattern Analysis**:
   ```bash
   # API call volume spikes
   curl "http://localhost:9090/api/v1/query?query=increase(http_request_duration_seconds_count[1h]) / increase(http_request_duration_seconds_count[1h] offset 1h)"
   
   # Unusual endpoint access
   curl "http://localhost:9090/api/v1/query?query=topk(10, sum by (endpoint) (increase(http_request_duration_seconds_count[1h])))"
   ```

2. **User Behavior Analysis**:
   - Check for automated/bot-like behavior
   - Review API key usage patterns
   - Analyze geographic access patterns

#### Resolution
- Investigate suspicious patterns
- Implement additional monitoring
- Contact users with unusual patterns
- Consider temporary rate limiting

---

### GDPR Data Export Request

**Alert Severity**: 📝 Info  
**Evaluation Time**: Immediate  
**Response Time**: Within 1 hour  
**Responsible Team**: Compliance + Legal

#### Investigation Steps
1. **Request Validation**:
   - Verify user identity
   - Confirm request authenticity
   - Check legal requirements

2. **Data Collection Preparation**:
   ```bash
   # User data query preparation
   docker exec postgres_container psql -U postgres -c "
   SELECT table_name 
   FROM information_schema.tables 
   WHERE table_schema = 'public' 
   AND table_name LIKE '%user%';"
   ```

#### Resolution
- Generate user data export
- Verify data completeness
- Secure transmission to user
- Document compliance actions

---

## 🆘 Emergency Procedures

### Complete System Failure

**When**: All dashboards show red, multiple critical alerts

**Immediate Actions** (2 minutes):
1. **System Status Check**:
   ```bash
   # Check all services
   docker ps -a
   
   # Check system resources
   free -h && df -h
   
   # Check network connectivity
   ping google.com
   ```

2. **Emergency Restart**:
   ```bash
   # Nuclear option - restart everything
   make monitoring-stop
   make docker-compose-down
   make docker-compose-up ENV=production
   make monitoring-start
   ```

### Data Corruption

**When**: Metrics showing impossible values, dashboard errors

**Actions**:
1. **Backup Current State**:
   ```bash
   make monitoring-backup
   ```

2. **Data Integrity Check**:
   ```bash
   # Check Prometheus data
   curl "http://localhost:9090/api/v1/query?query=up"
   
   # Check database
   docker exec postgres_container psql -U postgres -c "SELECT COUNT(*) FROM pg_tables;"
   ```

3. **Recovery**:
   - Restore from latest backup if needed
   - Restart data collection services
   - Verify metrics collection resumed

### Contact Escalation Matrix

| Severity | Time | Contact | Method |
|----------|------|---------|--------|
| Critical | 0-2 min | Engineering Oncall | Phone + Slack |
| Critical | 2-10 min | Engineering Manager | Phone + Email |
| Critical | 10-30 min | CTO | Phone |
| Critical | 30+ min | CEO | Phone |
| Warning | 0-30 min | Team Lead | Slack |
| Warning | 30-60 min | Manager | Email |
| Info | As needed | Team | Slack |

---

*These runbooks ensure rapid and effective response to all monitoring alerts in the PratikoAI system. Keep this documentation updated as systems evolve and new learnings emerge from incident responses.*