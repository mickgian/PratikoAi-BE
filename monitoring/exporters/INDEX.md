# PratikoAI Database Exporters Configuration

This directory contains the configuration for Redis and PostgreSQL exporters that provide business metrics to Prometheus.

## 🏗️ Exporter Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│     Redis       │───▶│Redis Exporter│───▶│   Prometheus    │
│    :6379        │    │    :9121     │    │     :9090       │
│ Cache Metrics   │    │              │    │                 │
└─────────────────┘    └──────────────┘    └─────────────────┘

┌─────────────────┐    ┌──────────────┐           │
│   PostgreSQL    │───▶│PG Exporter   │───────────┘
│    :5433        │    │    :9187     │
│Business Metrics │    │Custom Queries│
└─────────────────┘    └──────────────┘
```

## ✅ Completed Configuration

### 1. Redis Exporter (`:9121`)
- **Status**: ✅ UP and running
- **Metrics**: Cache performance, memory usage, connection counts
- **Key patterns**: LLM responses, conversations, embeddings
- **Health check**: Automated via Docker healthcheck

### 2. PostgreSQL Exporter (`:9187`)
- **Status**: ✅ UP and running
- **Database**: Connected to PratikoAI database on port 5433
- **User**: `postgres_exporter` (read-only monitoring user)
- **Custom queries**: Italian business metrics, user activity, payments

### 3. Security Configuration
- **PostgreSQL port**: Changed from 5432 to 5433 to avoid conflicts
- **Monitoring user**: Read-only access with limited permissions
- **Password**: Securely stored in Docker environment variables
- **Network isolation**: All services on `monitoring` network

## 📊 Business Metrics Available

### User Activity Metrics
```sql
pratikoai_active_users_total_users        # Total registered users
pratikoai_active_users_active_24h         # Users active in 24h
pratikoai_active_users_active_7d          # Users active in 7 days
pratikoai_active_users_active_30d         # Users active in 30 days
```

### Subscription & Revenue Metrics
```sql
pratikoai_subscriptions_subscription_count{status,plan_type}  # Active subscriptions
pratikoai_subscriptions_total_revenue{status,plan_type}       # Revenue by plan
```

### Payment Processing Metrics
```sql
pratikoai_payments_payment_count{status,method}     # Payment volume
pratikoai_payments_total_amount{status,method}      # Payment amounts
pratikoai_payments_avg_amount{status,method}        # Average transaction
```

### Italian Knowledge Base Metrics
```sql
pratikoai_italian_knowledge_total_count{resource_type}    # Documents/calculations
pratikoai_italian_knowledge_recent_count{resource_type}   # Recent activity
pratikoai_italian_knowledge_avg_size{resource_type}       # Average size/value
```

### Database Performance Metrics
```sql
pratikoai_database_performance_live_tuples{table}    # Table row counts
pratikoai_database_performance_dead_tuples{table}    # Cleanup needed
pratikoai_slow_queries_mean_time{query}              # Query performance
```

## 🔧 Configuration Files

### `/postgres_queries.yml`
Contains 7 custom query groups:
- **pratikoai_active_users**: User activity tracking
- **pratikoai_subscriptions**: Subscription metrics by status/plan
- **pratikoai_payments**: Payment processing statistics (30-day window)
- **pratikoai_italian_knowledge**: Italian tax and document metrics
- **pratikoai_database_performance**: Table statistics and performance
- **pratikoai_slow_queries**: Query performance monitoring (>100ms)
- **pg_replication**: Standard PostgreSQL replication metrics

### `/postgres_setup.sql`
Database initialization script that:
- Creates `postgres_exporter` monitoring user
- Grants read-only permissions to all tables
- Enables `pg_stat_statements` extension
- Sets up secure monitoring functions

## 🚀 Current Status

### ✅ Working Exporters
- **Redis Exporter**: `curl http://localhost:9121/metrics`
- **PostgreSQL Exporter**: `curl http://localhost:9187/metrics`
- **Node Exporter**: `curl http://localhost:9100/metrics`

### ⚠️ App Status
- **PratikoAI App**: Currently initializing (downloading ML models)
- **Expected**: Will be available at `http://localhost:8000/metrics` once startup completes
- **Metrics**: 27 custom business metrics already initialized

### 📈 Prometheus Targets
```
prometheus          ✅ UP    (localhost:9090)
redis               ✅ UP    (redis-exporter:9121)
postgres            ✅ UP    (postgres-exporter:9187)
node                ✅ UP    (node-exporter:9100)
pratikoai-app       ⏳ DOWN  (startup in progress)
```

## 🔍 Verification Commands

### Test Redis Metrics
```bash
curl -s http://localhost:9121/metrics | grep redis_connected_clients
curl -s http://localhost:9121/metrics | grep redis_memory_used_bytes
```

### Test PostgreSQL Metrics
```bash
curl -s http://localhost:9187/metrics | grep pg_up
curl -s http://localhost:9187/metrics | grep pratikoai_active_users
```

### Test Prometheus Scraping
```bash
curl -s 'http://localhost:9090/api/v1/query?query=up' | jq '.data.result[]'
curl -s 'http://localhost:9090/api/v1/query?query=redis_connected_clients'
```

## 🛠️ Troubleshooting

### Common Issues

1. **PostgreSQL Connection Refused**
   - Check if database is running: `docker-compose ps db`
   - Verify port 5433 is accessible: `nc -zv localhost 5433`
   - Check exporter logs: `docker-compose logs postgres-exporter`

2. **Redis Metrics Missing**
   - Verify Redis is running: `docker-compose ps redis`
   - Check Redis connectivity: `docker-compose exec redis redis-cli ping`
   - Review exporter config: `docker-compose logs redis-exporter`

3. **Custom Queries Failing**
   - Verify monitoring user exists: Connect to DB and check permissions
   - Test query syntax: Run queries manually in PostgreSQL
   - Check table names match application schema

### Service Restart Commands
```bash
# Restart individual exporters
docker-compose restart redis-exporter
docker-compose restart postgres-exporter

# Restart monitoring stack
docker-compose restart prometheus alertmanager

# View exporter logs
docker-compose logs -f postgres-exporter
docker-compose logs -f redis-exporter
```

## 🎯 Next Steps

1. **Wait for App Startup**: PratikoAI app is downloading ML models (5-10 minutes)
2. **Verify App Metrics**: Once ready, check `http://localhost:8000/metrics`
3. **Create Grafana Dashboards**: Visualize these metrics in Grafana
4. **Set Up Alerting**: Configure alerts based on business thresholds
5. **Test Custom Queries**: Validate Italian business metrics are collecting properly

## 🔐 Security Notes

- **Monitoring user**: Limited to SELECT permissions only
- **Password**: Stored in environment variables, not in code
- **Network**: All services isolated on monitoring network
- **Query limitations**: Custom queries have built-in safety limits
- **Audit trail**: All monitoring access is logged in PostgreSQL
