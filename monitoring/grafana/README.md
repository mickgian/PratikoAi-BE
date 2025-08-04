# PratikoAI Grafana Dashboards

This directory contains Grafana configuration and pre-built dashboards for PratikoAI monitoring.

## 🏗️ Auto-Provisioning Setup

Grafana is configured with automatic provisioning to load dashboards and data sources on startup.

```
monitoring/grafana/
├── provisioning/
│   ├── datasources/
│   │   └── prometheus.yml          # Auto-configure Prometheus data source
│   └── dashboards/
│       └── dashboard.yml          # Auto-load dashboard definitions
└── dashboards/
    ├── overview.json              # System health overview
    ├── costs.json                 # Cost management & €2/user target
    ├── business.json              # Revenue & €25k ARR progress
    └── performance.json           # Technical performance metrics
```

## 📊 Dashboard Overview

### 1. **System Overview** (`overview.json`)
**Purpose**: High-level health check and key metrics  
**Refresh**: 30 seconds  
**Key Panels**:
- System Health Status (UP/DOWN indicators)
- Active Users (24h)
- Monthly Revenue Progress
- Active Subscriptions
- HTTP Request Rate
- Cache Hit Ratio

### 2. **Cost Management** (`costs.json`)
**Purpose**: Track cost efficiency and €2/user target  
**Refresh**: 1 minute  
**Key Panels**:
- Cost per User vs €2 Target (with thresholds)
- Total LLM Costs (24h)
- Cost Efficiency Gauge
- LLM Costs by Provider (pie chart)
- Cost Trends Over Time
- API Calls by Provider
- Cost per User Distribution

### 3. **Business KPIs** (`business.json`)
**Purpose**: Revenue tracking and €25k ARR progress  
**Refresh**: 5 minutes  
**Key Panels**:
- MRR Progress to €25k Target (gauge)
- Monthly Revenue (current)
- Active Subscriptions Count
- Subscription Status Breakdown
- Trial Conversions Rate
- Italian Tax Operations
- Payment Success Rate
- User Activity Trends

### 4. **Performance Monitoring** (`performance.json`)
**Purpose**: Technical performance and system health  
**Refresh**: 30 seconds  
**Key Panels**:
- API Response Time (95th percentile)
- Cache Hit Ratio vs 80% target
- System Resource Usage (Memory/CPU)
- Database Connections
- HTTP Request Rate by Endpoint
- Error Rate by Category
- Redis Memory Usage
- Document Processing Performance

## 🎯 Key Performance Targets

### Financial KPIs
- **Cost per User**: <€2.00/month (Green <€1.50, Yellow €1.50-€2.00, Red >€2.00)
- **Monthly Revenue**: €25,000 target (Red <€10k, Yellow €10k-€20k, Green >€20k)
- **Cost Efficiency**: >75% efficiency vs €2 target

### Technical KPIs
- **API Response Time**: <5 seconds 95th percentile
- **Cache Hit Ratio**: >80% for all cache types
- **System Uptime**: 99.9% availability
- **Payment Success Rate**: >95%

### Business KPIs
- **Active Subscriptions**: 50 target for €25k ARR
- **Trial Conversion**: >10% trial-to-paid conversion
- **User Activity**: Growing 24h/7d/30d active users

## 🚀 Getting Started

### 1. Start Grafana
```bash
docker-compose up -d grafana
```

### 2. Access Grafana
- **URL**: http://localhost:3000
- **Username**: admin
- **Password**: admin

### 3. Verify Setup
- Check that Prometheus data source is connected (green dot)
- Verify all 4 dashboards are loaded in "PratikoAI" folder
- Test that panels are showing data (may show "No data" until app starts)

## 🔧 Configuration Details

### Data Source Configuration
```yaml
# prometheus.yml
name: Prometheus
type: prometheus
url: http://prometheus:9090
isDefault: true
```

### Dashboard Provisioning
```yaml
# dashboard.yml
providers:
  - name: 'PratikoAI Dashboards'
    folder: 'PratikoAI'
    path: /var/lib/grafana/dashboards
```

### Environment Variables
```yaml
GF_SECURITY_ADMIN_PASSWORD=admin
GF_USERS_ALLOW_SIGN_UP=false
GF_INSTALL_PLUGINS=grafana-clock-panel,grafana-simple-json-datasource,grafana-piechart-panel
```

## 📈 Custom Queries Used

### Cost Tracking
```promql
# Average cost per user
avg(user_monthly_cost_eur)

# Cost efficiency vs €2 target
(2.0 - avg(user_monthly_cost_eur)) / 2.0 * 100

# LLM costs by provider (24h)
sum by (provider) (increase(llm_cost_total_eur[24h]))
```

### Business Metrics
```promql
# MRR progress to €25k
monthly_revenue_eur / 25000 * 100

# Payment success rate
rate(payment_operations_total{status="succeeded"}[1h]) / rate(payment_operations_total[1h]) * 100

# Active subscriptions
active_subscriptions_total{status="active"}
```

### Performance Metrics
```promql
# API response time 95th percentile
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Cache hit ratio
cache_hit_ratio

# Error rate
rate(api_errors_total[5m])
```

## 🚨 Alert Integration

Dashboards include annotations for:
- **Cost Target Breach**: When user cost exceeds €2.50
- **Revenue Milestones**: When MRR passes key thresholds
- **Performance Alerts**: When response times exceed SLA

## 🔍 Troubleshooting

### No Data Showing
1. Check Prometheus data source connection (Settings > Data Sources)
2. Verify Prometheus is scraping metrics: http://localhost:9090/targets
3. Check that app is running and exposing metrics: http://localhost:8000/metrics

### Dashboards Not Loading
1. Check Grafana logs: `docker-compose logs grafana`
2. Verify provisioning path: `/etc/grafana/provisioning`
3. Check dashboard JSON syntax

### Authentication Issues
1. Default login: admin/admin
2. Reset password via Docker environment variable
3. Check user permissions and organization access

## 🎨 Customization

### Adding New Panels
1. Use Grafana UI to create panels
2. Export dashboard JSON
3. Replace corresponding file in `/dashboards/`
4. Restart Grafana to reload

### Color Thresholds
- **Green**: Target achieved or excellent performance
- **Yellow**: Warning level, attention needed
- **Orange**: Approaching critical levels
- **Red**: Critical threshold breached, immediate action required

### Refresh Rates
- **Overview**: 30s (real-time monitoring)
- **Costs**: 1m (cost tracking)
- **Business**: 5m (business metrics)
- **Performance**: 30s (technical monitoring)

## 📱 Mobile Responsive

All dashboards are designed to work on mobile devices with responsive panels and appropriate sizing for executive mobile access.