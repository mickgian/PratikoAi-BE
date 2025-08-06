# Load Testing for PratikoAI

This document provides comprehensive documentation for the load testing system implemented to validate that PratikoAI can handle 50-100 concurrent users, supporting the target €25k ARR business goal.

## Overview

The load testing framework validates system performance under realistic load conditions, ensuring production readiness for the Italian tax/accounting market with specific focus on:

- **Target Users**: 50-100 concurrent users (€25k ARR = ~50 active customers)
- **Performance SLAs**: <3s single user, <5s @ 50 users, <8s @ 100 users (P95)
- **Error Tolerance**: <1% error rate under normal load, <2% under stress
- **Throughput**: 1000+ requests/minute sustained
- **Cache Performance**: >70% hit rate under load

## Architecture

### Core Components

```
Load Testing Framework
├── TDD Test Suite (tests/test_load_testing.py)
├── Load Testing Tools
│   ├── Locust Implementation (load_testing/locust_tests.py)
│   ├── k6 Implementation (load_testing/k6_tests.js)
│   └── Configuration (load_testing/config.py)
├── Performance Monitoring (load_testing/monitoring.py)
├── Test Framework (load_testing/framework.py)
├── Execution Script (load_testing/run_tests.py)
└── CI/CD Integration (.github/workflows/load_test.yml)
```

### Technology Stack

- **Locust**: Python-based load testing for complex user behavior simulation
- **k6**: JavaScript-based testing for performance thresholds and metrics
- **Performance Monitoring**: Real-time system resource tracking
- **PostgreSQL Monitoring**: Database performance and connection tracking
- **Redis Monitoring**: Cache performance and memory usage
- **Prometheus Integration**: Metrics collection and alerting

## Quick Start

### Prerequisites

```bash
# Install Python dependencies
pip install locust psutil aioredis asyncpg aiohttp aiofiles

# Install k6 (on macOS)
brew install k6

# Install k6 (on Ubuntu)
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6
```

### Environment Setup

```bash
# Set required environment variables
export DATABASE_URL="postgresql://user:password@localhost:5432/pratikoai"
export REDIS_URL="redis://localhost:6379/0"
export JWT_SECRET_KEY="your-secret-key"
export LLM_API_KEY="your-openai-api-key"
export LOAD_TEST_BASE_URL="http://localhost:8000"
```

### Running Load Tests

#### Quick Test (Development)
```bash
# Single user baseline
python load_testing/run_tests.py --users 1 --duration 60

# Normal load test
python load_testing/run_tests.py --users 30 --duration 300

# Target load test (key validation)
python load_testing/run_tests.py --users 50 --duration 600
```

#### Predefined Profiles
```bash
# Normal day simulation
python load_testing/run_tests.py --profile normal_day

# Peak hours (target test)
python load_testing/run_tests.py --profile peak_hours

# Tax deadline stress test
python load_testing/run_tests.py --profile tax_deadline

# Spike test
python load_testing/run_tests.py --profile spike_test
```

#### Full Test Suite
```bash
# Complete validation suite (~30 minutes)
python load_testing/run_tests.py --full-suite
```

## Test Profiles

### Baseline Profile
- **Users**: 1 concurrent user
- **Duration**: 1 minute
- **Purpose**: Establish performance baseline
- **SLA**: P95 response time <3 seconds

### Normal Day Profile  
- **Users**: 30 concurrent users
- **Duration**: 10 minutes
- **Scenario**: Typical business day usage
- **SLA**: P95 response time <4 seconds, <1% errors

### Peak Hours Profile (Critical Test)
- **Users**: 50 concurrent users  
- **Duration**: 10 minutes sustained
- **Purpose**: Validate €25k ARR capacity
- **SLA**: P95 response time <5 seconds, <1% errors, >70% cache hits

### Tax Deadline Profile
- **Users**: 100 concurrent users
- **Duration**: 30 minutes
- **Scenario**: Tax deadline rush
- **SLA**: P95 response time <8 seconds, <2% errors

### Stress Test Profile
- **Users**: 150 concurrent users
- **Duration**: 10 minutes
- **Purpose**: Find breaking point
- **SLA**: Graceful degradation, no crashes

