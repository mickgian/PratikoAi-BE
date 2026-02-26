# PratikoAI Pre-Production KPIs

## Status
ACCEPTED

## Date
2026-02-26

## Context

PratikoAI is not yet in production. Revenue, churn, and growth KPIs are premature at this stage. What matters now is **"does the system work correctly and reliably?"** — the operational foundation that production-readiness depends on.

This document defines the **Top 5 Pre-Production KPIs**, maps them to existing monitoring infrastructure, identifies gaps, and provides a phased expansion plan toward full production KPIs.

---

## Top 5 Pre-Production KPIs

### KPI-1: RAG Answer Quality Score

**What it measures:** Whether the AI gives correct, grounded, relevant answers to Italian professional services queries.

**Why it's #1:** An AI tool for lawyers and accountants that gives wrong answers is worse than no tool. Professional services have zero tolerance for hallucinations on regulatory matters. If quality is poor, nothing else matters.

**Composite score (3 sub-metrics from ADR-032):**

| Sub-Metric | Target | Blocking? | Description |
|---|---|---|---|
| Contextual Precision | > 0.70 | Yes | Are retrieved documents relevant? |
| Faithfulness | > 0.85 | Yes | Is the answer grounded in context (no hallucination)? |
| Answer Relevancy | > 0.75 | Yes | Does the answer actually address the question? |
| Contextual Recall | > 0.70 | No (warning) | Are all relevant documents retrieved? |

**Current infrastructure:**
- DeepEval golden dataset (30-50 Italian CCNL/labor law queries) — defined in ADR-032
- Langfuse stores eval results as scores for trend tracking
- Benchmarks run in CI after QA deployment (`benchmarks.yml`)
- Classification confidence tracked via `classification_confidence_distribution` histogram

**What's missing:**
- User acceptance rate tracking (did the user accept/reject AI output in the UI?)
- Per-feature quality breakdown (normative matching vs document ID vs communications)
- Quality regression alerting beyond CI (continuous monitoring in QA environment)

**How to track:**
```promql
# Average faithfulness across latest benchmark run (from Langfuse)
# Tracked via DeepEval → Langfuse scores pipeline

# Classification confidence (proxy for quality in production)
histogram_quantile(0.50, classification_confidence_distribution)

# Low-confidence fallback rate (signals quality degradation)
rate(query_classifications_total{fallback_used="True"}[1h])
  / rate(query_classifications_total[1h])
```

**Alert rule (add to `alerts.yml`):**
```yaml
- alert: HighClassificationFallbackRate
  expr: >
    rate(query_classifications_total{fallback_used="True"}[1h])
    / rate(query_classifications_total[1h]) > 0.3
  for: 15m
  labels:
    severity: warning
    category: ai_quality
  annotations:
    summary: "High classification fallback rate"
    description: "{{ $value | humanizePercentage }} of queries falling back to LLM classification"
```

---

### KPI-2: API Reliability (Error Rate + Uptime)

**What it measures:** Whether the system stays up and responds correctly.

**Why it's #2:** Users will not tolerate a system that crashes, returns 500 errors, or goes down during working hours. Reliability is the baseline expectation for professional tools.

**Targets:**

| Metric | Target | Critical | Description |
|---|---|---|---|
| API Error Rate | < 1% | > 5% | Percentage of 4xx/5xx responses |
| Uptime | > 99.5% | < 99% | Service availability |
| LLM Provider Error Rate | < 2% | > 5% | External LLM API failures |
| DB Connection Health | > 0 active | = 0 | Database reachability |

**Current infrastructure:**
- `api_errors_total` counter with `[error_category, error_type, endpoint, status_code]` labels
- `up` metric for service availability
- `llm_errors_total` counter with `[provider, error_type, model]` labels
- `database_connections_active` gauge
- Prometheus alerts: `HighErrorRate`, `ServiceDown`, `LLMProviderErrors`, `DatabaseConnectionIssues`
- Health check endpoint: `GET /api/v1/health/rss`

**What's missing:**
- A simple `GET /healthz` liveness probe (current health check is RSS-specific)
- Structured uptime tracking over time windows (daily/weekly/monthly percentage)
- Incident log or MTTR tracking

