# 🛠️ PratikoAI Rollback System Troubleshooting Guide

This comprehensive troubleshooting guide covers common issues, diagnostic procedures, and recovery steps for the PratikoAI Rollback System.

## 📋 Table of Contents

1. [Quick Diagnostic Checklist](#quick-diagnostic-checklist)
2. [Common Issues](#common-issues)
3. [Service-Specific Troubleshooting](#service-specific-troubleshooting)
4. [Emergency Procedures](#emergency-procedures)
5. [Diagnostic Tools](#diagnostic-tools)
6. [Log Analysis](#log-analysis)
7. [Performance Issues](#performance-issues)
8. [Recovery Procedures](#recovery-procedures)

## 🚨 Quick Diagnostic Checklist

When experiencing rollback issues, run through this checklist first:

### System Health Check
```bash
# 1. Check system resources
df -h                    # Disk space
free -h                  # Memory usage
top                      # CPU usage
iostat -x 1 5           # I/O statistics

# 2. Check network connectivity
ping api.pratiko.ai
ping database-host
curl -I https://api.pratiko.ai/health

# 3. Check service status
systemctl status pratiko-rollback
systemctl status postgresql
systemctl status redis
systemctl status nginx

# 4. Check log files
tail -f /var/log/pratiko-integration.log
tail -f /var/log/pratiko-rollback/rollback_execution.log
```

### Configuration Validation
```bash
# Validate YAML configuration files
python -c "import yaml; yaml.safe_load(open('health_monitor_config.yaml'))"
python -c "import yaml; yaml.safe_load(open('rollback_config.yaml'))"

# Check environment variables
echo $DATABASE_URL
echo $REDIS_URL
echo $GITHUB_TOKEN
echo $SLACK_WEBHOOK_URL

# Test database connectivity
python -c "import asyncpg; import asyncio; asyncio.run(asyncpg.connect('$DATABASE_URL'))"
```

### Process Check
```bash
# Check if processes are running
ps aux | grep -E "(health_monitor|rollback_orchestrator|integration)"

# Check process resource usage
ps -eo pid,ppid,cmd,%mem,%cpu --sort=-%mem | head -20

# Check for zombie processes
ps aux | grep -E "<defunct>|<zombie>"
```

---

## 🔧 Common Issues

### Issue 1: Rollback Initiation Failures

**Symptoms:**
- Rollback process fails to start
- Error messages about connection failures
- Timeout errors during initialization

**Diagnostic Steps:**

1. **Check Database Connectivity:**
   ```bash
   # Test database connection
   psql $DATABASE_URL -c "SELECT 1;"
   
   # Check database permissions
   psql $DATABASE_URL -c "SELECT current_user, session_user;"
   psql $DATABASE_URL -c "SELECT has_database_privilege('pratiko', 'CREATE');"
   
   # Check database locks
   psql $DATABASE_URL -c "SELECT * FROM pg_locks WHERE NOT granted;"
   ```

2. **Verify Container Access:**
   ```bash
   # Docker connectivity
   docker ps
   docker info
   
   # Kubernetes connectivity
   kubectl cluster-info
   kubectl get nodes
   kubectl get pods -n pratiko
   
   # Check permissions
   ls -la /var/run/docker.sock
   kubectl auth can-i get pods
   ```

3. **Environment Variables:**
   ```bash
   # Check all required variables
   env | grep -E "(DATABASE|REDIS|GITHUB|SLACK|AWS|KUBECONFIG)"
   
   # Test each service connection
   redis-cli -u $REDIS_URL ping
   curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user
   ```

**Solutions:**

1. **Database Issues:**
   ```bash
   # Restart database service
   sudo systemctl restart postgresql
   
   # Grant necessary permissions
   psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE pratiko TO rollback_user;"
   
   # Kill blocking connections
   psql $DATABASE_URL -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle in transaction';"
   ```

2. **Container Access Issues:**
   ```bash
   # Fix Docker socket permissions
   sudo chmod 666 /var/run/docker.sock
   
   # Update kubeconfig
   kubectl config view --minify --raw > ~/.kube/config
   
   # Restart container runtime
   sudo systemctl restart docker
   sudo systemctl restart containerd
   ```

3. **Environment Variable Issues:**
   ```bash
   # Reload environment
   source /etc/environment
   source ~/.bashrc
   
   # Set missing variables
   export DATABASE_URL="postgresql://user:pass@localhost/pratiko"
   export REDIS_URL="redis://localhost:6379"
   
   # Make permanent
   echo 'export DATABASE_URL="postgresql://user:pass@localhost/pratiko"' >> ~/.bashrc
   ```

---

### Issue 2: Health Check Failures

**Symptoms:**
- Health checks consistently fail for healthy services
- False positive failure detection
- Incorrect rollback triggering

**Diagnostic Steps:**

1. **Test Health Endpoints Manually:**
   ```bash
   # Test backend health
   curl -v https://api.pratiko.ai/health
   curl -v https://api.pratiko.ai/metrics
   
   # Test frontend health
   curl -v https://pratiko.ai/health
   curl -I https://cdn.pratiko.ai/app.js
   
   # Test database health
   psql $DATABASE_URL -c "SELECT 1, NOW();"
   
   # Test with different timeout values
   timeout 5 curl https://api.pratiko.ai/health
   timeout 30 curl https://api.pratiko.ai/health
   ```

2. **Network Connectivity:**
   ```bash
   # DNS resolution
   nslookup api.pratiko.ai
   dig api.pratiko.ai
   
   # Network path testing
   traceroute api.pratiko.ai
   mtr --report-cycles 10 api.pratiko.ai
   
   # Port connectivity
   telnet api.pratiko.ai 443
   nc -zv api.pratiko.ai 443
   ```

3. **Service Response Analysis:**
   ```bash
   # Detailed HTTP response
   curl -w "Connect: %{time_connect}s\nTTFB: %{time_starttransfer}s\nTotal: %{time_total}s\nHTTP: %{http_code}\n" https://api.pratiko.ai/health
   
   # Check response headers
   curl -I https://api.pratiko.ai/health
   
   # Monitor response times
   for i in {1..10}; do
     time curl -s https://api.pratiko.ai/health > /dev/null
     sleep 1
   done
   ```

**Solutions:**

1. **Configuration Adjustments:**
   ```yaml
   # health_monitor_config.yaml - Increase timeouts
   health_checks:
     - check_id: backend_health
       timeout_seconds: 30  # Increased from 10
       interval_seconds: 60  # Reduced frequency
       consecutive_failures_for_critical: 5  # Increased threshold
   ```

2. **Network Issues:**
   ```bash
   # Update DNS settings
   echo "nameserver 8.8.8.8" | sudo tee -a /etc/resolv.conf
   
   # Flush DNS cache
   sudo systemctl restart systemd-resolved
   
   # Check firewall rules
   sudo iptables -L
   sudo ufw status
   ```

3. **Service-Specific Solutions:**
   ```bash
   # Restart health check target services
   sudo systemctl restart nginx
   sudo systemctl restart pratiko-backend
   
   # Check service logs
   journalctl -u nginx -f
   journalctl -u pratiko-backend -f
   ```

---

### Issue 3: Database Rollback Problems

**Symptoms:**
- Database rollback fails midway
- Data loss or corruption
- Migration conflicts
- Backup/restore failures

**Diagnostic Steps:**

1. **Check Migration State:**
   ```bash
   # View migration history
   python manage.py showmigrations --list
   
   # Check migration dependencies
   python manage.py migrate --plan
   
   # Identify conflicting migrations
   python manage.py makemigrations --dry-run --verbosity=2
   ```

2. **Database Integrity:**
   ```bash
   # Check database connectivity
   psql $DATABASE_URL -c "SELECT version();"
   
   # Verify table integrity
   psql $DATABASE_URL -c "SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del FROM pg_stat_user_tables;"
   
   # Check for locks
   psql $DATABASE_URL -c "SELECT * FROM pg_locks l JOIN pg_stat_activity a ON l.pid = a.pid WHERE NOT l.granted;"
   
   # Check disk space
   psql $DATABASE_URL -c "SELECT pg_size_pretty(pg_database_size('pratiko'));"
   ```

3. **Backup Verification:**
   ```bash
   # Check backup storage
   aws s3 ls s3://pratiko-rollback-backups/ --recursive
   
   # Verify backup integrity
   aws s3 cp s3://pratiko-rollback-backups/latest/backup.sql /tmp/
   head -100 /tmp/backup.sql
   
   # Test backup restoration
   createdb test_restore
   psql test_restore < /tmp/backup.sql
   dropdb test_restore
   ```

**Solutions:**

1. **Migration Conflicts:**
   ```bash
   # Reset migrations to known good state
   python manage.py migrate app_name 0044_last_known_good
   
   # Remove conflicting migration files
   rm app/migrations/0045_conflicting_migration.py
   
   # Recreate clean migrations
   python manage.py makemigrations app_name
   python manage.py migrate app_name
   ```

2. **Database Recovery:**
   ```bash
   # Stop all database connections
   sudo systemctl stop pratiko-backend
   sudo systemctl stop celery
   
   # Kill existing connections
   psql -U postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'pratiko' AND pid <> pg_backend_pid();"
   
   # Restore from backup
   dropdb pratiko
   createdb pratiko
   psql pratiko < /path/to/backup.sql
   
   # Restart services
   sudo systemctl start pratiko-backend
   sudo systemctl start celery
   ```

3. **Data Preservation:**
   ```bash
   # Create manual backup before rollback
   pg_dump $DATABASE_URL > /tmp/pre_rollback_backup.sql
   
   # Export critical data
   psql $DATABASE_URL -c "COPY (SELECT * FROM critical_table) TO '/tmp/critical_data.csv' WITH CSV HEADER;"
   
   # Verify data after rollback
   psql $DATABASE_URL -c "SELECT COUNT(*) FROM critical_table;"
   ```

---

### Issue 4: Frontend Rollback Issues

**Symptoms:**
- Frontend doesn't revert to previous version
- CDN cache issues
- Mobile app rollback failures
- Asset deployment problems

**Diagnostic Steps:**

1. **CDN and Asset Verification:**
   ```bash
   # Check current asset versions
   curl -I https://cdn.pratiko.ai/app.js
   curl -I https://cdn.pratiko.ai/manifest.json
   
   # Check cache headers
   curl -H "Cache-Control: no-cache" https://cdn.pratiko.ai/app.js | head -10
   
   # Verify asset integrity
   curl -s https://cdn.pratiko.ai/manifest.json | jq '.version'
   ```

2. **Version Registry Check:**
   ```bash
   # Check available versions
   curl -s https://version-registry.pratiko.ai/api/v1/versions/frontend/web | jq '.'
   
   # Verify rollback target version exists
   curl -s https://version-registry.pratiko.ai/api/v1/versions/frontend/web/2.0.5
   
   # Check deployment history
   curl -s https://version-registry.pratiko.ai/api/v1/deployments | jq '.[] | select(.service=="frontend")'
   ```

3. **Mobile App Store Status:**
   ```bash
   # Check app store metadata (pseudo-commands)
   # iOS App Store Connect API would be used here
   # Google Play Console API would be used here
   
   # Check mobile API compatibility
   curl https://mobile-api.pratiko.ai/version
   curl https://mobile-api.pratiko.ai/compatibility?client_version=2.0.5
   ```

**Solutions:**

1. **CDN Cache Issues:**
   ```bash
   # Clear CloudFront cache
   aws cloudfront create-invalidation --distribution-id E123456789 --paths "/*"
   
   # Clear multiple CDN caches
   for dist in E123456789 E987654321; do
     aws cloudfront create-invalidation --distribution-id $dist --paths "/*"
   done
   
   # Verify cache clearance
   aws cloudfront get-invalidation --distribution-id E123456789 --id I1234567890
   ```

2. **Asset Deployment:**
   ```bash
   # Manual asset rollback
   aws s3 sync s3://pratiko-assets/versions/2.0.5/ s3://pratiko-assets/current/
   
   # Update asset versions
   aws s3 cp s3://pratiko-assets/versions/2.0.5/manifest.json s3://pratiko-assets/current/manifest.json
   
   # Verify deployment
   curl -s https://cdn.pratiko.ai/manifest.json | jq '.version'
   ```

3. **Mobile App Issues:**
   ```bash
   # Update mobile app metadata
   curl -X POST https://mobile-api.pratiko.ai/admin/rollback \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -d '{"platform": "android", "version": "2.0.5"}'
   
   # Notify mobile clients
   curl -X POST https://mobile-api.pratiko.ai/admin/force-update \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -d '{"message": "Please update to the latest version"}'
   ```

---

### Issue 5: System Resource Problems

**Symptoms:**
- High CPU/memory usage during rollback
- Disk space exhaustion
- Network bandwidth saturation
- I/O bottlenecks

**Diagnostic Steps:**

1. **Resource Monitoring:**
   ```bash
   # Real-time resource monitoring
   top -p $(pgrep -d',' -f rollback)
   htop -p $(pgrep -d',' -f rollback)
   
   # Detailed resource usage
   pidstat -p $(pgrep -f rollback) 1 10
   iotop -p $(pgrep -f rollback)
   
   # Memory analysis
   ps -o pid,ppid,cmd,pmem,rss,vsz --sort=-rss | head -20
   ```

2. **Disk Space Analysis:**
   ```bash
   # Check disk usage
   df -h
   du -sh /var/log/pratiko-rollback/*
   du -sh /tmp/pratiko-*
   
   # Find large files
   find /var/log -size +100M -type f
   find /tmp -name "pratiko-*" -size +50M
   
   # Check inode usage
   df -i
   ```

3. **Network Analysis:**
   ```bash
   # Network usage by process
   ss -tuln | grep -E "(rollback|pratiko)"
   netstat -i
   
   # Bandwidth monitoring
   iftop -i eth0
   nload eth0
   
   # Connection analysis
   ss -s
   ss -p | grep rollback
   ```

**Solutions:**

1. **Resource Optimization:**
   ```bash
   # Reduce rollback concurrency
   export ROLLBACK_MAX_WORKERS=2
   export ROLLBACK_BATCH_SIZE=1
   
   # Increase system limits
   echo "pratiko soft nofile 65536" | sudo tee -a /etc/security/limits.conf
   echo "pratiko hard nofile 65536" | sudo tee -a /etc/security/limits.conf
   
   # Optimize memory usage
   echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
   sudo sysctl -p
   ```

2. **Disk Space Management:**
   ```bash
   # Clean up old logs
   find /var/log/pratiko-rollback -name "*.log" -mtime +7 -delete
   
   # Compress large log files
   gzip /var/log/pratiko-rollback/*.log
   
   # Move backups to cheaper storage
   aws s3 mv s3://pratiko-rollback-backups/old/ s3://pratiko-archive-backups/ --recursive
   ```

3. **Network Optimization:**
   ```bash
   # Rate limit network operations
   trickle -d 1000 -u 1000 python rollback_orchestrator.py
   
   # Use connection pooling
   export ROLLBACK_CONNECTION_POOL_SIZE=5
   export ROLLBACK_CONNECTION_TIMEOUT=30
   ```

---

## 🏥 Service-Specific Troubleshooting

### Backend Service Issues

**Common Problems:**
- Container startup failures
- Load balancer configuration issues
- Service discovery problems
- Health check endpoint failures

**Diagnostic Commands:**
```bash
# Check container status
docker ps -a | grep pratiko-backend
kubectl get pods -l app=pratiko-backend

# View container logs
docker logs pratiko-backend-container
kubectl logs -l app=pratiko-backend --tail=100

# Test service endpoints
curl https://api.pratiko.ai/health
curl https://api.pratiko.ai/metrics
curl https://api.pratiko.ai/version

# Check load balancer
curl -H "Host: api.pratiko.ai" http://load-balancer-ip/health
nginx -t
sudo systemctl status nginx
```

**Solutions:**
```bash
# Restart backend service
docker-compose restart backend
kubectl rollout restart deployment/pratiko-backend

# Update load balancer configuration
sudo nginx -s reload
kubectl apply -f k8s/nginx-config.yaml

# Reset service discovery
consul catalog deregister -id=pratiko-backend
systemctl restart consul
```

### Database Service Issues

**Common Problems:**
- Connection pool exhaustion
- Long-running transactions
- Lock contention
- Replication lag

**Diagnostic Commands:**
```bash
# Check database connections
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"
psql $DATABASE_URL -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"

# Check locks
psql $DATABASE_URL -c "SELECT * FROM pg_locks WHERE NOT granted;"

# Check replication
psql $DATABASE_URL -c "SELECT * FROM pg_stat_replication;"

# Performance analysis
psql $DATABASE_URL -c "SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
```

**Solutions:**
```bash
# Kill long-running queries
psql $DATABASE_URL -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE query_start < NOW() - INTERVAL '10 minutes';"

# Increase connection limits
sudo sed -i 's/max_connections = 100/max_connections = 200/' /etc/postgresql/12/main/postgresql.conf
sudo systemctl restart postgresql

# Optimize configuration
sudo sed -i 's/#shared_buffers = 128MB/shared_buffers = 256MB/' /etc/postgresql/12/main/postgresql.conf
```

### Frontend Service Issues

**Common Problems:**
- Asset loading failures
- CDN synchronization issues
- Mobile app compatibility
- Browser caching problems

**Diagnostic Commands:**
```bash
# Check asset availability
curl -I https://cdn.pratiko.ai/app.js
curl -I https://cdn.pratiko.ai/style.css
curl -s https://cdn.pratiko.ai/manifest.json

# Verify CDN configuration
dig cdn.pratiko.ai
nslookup cdn.pratiko.ai

# Check mobile API compatibility
curl https://mobile-api.pratiko.ai/version
curl https://mobile-api.pratiko.ai/compatibility
```

**Solutions:**
```bash
# Sync assets to CDN
aws s3 sync ./dist/ s3://pratiko-cdn/
aws cloudfront create-invalidation --distribution-id E123456 --paths "/*"

# Update mobile compatibility
curl -X POST https://mobile-api.pratiko.ai/admin/compatibility \
  -d '{"min_version": "2.0.5", "recommended_version": "2.1.0"}'

# Clear browser caches (update cache headers)
sed -i 's/Cache-Control: max-age=3600/Cache-Control: no-cache/' nginx.conf
```

---

## 🚨 Emergency Procedures

### Emergency Rollback Stop

If a rollback is causing more problems than it's solving:

```bash
# 1. Immediate stop of all rollback processes
sudo pkill -9 -f "rollback_orchestrator"
sudo pkill -9 -f "health_monitor"
sudo pkill -9 -f "monitor_rollback_integration"

# 2. Stop systemd services
sudo systemctl stop pratiko-rollback
sudo systemctl disable pratiko-rollback

# 3. Terminate database connections
psql -U postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE application_name LIKE '%rollback%';"

# 4. Stop container operations
docker stop $(docker ps -q --filter "label=rollback")
kubectl delete jobs -l component=rollback

# 5. Lock deployment system
touch /var/lock/deployment-emergency-stop
```

### System-Wide Recovery

For complete system recovery:

```bash
# 1. Create recovery point
sudo tar -czf /backup/emergency-recovery-$(date +%Y%m%d-%H%M%S).tar.gz \
  /opt/pratiko/ \
  /etc/nginx/ \
  /etc/systemd/system/pratiko-*

# 2. Stop all services
sudo systemctl stop pratiko-*
sudo systemctl stop nginx
sudo systemctl stop postgresql
sudo systemctl stop redis

# 3. Restore from known good backup
sudo tar -xzf /backup/last-known-good.tar.gz -C /

# 4. Restore database
sudo -u postgres dropdb pratiko
sudo -u postgres createdb pratiko
sudo -u postgres psql pratiko < /backup/database-backup.sql

# 5. Start services in order
sudo systemctl start postgresql
sudo systemctl start redis
sudo systemctl start nginx
sudo systemctl start pratiko-backend
sudo systemctl start pratiko-frontend

# 6. Verify system health
curl https://api.pratiko.ai/health
curl https://pratiko.ai/health
```

### Data Recovery

If data loss is suspected:

```bash
# 1. Stop all write operations
sudo systemctl stop pratiko-backend
sudo systemctl stop celery-worker
sudo systemctl stop pratiko-scheduler

# 2. Create forensic copy
sudo dd if=/dev/sda1 of=/backup/forensic-copy-$(date +%Y%m%d).img bs=4M

# 3. Analyze data integrity
sudo fsck -n /dev/sda1
psql $DATABASE_URL -c "SELECT pg_database_size('pratiko');"

# 4. Restore from point-in-time backup
sudo -u postgres pg_restore -d pratiko -t user_data /backup/point-in-time-backup.dump

# 5. Verify data integrity
psql $DATABASE_URL -c "SELECT COUNT(*) FROM critical_tables;"
python manage.py check --database default
```

---

## 🔍 Diagnostic Tools

### Health Check Script

Create a comprehensive health check script:

```bash
#!/bin/bash
# health-check.sh

echo "=== PratikoAI System Health Check ==="
echo "Timestamp: $(date)"
echo

# System resources
echo "=== System Resources ==="
echo "CPU Usage: $(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1"%"}')"
echo "Memory Usage: $(free | grep Mem | awk '{printf("%.2f%%", $3/$2 * 100.0)}')"
echo "Disk Usage: $(df -h / | awk 'NR==2{printf "%s", $5}')"
echo

# Service status
echo "=== Service Status ==="
services=("pratiko-rollback" "postgresql" "redis" "nginx")
for service in "${services[@]}"; do
  status=$(systemctl is-active $service)
  echo "$service: $status"
done
echo

# Network connectivity
echo "=== Network Connectivity ==="
endpoints=("api.pratiko.ai" "pratiko.ai" "cdn.pratiko.ai")
for endpoint in "${endpoints[@]}"; do
  if curl -s --max-time 5 "https://$endpoint/health" > /dev/null; then
    echo "$endpoint: OK"
  else
    echo "$endpoint: FAILED"
  fi
done
echo

# Database connectivity
echo "=== Database Status ==="
if psql $DATABASE_URL -c "SELECT 1;" > /dev/null 2>&1; then
  connections=$(psql $DATABASE_URL -t -c "SELECT count(*) FROM pg_stat_activity;")
  echo "Database: OK ($connections connections)"
else
  echo "Database: FAILED"
fi
echo

# Log recent errors
echo "=== Recent Errors ==="
if [ -f /var/log/pratiko-integration.log ]; then
  grep -i error /var/log/pratiko-integration.log | tail -5
else
  echo "No error logs found"
fi
```

### Performance Monitoring Script

```bash
#!/bin/bash
# performance-monitor.sh

LOG_FILE="/var/log/pratiko-performance.log"

while true; do
  timestamp=$(date)
  cpu=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
  memory=$(free | grep Mem | awk '{printf("%.1f", $3/$2 * 100.0)}')
  disk=$(df / | awk 'NR==2{printf("%.1f", $3/$2 * 100.0)}')
  
  # Log performance metrics
  echo "$timestamp,CPU:$cpu%,Memory:$memory%,Disk:$disk%" >> $LOG_FILE
  
  # Check thresholds and alert
  if (( $(echo "$cpu > 90" | bc -l) )); then
    echo "ALERT: High CPU usage: $cpu%" | logger -t pratiko-monitor
  fi
  
  if (( $(echo "$memory > 90" | bc -l) )); then
    echo "ALERT: High memory usage: $memory%" | logger -t pratiko-monitor
  fi
  
  sleep 60
done
```

### Rollback Status Checker

```python
#!/usr/bin/env python3
# rollback-status.py

import asyncio
import json
import sys
from datetime import datetime

async def check_rollback_status():
    """Check current rollback system status."""
    
    try:
        from rollback_orchestrator import RollbackOrchestrator
        from health_monitor import HealthMonitor
        
        # Initialize components
        orchestrator = RollbackOrchestrator()
        monitor = HealthMonitor()
        
        # Get current status
        deployment_id = sys.argv[1] if len(sys.argv) > 1 else "current"
        
        # Get health report
        health_report = await monitor.generate_health_report(deployment_id)
        
        # Get rollback history
        history = getattr(orchestrator, 'rollback_history', [])
        
        status = {
            "timestamp": datetime.now().isoformat(),
            "deployment_id": deployment_id,
            "health_status": health_report.overall_status.value,
            "services": dict(health_report.services),
            "failed_checks": health_report.failed_checks,
            "warnings": health_report.warnings,
            "recent_rollbacks": len([h for h in history if h.get('deployment_id') == deployment_id]),
            "system_healthy": health_report.overall_status.value == "healthy"
        }
        
        print(json.dumps(status, indent=2))
        
        # Exit with appropriate code
        if health_report.overall_status.value == "critical":
            sys.exit(2)
        elif health_report.overall_status.value == "warning":
            sys.exit(1)
        else:
            sys.exit(0)
            
    except Exception as e:
        error_status = {
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "status": "error"
        }
        print(json.dumps(error_status, indent=2))
        sys.exit(3)

if __name__ == "__main__":
    asyncio.run(check_rollback_status())
```

---

## 📊 Log Analysis

### Important Log Locations

```bash
# Main system logs
/var/log/pratiko-integration.log
/var/log/pratiko-rollback/rollback_execution.log
/var/log/pratiko-rollback/health_monitor.log
/var/log/pratiko-rollback/system.log

# Service-specific logs
/var/log/nginx/access.log
/var/log/nginx/error.log
/var/log/postgresql/postgresql-12-main.log
/var/log/redis/redis-server.log

# Application logs
/opt/pratiko/backend/logs/app.log
/opt/pratiko/backend/logs/error.log
/opt/pratiko/frontend/logs/deploy.log

# System logs
/var/log/syslog
/var/log/kern.log
/var/log/auth.log
```

### Log Analysis Commands

```bash
# Find errors in the last hour
find /var/log/pratiko-rollback/ -name "*.log" -exec grep -l "ERROR\|CRITICAL" {} \; | xargs grep "$(date +%Y-%m-%d\ %H)" | grep -E "ERROR|CRITICAL"

# Count rollback events
grep -c "rollback.*initiated" /var/log/pratiko-integration.log

# Find slow operations
grep -E "took [0-9]{3,}" /var/log/pratiko-rollback/*.log

# Analyze rollback success rate
grep "rollback.*completed" /var/log/pratiko-integration.log | awk '{print $NF}' | sort | uniq -c

# Monitor real-time logs
multitail /var/log/pratiko-integration.log /var/log/pratiko-rollback/rollback_execution.log

# Extract rollback timeline
grep -E "(rollback.*initiated|rollback.*completed|rollback.*failed)" /var/log/pratiko-integration.log | sort
```

### Log Rotation Configuration

```bash
# /etc/logrotate.d/pratiko-rollback
/var/log/pratiko-rollback/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 pratiko pratiko
    postrotate
        systemctl reload pratiko-rollback
    endscript
}
```

---

## 🎯 Performance Issues

### High CPU Usage

**Symptoms:**
- System becomes unresponsive during rollback
- Rollback operations timeout
- High load average

**Investigation:**
```bash
# Identify CPU-intensive processes
top -H -p $(pgrep -f rollback)
perf top -p $(pgrep -f rollback)

# CPU profiling
perf record -p $(pgrep -f rollback) -g -- sleep 30
perf report

# Check for CPU throttling
dmesg | grep -i "thermal\|throttl"
```

**Solutions:**
```bash
# Reduce rollback concurrency
export ROLLBACK_MAX_WORKERS=1
export ROLLBACK_PARALLEL_OPERATIONS=2

# Lower process priority
renice 10 $(pgrep -f rollback)

# CPU frequency scaling
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

### Memory Issues

**Symptoms:**
- Out of memory errors
- System swapping heavily
- Process crashes

**Investigation:**
```bash
# Memory usage analysis
ps aux --sort=-rss | head -20
smem -r -s rss

# Memory leaks detection
valgrind --tool=memcheck --leak-check=full python rollback_orchestrator.py

# System memory analysis
cat /proc/meminfo
free -h
```

**Solutions:**
```bash
# Increase swap space
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Memory optimization
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
echo 'vm.vfs_cache_pressure=50' | sudo tee -a /etc/sysctl.conf

# Process memory limits
systemctl edit pratiko-rollback
# Add:
# [Service]
# MemoryLimit=1G
```

### Network Performance

**Symptoms:**
- Slow rollback operations
- Timeout errors
- Network congestion

**Investigation:**
```bash
# Network throughput testing
iperf3 -c api.pratiko.ai -p 80
curl -w "@curl-format.txt" https://api.pratiko.ai/health

# Connection analysis
ss -tuln | grep rollback
netstat -i

# Bandwidth monitoring
iftop -i eth0
nethogs
```

**Solutions:**
```bash
# Network optimization
echo 'net.core.rmem_max = 16777216' | sudo tee -a /etc/sysctl.conf
echo 'net.core.wmem_max = 16777216' | sudo tee -a /etc/sysctl.conf

# Connection pooling
export ROLLBACK_CONNECTION_POOL_SIZE=10
export ROLLBACK_CONNECTION_TIMEOUT=30

# Rate limiting
trickle -d 1000 -u 1000 python rollback_orchestrator.py
```

---

## 🔄 Recovery Procedures

### Partial Rollback Recovery

If a rollback partially completes:

```bash
# 1. Assess current state
python rollback-status.py deployment-id

# 2. Identify completed/failed components
grep "rollback.*step.*completed\|failed" /var/log/pratiko-rollback/rollback_execution.log

# 3. Manual completion of failed steps
# Backend
docker tag pratiko-backend:v1.2.0 pratiko-backend:latest
docker-compose up -d backend

# Database
python manage.py migrate app_name 0044_target_migration

# Frontend
aws s3 sync s3://pratiko-assets/v2.0.5/ s3://pratiko-assets/current/

# 4. Verify system health
curl https://api.pratiko.ai/health
```

### Failed Health Check Recovery

If health checks are failing after rollback:

```bash
# 1. Manual health verification
curl -v https://api.pratiko.ai/health
curl -v https://pratiko.ai/health

# 2. Service restart
sudo systemctl restart nginx
sudo systemctl restart pratiko-backend

# 3. Clear caches
redis-cli FLUSHALL
aws cloudfront create-invalidation --distribution-id E123456 --paths "/*"

# 4. Database health check
psql $DATABASE_URL -c "SELECT 1;"

# 5. Update health check configuration
vim health_monitor_config.yaml
# Adjust thresholds temporarily
```

### Complete System Recovery

For complete system failure:

```bash
# 1. Emergency backup
sudo tar -czf /backup/emergency-$(date +%Y%m%d-%H%M%S).tar.gz /opt/pratiko/

# 2. Stop all services
sudo systemctl stop pratiko-*

# 3. Database point-in-time recovery
sudo -u postgres pg_basebackup -D /var/lib/postgresql/recovery -Ft -z -P

# 4. Application recovery
cd /opt/pratiko
git checkout last-known-good-commit
docker-compose down
docker-compose pull
docker-compose up -d

# 5. Verify recovery
./health-check.sh
```

---

## 📞 Support Escalation

### When to Escalate

Escalate to senior team members when:

1. **Data Loss Risk**: Any indication of potential data corruption or loss
2. **System-Wide Failure**: Multiple services affected simultaneously
3. **Security Issues**: Suspected security breach or vulnerability
4. **Extended Downtime**: Recovery taking longer than 30 minutes
5. **Unknown Issues**: Problems not covered in this guide

### Escalation Contacts

1. **Level 1 - DevOps Team**: Slack #deployment-alerts
2. **Level 2 - Senior Engineer**: On-call rotation (PagerDuty)
3. **Level 3 - Engineering Manager**: Direct escalation
4. **Level 4 - CTO**: Critical business impact

### Information to Provide

When escalating, include:

```bash
# System information
uname -a
uptime
df -h
free -h

# Service status
systemctl status pratiko-*

# Recent logs
tail -100 /var/log/pratiko-integration.log

# Error summary
grep -i error /var/log/pratiko-rollback/*.log | tail -20

# Current deployment
curl -s https://api.pratiko.ai/version
```

---

**Document Version**: 1.0.0  
**Last Updated**: January 15, 2024  
**Next Review**: February 15, 2024  

For additional support, contact the DevOps team in Slack (#deployment-alerts) or create an issue in the GitHub repository.