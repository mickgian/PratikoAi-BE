# PratikoAI Monitoring Automation Guide

This guide covers all monitoring automation scripts, their usage, scheduling, and maintenance procedures for the PratikoAI system.

## 📋 Overview

The monitoring automation system provides comprehensive oversight of PratikoAI's business and technical metrics through four main automation scripts:

1. **Daily Report Generator** - Comprehensive business and technical summaries
2. **Cost Optimization Analyzer** - Identifies cost reduction opportunities
3. **Health Check Monitor** - Validates system health and performance
4. **Dashboard Backup Manager** - Protects Grafana configurations

## 🎯 Quick Start

### Prerequisites
- Prometheus running on `http://localhost:9090`
- Grafana running on `http://localhost:3000` (admin/admin)
- PratikoAI application running on `http://localhost:8000`
- Email/Slack/webhook configurations (optional)

### Basic Usage
```bash
# Run individual automation tasks
make monitoring-daily      # Daily report with email
make monitoring-costs      # Cost optimization analysis  
make monitoring-health     # System health check
make monitoring-backup     # Dashboard backup

# Run complete automation suite
make monitoring-suite      # All tasks with notifications

# Set up automated scheduling
make monitoring-setup      # Generate cron jobs
```

## 📊 Automation Scripts

### 1. Daily Report Generator (`daily_report.py`)

**Purpose**: Generate comprehensive daily business and technical reports with email/webhook delivery.

**Key Features**:
- Cost analysis with €2.00/user target tracking
- Revenue metrics toward €25k ARR goal  
- Performance monitoring (API response times, cache ratios)
- Alert summaries and actionable recommendations
- Multiple output formats (HTML, JSON, text)

**Usage Examples**:
```bash
# Basic daily report
python monitoring/scripts/daily_report.py

# Email report with HTML format
python monitoring/scripts/daily_report.py --email --format html

# Save to file with webhook notification
python monitoring/scripts/daily_report.py --webhook --output daily_report.html

# Via make command
make monitoring-daily
```

**Configuration**:
```bash
# Email settings
export ALERT_EMAIL_FROM="alerts@pratikoai.com"
export ALERT_EMAIL_TO="admin@pratikoai.com,team@pratikoai.com"
export ALERT_EMAIL_SMTP_HOST="smtp.gmail.com"
export ALERT_EMAIL_SMTP_PORT="587"
export ALERT_EMAIL_USERNAME="your-email@gmail.com"
export ALERT_EMAIL_PASSWORD="your-app-password"

# Webhook settings
export WEBHOOK_URL="http://localhost:3001/daily-report"
export WEBHOOK_SECRET="your-webhook-secret"
```

### 2. Cost Optimization Analyzer (`optimize_costs.py`)

**Purpose**: Analyze costs and identify optimization opportunities to stay under €2.00/user target.

**Key Features**:
- High-cost user identification and analysis
- Caching efficiency optimization recommendations
- LLM provider cost comparison and switching suggestions
- API usage pattern analysis for efficiency improvements
- Resource utilization optimization (DB connections, Redis memory)

**Usage Examples**:
```bash
# Basic cost analysis
python monitoring/scripts/optimize_costs.py

# Detailed analysis with €2.50 threshold
python monitoring/scripts/optimize_costs.py --detailed --threshold 2.5

# Export results to JSON
python monitoring/scripts/optimize_costs.py --export cost_analysis.json

# Via make command
make monitoring-costs
```

**Sample Output**:
```
💰 COST OVERVIEW
Current monthly cost: €1,250.00
Current cost per user: €1.85
Target cost per user: €2.00
Potential monthly savings: €185.00
Cost efficiency: 108.1%

🎯 PRIORITY RECOMMENDATIONS
1. [HIGH] Improve Cache Performance - Potential savings: €75/month
2. [MEDIUM] Optimize LLM Provider Usage - Potential savings: €60/month
3. [HIGH] Reduce High Error Rates - Potential savings: €50/month
```

### 3. Health Check Monitor (`health_check.py`)

**Purpose**: Comprehensive system health validation with threshold monitoring and recommendations.

**Key Features**:
- Service availability monitoring (Prometheus, Grafana, Redis, PostgreSQL)
- Metric collection validation and freshness checks
- Business threshold monitoring (costs, revenue, performance)
- Data quality validation with anomaly detection
- Actionable recommendations for detected issues

**Usage Examples**:
```bash
# Full health check
python monitoring/scripts/health_check.py

# Critical issues only
python monitoring/scripts/health_check.py --critical-only

# Export detailed results
python monitoring/scripts/health_check.py --export health_report.json

# Via make command
make monitoring-health
```

**Health Status Levels**:
- 🟢 **HEALTHY**: All systems operational, metrics within targets
- 🟡 **WARNING**: Some issues detected, attention recommended
- 🔴 **CRITICAL**: Serious issues requiring immediate action

### 4. Dashboard Backup Manager (`backup_dashboards.py`)

