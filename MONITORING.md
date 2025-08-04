# PratikoAI Monitoring System Documentation

This document provides comprehensive documentation for PratikoAI's monitoring and observability infrastructure, designed to ensure profitability, performance, and reliability.

## 📊 System Overview

### Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   PratikoAI     │    │    Prometheus    │    │     Grafana     │
│   FastAPI App   │───▶│   Metrics Store  │───▶│   Dashboards    │
│   Port: 8000    │    │   Port: 9090     │    │   Port: 3000    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │      Redis       │    │  AlertManager   │
│   Database      │    │      Cache       │    │  Notifications  │
│   Port: 5433    │    │   Port: 6379     │    │   Port: 9093    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Key Components

- **Prometheus**: Metrics collection and storage (30-day retention)
- **Grafana**: Visualization dashboards and alerting (4 dashboards)
- **AlertManager**: Alert routing and notifications (4 channels)
- **Exporters**: PostgreSQL, Redis, and Node metrics
- **Automation**: 4 scripts for reports, optimization, health checks, backups

### Business Alignment

**Financial Targets**:
- 💰 **User Cost Target**: €2.00/month (Critical: >€2.50)
- 💼 **Revenue Target**: €25,000 MRR
- 📈 **Growth Target**: 50 active subscriptions

**Performance SLAs**:
- ⚡ **API Response**: <5 seconds (95th percentile)
- 💾 **Cache Hit Ratio**: >80%
- 🚫 **Error Rate**: <5%
- 🔄 **System Uptime**: >99.9%

## 🎛️ Dashboard Access

### Quick Access URLs

| Service | URL | Default Credentials |
|---------|-----|-------------------|
| **Grafana Dashboards** | http://localhost:3000 | admin / admin |
| **Prometheus Metrics** | http://localhost:9090 | No authentication |
| **AlertManager** | http://localhost:9093 | No authentication |
| **PratikoAI API** | http://localhost:8000/docs | JWT required |

### Available Dashboards

#### 1. 📊 **System Overview Dashboard**
**Purpose**: Executive summary of all key metrics
**URL**: http://localhost:3000/d/overview/pratikoai-system-overview

**Key Panels**:
- User cost per month (€2.00 target)
- Monthly recurring revenue progress (€25k target)
- API response times and error rates
- System uptime and service health
- Daily active users and new signups

**Use Cases**:
- Daily business reviews
- Executive reporting
- System health at-a-glance

#### 2. 💰 **Cost Analysis Dashboard**
**Purpose**: Detailed cost breakdown and optimization tracking
**URL**: http://localhost:3000/d/costs/pratikoai-cost-analysis

**Key Panels**:
- Cost per user trend over time
- LLM provider cost breakdown (OpenAI, Anthropic, etc.)
- High-cost user identification
- Cost optimization opportunities
- Daily/monthly cost trends

**Use Cases**:
- Cost optimization planning
- Budget management
- Profitability analysis

#### 3. 💼 **Business Metrics Dashboard**
**Purpose**: Revenue, growth, and customer metrics
**URL**: http://localhost:3000/d/business/pratikoai-business-metrics

**Key Panels**:
- Monthly recurring revenue (MRR) tracking
- Active subscription count and trends
- Payment success rates and failures
- User acquisition and churn rates
- Revenue per user analysis

**Use Cases**:
- Business performance review
- Growth tracking
- Customer success monitoring

#### 4. ⚡ **Performance Dashboard**
**Purpose**: Technical performance and reliability metrics
**URL**: http://localhost:3000/d/performance/pratikoai-performance

**Key Panels**:
- API response time percentiles
- Database query performance
- Cache hit ratios and efficiency
- Error rates by endpoint
- System resource utilization

**Use Cases**:
- Performance optimization
- SLA monitoring
- Technical troubleshooting

#### 5. 🚨 **Alert Management Dashboard**
**Purpose**: Alert overview and management
**URL**: http://localhost:3000/d/alerts/pratikoai-alerts

**Key Panels**:
- Active alerts by severity
- Alert frequency trends
- Resolution time tracking
- Alert status by team
- Critical threshold monitoring

**Use Cases**:
- Incident management
- Alert fatigue monitoring
- Response time analysis

## 🚨 Alert System

### Alert Categories

#### 💰 **Cost Alerts** (Business Critical)

| Alert | Threshold | Severity | Evaluation | Team |
|-------|-----------|----------|------------|------|
| **High User Cost** | >€2.50/user/month | Critical | 2 minutes | Finance |
| **Daily Cost Spike** | >50% increase | Warning | 5 minutes | Finance |
| **High LLM Daily Cost** | >€100/day | Warning | 10 minutes | Engineering |