**How to track:**
```promql
# API error rate (5-minute window)
rate(api_errors_total[5m])
  / rate(http_request_duration_seconds_count[5m]) * 100

# Service uptime
avg_over_time(up{job="pratikoai"}[24h]) * 100

# LLM provider error rate
rate(llm_errors_total[5m])
  / rate(api_calls_total[5m]) * 100
```

---

### KPI-3: Response Latency (P95)

**What it measures:** How fast the system responds to user requests.

**Why it's #3:** Professional users bill by the hour. A slow tool is an expensive tool. If PratikoAI takes 10 seconds to answer what could take 2, users will abandon it.

**Targets:**

| Metric | Target | Critical | Description |
|---|---|---|---|
| API P95 Latency | < 2s | > 5s | 95th percentile HTTP response time |
| API P50 Latency | < 500ms | > 2s | Median HTTP response time |
| Knowledge Base Query P95 | < 1s | > 2s | RAG retrieval step latency |
| CCNL Query P95 | < 5s | > 10s | Complex CCNL lookup latency |

**Current infrastructure:**
- `http_request_duration_seconds` histogram with `[method, endpoint, status_code]` labels and buckets `(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, +Inf)`
- `knowledge_base_query_duration_seconds` histogram with `[query_type, source]`
- `ccnl_query_duration_seconds` histogram with `[query_type, sector]`
- `document_processing_duration_seconds` histogram
- Prometheus alert: `HighAPILatency` (P95 > 5s for 2m)
- k6 load testing from ADR-032: ramp to 10 concurrent users, P95 < 5s

