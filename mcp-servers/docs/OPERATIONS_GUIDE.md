# PratikoAI MCP Server Operations Guide

This comprehensive guide covers day-to-day operations, maintenance procedures, troubleshooting, and disaster recovery for PratikoAI's AWS-optimized MCP (Model Context Protocol) server infrastructure.

## Table of Contents

1. [Daily Operations](#daily-operations)
2. [Monitoring and Alerting](#monitoring-and-alerting) 
3. [Scaling Operations](#scaling-operations)
4. [Backup and Recovery](#backup-and-recovery)
5. [Security Operations](#security-operations)
6. [Troubleshooting](#troubleshooting)
7. [Emergency Procedures](#emergency-procedures)
8. [Maintenance Windows](#maintenance-windows)

## Daily Operations

### Morning Health Checks

Run the comprehensive health check script:

```bash
# Check all environments
./scripts/health-check.sh all report

# Check specific environment
./scripts/health-check.sh production report
```

**Expected Results:**
- All services should show "HEALTHY" status
- Response times should be < 500ms
- Resource utilization should be < 80%
- No critical alerts in monitoring systems

### Performance Monitoring

**Key Metrics to Monitor Daily:**

1. **Request Metrics**
   - Total requests per hour: Should follow expected patterns
   - Error rate: Should be < 1%
   - Response time P95: Should be < 500ms

2. **Resource Utilization**
   - CPU usage: Should be < 70% average
   - Memory usage: Should be < 80% average
   - Disk usage: Should be < 85%

3. **Database Performance**
   - Connection count: Should be < 80% of max
   - Query performance: Slow queries < 1 second
   - Lock contention: Minimal blocking queries

4. **Cache Performance**
   - Redis memory usage: Should be < 80%
   - Cache hit rate: Should be > 95%
   - Eviction rate: Should be minimal

### Log Review

**Daily Log Analysis:**

```bash
# Check for errors in the last 24 hours
kubectl logs -n mcp-production deployment/mcp-server-production --since=24h | grep -i error

# Check authentication failures
kubectl logs -n mcp-production deployment/mcp-server-production --since=24h | grep -i "auth\|unauthorized\|forbidden"

# Check slow queries
kubectl logs -n mcp-production deployment/mcp-server-production --since=24h | grep -i "slow\|timeout"
```

## Monitoring and Alerting

### Grafana Dashboards

**Primary Dashboards:**

1. **MCP Server Overview** - `http://grafana.pratiko.ai/d/mcp-overview`
   - Service health status
   - Request rates and response times
   - Error rates and success rates
   - Resource utilization

2. **Database Dashboard** - `http://grafana.pratiko.ai/d/postgres-dashboard`
   - Connection pools
   - Query performance
   - Lock contention
   - Replication lag

3. **Infrastructure Dashboard** - `http://grafana.pratiko.ai/d/infrastructure`
   - Kubernetes cluster health
   - Node resource utilization
   - Network performance
   - Storage utilization

### Alert Response Procedures

**Critical Alerts (Immediate Response Required):**

1. **Service Down**
   ```bash
   # Check service status
   kubectl get pods -n mcp-production
   
   # Check recent deployments
   kubectl rollout history deployment/mcp-server-production -n mcp-production
   
   # Check pod logs
   kubectl logs -f deployment/mcp-server-production -n mcp-production
   
   # If needed, restart service
   kubectl rollout restart deployment/mcp-server-production -n mcp-production
   ```

2. **High Error Rate (> 5%)**
   ```bash
   # Check error distribution
   kubectl logs --since=10m -n mcp-production deployment/mcp-server-production | grep -i error | tail -50
   
   # Check database connectivity
   kubectl exec -n mcp-production deployment/mcp-server-production -- curl -f http://localhost:8080/health/database
   
   # Check external dependencies
   kubectl exec -n mcp-production deployment/mcp-server-production -- curl -f http://localhost:8080/health/dependencies
   ```

3. **Database Connection Issues**
   ```bash
   # Check PostgreSQL status
   kubectl get pods -n mcp-production -l app=postgresql
   
   # Check connection pool
   kubectl exec -n mcp-production deployment/postgres-production-primary -- psql -c "SELECT count(*) FROM pg_stat_activity;"
   
   # Check for blocking queries
   kubectl exec -n mcp-production deployment/postgres-production-primary -- psql -c "SELECT * FROM pg_stat_activity WHERE wait_event IS NOT NULL;"
   ```

**Warning Alerts (Response Within 30 Minutes):**

1. **High CPU/Memory Usage**
   ```bash
   # Check resource usage
   kubectl top pods -n mcp-production
   
   # Check if auto-scaling is working
   kubectl get hpa -n mcp-production
   
   # Check for resource limits
   kubectl describe pod -n mcp-production -l app=mcp-server
   ```

2. **Slow Response Times**
   ```bash
   # Check application performance
   kubectl exec -n mcp-production deployment/mcp-server-production -- curl -w "@curl-format.txt" -s -o /dev/null http://localhost:8080/health
   
   # Check database performance
   kubectl exec -n mcp-production deployment/postgres-production-primary -- psql -c "SELECT query, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
   ```

## Scaling Operations

### Manual Scaling

**Scale MCP Server:**

```bash
# Scale up during high traffic
kubectl scale deployment/mcp-server-production --replicas=10 -n mcp-production

# Scale down during low traffic
kubectl scale deployment/mcp-server-production --replicas=6 -n mcp-production

# Verify scaling
kubectl get pods -n mcp-production -l app=mcp-server
```

**Scale Database (Read Replicas):**

```bash
# Scale PostgreSQL read replicas
helm upgrade postgres-production bitnami/postgresql-ha \
  --namespace mcp-production \
  --reuse-values \
  --set readReplicas.replicaCount=3
```

### Auto-scaling Configuration

**Modify HPA Settings:**

```bash
# Update CPU threshold
kubectl patch hpa mcp-server-hpa -n mcp-production -p '{"spec":{"metrics":[{"type":"Resource","resource":{"name":"cpu","target":{"type":"Utilization","averageUtilization":50}}}]}}'

# Update max replicas for high traffic periods
kubectl patch hpa mcp-server-hpa -n mcp-production -p '{"spec":{"maxReplicas":20}}'
```

### Traffic Pattern Analysis

**Weekly Traffic Review:**

```bash
# Generate traffic pattern report
kubectl exec -n monitoring deployment/prometheus-server -- promtool query instant 'sum(rate(http_requests_total{job="mcp-server-production"}[24h]))'

# Check peak usage times
kubectl exec -n monitoring deployment/prometheus-server -- promtool query range 'sum(rate(http_requests_total{job="mcp-server-production"}[5m]))' --start="$(date -d '7 days ago' --iso-8601)" --end="$(date --iso-8601)" --step=1h
```

## Backup and Recovery

### Daily Backup Verification

**Check Backup Status:**

```bash
# Check Velero backups
kubectl get backups -n velero --sort-by='.metadata.creationTimestamp'

# Check database backups
aws s3 ls s3://pratiko-backups/production/postgres/ --recursive --human-readable

# Verify backup integrity
kubectl logs -n mcp-production job/postgres-backup-$(date +%Y%m%d) | grep -i "success\|error"
```

### Recovery Procedures

**Database Point-in-Time Recovery:**

```bash
# 1. Stop application traffic
kubectl scale deployment/mcp-server-production --replicas=0 -n mcp-production

# 2. Create recovery instance
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: postgres-recovery
  namespace: mcp-production
spec:
  containers:
  - name: postgres
    image: postgres:15-alpine
    env:
    - name: POSTGRES_PASSWORD
      valueFrom:
        secretKeyRef:
          name: postgres-credentials
          key: password
    volumeMounts:
    - name: recovery-data
      mountPath: /var/lib/postgresql/data
  volumes:
  - name: recovery-data
    persistentVolumeClaim:
      claimName: postgres-recovery-pvc
EOF

# 3. Restore from backup
kubectl exec -n mcp-production postgres-recovery -- pg_restore -d pratiko_mcp_production /backup/latest-backup.sql

# 4. Verify data integrity
kubectl exec -n mcp-production postgres-recovery -- psql -d pratiko_mcp_production -c "SELECT count(*) FROM critical_table;"

# 5. Switch to recovered database and restart application
kubectl scale deployment/mcp-server-production --replicas=6 -n mcp-production
```

**Application Recovery from Backup:**

```bash
# 1. List available backups
velero backup get

# 2. Restore from specific backup
velero restore create --from-backup=daily-backup-20240115

# 3. Monitor restore progress
velero restore describe restore-name --details

# 4. Verify application health
./scripts/health-check.sh production
```

### Disaster Recovery Scenarios

**Complete Region Failure:**

1. **Activate DR Environment:**
   ```bash
   # Switch to DR region
   kubectl config use-context production-dr
   
   # Deploy from backup
   velero restore create --from-backup=latest-cross-region-backup
   
   # Update DNS to point to DR region
   aws route53 change-resource-record-sets --hosted-zone-id Z123456789 --change-batch file://dr-dns-change.json
   ```

2. **Database Failover:**
   ```bash
   # Promote read replica to primary
   aws rds promote-read-replica --db-instance-identifier pratiko-mcp-dr-replica
   
   # Update application configuration
   kubectl patch secret postgres-credentials -n mcp-production -p '{"data":{"host":"new-primary-endpoint"}}'
   
   # Restart application
   kubectl rollout restart deployment/mcp-server-production -n mcp-production
   ```

## Security Operations

### Daily Security Checks

**Security Monitoring:**

```bash
# Check failed authentication attempts
kubectl logs -n mcp-production deployment/mcp-server-production --since=24h | grep -i "authentication failed\|unauthorized" | wc -l

# Check unusual access patterns
kubectl logs -n mcp-production deployment/mcp-server-production --since=24h | grep -E "([0-9]{1,3}\.){3}[0-9]{1,3}" | sort | uniq -c | sort -nr | head -20

# Check for security alerts
kubectl logs -n security deployment/falco --since=24h | grep -i "warning\|error"
```

### Certificate Management

**SSL Certificate Renewal:**

```bash
# Check certificate expiration
echo | openssl s_client -connect mcp.pratiko.ai:443 2>/dev/null | openssl x509 -noout -dates

# Request new certificate (if using cert-manager)
kubectl annotate certificate production-tls -n mcp-production cert-manager.io/issue-temporary-certificate="true"

# Verify new certificate
kubectl describe certificate production-tls -n mcp-production
```

### Access Control Review

**Monthly Access Review:**

```bash
# List all service accounts
kubectl get serviceaccounts -A

# Review RBAC permissions
kubectl auth can-i --list --as=system:serviceaccount:mcp-production:mcp-server-production

# Check for unused secrets
kubectl get secrets -A --sort-by='.metadata.creationTimestamp'
```

## Troubleshooting

### Common Issues and Solutions

**1. High Memory Usage**

*Symptoms:* Pods getting OOMKilled, slow response times

*Diagnosis:*
```bash
# Check memory usage
kubectl top pods -n mcp-production --sort-by=memory

# Check for memory leaks
kubectl exec -n mcp-production deployment/mcp-server-production -- curl http://localhost:8080/metrics | grep memory
```

*Solution:*
```bash
# Increase memory limits
kubectl patch deployment mcp-server-production -n mcp-production -p '{"spec":{"template":{"spec":{"containers":[{"name":"mcp-server","resources":{"limits":{"memory":"8Gi"}}}]}}}}'

# Or restart pods to clear memory
kubectl rollout restart deployment/mcp-server-production -n mcp-production
```

**2. Database Connection Pool Exhaustion**

*Symptoms:* "too many connections" errors, connection timeouts

*Diagnosis:*
```bash
# Check active connections
kubectl exec -n mcp-production deployment/postgres-production-primary -- psql -c "SELECT count(*) FROM pg_stat_activity;"

# Check connection distribution
kubectl exec -n mcp-production deployment/postgres-production-primary -- psql -c "SELECT application_name, count(*) FROM pg_stat_activity GROUP BY application_name;"
```

*Solution:*
```bash
# Increase max connections temporarily
kubectl exec -n mcp-production deployment/postgres-production-primary -- psql -c "ALTER SYSTEM SET max_connections = 200;"
kubectl exec -n mcp-production deployment/postgres-production-primary -- psql -c "SELECT pg_reload_conf();"

# Or restart application pods to reset connections
kubectl rollout restart deployment/mcp-server-production -n mcp-production
```

**3. Redis Performance Issues**

*Symptoms:* Slow cache operations, high Redis CPU usage

*Diagnosis:*
```bash
# Check Redis performance
kubectl exec -n mcp-production deployment/redis-production-master -- redis-cli info stats

# Check slow log
kubectl exec -n mcp-production deployment/redis-production-master -- redis-cli slowlog get 10
```

*Solution:*
```bash
# Clear problematic keys
kubectl exec -n mcp-production deployment/redis-production-master -- redis-cli flushdb

# Or increase Redis memory/CPU limits
helm upgrade redis-production bitnami/redis \
  --namespace mcp-production \
  --reuse-values \
  --set master.resources.limits.memory=4Gi \
  --set master.resources.limits.cpu=2000m
```

### Log Analysis

**Centralized Logging Commands:**

```bash
# Search for specific errors across all pods
kubectl logs -n mcp-production -l app=mcp-server --since=1h | grep -i "database\|connection\|timeout"

# Check application startup logs
kubectl logs -n mcp-production deployment/mcp-server-production | grep -A5 -B5 "Starting\|Started\|Failed"

# Monitor real-time logs with filtering
kubectl logs -f -n mcp-production deployment/mcp-server-production | grep -E "(ERROR|WARN|Exception)"
```

## Emergency Procedures

### Service Outage Response

**Complete Service Outage:**

1. **Immediate Assessment (0-5 minutes)**
   ```bash
   # Check overall service health
   ./scripts/health-check.sh production json
   
   # Check Kubernetes cluster status
   kubectl get nodes
   kubectl get pods -A | grep -v Running
   ```

2. **Traffic Diversion (5-10 minutes)**
   ```bash
   # Activate maintenance page
   kubectl apply -f k8s/maintenance-mode.yaml
   
   # Or redirect traffic to staging
   aws route53 change-resource-record-sets --hosted-zone-id Z123456789 --change-batch file://staging-redirect.json
   ```

3. **Root Cause Analysis (10-30 minutes)**
   ```bash
   # Check recent changes
   kubectl rollout history deployment/mcp-server-production -n mcp-production
   
   # Check system events
   kubectl get events -n mcp-production --sort-by='.lastTimestamp'
   
   # Check infrastructure
   aws ec2 describe-instances --filters "Name=tag:Environment,Values=production"
   ```

4. **Recovery Actions (30+ minutes)**
   ```bash
   # Rollback if recent deployment caused issue
   kubectl rollout undo deployment/mcp-server-production -n mcp-production
   
   # Or restore from backup
   velero restore create --from-backup=pre-incident-backup
   ```

### Security Incident Response

**Suspected Security Breach:**

1. **Immediate Containment**
   ```bash
   # Block suspicious IP addresses
   kubectl apply -f - <<EOF
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: emergency-block
     namespace: mcp-production
   spec:
     podSelector: {}
     policyTypes:
     - Ingress
     ingress:
     - from:
       - ipBlock:
           cidr: 0.0.0.0/0
           except:
           - suspicious.ip.address/32
   EOF
   ```

2. **Evidence Collection**
   ```bash
   # Collect logs
   kubectl logs -n mcp-production deployment/mcp-server-production --since=24h > /tmp/incident-logs.txt
   
   # Take snapshots
   kubectl exec -n mcp-production deployment/postgres-production-primary -- pg_dump pratiko_mcp_production > /tmp/incident-db-dump.sql
   ```

3. **Notification**
   ```bash
   # Send alert to security team
   curl -X POST -H 'Content-type: application/json' \
     --data '{"text":"Security incident detected in production MCP environment"}' \
     $SECURITY_SLACK_WEBHOOK
   ```

## Maintenance Windows

### Scheduled Maintenance Procedures

**Monthly Maintenance Window (2nd Sunday, 2-6 AM EST)**

**Pre-maintenance Checklist:**

```bash
# 1. Create pre-maintenance backup
velero backup create pre-maintenance-backup-$(date +%Y%m%d)

# 2. Scale up replicas for faster rollback if needed
kubectl scale deployment/mcp-server-production --replicas=8 -n mcp-production

# 3. Verify backup integrity
./scripts/verify-backup.sh

# 4. Notify users (if required)
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Maintenance window starting - expect brief service interruptions"}' \
  $STATUS_PAGE_WEBHOOK
```

**Maintenance Activities:**

1. **System Updates**
   ```bash
   # Update Kubernetes nodes
   kubectl drain node-1 --ignore-daemonsets --delete-emptydir-data
   # Perform OS updates on node-1
   kubectl uncordon node-1
   ```

2. **Application Updates**
   ```bash
   # Update MCP server
   kubectl set image deployment/mcp-server-production mcp-server=pratiko/mcp-server:v1.2.0 -n mcp-production
   kubectl rollout status deployment/mcp-server-production -n mcp-production
   ```

3. **Database Maintenance**
   ```bash
   # Run VACUUM and ANALYZE
   kubectl exec -n mcp-production deployment/postgres-production-primary -- psql -c "VACUUM ANALYZE;"
   
   # Update statistics
   kubectl exec -n mcp-production deployment/postgres-production-primary -- psql -c "SELECT pg_stat_reset();"
   ```

**Post-maintenance Verification:**

```bash
# 1. Run comprehensive health check
./scripts/health-check.sh production report

# 2. Verify performance metrics
kubectl exec -n monitoring deployment/prometheus-server -- promtool query instant 'up{job="mcp-server-production"}'

# 3. Scale back to normal replica count
kubectl scale deployment/mcp-server-production --replicas=6 -n mcp-production

# 4. Update documentation
echo "Maintenance completed $(date)" >> docs/maintenance-log.md
```

## Performance Optimization

### Regular Performance Reviews

**Weekly Performance Analysis:**

```bash
# Generate performance report
./scripts/performance-analysis.sh --period=7d --output=report

# Check slow queries
kubectl exec -n mcp-production deployment/postgres-production-primary -- psql -c "SELECT query, mean_time, calls FROM pg_stat_statements WHERE mean_time > 1000 ORDER BY mean_time DESC LIMIT 10;"

# Review cache efficiency
kubectl exec -n mcp-production deployment/redis-production-master -- redis-cli info stats | grep -E "keyspace_hits|keyspace_misses"
```

**Performance Tuning Actions:**

1. **Database Optimization**
   ```bash
   # Create missing indexes
   kubectl exec -n mcp-production deployment/postgres-production-primary -- psql -c "CREATE INDEX CONCURRENTLY idx_table_column ON table_name(column_name);"
   
   # Update table statistics
   kubectl exec -n mcp-production deployment/postgres-production-primary -- psql -c "ANALYZE table_name;"
   ```

2. **Application Optimization**
   ```bash
   # Update resource limits based on usage patterns
   kubectl patch deployment mcp-server-production -n mcp-production -p '{"spec":{"template":{"spec":{"containers":[{"name":"mcp-server","resources":{"requests":{"cpu":"1000m","memory":"2Gi"},"limits":{"cpu":"4000m","memory":"8Gi"}}}]}}}}'
   
   # Adjust auto-scaling parameters
   kubectl patch hpa mcp-server-hpa -n mcp-production -p '{"spec":{"targetCPUUtilizationPercentage":60}}'
   ```

---

## Quick Reference

### Emergency Contacts

- **Platform Engineering Team**: platform-eng@pratiko.ai
- **Security Team**: security@pratiko.ai  
- **PagerDuty**: +1-555-PAGE-DUTY
- **Slack**: #platform-alerts, #security-incidents

### Key URLs

- **Production MCP**: https://mcp.pratiko.ai
- **Staging MCP**: https://mcp-staging.pratiko.ai
- **Grafana**: https://grafana.pratiko.ai
- **Status Page**: https://status.pratiko.ai

### Common Commands

```bash
# Health check
./scripts/health-check.sh production

# Scale service
kubectl scale deployment/mcp-server-production --replicas=N -n mcp-production

# View logs
kubectl logs -f deployment/mcp-server-production -n mcp-production

# Check resource usage
kubectl top pods -n mcp-production

# Emergency rollback
kubectl rollout undo deployment/mcp-server-production -n mcp-production
```

This operations guide should be reviewed and updated monthly to ensure accuracy and completeness.