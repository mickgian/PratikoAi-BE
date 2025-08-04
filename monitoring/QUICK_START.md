# PratikoAI Monitoring Quick Start Guide

Get up and running with PratikoAI's monitoring system in 15 minutes. This guide covers the essentials for daily monitoring operations.

## 🚀 5-Minute Setup

### 1. Access the Monitoring Stack

```bash
# Start monitoring stack
make monitoring-start

# Verify all services are running
docker ps | grep -E "(prometheus|grafana|redis|postgres)"
```

### 2. Open Key Dashboards

**Bookmark these URLs:**
- 📊 **Main Dashboard**: http://localhost:3000/d/overview/pratikoai-system-overview
- 💰 **Cost Analysis**: http://localhost:3000/d/costs/pratikoai-cost-analysis  
- 💼 **Business Metrics**: http://localhost:3000/d/business/pratikoai-business-metrics
- ⚡ **Performance**: http://localhost:3000/d/performance/pratikoai-performance

**Default Login**: `admin` / `admin`

### 3. Quick Health Check

```bash
# Run automated health check
make monitoring-health

# Check key metrics manually
curl http://localhost:8000/metrics | grep -E "(user_monthly_cost|monthly_revenue|http_request_duration)"
```

## 📊 Understanding the Dashboards

### System Overview Dashboard
**Your daily starting point** - Executive summary of all key metrics

#### 🟢 **Green Status** (Good)
- User cost: <€2.00/month
- API response: <2 seconds
- Error rate: <1%
- All services: UP

#### 🟡 **Yellow Status** (Warning)
- User cost: €2.00-€2.50/month
- API response: 2-5 seconds  
- Error rate: 1-5%
- Some service issues

#### 🔴 **Red Status** (Critical)
- User cost: >€2.50/month
- API response: >5 seconds
- Error rate: >5%
- Service outages

### Key Panels to Monitor Daily

#### 1. **Cost per User** (Top Left)
- **Target**: €2.00/month
- **Alert**: >€2.50/month
- **Action**: If trending up, run `make monitoring-costs`

#### 2. **Monthly Revenue** (Top Right)  
- **Target**: €25,000/month
- **Current Milestone**: €20,000/month
- **Action**: Track progress, identify growth blockers

#### 3. **API Response Time** (Bottom Left)
- **Target**: <2 seconds (95th percentile)
- **SLA**: <5 seconds
- **Action**: If >5s, check Performance Dashboard

#### 4. **System Health** (Bottom Right)
- **Target**: All services UP
- **Alert**: Any service DOWN
- **Action**: Check individual service logs

## 🚨 Responding to Common Alerts

### 💰 **Cost Alert: User Cost >€2.50**

**Immediate Actions** (5 minutes):
1. Open Cost Analysis Dashboard
2. Identify high-cost users in the table
3. Check LLM provider breakdown
4. Note the cost increase trend

**Investigation** (15 minutes):
```bash
# Run detailed cost analysis
make monitoring-costs

# Check top expensive users
curl "http://localhost:9090/api/v1/query?query=topk(10, user_monthly_cost_eur)"

# Review LLM usage patterns
curl "http://localhost:9090/api/v1/query?query=sum by (provider) (increase(llm_cost_total_eur[24h]))"
```

**Actions**:
- Implement user usage limits if cost >€5/user
- Switch expensive LLM calls to cheaper models
- Improve caching for repeated requests
- Contact high-usage users about optimization

### ⚡ **Performance Alert: API Response >5s**

**Immediate Actions** (5 minutes):
1. Open Performance Dashboard
2. Check current response time trend
3. Identify slowest endpoints
4. Check error rate correlation

**Investigation** (15 minutes):
```bash
# Check current response times
curl "http://localhost:9090/api/v1/query?query=histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"

# Find slowest endpoints
curl "http://localhost:9090/api/v1/query?query=topk(5, histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])))"

# Check database performance
docker exec postgres_container psql -U postgres -c "SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
```

**Actions**:
- Restart application if response time is consistently >10s
- Optimize slow database queries
- Increase cache hit ratio
- Scale application if CPU >80%

### 💼 **Business Alert: Payment Failure Rate >5%**

**Immediate Actions** (5 minutes):
1. Open Business Metrics Dashboard
2. Check current payment success rate
3. Review payment volume trends
4. Check for service outages

**Investigation** (10 minutes):
```bash
# Check payment metrics
curl "http://localhost:9090/api/v1/query?query=rate(payment_operations_total{status=\"failed\"}[5m]) / rate(payment_operations_total[5m]) * 100"

# Review error types
curl "http://localhost:9090/api/v1/query?query=sum by (error_type) (increase(payment_operations_total{status=\"failed\"}[1h]))"
```

**Actions**:
- Check payment provider status
- Review recent payment integration changes
- Contact payment support if provider issue
- Implement retry logic for transient failures

### 🔒 **Security Alert: Failed Authentication >0.1/sec**

**Immediate Actions** (2 minutes):
1. Check alert details for source IP
2. Review authentication failure patterns
3. Determine if it's an attack or system issue

**Investigation** (10 minutes):
```bash
# Check failure rate
curl "http://localhost:9090/api/v1/query?query=rate(auth_failures_total[5m])"

# Review source IPs (if available)
curl "http://localhost:9090/api/v1/query?query=topk(10, sum by (source_ip) (increase(auth_failures_total[1h])))"
```

