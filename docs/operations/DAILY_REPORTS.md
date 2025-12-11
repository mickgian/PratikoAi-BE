# Daily Ingestion Collection Email Report

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
