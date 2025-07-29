# 🔍 Troubleshooting Guide

Common issues and solutions for the PratikoAI Version Management System.

## 🚨 Common Issues

### Database Connection Issues

#### Problem: "Database connection failed"

```bash
ERROR: Database connection failed: could not connect to server
```

**Causes:**
- Database server not running
- Incorrect connection credentials
- Network connectivity issues
- Database doesn't exist

**Solutions:**

1. **Check database server status:**
```bash
# PostgreSQL
sudo systemctl status postgresql
pg_isready -h localhost -p 5432

# Start if not running
sudo systemctl start postgresql
```

2. **Verify connection string:**
```bash
# Test connection manually
psql -h localhost -U version_manager -d version_registry

# Check environment variable
echo $VERSION_REGISTRY_DB_URL
```

3. **Create database if missing:**
```sql
-- As postgres superuser
CREATE DATABASE version_registry;
CREATE USER version_manager WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE version_registry TO version_manager;
```

4. **Initialize schema:**
```bash
python -c "
from registry.database import init_database
db = init_database()
print('Database initialized successfully!')
"
```

---

### API Service Issues

#### Problem: "API service not responding"

```bash
curl: (7) Failed to connect to localhost port 8001: Connection refused
```

**Solutions:**

1. **Check service status:**
```bash
sudo systemctl status pratiko-version-api
```

2. **Check if port is in use:**
```bash
sudo netstat -tlnp | grep 8001
sudo lsof -i :8001
```

3. **Start service manually for debugging:**
```bash
cd /path/to/version-management
python -m uvicorn registry.api:app --host 0.0.0.0 --port 8001 --reload
```

4. **Check logs:**
```bash
sudo journalctl -u pratiko-version-api -f
tail -f /var/log/pratiko-version/app.log
```

#### Problem: "Internal Server Error (500)"

**Debug steps:**

1. **Enable debug logging:**
```bash
export LOG_LEVEL=DEBUG
python -m registry.api
```

2. **Check application logs:**
```bash
# Look for Python tracebacks
grep -A 20 "ERROR" /var/log/pratiko-version/app.log
```

3. **Test database connectivity from API:**
```bash
curl http://localhost:8001/health
```

---

### Authentication Issues

#### Problem: "401 Unauthorized"

```json
{
  "error": "unauthorized",
  "message": "Invalid or missing authentication token"
}
```

**Solutions:**

1. **Verify token format:**
```bash
# Token should be passed in Authorization header
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8001/api/v1/versions
```

2. **Check token validity:**
```bash
# Decode JWT token (if using JWT)
python -c "
import jwt
token = 'YOUR_TOKEN'
try:
    payload = jwt.decode(token, options={'verify_signature': False})
    print('Token payload:', payload)
except Exception as e:
    print('Token decode error:', e)
"
```

3. **Generate new token:**
```bash
# Using the CLI
python cli/version_cli.py generate-token --user john.doe

# Or via API (if admin access available)
curl -X POST http://localhost:8001/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin_password"}'
```

---

### Version Registration Issues

#### Problem: "Version already exists"

```json
{
  "error": "version_exists",
  "message": "Version 1.2.0 already exists for backend"
}
```

**Solutions:**

1. **Check existing version:**
```bash
python cli/version_cli.py show backend 1.2.0
```

2. **Use different version number:**
```bash
# Increment patch version
python cli/version_cli.py register --version 1.2.1

# Or use build-specific version
python cli/version_cli.py register --version 1.2.0-build.$(date +%s)
```

3. **Update existing version (if allowed):**
```bash
curl -X PUT http://localhost:8001/api/v1/versions/backend/1.2.0 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"release_notes": "Updated release notes"}'
```

#### Problem: "Invalid version format"

**Solutions:**

1. **Use semantic versioning:**
```bash
# Good
python cli/version_cli.py register --version 1.2.3
python cli/version_cli.py register --version 1.2.3-alpha.1

# Bad
python cli/version_cli.py register --version v1.2.3
python cli/version_cli.py register --version 1.2
```