#### 💼 **Business Alerts** (Revenue Protection)

| Alert | Threshold | Severity | Evaluation | Team |
|-------|-----------|----------|------------|------|
| **High Payment Failure** | >5% failure rate | Critical | 10 minutes | Business |
| **Low MRR Progress** | <€20k monthly | Warning | 30 minutes | Business |
| **High Churn Rate** | >10% in 24h | Warning | 1 hour | Business |
| **No New Signups** | 0 in 48 hours | Warning | 48 hours | Marketing |

#### ⚡ **Performance Alerts** (System Reliability)

| Alert | Threshold | Severity | Evaluation | Team |
|-------|-----------|----------|------------|------|
| **High API Response Time** | >5s (95th percentile) | Critical | 2 minutes | Engineering |
| **Low Cache Hit Ratio** | <70% efficiency | Warning | 5 minutes | Engineering |
| **High DB Connections** | >80% pool usage | Warning | 5 minutes | Engineering |
| **High Error Rate** | >5% API errors | Critical | 2 minutes | Engineering |

#### 🔒 **Security Alerts** (Threat Detection)

| Alert | Threshold | Severity | Evaluation | Team |
|-------|-----------|----------|------------|------|
| **Failed Authentication** | >0.1/sec | Critical | 1 minute | Security |
| **Unusual API Usage** | Anomaly detection | Warning | 10 minutes | Security |
| **GDPR Data Export** | Any request | Info | Immediate | Compliance |

### Notification Channels

#### 📧 **Email Notifications**
- **Recipients**: admin@pratikoai.com, alerts@pratikoai.com
- **Format**: HTML with alert details and runbook links
- **Delivery**: Critical alerts immediately, warnings during business hours

#### 💬 **Slack Integration**
- **Channel**: #pratikoai-alerts
- **Features**: Rich messages with severity colors, runbook links
- **Escalation**: @channel for critical alerts

#### 🔗 **Webhook Integration**
- **Endpoint**: http://localhost:3001/alerts
- **Format**: JSON payload for custom integrations
- **Use Cases**: Third-party tools, custom dashboards

#### 📟 **PagerDuty Integration**
- **Scope**: Critical alerts only
- **Features**: Incident creation, escalation policies
- **Teams**: Engineering oncall rotation

## 📈 Key Metrics Explained

### Business Metrics

#### 💰 **User Monthly Cost (EUR)**
- **Definition**: Average monthly cost per active user
- **Target**: €2.00/month
- **Critical Threshold**: €2.50/month
- **Calculation**: `sum(llm_cost_total_eur) / count(active_users)`
- **Business Impact**: Direct profitability indicator

#### 💼 **Monthly Recurring Revenue (MRR)**
- **Definition**: Predictable monthly subscription revenue
- **Target**: €25,000/month
- **Warning Threshold**: <€20,000/month
- **Calculation**: `sum(subscription_value_eur{status="active"})`
- **Business Impact**: Growth and sustainability measure

#### 📊 **Payment Success Rate**
- **Definition**: Percentage of successful payment transactions
- **Target**: >95%
- **Critical Threshold**: <95%
- **Calculation**: `rate(payment_operations_total{status="succeeded"}) / rate(payment_operations_total) * 100`
- **Business Impact**: Revenue collection efficiency

### Technical Metrics

#### ⚡ **API Response Time (P95)**
- **Definition**: 95th percentile of API response times
- **Target**: <2 seconds
- **SLA Threshold**: <5 seconds
- **Query**: `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`
- **Technical Impact**: User experience and system performance

#### 💾 **Cache Hit Ratio**
- **Definition**: Percentage of requests served from cache
- **Target**: >80%
- **Warning Threshold**: <70%
- **Calculation**: `cache_hits / (cache_hits + cache_misses) * 100`
- **Technical Impact**: Performance and cost optimization

#### 🚫 **API Error Rate**
- **Definition**: Percentage of API requests resulting in errors
- **Target**: <1%
- **Critical Threshold**: >5%
- **Calculation**: `rate(api_errors_total) / rate(http_request_duration_seconds_count) * 100`
- **Technical Impact**: System reliability and user experience

## 🔧 Troubleshooting Guide

### Common Issues and Solutions

#### 🔴 **No Data in Dashboards**

**Symptoms**:
- Empty panels showing "No data"
- Prometheus targets down
- Recent data missing