### Spike Test Profile
- **Users**: 10 → 100 users in 30 seconds
- **Duration**: 10 minutes total
- **Purpose**: Validate auto-scaling and recovery
- **SLA**: System recovery within 2 minutes

## User Scenarios

### Italian Market Scenarios

#### Simple Query (30% of traffic)
```
User actions:
1. Login with test credentials
2. Submit common Italian tax questions:
   - "Come calcolare l'IVA?"
   - "Scadenze fiscali per SRL"
   - "Regime forfettario requisiti"
3. Expect FAQ-style responses <3 seconds
4. High cache hit rate expected
```

#### Complex Query (25% of traffic)
```
User actions:
1. Submit detailed analysis requests:
   - "Analizza le implicazioni fiscali di una SRL che diventa SPA"
   - "Strategie di pianificazione fiscale per startup innovative"
2. Expect comprehensive responses <5 seconds
3. LLM processing with potential retries
```

#### Tax Calculation (20% of traffic)
```
User actions:
1. Submit tax calculation requests:
   - IVA, IRPEF, IMU calculations
   - Various Italian regions
   - Different income/property values
2. Expect precise calculations <2 seconds
3. Validate accuracy under load
```

#### Document Upload (10% of traffic)
```
User actions:
1. Upload Italian tax documents:
   - Fattura elettronica (PDF)
   - F24 forms
   - Dichiarazione dei redditi
2. Expect document analysis <30 seconds
3. Queue management for heavy processing
```

#### Knowledge Search (10% of traffic)
```
User actions:
1. Search regulatory knowledge base:
   - "Circolare Agenzia Entrate 2024"
   - "Normativa fatturazione elettronica"
2. Expect search results <3 seconds
3. Efficient index performance
```

#### User Operations (5% of traffic)
```
User actions:
1. Profile management
2. Subscription status
3. Usage statistics
4. Account settings
2. Expect fast responses <1 second
```

## Performance Monitoring

### System Metrics Tracked

#### CPU and Memory
```python
# Collected every 5 seconds during tests
- CPU usage percentage
- Memory usage percentage and absolute values
- Load averages (1m, 5m, 15m)
- Process count
```

#### Database Performance
```sql
-- PostgreSQL metrics
- Active/idle connection counts
- Query performance statistics
- Slow query identification (>1000ms)
- Cache hit ratios
- Database size and growth
- Lock waits and deadlocks
```

#### Redis Performance
```
- Memory usage (current and peak)
- Connected clients
- Commands per second
- Cache hit/miss ratios
- Key eviction and expiration
```

#### Application Metrics
```python
- Request rate and response times (P50, P95, P99)
- Error rates by endpoint
- LLM request counts and retry statistics
- Circuit breaker states
- Queue sizes for background processing
```

### Alert Thresholds

```yaml
System Alerts:
  cpu_percent: >80%
  memory_percent: >90%
  
Database Alerts:
  total_connections: >80 (of max 100)
  slow_queries: >10 per minute
  
Application Alerts:
  response_time_p95: >5000ms
  error_rate: >1%
  
Cache Alerts:
  cache_hit_rate: <70%
  redis_memory: >4GB
```

## Running Tests Locally

### 1. Environment Preparation

```bash
# Start required services
docker-compose up -d postgres redis

# Run database migrations
uv run alembic upgrade head

# Start the application
uv run uvicorn app.main:app --reload
```

### 2. Test User Setup

The framework automatically creates 200 test users:
```
Email: loadtest_user_1@pratikoai.it to loadtest_user_200@pratikoai.it
Password: TestPassword123!
Company: Test Company 1 to Test Company 200
VAT: IT00000000001 to IT00000000200
```

### 3. Execute Tests

```bash
# Quick validation (development)
python load_testing/run_tests.py --users 10 --duration 120

# Target capacity test (key validation)
python load_testing/run_tests.py --profile peak_hours

# Full suite (pre-production validation)
python load_testing/run_tests.py --full-suite
```

### 4. Analyze Results

Results are saved to `load_test_results/` directory:
```
load_test_results/
├── load_test_report_YYYYMMDD_HHMMSS.json    # Detailed JSON report
├── load_test_summary_YYYYMMDD_HHMMSS.md     # Human-readable summary
├── locust_results.html                       # Locust web UI results
├── k6_summary.html                          # k6 performance report
└── performance_snapshots.json               # System metrics timeline
```