**What's missing:**
- Per-endpoint latency SLOs (chat endpoint vs document upload vs CCNL lookup)
- Latency budget breakdown (how much time is spent in retrieval vs LLM vs post-processing)
- Frontend-perceived latency tracking (time-to-first-byte from the user's browser)

**How to track:**
```promql
# Overall API P95
histogram_quantile(0.95,
  rate(http_request_duration_seconds_bucket[5m]))

# Knowledge base query P95
histogram_quantile(0.95,
  rate(knowledge_base_query_duration_seconds_bucket[5m]))

# Slowest endpoints (top 5)
topk(5, histogram_quantile(0.95,
  rate(http_request_duration_seconds_bucket[5m])))
```

---

### KPI-4: LLM Cost Per Query

**What it measures:** How much each AI-powered interaction costs in infrastructure.

**Why it's #4:** Even pre-production, AI compute costs are real money. If each query costs EUR 0.50 and you price at EUR 0.10, no amount of growth will save you. Understanding unit economics now prevents a loss-making product at launch.

**Targets:**

| Metric | Target | Critical | Description |
|---|---|---|---|
| Cost Per Query | < EUR 0.05 | > EUR 0.10 | Average LLM cost per user query |
| User Monthly Cost | < EUR 2.00 | > EUR 2.50 | Total infrastructure cost per user per month |
| Cache Hit Ratio | > 80% | < 70% | Percentage of queries served from cache |
| Model Routing to BASIC tier | > 50% | < 30% | Queries routed to cheaper models (ADR-025) |

**Current infrastructure:**
- `llm_cost_total_eur` counter with `[provider, model, user_id]` labels
- `user_monthly_cost_eur` gauge with `[user_id, plan_type]` labels (target < EUR 2.00)
- `cache_hit_ratio` gauge with `[cache_type]` labels (target > 0.80)
- `api_calls_total` counter with `[provider, model, status]` labels
- `ccnl_cache_hits_total` counter
- Prometheus alerts: `HighUserCost` (> EUR 2.50), `HighLLMCosts`, `LowCacheHitRatio`

**What's missing:**
- Cost per query calculation (need to divide cost by query count over time)
- Model routing efficiency metric (% queries to BASIC vs PREMIUM vs LOCAL per ADR-025)
- Cost breakdown by feature (CCNL queries vs document processing vs chat)
- Token usage tracking (input vs output tokens per query)

**How to track:**
```promql
# Cost per query (1-hour average)
increase(llm_cost_total_eur[1h])
  / increase(api_calls_total{status="success"}[1h])

# Daily LLM spend
increase(llm_cost_total_eur[24h])

# Cost by provider
sum by (provider) (increase(llm_cost_total_eur[24h]))

# Cache effectiveness (cost savings proxy)
avg(cache_hit_ratio{cache_type="llm_responses"})
```

---

### KPI-5: Core Feature Success Rate

**What it measures:** Whether each major feature works end-to-end when users exercise it.

**Why it's #5:** A system can be "up" with low error rates but still have broken features. Tracking per-feature success ensures that the things users actually do (search regulations, process documents, calculate taxes) work correctly.

**Features to track:**

| Feature | Metric | Target | Description |
|---|---|---|---|
| Knowledge Base Search | `knowledge_base_queries_total{status="success"}` / total | > 95% | RAG retrieval success rate |
| Document Processing | `document_processing_operations_total{status="success"}` / total | > 90% | Upload + analysis pipeline |
| CCNL Queries | `ccnl_queries_total{status="success"}` / total | > 95% | Italian labor law lookups |
| Tax Calculations | `italian_tax_calculations_total{status="success"}` / total | > 98% | Financial calculations (zero tolerance for errors) |
| Payment Processing | `payment_operations_total{status="succeeded"}` / total | > 95% | Billing operations |

**Current infrastructure:**
- All five features have dedicated Prometheus counters with `status` labels
- Duration histograms for knowledge base, document processing, CCNL, and payment operations
- `knowledge_base_results_found` histogram tracks empty-result queries
- Prometheus alerts: `KnowledgeBaseQueryFailures`, `DocumentProcessingFailures`, `ItalianTaxCalculationFailures`, `PaymentFailures`

**What's missing:**
- Composite "feature health" dashboard showing all five at a glance
- Empty-result rate for searches (system returns 200 OK but zero useful results)
- End-to-end flow tracking (user uploads document → AI analyzes → user sees results)

**How to track:**
```promql
# Knowledge base success rate
rate(knowledge_base_queries_total{status="success"}[1h])
  / rate(knowledge_base_queries_total[1h]) * 100

# Document processing success rate
rate(document_processing_operations_total{status="success"}[1h])
  / rate(document_processing_operations_total[1h]) * 100

# CCNL query success rate
rate(ccnl_queries_total{status="success"}[1h])
  / rate(ccnl_queries_total[1h]) * 100

# Tax calculation success rate
rate(italian_tax_calculations_total{status="success"}[1h])
  / rate(italian_tax_calculations_total[1h]) * 100
```

---

## Summary: Pre-Production KPI Dashboard

| # | KPI | What | Target | Infra Status |
|---|---|---|---|---|
| 1 | RAG Answer Quality | AI correctness + faithfulness | > 0.85 faithfulness | Mostly in place (DeepEval + Langfuse) |
| 2 | API Reliability | Error rate + uptime | < 1% errors, > 99.5% up | In place (Prometheus + alerts) |
| 3 | Response Latency | P95 response time | < 2s API, < 5s CCNL | In place (histograms + alerts) |
| 4 | LLM Cost Per Query | Infrastructure unit economics | < EUR 0.05/query | Partially in place (need cost/query calc) |
| 5 | Feature Success Rate | Per-feature end-to-end health | > 90-98% per feature | In place (counters + alerts) |

---

## Phased Expansion Plan

### Phase 1: Pre-Production (Now → Launch)

**Focus: "Does it work?"**

Track the 5 KPIs defined above. The infrastructure is largely in place — the main work is:

1. **Create a Grafana "Pre-Production Health" dashboard** consolidating all 5 KPIs in one view. Use the existing Grafana provisioning at `monitoring/grafana/`.

2. **Add a `GET /healthz` liveness probe** — a simple endpoint that checks DB connectivity, Redis availability, and returns 200/503. The current `/health/rss` endpoint is too specific.

3. **Add the `HighClassificationFallbackRate` alert** to `monitoring/prometheus/alerts.yml`.

4. **Calculate cost-per-query** as a derived PromQL metric or Grafana panel. No new instrumentation needed — just divide `llm_cost_total_eur` by `api_calls_total`.

5. **Run the DeepEval benchmark suite** regularly in QA (already planned via `benchmarks.yml`).

### Phase 2: Early Production (Launch → 3 months)

**Focus: "Do users find value?"**

Add these KPIs on top of Phase 1:

| KPI | Category | Why |
|---|---|---|
| Time to First Value (TTFV) | Onboarding | Days from signup to first meaningful AI query. Target < 7 days. |
| Weekly Active Users (WAU) | Engagement | Are professionals coming back? Target: WAU/MAU > 60%. |
| Feature Adoption Rate | Product | Which AI features get used? Track per-feature (normative matching, document ID, communications). |
| User Acceptance Rate | AI Quality | Do users accept or override AI suggestions? Target: < 20% override rate. |
| NPS / CSAT | Satisfaction | Quarterly survey. Target: NPS > 30. |

**Implementation work:**
- Add user-action tracking events in the frontend (feature clicks, AI acceptance/rejection)
- Track `user_first_query_timestamp` in the user model for TTFV calculation
- Build a "User Engagement" Grafana dashboard
- Integrate a simple in-app NPS survey (quarterly)

### Phase 3: Growth (3-12 months post-launch)

**Focus: "Is the business viable?"**

Add revenue and unit economics KPIs:

| KPI | Category | Why |
|---|---|---|
| MRR / ARR | Revenue | Foundation metric. Track committed + usage revenue separately. |
| Churn Rate | Retention | Monthly logo churn. Target < 10% annual for professional services. |
| LTV:CAC Ratio | Unit Economics | Must be > 3x to be sustainable. |
| Net Revenue Retention (NRR) | Expansion | Usage-based model should drive NRR > 110%. |
| AI Gross Margin | Profitability | (AI Revenue - AI COGS) / AI Revenue. Target > 40%. |
| Consumption Growth Rate | Usage | QoQ usage growth from existing customers. Expect spikes around dichiarazione dei redditi. |

**Implementation work:**
- Integrate Stripe/payment data into metrics pipeline
- Build cohort analysis for retention tracking
- Implement revenue attribution per feature
- Create a "Business Health" Grafana dashboard

### Phase 4: Scale (12+ months post-launch)

**Focus: "Are we efficient?"**

Add operational efficiency and optimization KPIs:

| KPI | Category | Why |
|---|---|---|
| Rule of 40 | Balance | Growth Rate % + Profit Margin % > 40. |
| ARR per FTE | Efficiency | AI-native companies target EUR 130K+. |
| Model Routing Efficiency | Cost Optimization | % queries routed to BASIC tier (ADR-025). Target > 60%. |
| Usage Distribution | Risk | Gini coefficient — avoid top 10% of users generating > 50% of cost. |
| Billing Accuracy | Trust | < 1% dispute rate. Critical for financially sophisticated clients. |
| Predictive Usage Forecasting | Planning | MAPE for capacity planning around tax deadlines. |

**Implementation work:**
- Build model routing analytics (BASIC vs PREMIUM vs LOCAL distribution)
- Implement usage forecasting based on seasonal patterns (tax season, regulatory deadlines)
- Create executive dashboard with Rule of 40 and efficiency metrics

---

## Relationship to Existing Infrastructure

| Component | Location | Role |
|---|---|---|
| Prometheus metrics | `app/core/monitoring/metrics.py` | 40+ metrics already defined and instrumented |
| Prometheus config | `monitoring/prometheus/prometheus.yml` | Scrape config for all services |
| Prometheus alerts | `monitoring/prometheus/alerts.yml` | 18 alert rules across 7 categories |
| Grafana dashboards | `monitoring/grafana/dashboards/` | 5 dashboards (overview, performance, costs, business, alerts) |
| Prometheus middleware | `app/core/middleware/prometheus_middleware.py` | Auto-instruments HTTP requests |
| Metrics API | `app/api/v1/metrics.py` + `app/api/v1/monitoring.py` | Metrics endpoints |
| Health checks | `app/api/v1/health.py` | RSS feed health (needs generic `/healthz`) |
| DeepEval benchmarks | ADR-032 | RAG quality evaluation pipeline |
| Langfuse integration | ADR-032 | Quality trend tracking across deployments |
| k6 load testing | ADR-032 | Performance regression testing |
| Metrics glossary | `monitoring/METRICS_GLOSSARY.md` | Full metric reference |
| Cost limiter | `app/core/middleware/cost_limiter.py` | Per-user cost control |

---

## Related

- **ADR-025:** LLM Model Inventory & Tiering (BASIC/PREMIUM/LOCAL)
- **ADR-027:** Usage-Based Billing
- **ADR-032:** Automated Benchmarking Strategy
- **Metrics Glossary:** `monitoring/METRICS_GLOSSARY.md`
- **Prometheus Alerts:** `monitoring/prometheus/alerts.yml`
- **Grafana Dashboards:** `monitoring/grafana/dashboards/`