**Investigation Steps**:
1. Check Prometheus targets: http://localhost:9090/targets
2. Verify application metrics endpoint: http://localhost:8000/metrics
3. Check Docker container status: `docker ps`

**Solutions**:
```bash
# Restart monitoring stack
make monitoring-stop
make monitoring-start

# Check application metrics
curl http://localhost:8000/metrics

# Verify Prometheus configuration
docker logs prometheus_container
```

#### 🟡 **High Response Times**

**Symptoms**:
- API response time alerts firing
- Slow dashboard loading
- User complaints about performance

**Investigation Steps**:
1. Check current response times in Performance Dashboard
2. Identify slow endpoints: Top slow queries panel
3. Check database performance metrics
4. Review error rates for correlation

**Solutions**:
```bash
# Check database connections
docker exec -it postgres_container psql -U postgres -c "SELECT * FROM pg_stat_activity;"

# Analyze slow queries
curl "http://localhost:9090/api/v1/query?query=topk(5, histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])))"

# Restart application if needed
make docker-compose-down
make docker-compose-up ENV=production
```

#### 💰 **Cost Alerts Firing**

**Symptoms**:
- User cost exceeding €2.50 threshold
- Daily cost spike alerts
- High LLM usage notifications

**Investigation Steps**:
1. Open Cost Analysis Dashboard
2. Identify high-cost users in table
3. Check LLM provider breakdown
4. Review usage patterns in last 24h

**Solutions**:
```bash
# Run cost optimization analysis
make monitoring-costs

# Check specific user costs
curl "http://localhost:9090/api/v1/query?query=user_monthly_cost_eur"

# Review LLM provider costs
curl "http://localhost:9090/api/v1/query?query=sum by (provider) (increase(llm_cost_total_eur[24h]))"
```

#### 📧 **Alert Notifications Not Working**

**Symptoms**:
- No email notifications received
- Slack messages not appearing
- PagerDuty incidents not created

**Investigation Steps**:
1. Check AlertManager status: http://localhost:9093
2. Verify notification channel configuration
3. Test SMTP connectivity
4. Review AlertManager logs

**Solutions**:
```bash
# Check AlertManager configuration
docker logs alertmanager_container

# Test email configuration
python -c "
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('your-email', 'your-password')
print('SMTP connection successful')
"

# Restart AlertManager
docker restart alertmanager_container
```

### Emergency Procedures

#### 🚨 **System Down**

**Immediate Actions**:
1. Check system status: `make monitoring-health`
2. Verify all containers running: `docker ps`
3. Check recent alerts in Grafana
4. Notify team via emergency channels

**Recovery Steps**:
```bash
# Emergency restart
make monitoring-stop
make docker-compose-down
make docker-compose-up ENV=production
make monitoring-start

# Verify recovery
make monitoring-health
curl http://localhost:8000/health
```

#### 💸 **Cost Crisis**

**Immediate Actions**:
1. Check Cost Dashboard for current spend
2. Identify top spending users immediately
3. Review LLM provider costs
4. Consider temporary usage limits

**Mitigation Steps**:
```bash
# Immediate cost analysis
make monitoring-costs

# Check current daily spend
curl "http://localhost:9090/api/v1/query?query=increase(llm_cost_total_eur[24h])"

# Implement emergency cost controls (if needed)
# This would require application-level rate limiting
```

## 🔄 Maintenance Procedures

### Daily Maintenance

#### Morning Health Check (9:00 AM)
```bash
# Automated daily report (already scheduled)
make monitoring-daily

# Manual verification if needed
make monitoring-health
```

#### Evening Review (6:00 PM)
- Review daily cost summary
- Check for any new alerts
- Verify backup completion
- Review performance trends

### Weekly Maintenance

#### Monday: Cost Optimization (10:00 AM)
```bash
# Automated cost analysis (scheduled)
make monitoring-costs

# Review recommendations
# Implement optimization suggestions
```

#### Wednesday: Dashboard Review
- Check dashboard performance
- Update thresholds if needed
- Review alert frequency
- Test notification channels

#### Friday: Backup Verification
```bash
# Verify dashboard backups
make monitoring-compare

# Test restore procedure (monthly)
python monitoring/scripts/backup_dashboards.py --restore test_dashboard.json
```

### Monthly Maintenance

#### First Monday: Comprehensive Review
1. **Metrics Analysis**:
   - Review all KPI trends
   - Update business targets if needed
   - Analyze alert patterns

2. **Performance Optimization**:
   - Review slow queries
   - Optimize dashboard panels
   - Update retention policies