## CI/CD Integration

### Automated Testing Schedule

```yaml
Triggers:
  - Weekly: Complete test suite (Sundays 2 AM UTC)
  - Push/PR: Quick load test (10 users, 60s)
  - Manual: Custom parameters via workflow_dispatch

Test Types by Trigger:
  - PR/Push: Light validation (5 minutes)
  - Scheduled: Full suite (45 minutes)
  - Manual: Configurable profiles and parameters
```

### GitHub Actions Workflow

The workflow automatically:
1. Sets up test environment (PostgreSQL, Redis, Prometheus)
2. Optimizes system settings for load testing
3. Runs comprehensive test suite
4. Collects system metrics and generates reports
5. Creates GitHub issues on failure
6. Comments on PRs with test results
7. Publishes reports to GitHub Pages

### Performance Regression Detection

Automated regression analysis compares current results with previous runs:
```python
# Alert if performance degrades >10%
regression_threshold = 0.10

if (current_p95 - previous_p95) / previous_p95 > regression_threshold:
    create_github_issue("Performance Regression Detected")
```

## Interpreting Results

### Success Criteria

#### Critical Test (50 Users - Peak Hours)
```
✅ PASS Criteria:
- P95 response time: <5000ms
- Error rate: <1%
- Throughput: >1000 req/min
- Cache hit rate: >70%

❌ FAIL if any criteria not met
```

#### Stress Test (100 Users)
```
✅ PASS Criteria:
- P95 response time: <8000ms
- Error rate: <2%
- No system crashes
- Graceful degradation

🟡 WARNING if approaching limits
```

### Performance Baseline Establishment

Single user baseline provides reference metrics:
```json
{
  "single_user_p95": 1200,     // ms - optimal performance
  "optimal_throughput": 50,     // req/min per user
  "baseline_error_rate": 0.0,   // 0% errors expected
  "resource_baseline": {
    "cpu_baseline": 15,         // % CPU per user
    "memory_baseline": 25       // % memory per user
  }
}
```

### Bottleneck Identification

The system automatically identifies performance bottlenecks:

#### CPU Bottleneck
```
Indicators:
- Average CPU >80%
- High load averages
- Response time correlation with CPU

Recommendations:
- Scale CPU resources (horizontal/vertical)
- Optimize CPU-intensive operations
- Implement request queuing
```

#### Memory Bottleneck
```
Indicators:
- Memory usage >85%
- Increasing memory over time (leaks)
- OOM errors in logs

Recommendations:
- Increase memory allocation
- Optimize memory usage patterns
- Implement memory monitoring
```

#### Database Bottleneck
```
Indicators:
- Connection pool exhaustion (>80 connections)
- High slow query count
- Lock waits and deadlocks

Recommendations:
- Increase connection pool size
- Add database read replicas
- Optimize query performance
- Implement connection pooling
```

#### Cache Bottleneck
```
Indicators:
- Cache hit rate <70%
- High cache eviction rate
- Redis memory pressure

Recommendations:
- Increase Redis memory
- Optimize cache keys and TTL
- Implement cache warming
- Review caching strategy
```

## Scaling Recommendations

### Infrastructure Scaling

Based on load test results, the system provides specific scaling recommendations:

#### CPU Scaling
```yaml
Trigger: Average CPU >70%
Recommendation:
  component: "CPU"
  current: "2 cores"
  recommended: "4 cores"
  priority: "HIGH"
  cost: "€50-100/month"
  effort: "LOW"
  improvement: "40% performance gain"
```

#### Memory Scaling
```yaml
Trigger: Memory usage >80%
Recommendation:
  component: "Memory"
  current: "4GB RAM"
  recommended: "8GB RAM"
  priority: "HIGH"
  cost: "€30-60/month"  
  effort: "LOW"
  improvement: "35% performance gain"
```

#### Database Scaling
```yaml
Trigger: DB connections >70 or slow queries >10/min
Recommendation:
  component: "Database"
  current: "Single PostgreSQL instance"
  recommended: "Primary + 2 read replicas"
  priority: "MEDIUM"
  cost: "€100-200/month"
  effort: "MEDIUM"
  improvement: "25% query performance"
```