**Purpose**: Backup, version control, and restore Grafana dashboards and configurations.

**Key Features**:
- Complete dashboard export to JSON files
- Git version control with commit tracking
- Data source backup (with sensitive data redaction)
- Dashboard comparison and change detection
- Automated cleanup of old backups

**Usage Examples**:
```bash
# Full backup
python monitoring/scripts/backup_dashboards.py

# Compare with previous backups
python monitoring/scripts/backup_dashboards.py --compare

# Restore specific dashboard
python monitoring/scripts/backup_dashboards.py --restore dashboard_file.json --overwrite

# Cleanup old backups (keep 30 days)
python monitoring/scripts/backup_dashboards.py --cleanup 30

# Via make commands
make monitoring-backup
make monitoring-compare
```

**Backup Structure**:
```
monitoring/backups/
├── dashboards/           # Individual dashboard JSON files
├── datasources/          # Data source configurations
├── metadata/             # Backup metadata and timestamps
├── snapshots/            # Point-in-time snapshots
└── .git/                 # Git repository for version control
```

## 🎛️ Unified Orchestrator (`run_monitoring.py`)

**Purpose**: Single interface for all monitoring automation with integrated reporting and scheduling.

**Features**:
- Unified command interface for all automation tasks
- Integrated result aggregation and reporting
- Automatic error handling and retry logic
- Scheduling and cron job generation
- Performance tracking and metrics

**Usage Examples**:
```bash
# Individual tasks
python monitoring/scripts/run_monitoring.py daily-report --email
python monitoring/scripts/run_monitoring.py optimize-costs --threshold 2.5
python monitoring/scripts/run_monitoring.py health-check --critical-only
python monitoring/scripts/run_monitoring.py backup-dashboards

# Full automation suite
python monitoring/scripts/run_monitoring.py full-suite --email --webhook

# Generate scheduling configuration
python monitoring/scripts/run_monitoring.py schedule
```

## ⏰ Automated Scheduling

### Cron Job Setup

Generate cron configuration:
```bash
make monitoring-setup
# Creates monitoring/crontab.monitoring file
```

Install cron jobs:
```bash
crontab monitoring/crontab.monitoring
```

**Default Schedule**:
```cron
# Daily report at 9:00 AM with email notifications
0 9 * * * python monitoring/scripts/run_monitoring.py daily-report --email

# Cost optimization analysis every Monday at 10:00 AM  
0 10 * * 1 python monitoring/scripts/run_monitoring.py optimize-costs --detailed

# Health check every 6 hours
0 */6 * * * python monitoring/scripts/run_monitoring.py health-check

# Dashboard backup daily at 2:00 AM
0 2 * * * python monitoring/scripts/run_monitoring.py backup-dashboards

# Full monitoring suite weekly on Sundays at 8:00 AM
0 8 * * 0 python monitoring/scripts/run_monitoring.py full-suite --email --webhook
```

### Systemd Timers (Alternative)

For systemd-based systems, generate timer files:
```bash
python monitoring/scripts/run_monitoring.py schedule --cron
```

This creates systemd service and timer files in `monitoring/systemd/`:
- `pratikoai-daily-report.service`
- `pratikoai-daily-report.timer`

Install and enable:
```bash
sudo cp monitoring/systemd/* /etc/systemd/system/
sudo systemctl enable pratikoai-daily-report.timer
sudo systemctl start pratikoai-daily-report.timer
```

## 📧 Notification Configuration

### Email Notifications

Configure SMTP settings in environment:
```bash
export ALERT_EMAIL_FROM="alerts@pratikoai.com"
export ALERT_EMAIL_TO="admin@pratikoai.com,finance@pratikoai.com"
export ALERT_EMAIL_SMTP_HOST="smtp.gmail.com"
export ALERT_EMAIL_SMTP_PORT="587"
export ALERT_EMAIL_USERNAME="your-email@gmail.com"
export ALERT_EMAIL_PASSWORD="your-app-password"  # Use app-specific password
export ALERT_EMAIL_USE_TLS="true"
```

### Slack Integration

Set up webhook URL:
```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
```

### Custom Webhooks

Configure custom webhook endpoints:
```bash
export WEBHOOK_URL="https://your-api.com/monitoring-webhook"
export WEBHOOK_SECRET="your-webhook-secret"
```

## 📁 Output and Results

### File Locations

All automation outputs are saved to `monitoring/results/`:
```
monitoring/results/
├── daily_report_20241201_090000.html
├── cost_analysis_20241201_100000.json
├── health_check_20241201_060000.json
└── backup_metadata_20241201_020000.json
```

### Report Formats

**Daily Reports**:
- **HTML**: Rich formatted reports for email
- **JSON**: Machine-readable data for integrations
- **Text**: Plain text for console/logs

**Cost Analysis**:
- **Console**: Human-readable summary with recommendations
- **JSON**: Detailed analysis data with all insights

**Health Checks**:
- **Console**: Status summary with color coding
- **JSON**: Complete health data for monitoring systems