3. **Security Review**:
   - Review access logs
   - Update credentials if needed
   - Test disaster recovery

#### Third Friday: System Updates
1. **Version Updates**:
   - Update Grafana to latest stable
   - Update Prometheus version
   - Test new features

2. **Configuration Review**:
   - Review alert rules effectiveness
   - Update notification channels
   - Optimize queries for performance

### Quarterly Maintenance

#### Planning and Optimization
1. **Capacity Planning**:
   - Review storage usage
   - Plan for growth in metrics
   - Update infrastructure sizing

2. **Process Improvement**:
   - Review incident response times
   - Update runbooks based on learnings
   - Training updates for team

3. **Business Alignment**:
   - Review KPI relevance
   - Update financial targets
   - Align with business strategy

## 🔐 Security and Access Control

### Access Management

#### Grafana Users
- **Admin**: Full dashboard and user management
- **Editor**: Dashboard creation and editing
- **Viewer**: Read-only dashboard access

#### Prometheus Security
- **Network**: Accessible only from internal network
- **API**: No authentication (internal only)
- **Data**: 30-day retention for security

#### Alert Security
- **Notifications**: Sensitive data filtered
- **Runbooks**: Internal access only
- **Escalation**: Role-based contact lists

### Audit Procedures

#### Monthly Security Review
- Review Grafana user access
- Check notification channel security
- Audit sensitive metric exposure
- Verify data retention compliance

#### Incident Response
- Document all security-related alerts
- Maintain audit trail for compliance
- Regular security training updates
- Emergency contact procedures

## 📞 Contact Information

### Team Responsibilities

#### 🏢 **Business Team**
- **Responsible for**: Revenue, cost, and customer metrics
- **Primary Contact**: business@pratikoai.com
- **Escalation**: CEO, CFO
- **Hours**: Business hours (9 AM - 6 PM CET)

#### 🔧 **Engineering Team**
- **Responsible for**: Performance, reliability, and technical metrics
- **Primary Contact**: engineering@pratikoai.com
- **Escalation**: CTO, Lead Engineer
- **Hours**: 24/7 on-call rotation

#### 💰 **Finance Team**
- **Responsible for**: Cost optimization and budget monitoring
- **Primary Contact**: finance@pratikoai.com
- **Escalation**: CFO, Finance Manager
- **Hours**: Business hours (9 AM - 5 PM CET)

#### 🔒 **Security Team**
- **Responsible for**: Security alerts and compliance
- **Primary Contact**: security@pratikoai.com
- **Escalation**: CISO, Security Lead
- **Hours**: 24/7 for critical security alerts

### Emergency Contacts

#### Critical System Outage
1. **Primary**: engineering-oncall@pratikoai.com
2. **Secondary**: CTO direct line
3. **Escalation**: CEO notification after 30 minutes

#### Financial Crisis (>€5/user cost)
1. **Primary**: finance@pratikoai.com + CEO
2. **Secondary**: CFO direct line
3. **Action**: Emergency cost controls

#### Security Incident
1. **Primary**: security@pratikoai.com
2. **Secondary**: CISO direct line
3. **Escalation**: Legal and compliance teams

## 🚀 Getting Started Checklist

### For New Team Members

#### Initial Setup (30 minutes)
- [ ] Access Grafana: http://localhost:3000 (admin/admin)
- [ ] Bookmark all dashboard URLs
- [ ] Join #pratikoai-alerts Slack channel
- [ ] Configure email notifications
- [ ] Review this documentation thoroughly

#### First Week
- [ ] Shadow during alert response
- [ ] Practice using troubleshooting procedures
- [ ] Complete monitoring training module
- [ ] Set up local monitoring environment

#### First Month
- [ ] Lead response to non-critical alert
- [ ] Suggest improvement to runbook
- [ ] Complete emergency response drill
- [ ] Contribute to monthly maintenance

### For System Administrators

#### Setup Verification
- [ ] All Docker containers running
- [ ] Prometheus collecting metrics
- [ ] Grafana dashboards loading
- [ ] Alerts configured and testing
- [ ] Notifications working (email, Slack, PagerDuty)

#### Automation Setup
- [ ] Cron jobs configured: `make monitoring-setup`
- [ ] Daily reports generating
- [ ] Cost optimization running weekly
- [ ] Dashboard backups daily
- [ ] Health checks every 6 hours

---

*This monitoring system ensures PratikoAI maintains its €2/user profitability target while scaling toward €25k MRR through comprehensive observability, proactive alerting, and automated optimization.*