**Actions**:
- Implement IP blocking for obvious attacks
- Check for application bugs causing failures
- Review recent authentication changes
- Notify security team if attack pattern detected

## 🔍 Essential Queries

### Business Queries

```promql
# Current user cost per month
avg(user_monthly_cost_eur)

# Monthly recurring revenue
sum(monthly_revenue_eur)

# Payment success rate (last hour)
rate(payment_operations_total{status="succeeded"}[1h]) / rate(payment_operations_total[1h]) * 100

# New signups today
increase(active_users_total{time_window="24h"}[24h])
```

### Technical Queries

```promql
# API response time (95th percentile)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate by endpoint
rate(api_errors_total[5m]) / rate(http_request_duration_seconds_count[5m]) * 100

# Cache hit ratio
cache_hits / (cache_hits + cache_misses) * 100

# Database connections used
database_connections_active / database_connections_total * 100
```

### Cost Optimization Queries

```promql
# Top 10 expensive users
topk(10, user_monthly_cost_eur)

# LLM cost by provider (daily)
sum by (provider) (increase(llm_cost_total_eur[24h]))

# Cost trend (last 7 days)
increase(llm_cost_total_eur[7d])
```

## 🛠️ Daily Operations Checklist

### Morning Routine (9:00 AM - 10 minutes)

- [ ] Check overnight alerts in #pratikoai-alerts
- [ ] Review System Overview Dashboard
- [ ] Verify all services are UP (green dots)
- [ ] Check user cost is <€2.00/month
- [ ] Confirm API response time <2 seconds
- [ ] Review daily revenue progress

```bash
# Automated morning report
make monitoring-daily
```

### Midday Check (1:00 PM - 5 minutes)

- [ ] Quick glance at Cost Analysis Dashboard
- [ ] Check for any new alerts
- [ ] Verify payment processing is healthy
- [ ] Monitor peak usage patterns

### Evening Review (6:00 PM - 10 minutes)

- [ ] Review day's cost trends
- [ ] Check performance during peak hours
- [ ] Verify automated backups completed
- [ ] Plan any overnight maintenance

```bash
# Evening health check
make monitoring-health
```

## 🚨 Emergency Response

### When to Escalate Immediately

#### 🔴 **Critical - Immediate Response Required**
- System completely down (all services red)
- User cost >€5/month (unsustainable)
- API response time >30 seconds
- Error rate >50%
- Security breach detected

#### 🟡 **Warning - Response Within 1 Hour**
- Single service down
- User cost €2.50-€3.00/month
- API response time 5-10 seconds
- Error rate 5-10%
- Multiple failed authentication attempts

### Emergency Contacts

```
Critical System Issues:
📞 Engineering Oncall: +XX-XXX-XXX-XXXX
📧 Urgent: engineering-urgent@pratikoai.com

Cost Crisis (>€5/user):
📞 CEO Direct: +XX-XXX-XXX-XXXX  
📧 Urgent: ceo@pratikoai.com

Security Incident:
📞 Security Lead: +XX-XXX-XXX-XXXX
📧 Urgent: security-urgent@pratikoai.com
```

### Emergency Commands

```bash
# Complete system restart
make monitoring-stop
make docker-compose-down
make docker-compose-up ENV=production
make monitoring-start

# Emergency health check
make monitoring-health

# Cost crisis analysis
make monitoring-costs

# Generate immediate report
make monitoring-suite
```

## 🎯 Success Metrics

### Daily Targets
- ✅ User cost: <€2.00/month
- ✅ API response: <2 seconds (95th percentile)
- ✅ Error rate: <1%
- ✅ All services: UP
- ✅ Payment success: >95%

### Weekly Targets  
- ✅ Revenue growth: Progress toward €25k MRR
- ✅ Cost optimization: Identified savings opportunities
- ✅ Zero critical alerts
- ✅ All automation scripts running successfully

### Monthly Targets
- ✅ Cost efficiency: Maintained <€2/user average
- ✅ Performance: 99.9%+ uptime
- ✅ Growth: New user acquisition on target
- ✅ Zero security incidents

## 📱 Mobile Monitoring

### Grafana Mobile App
1. Download Grafana Mobile from app store
2. Add server: http://localhost:3000 (or your domain)
3. Login with: admin/admin
4. Add key dashboards to favorites
5. Enable push notifications for critical alerts

### Quick Mobile Checks
- System Overview Dashboard (overall health)
- Key metrics widgets
- Alert notifications
- Emergency contact access

## 🔄 Automation Status

### Scheduled Tasks
- **Daily Report**: 9:00 AM (automated email)
- **Cost Analysis**: Monday 10:00 AM (weekly)
- **Health Check**: Every 6 hours (automated)
- **Dashboard Backup**: 2:00 AM daily (automated)
- **Full Suite**: Sunday 8:00 AM (weekly summary)

### Manual Tasks
- Dashboard reviews (weekly)
- Alert threshold updates (monthly)
- Performance optimization (as needed)
- Security reviews (monthly)

---

**Need Help?** 
- 📚 Full documentation: [MONITORING.md](../MONITORING.md)
- 🔧 Troubleshooting: See MONITORING.md "Troubleshooting Guide"
- 📞 Emergency: Use contact info above
- 💬 Questions: #pratikoai-monitoring Slack channel

*This quick start guide gets you monitoring PratikoAI effectively. For detailed procedures and advanced topics, refer to the complete monitoring documentation.*