2. **Check version validation rules:**
```python
import re
version_pattern = r'^\d+\.\d+\.\d+(-[a-zA-Z0-9.-]+)?$'
version = "1.2.3-alpha.1"
if re.match(version_pattern, version):
    print("Valid version format")
else:
    print("Invalid version format")
```

---

### Compatibility Check Issues

#### Problem: "Compatibility check failed"

```bash
ERROR: Compatibility check failed: Service backend version 1.3.0 not found
```

**Solutions:**

1. **Verify version exists:**
```bash
python cli/version_cli.py list --service backend
```

2. **Register missing version:**
```bash
python cli/version_cli.py register \
  --service backend \
  --version 1.3.0 \
  --git-commit $(git rev-parse HEAD)
```

3. **Check dependency requirements:**
```bash
python cli/version_cli.py show backend 1.3.0
# Look at the dependencies section
```

#### Problem: "Deployment blocked by compatibility issues"

```bash
❌ Deployment blocked due to compatibility issues
- Incompatible with frontend-android 2.1.0
- Required dependency backend 1.2.0+ not satisfied
```

**Solutions:**

1. **Review compatibility report:**
```bash
python scripts/compatibility_checker.py \
  --service backend \
  --version 1.3.0 \
  --environment production \
  --output detailed-report.json

# Review the issues
cat detailed-report.json | jq '.blocking_issues'
```

2. **Update dependent services first:**
```bash
# Deploy required backend version first
python cli/version_cli.py validate backend 1.2.0 production

# Then deploy your service
python cli/version_cli.py validate frontend-android 2.1.0 production
```

3. **Use compatibility override (emergency only):**
```bash
python scripts/compatibility_checker.py \
  --service backend \
  --version 1.3.0 \
  --environment production \
  --skip-compatibility-check
```

---

### CI/CD Integration Issues

#### Problem: "GitHub Actions workflow fails"

```yaml
Error: Version registry not accessible
```

**Solutions:**

1. **Check GitHub Secrets:**
```bash
# Verify these secrets are set in your repository:
# - VERSION_REGISTRY_URL
# - VERSION_REGISTRY_TOKEN
# - VERSION_REGISTRY_DB_URL (if needed)
```

2. **Test API connectivity from GitHub Actions:**
```yaml
- name: Test API Connectivity
  run: |
    curl -f $VERSION_REGISTRY_URL/health || exit 1
    echo "API is accessible"
```

3. **Check workflow permissions:**
```yaml
# In your workflow file
permissions:
  contents: read
  pull-requests: write  # For PR comments
  checks: write         # For check status
```

#### Problem: "Version generation fails in CI"

**Solutions:**

1. **Ensure Git history is available:**
```yaml
- name: Checkout Code
  uses: actions/checkout@v4
  with:
    fetch-depth: 0  # Full history needed for version generation
```

2. **Set Git user for version operations:**
```yaml
- name: Configure Git
  run: |
    git config --global user.name "GitHub Actions"
    git config --global user.email "actions@github.com"
```

---

### Performance Issues

#### Problem: "API responses are slow"

**Diagnostics:**

1. **Check database performance:**
```sql
-- Check long-running queries
SELECT query, query_start, state, wait_event_type 
FROM pg_stat_activity 
WHERE state != 'idle' AND query_start < now() - interval '10 seconds';

-- Check table sizes
SELECT schemaname, tablename, pg_total_relation_size(schemaname||'.'||tablename) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY size DESC;
```

2. **Check API metrics:**
```bash
curl http://localhost:8001/metrics | grep response_time
```

**Solutions:**

1. **Add database indexes:**
```sql
-- Common indexes for performance
CREATE INDEX CONCURRENTLY idx_versions_service_created_at 
ON service_versions(service_type, created_at DESC);

CREATE INDEX CONCURRENTLY idx_deployments_env_service 
ON deployments(environment, service_type, deployed_at DESC);
```