### Application Optimization

#### Code-Level Optimizations
```python
# Query optimization
- Add database indexes for frequent queries
- Implement query result caching
- Use database connection pooling
- Optimize ORM queries (avoid N+1)

# Cache optimization
- Increase cache TTL for stable data
- Implement cache warming strategies
- Use Redis clustering for scale
- Add cache compression

# API optimization
- Implement request batching
- Add response compression
- Use async/await patterns
- Optimize serialization
```

#### Infrastructure Optimization
```yaml
# Load balancing
- Implement sticky sessions for better cache hits
- Use health checks for automatic failover
- Configure proper connection limits

# Auto-scaling
- Set up horizontal pod autoscaling
- Configure based on CPU and memory metrics
- Implement gradual scale-up/down

# Monitoring
- Add APM for detailed performance insights
- Implement distributed tracing
- Set up comprehensive alerting
```

## Troubleshooting

### Common Issues

#### High Response Times
```bash
# Check system resources
htop
iotop -ao

# Database analysis
psql -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"
psql -c "SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# Redis analysis
redis-cli info memory
redis-cli slowlog get 10
```

#### High Error Rates
```bash
# Check application logs
tail -f app.log | grep ERROR

# Database connection issues
psql -c "SELECT count(*) FROM pg_stat_activity;"

# API health check
curl -f http://localhost:8000/health
```

#### Cache Performance Issues
```bash
# Redis performance
redis-cli info stats
redis-cli info commandstats

# Cache hit rate analysis
redis-cli eval "return redis.call('INFO', 'stats')" 0 | grep hit_rate
```

### Load Test Failures

#### Setup Failures
```bash
# Test user creation issues
Check: Database connectivity
Check: API authentication endpoints
Check: Rate limiting configuration

# Environment issues  
Check: Required environment variables
Check: Service dependencies (PostgreSQL, Redis)
Check: Network connectivity to test target
```

#### Test Execution Failures
```bash
# Locust failures
Check: Python dependencies installed
Check: Test script syntax and imports
Check: Network timeouts and rate limits

# k6 failures
Check: k6 installation and version
Check: JavaScript syntax in test scripts
Check: Environment variable configuration
```

#### Results Analysis Failures
```bash
# Missing results files
Check: Test completed successfully
Check: Results directory permissions
Check: Disk space availability

# Metric collection failures
Check: Monitoring service connectivity
Check: Database query permissions
Check: Redis connection stability
```

## Emergency Procedures

### Production Load Exceeds Capacity

#### Immediate Actions (0-15 minutes)
```bash
1. Enable emergency rate limiting
2. Scale infrastructure immediately:
   - Horizontal: Add application instances
   - Vertical: Increase CPU/memory
3. Enable cache-only mode for common queries
4. Redirect traffic to maintenance page if needed
```

#### Short-term Actions (15 minutes - 1 hour)
```bash
1. Analyze performance bottlenecks in real-time
2. Optimize database queries causing slowdowns
3. Implement connection pooling if not present
4. Scale database read replicas
5. Communicate with users about temporary slowdowns
```

#### Long-term Actions (1+ hours)
```bash
1. Conduct thorough post-incident analysis
2. Implement permanent infrastructure scaling
3. Improve monitoring and alerting
4. Update load testing scenarios based on actual patterns
5. Review and update capacity planning
```

### Load Test Alert Response

#### High CPU Alert (>80%)
```bash
1. Check if test is within expected parameters
2. Verify no background processes interfering
3. Monitor for memory leaks or infinite loops
4. Consider test environment limitations
5. Update CPU scaling recommendations
```

#### Database Connection Exhaustion
```bash
1. Identify connection pool configuration
2. Check for connection leaks in application code
3. Monitor long-running queries
4. Consider connection pool size increase
5. Implement connection timeout policies
```

#### Memory Exhaustion
```bash
1. Check for memory leaks in application
2. Monitor garbage collection patterns
3. Verify cache size configurations
4. Check for large object allocations
5. Consider memory scaling recommendations
```

## Monthly Load Testing Schedule

