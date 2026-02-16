# Daily Email Reports

This document covers the two automated daily email reports:
1. [Daily Cost Spending Report](#daily-cost-spending-report-dev-246) — LLM and third-party API costs
2. [Daily Ingestion Collection Report](#daily-ingestion-collection-email-report-dev-be-70) — RSS/scraper health

---

# Daily Cost Spending Report (DEV-246)

**Task:** DEV-246
**Status:** Implemented
**Last Updated:** 2026-02-13

## Overview

The Daily Cost Spending Report provides visibility into LLM inference and third-party API costs, broken down by environment, user, and API type. Designed to maintain the **target of under €2/user/month**.

## Data Sources

- **UsageEvent** table — records every LLM call and third-party API request with cost
- **User** table — provides human-readable `account_code` for the report

## Configuration

### Environment Variables

```env
# Recipients (comma-separated)
DAILY_COST_REPORT_RECIPIENTS=your-email@pratikoai.com

# Time to send report in HH:MM format (Europe/Rome timezone)
DAILY_COST_REPORT_TIME=07:00

# Enable/disable the report
DAILY_COST_REPORT_ENABLED=true
```

## Report Structure

### 1. Header with Environment Badge
- Same color coding as ingestion report (DEV/QA/PROD)
- Report date

### 2. Summary Cards
- **Total Cost** (€, :.2f)
- **Total Requests**
- **Unique Users**

### 3. Cost Breakdown by Category
- **LLM Inference** (€, :.2f)
- **Third-Party APIs** (€, :.4f — higher precision for small per-request costs)
- **Total Tokens**

### 4. Cost by Environment (Table)
| Environment | Total Cost | LLM Cost | Third-Party | Requests | Users |

### 5. Top Users by Cost (Table)
| User ID (account_code) | Total Cost | % of Total | Requests | Tokens |

- Displays `account_code` (e.g., "MIC40048-1") instead of raw DB integer ID
- Falls back to raw ID when `account_code` is NULL

### 6. Third-Party API Costs (Table)
| API Type | Total Cost (:.4f) | Requests | Avg/Request (:.4f) |

### 7. Cost Alerts
| Alert Type | Condition | Severity |
|------------|-----------|----------|
| DAILY_THRESHOLD_EXCEEDED | Environment daily cost > threshold | HIGH |
| USER_THRESHOLD_EXCEEDED | User daily cost > €2/day | MEDIUM |

**Thresholds by environment:**
| Environment | Daily Total | Per User |
|-------------|-------------|----------|
| Development | €10 | €1 |
| QA | €25 | €2 |
| Production | €50 | €2 |
| Test | €5 | €5 |

## Decimal Precision

| Cost Type | Format | Rationale |
|-----------|--------|-----------|
| Total, LLM costs | :.2f | Amounts typically > €0.01 |
| Third-party costs | :.4f | Per-request costs like Brave (€0.003) would show €0.00 with :.2f |
| Avg/request | :.4f | Same rationale |

## Scheduler Task

```python
# Task name: daily_cost_report
# Interval: DAILY
# Default time: 07:00 Europe/Rome
# Function: send_daily_cost_report_task
```

## Testing

```bash
uv run pytest tests/services/test_daily_cost_report_service.py -v
```

Current test coverage: 19 tests covering:
- Dataclass defaults and calculations
- Environment breakdown aggregation
- User breakdown with account_code display
- Third-party breakdown aggregation
- HTML report generation (with data and empty)
- Full report generation pipeline
- Email sending
- Cost alert thresholds

## Files

- `app/services/daily_cost_report_service.py` — Report generation, HTML rendering, email sending
- `app/services/scheduler_service.py` — Daily task registration
- `tests/services/test_daily_cost_report_service.py` — Unit tests

## Change Log

| Date | Change |
|------|--------|
| 2026-01-24 | Initial implementation (DEV-246) |
| 2026-02-13 | Fix: :.2f → :.4f for third-party costs; JOIN with User table for account_code display |

---

# Daily Ingestion Collection Email Report (DEV-BE-70)

**Task:** DEV-BE-70
**Status:** Implemented
**Last Updated:** 2024-12-10

## Overview

The Daily Ingestion Collection Email Report provides visibility into the health and activity of all knowledge base ingestion sources, including RSS feeds and web scrapers.

## Data Sources

### RSS Feeds (13 sources from DEV-BE-69)
- Agenzia Entrate (Normativa, News)
- INPS (News, Comunicati, Circolari, Messaggi, Sentenze)
- Ministero del Lavoro
- MEF (Documenti, Aggiornamenti)
- INAIL (Notizie, Eventi)
- Gazzetta Ufficiale RSS (Serie Generale, Corte Costituzionale, UE, Regioni)

### Web Scrapers (2 sources)
- Gazzetta Ufficiale (full scraper)
- Corte di Cassazione (decisions scraper)

## Configuration

### Environment Variables

```env
# Recipients (comma-separated) - same for all environments
INGESTION_REPORT_RECIPIENTS=your-email@pratikoai.com

# Time to send report in HH:MM format (Europe/Rome timezone)
INGESTION_REPORT_TIME=08:00

# Enable/disable the report
INGESTION_REPORT_ENABLED=true
```

### Notes
- Same recipients receive emails from ALL environments
- Environment is clearly identified via:
  - Email subject prefix: `[DEV]`, `[QA]`, `[PROD]`
  - Color-coded header banner in email body

## Report Structure

### 1. Header with Environment Badge
- Environment name with color coding:
  - **DEVELOPMENT**: Gray (#6c757d)
  - **QA**: Blue (#007bff)
  - **PRODUCTION**: Green (#28a745)
- Report date and generation timestamp (Europe/Rome timezone)

### 2. Executive Summary
- Total documents collected (all sources) + WoW change
- Total documents added to DB (after deduplication) + WoW change
- Overall success rate (%) + WoW change
- Overall junk rate (%) + WoW change
- Alert count by severity

### 3. RSS Feeds Section (Table)
| Feed Name | Processed | Added | Success % | Junk % | Last Check | Status |

### 4. Web Scrapers Section (Table)
| Scraper Name | Processed | Added | Success % | Junk % | Last Run | Status |

### 5. Alerts Section
Five alert types with severity levels:

| Alert Type | Condition | Severity |
|------------|-----------|----------|
| FEED_DOWN | HTTP 4xx/5xx for 2+ consecutive checks | HIGH |
| FEED_STALE | No new items in 7+ days | MEDIUM |
| HIGH_ERROR_RATE | >10% parse failures in 24h | MEDIUM |
| HIGH_JUNK_RATE | >25% junk detection rate | LOW |
| ZERO_DOCUMENTS | No documents from any source in 24h | HIGH |

### 6. New Documents Preview
- Top 5 new document titles per source added in last 24h
- Format: "Source: Document Title" (truncated to 100 chars)

### 7. Error Details
- Per-source error count
- 1-2 sample error messages for debugging (when errors > 0)

## Scheduler Task

The report is sent via the scheduler service as a daily task:

```python
# Task name: daily_ingestion_report
# Interval: DAILY
# Function: send_daily_ingestion_report_task
```

## Retry Logic

Email sending includes retry logic with exponential backoff:
- Maximum 3 attempts
- Backoff: 1s, 2s, 4s between attempts

## Disabling the Report

Set `INGESTION_REPORT_ENABLED=false` in your environment variables. No database changes required.

## Testing

Run the dedicated test suite:

```bash
pytest tests/services/test_ingestion_report_service.py -v
```

Current test coverage: 44 tests covering:
- Alert detection logic
- WoW comparison calculations
- Environment color mapping
- HTML template rendering
- Scheduler task registration
- Email retry logic

## Files Modified

- `app/core/config.py` - INGESTION_REPORT_* settings
- `app/services/ingestion_report_service.py` - Enhanced service with alerts, WoW, previews
- `app/services/scheduler_service.py` - Daily task registration
- `.env.example` - Configuration examples

## Files Created

- `tests/services/test_ingestion_report_service.py` - Extended tests for DEV-BE-70
- `docs/operations/DAILY_REPORTS.md` - This documentation

## Acceptance Criteria (All Met)

- [x] Report includes both RSS feed AND scraper statistics
- [x] Environment badge visible in email header with correct color
- [x] Email subject includes environment prefix
- [x] Week-over-week comparison shown in executive summary
- [x] Top 5 new document titles shown per source
- [x] Error count + sample error messages displayed when errors > 0
- [x] Alerts generated for stale feeds (7+ days no new items)
- [x] Alerts generated for high error rate (>10%)
- [x] Alerts generated for zero documents
- [x] Recipients configurable per environment
- [x] Report sends at configured time (default 08:00 Europe/Rome)
- [x] Report sends even with no activity (shows "0 documents")
- [x] HTML renders correctly in Gmail/Outlook/Apple Mail
- [x] Retry logic handles SMTP failures (3 attempts)
- [x] All unit tests pass (44 tests)