2. **Enable caching:**
```bash
export REDIS_URL=redis://localhost:6379/0
export CACHE_TTL=300  # 5 minutes
```

3. **Optimize database connection pooling:**
```bash
export DB_POOL_SIZE=20
export DB_MAX_OVERFLOW=30
export DB_POOL_TIMEOUT=30
```

#### Problem: "High memory usage"

**Solutions:**

1. **Monitor memory usage:**
```bash
# Check API process
ps aux | grep "registry.api"
top -p $(pgrep -f "registry.api")
```

2. **Optimize query results:**
```python
# Use pagination for large result sets
python cli/version_cli.py list --service backend --limit 10

# Avoid loading full objects when not needed
versions = db.get_versions_by_service(ServiceType.BACKEND, limit=100)
```

---

### Data Consistency Issues

#### Problem: "Version registry out of sync"

**Symptoms:**
- Compatibility checks pass but deployments fail
- Different results from CLI vs API
- Missing deployment records

**Solutions:**

1. **Verify data consistency:**
```bash
# Check for orphaned records
python -c "
from registry.database import init_database
db = init_database()
orphans = db.find_orphaned_dependencies()
print(f'Found {len(orphans)} orphaned dependencies')
"
```

2. **Rebuild compatibility matrix:**
```bash
python scripts/rebuild_compatibility_matrix.py --all-services
```

3. **Sync deployment status:**
```bash
# Sync with actual deployment status
python scripts/sync_deployment_status.py --environment production
```

---

### Backup and Recovery Issues

#### Problem: "Database backup fails"

**Solutions:**

1. **Check backup script permissions:**
```bash
ls -la /opt/pratiko-version/backup.sh
chmod +x /opt/pratiko-version/backup.sh
```

2. **Test backup manually:**
```bash
cd /opt/pratiko-version
./backup.sh
ls -la backups/
```

3. **Verify backup integrity:**
```bash
# Test restore to temporary database
createdb version_registry_test
gunzip -c backups/version_registry_20240115_020000.sql.gz | \
  psql -h localhost -U version_manager -d version_registry_test
```

#### Problem: "Recovery process fails"

**Solutions:**

1. **Stop all services:**
```bash
sudo systemctl stop pratiko-version-api
```

2. **Restore database:**
```bash
# Drop and recreate database
dropdb version_registry
createdb version_registry
gunzip -c backup_file.sql.gz | psql -h localhost -U version_manager -d version_registry
```

3. **Verify data integrity:**
```bash
python -c "
from registry.database import init_database
db = init_database()
count = db.get_total_versions()
print(f'Restored {count} versions')
"
```

---

## 🔧 Diagnostic Tools

### Health Check Script

Create a comprehensive health check:

```python
#!/usr/bin/env python3
# health_check.py

import sys
import requests
import asyncio
import psycopg2
from registry.database import init_database

async def check_system_health():
    issues = []
    
    # 1. Database connectivity
    try:
        db = init_database()
        count = db.get_total_versions()
        print(f"✅ Database: {count} versions found")
    except Exception as e:
        issues.append(f"❌ Database: {e}")
    
    # 2. API connectivity
    try:
        response = requests.get("http://localhost:8001/health", timeout=10)
        if response.status_code == 200:
            print("✅ API: Service healthy")
        else:
            issues.append(f"❌ API: HTTP {response.status_code}")
    except Exception as e:
        issues.append(f"❌ API: {e}")
    
    # 3. Version operations
    try:
        from scripts.compatibility_checker import CompatibilityChecker
        checker = CompatibilityChecker(db)
        print("✅ Compatibility Checker: Available")
    except Exception as e:
        issues.append(f"❌ Compatibility Checker: {e}")
    
    # Summary
    if issues:
        print("\n🚨 Issues found:")
        for issue in issues:
            print(f"  {issue}")
        sys.exit(1)
    else:
        print("\n✅ All systems healthy")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(check_system_health())
```