### Recommended Testing Cadence

#### Weekly (Automated)
- **Sunday 2 AM UTC**: Full test suite
- **Purpose**: Continuous performance validation
- **Duration**: 45 minutes
- **Scope**: All profiles with comprehensive monitoring

#### Monthly (Manual)
- **First Monday**: Capacity planning review
- **Purpose**: Update scaling recommendations
- **Duration**: 2 hours including analysis
- **Scope**: Extended stress testing and future capacity modeling

#### Quarterly (Comprehensive)
- **End of quarter**: Performance baseline update
- **Purpose**: Major version validation and capacity planning
- **Duration**: Half day including documentation updates
- **Scope**: Full suite + custom scenarios + infrastructure planning

#### Pre-Release (As Needed)
- **Before major releases**: Complete validation
- **Purpose**: Ensure no performance regressions
- **Duration**: 1-2 hours
- **Scope**: Target profile + regression testing

### Test Result Review Process

#### Weekly Review
```markdown
1. Automated review via GitHub Actions
2. Alert on test failures or performance regressions >10%
3. Update performance baseline if significant improvements
4. Archive results for historical analysis
```

#### Monthly Review
```markdown
1. Development team review of trends and patterns
2. Infrastructure scaling decisions based on results
3. Update load testing scenarios based on production patterns
4. Review and update performance SLAs if needed
```

#### Quarterly Review
```markdown
1. Complete performance analysis with stakeholders
2. Capacity planning for next quarter's growth
3. Load testing framework improvements
4. Update business requirements and user projections
```

## Performance Baseline Requirements

### Response Time Requirements

| User Load | P95 Response Time | P99 Response Time |
|-----------|------------------|------------------|
| 1 user    | <3 seconds       | <5 seconds       |
| 30 users  | <4 seconds       | <6 seconds       |
| 50 users  | <5 seconds       | <8 seconds       |
| 100 users | <8 seconds       | <12 seconds      |

### Throughput Requirements

| User Load | Min Throughput   | Target Throughput |
|-----------|------------------|-------------------|
| 1 user    | 20 req/min       | 60 req/min        |
| 30 users  | 600 req/min      | 1200 req/min      |
| 50 users  | 1000 req/min     | 2000 req/min      |
| 100 users | 1500 req/min     | 3000 req/min      |

### Error Rate Requirements

| Test Type    | Max Error Rate | Notes                    |
|--------------|----------------|--------------------------|
| Normal Load  | 1%             | Business hours simulation |
| Peak Load    | 1%             | Target capacity test      |
| Stress Test  | 2%             | Graceful degradation      |
| Spike Test   | 5%             | During spike only         |

### Resource Utilization Limits

| Resource     | Warning Level | Critical Level | Action Required       |
|--------------|---------------|----------------|-----------------------|
| CPU          | 70%           | 80%            | Scale CPU resources   |
| Memory       | 80%           | 90%            | Scale memory          |
| DB Conn      | 70            | 80             | Optimize connections  |
| Redis Memory | 4GB           | 6GB            | Scale Redis           |

## Italian Market Specific Requirements

### Tax Calculation Performance
- **Simple calculations** (IVA, basic IRPEF): <1 second
- **Complex calculations** (multi-region, multiple taxes): <2 seconds  
- **Bulk calculations** (batch processing): <30 seconds for 100 items

### Document Processing Performance
- **Small documents** (<1MB PDF): <10 seconds
- **Medium documents** (1-5MB PDF): <30 seconds
- **Large documents** (>5MB PDF): <60 seconds
- **Concurrent processing**: Max 20 documents simultaneously

### Knowledge Base Search Performance
- **Simple queries**: <1 second
- **Complex regulatory searches**: <3 seconds
- **Full-text searches**: <2 seconds
- **Search index updates**: <5 minutes (background)

### Regulatory Compliance Performance
- **GDPR data export**: <60 seconds
- **GDPR data deletion**: <30 seconds
- **Audit log queries**: <5 seconds
- **Compliance report generation**: <120 seconds

---

**Last Updated**: December 5, 2024  
**Version**: 1.0  
**Authors**: PratikoAI Development Team

For questions or issues with load testing, please refer to the troubleshooting section above or contact the development team.