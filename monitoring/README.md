# PratikoAI Monitoring Setup

This directory contains the complete monitoring stack configuration for PratikoAI using Prometheus, Grafana, and AlertManager.

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   PratikoAI     │    │  Prometheus  │    │    Grafana      │
│   App :8000     │───▶│    :9090     │───▶│     :3000       │
│   /metrics      │    │              │    │   Dashboards    │
└─────────────────┘    └──────────────┘    └─────────────────┘
         │                       │                    
         ▼                       ▼                    
┌─────────────────┐    ┌──────────────┐              
│   Exporters     │    │ AlertManager │              
│   Redis :9121   │    │    :9093     │              
│   Postgres:9187 │    │   Webhooks   │              
│   Node  :9100   │    │              │              
└─────────────────┘    └──────────────┘              
```

## 📊 Services Overview

### Core Monitoring
- **Prometheus** (`:9090`) - Metrics collection and storage
- **Grafana** (`:3000`) - Visualization dashboards  
- **AlertManager** (`:9093`) - Alert routing and notifications

### Metric Exporters
- **Redis Exporter** (`:9121`) - Redis performance metrics
- **PostgreSQL Exporter** (`:9187`) - Database metrics
- **Node Exporter** (`:9100`) - System resource metrics

### Application Metrics
- **PratikoAI App** (`:8000/metrics`) - Business and application metrics

## 🚀 Quick Start

1. **Start the monitoring stack:**
   ```bash
   docker-compose up -d prometheus redis-exporter postgres-exporter node-exporter alertmanager
   ```

2. **Verify all targets are UP:**
   - Open Prometheus: http://localhost:9090
   - Go to Status → Targets
   - Ensure all services show "UP" status

3. **Access monitoring interfaces:**
   - **Prometheus**: http://localhost:9090
   - **Grafana**: http://localhost:3000 (admin/admin)
   - **AlertManager**: http://localhost:9093

## 📈 Key Metrics Monitored

### Financial KPIs
- `user_monthly_cost_eur` - Cost per user (target: <€2/month)
- `monthly_revenue_eur` - MRR (target: €25k)
- `active_subscriptions_total` - Active subscriptions (target: 50)
- `llm_cost_total_eur` - LLM API costs

### Performance Metrics
- `http_request_duration_seconds` - API response times
- `cache_hit_ratio` - Cache performance (target: >80%)
- `active_users_total` - User activity levels

### Business Operations
- `italian_tax_calculations_total` - Tax processing volume
- `payment_operations_total` - Payment success/failure rates
- `document_processing_operations_total` - Document handling
- `knowledge_base_queries_total` - Search performance

## 🚨 Alert Categories

### Critical Alerts
- User cost >€2.50/month
- Payment failures >10%
- Service downtime
- Database connectivity issues

### Warning Alerts
- Cache hit ratio <70%
- API latency >5s
- High system resource usage
- Security anomalies

### Business Alerts
- MRR below €20k
- Trial conversion <10%
- High subscription churn
- Feature failure rates

## 🔧 Configuration Files

### `/prometheus/prometheus.yml`
- Scrape configuration for all services
- 15-second scrape intervals
- 30-day data retention
- Alert rule integration

### `/prometheus/alerts.yml`
- 25+ alert rules across all categories
- Business KPI thresholds
- Performance and reliability rules
- Security monitoring

### `/alertmanager/alertmanager.yml`
- Alert routing by severity/category
- Webhook integrations
- Alert deduplication and grouping
- Escalation policies

## 🔍 Testing Prometheus

### Basic Health Checks
```bash
# Check if Prometheus is scraping metrics
curl http://localhost:9090/api/v1/targets

# Test a sample query
curl 'http://localhost:9090/api/v1/query?query=up'

# Check alert rules
curl http://localhost:9090/api/v1/rules
```

### Sample Queries
```promql
# Current active subscriptions
active_subscriptions_total{status="active"}

# API response time 95th percentile
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# LLM cost rate per hour
rate(llm_cost_total_eur[1h])

# Cache hit ratio
cache_hit_ratio{cache_type="llm_responses"}
```

## 📁 Directory Structure

```
monitoring/
├── prometheus/
│   ├── prometheus.yml      # Main Prometheus config
│   └── alerts.yml          # Alert rules
├── alertmanager/
│   └── alertmanager.yml    # Alert routing config
└── README.md               # This file
```

## 🔄 Data Retention

- **Prometheus**: 30 days / 10GB limit
- **Automatic cleanup**: Old data removed when limits reached
- **WAL compression**: Enabled for storage efficiency

## 🎯 Next Steps

1. **Phase 3**: Set up Grafana dashboards
2. **Phase 4**: Configure alert notifications (Slack/email)
3. **Phase 5**: Add custom business dashboards
4. **Phase 6**: Set up log aggregation integration

## 🛠️ Troubleshooting

### Common Issues

1. **Targets showing as DOWN**
   - Check network connectivity between containers
   - Verify service names in docker-compose network
   - Check if application is exposing metrics endpoint

2. **No data in Prometheus**
   - Verify scrape_interval configuration
   - Check application metrics endpoint: http://localhost:8000/metrics
   - Review Prometheus logs: `docker-compose logs prometheus`

3. **Alerts not firing**
   - Check alert rules syntax: http://localhost:9090/rules
   - Verify alert evaluation interval
   - Check AlertManager configuration

### Useful Commands

```bash
# View Prometheus logs
docker-compose logs -f prometheus

# Reload Prometheus configuration
curl -X POST http://localhost:9090/-/reload

# Check AlertManager configuration
curl http://localhost:9093/api/v1/status

# Restart monitoring stack
docker-compose restart prometheus alertmanager
```