Run with:
```bash
python health_check.py
```

### Log Analysis Script

```bash
#!/bin/bash
# analyze_logs.sh

LOG_FILE="/var/log/pratiko-version/app.log"

echo "📊 Log Analysis Report"
echo "====================="

# Error count
echo "Errors in last 24h:"
grep -c "ERROR" $LOG_FILE | tail -n 1440

# Most common errors
echo -e "\nMost common errors:"
grep "ERROR" $LOG_FILE | cut -d' ' -f4- | sort | uniq -c | sort -nr | head -5

# API response times
echo -e "\nSlow API requests (>5s):"
grep "response_time" $LOG_FILE | awk '$NF > 5000' | tail -10

# Database issues
echo -e "\nDatabase errors:"
grep -i "database\|postgresql\|connection" $LOG_FILE | grep ERROR | tail -5
```

### Performance Monitor

```python
#!/usr/bin/env python3
# performance_monitor.py

import time
import psutil
import requests
from datetime import datetime

def monitor_performance():
    while True:
        timestamp = datetime.now().isoformat()
        
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # API metrics
        try:
            start_time = time.time()
            response = requests.get("http://localhost:8001/health")
            api_response_time = (time.time() - start_time) * 1000
            api_status = response.status_code
        except:
            api_response_time = -1
            api_status = 0
        
        print(f"{timestamp} | CPU: {cpu_percent:5.1f}% | "
              f"MEM: {memory.percent:5.1f}% | "
              f"DISK: {disk.percent:5.1f}% | "
              f"API: {api_response_time:6.1f}ms ({api_status})")
        
        time.sleep(60)  # Monitor every minute

if __name__ == "__main__":
    monitor_performance()
```

---

## 📞 Getting Help

### Before Asking for Help

1. **Check the logs:**
```bash
sudo journalctl -u pratiko-version-api --since "1 hour ago"
tail -100 /var/log/pratiko-version/app.log
```

2. **Run health checks:**
```bash
python health_check.py
curl http://localhost:8001/health
```

3. **Gather system information:**
```bash
# System info
uname -a
python --version
psql --version

# Service status
sudo systemctl status pratiko-version-api postgresql

# Configuration
echo "DB URL: $VERSION_REGISTRY_DB_URL"
echo "API URL: $VERSION_REGISTRY_URL"
```

### Support Channels

1. **Documentation**: Review all guides in the `docs/` directory
2. **Issues**: Create GitHub issue with full diagnostic information
3. **Team Chat**: #version-management Slack channel
4. **Emergency**: Page the on-call engineer

### Creating Good Bug Reports

Include:

1. **What you were trying to do**
2. **What you expected to happen**
3. **What actually happened**
4. **Error messages** (full stack traces)
5. **System information** (OS, Python version, etc.)
6. **Steps to reproduce**
7. **Workarounds tried**

Example:
```markdown
## Bug Report: Version Registration Fails

**Expected**: Version 1.2.0 should register successfully
**Actual**: Registration fails with "Database connection timeout"

**Error Message**:
```
ERROR: Database connection failed: timeout expired
Traceback (most recent call last):
  File "registry/database.py", line 45, in get_connection
    conn = psycopg2.connect(self.db_url, timeout=30)
psycopg2.OperationalError: timeout expired
```

**Environment**:
- OS: Ubuntu 20.04
- Python: 3.11.2
- PostgreSQL: 13.8
- Load: High (deployment rush)

**Steps to Reproduce**:
1. Run `python cli/version_cli.py register`
2. Enter service details
3. Wait for timeout

**Attempted Solutions**:
- Restarted API service
- Checked database connectivity
- Reduced connection pool size
```

---

This troubleshooting guide should help resolve most common issues. For complex problems, don't hesitate to reach out to the team with detailed diagnostic information.