## 🔧 Maintenance and Troubleshooting

### Common Issues

**1. Prometheus Connection Failed**
```bash
# Check Prometheus is running
curl http://localhost:9090/api/v1/status/config

# Verify Docker container
docker ps | grep prometheus
```

**2. Grafana Authentication Failed**
```bash
# Test Grafana login
curl -u admin:admin http://localhost:3000/api/health

# Reset Grafana password if needed
docker exec -it grafana_container grafana-cli admin reset-admin-password newpassword
```

**3. Email Delivery Failed**
```bash
# Test SMTP connection
telnet smtp.gmail.com 587

# Check environment variables
env | grep ALERT_EMAIL
```

**4. Dashboard Backup Failed**
```bash
# Verify Git repository
cd monitoring/backups && git status

# Check file permissions
ls -la monitoring/backups/
```

### Log Analysis

Monitor automation logs:
```bash
# Real-time monitoring
tail -f monitoring/results/*.log

# Search for errors
grep -r "ERROR" monitoring/results/

# Check specific script logs
python monitoring/scripts/daily_report.py 2>&1 | tee daily_report.log
```

### Performance Optimization

**1. Reduce Query Load**
- Adjust Prometheus query intervals
- Cache frequently accessed metrics
- Use range queries instead of instant queries

**2. Optimize Backup Storage**
- Enable compression for backup files
- Implement incremental backups
- Clean up old backups regularly

**3. Email Delivery Optimization**
- Use HTML email templates
- Compress large reports
- Implement delivery retries

## 🧪 Testing and Validation

### Alert Testing
```bash
# Test all alert configurations
make monitoring-test

# Test specific alert types
python monitoring/test_alerts.py --test cost
python monitoring/test_alerts.py --test performance
python monitoring/test_alerts.py --test security
```

### Automation Testing
```bash
# Test individual scripts
python monitoring/scripts/daily_report.py --format json --output test_report.json
python monitoring/scripts/optimize_costs.py --export test_costs.json
python monitoring/scripts/health_check.py --export test_health.json

# Validate outputs
jq . test_report.json  # Validate JSON format
```

### End-to-End Testing
```bash
# Run full suite in test mode
python monitoring/scripts/run_monitoring.py full-suite --email --webhook

# Verify all components
make monitoring-start    # Start monitoring stack
make monitoring-suite    # Run full automation
make monitoring-logs     # Check for errors
```

## 📈 Metrics and KPIs

### Business Metrics Tracked
- **Cost per User**: Target €2.00/month, alert at €2.50
- **Monthly Recurring Revenue**: Target €25k, milestone €20k
- **Payment Success Rate**: Target 95%+
- **User Acquisition**: Daily signup tracking

### Technical Metrics Tracked
- **API Response Time**: SLA 5 seconds (95th percentile)
- **Cache Hit Ratio**: Target 80%+
- **Error Rate**: Target <5%
- **System Uptime**: Target 99.9%

### Performance Indicators
- **Cost Optimization**: Monthly savings identified
- **Alert Response Time**: Time to resolution
- **Backup Success Rate**: Dashboard protection coverage
- **Health Check Frequency**: System validation intervals

## 🔄 Continuous Improvement

### Monthly Review Process
1. **Analyze Cost Trends**: Review monthly cost optimization reports
2. **Update Thresholds**: Adjust based on growth patterns
3. **Optimize Queries**: Improve Prometheus query performance
4. **Review Alerts**: Update alert rules based on false positives
5. **Test Backups**: Validate dashboard restore procedures

### Quarterly Updates
1. **Script Enhancement**: Add new monitoring capabilities
2. **Integration Updates**: Connect with new tools/services
3. **Performance Tuning**: Optimize automation execution
4. **Documentation Review**: Update guides and procedures

### Annual Planning
1. **Capacity Planning**: Scale monitoring infrastructure
2. **Tool Evaluation**: Assess new monitoring technologies
3. **Process Optimization**: Streamline automation workflows
4. **Training Updates**: Ensure team knowledge currency

## 🆘 Emergency Procedures

### Critical System Failure
1. **Immediate Response**: Run health check to assess damage
2. **Backup Recovery**: Restore dashboards from latest backup
3. **Service Restart**: Restart monitoring stack components
4. **Validation**: Verify all metrics collection resumed

### Data Loss Recovery
1. **Assess Scope**: Determine what data/dashboards were lost
2. **Restore from Backup**: Use git history to recover configurations
3. **Manual Recreation**: Rebuild missing components if needed
4. **Future Prevention**: Increase backup frequency

### Alert Storm Handling
1. **Identify Root Cause**: Use health check to find source
2. **Temporary Suppression**: Disable noisy alerts if needed
3. **Fix Underlying Issue**: Address the actual problem
4. **Re-enable Alerts**: Restore normal alerting after fix

---

*This automation system ensures PratikoAI maintains profitability, performance, and reliability through continuous monitoring and proactive optimization.*