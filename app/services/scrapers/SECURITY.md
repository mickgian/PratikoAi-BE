# Scraper Security Documentation - DEV-BE-69

## Overview

This document describes the security measures implemented in the PratikoAI web scrapers for Italian regulatory sources.

## Scrapers Covered

1. **GazzettaScraper** - Italian Official Gazette (Gazzetta Ufficiale)
2. **CassazioneScraper** - Italian Supreme Court (Corte di Cassazione)

## Security Measures

### 1. Robots.txt Compliance

Both scrapers implement robots.txt parsing and compliance:

- **Default behavior**: `respect_robots_txt=True`
- Robots.txt is fetched and parsed before scraping begins
- Disallowed paths are respected unless explicitly disabled
- User-Agent is identified as `PratikoAI Legal Research Bot/1.0`

#### Implementation Details

```python
# GazzettaScraper
async def _check_robots_txt(self):
    """Check and parse robots.txt for scraping rules."""
    # Fetches robots.txt from BASE_URL
    # Parses User-agent, Disallow, and Allow directives
    # Stores rules in _robots_rules dict

def _is_path_allowed(self, url: str) -> bool:
    """Check if URL path is allowed by robots.txt."""
    # Returns False if path matches a Disallow rule
```

### 2. Rate Limiting

All scrapers implement multiple layers of rate limiting:

#### Time-Based Rate Limiting
- **Minimum delay between requests**: 2.0 seconds (configurable)
- **Stagger delay for concurrent requests**: 1-3 seconds between task starts

#### Connection Limiting
- **Maximum concurrent requests**: 3-5 (configurable per scraper)
- **Connection pooling**: Controlled via aiohttp TCPConnector

#### Retry Logic
- **Maximum retries**: 3 attempts
- **Exponential backoff**: 2^attempt seconds between retries
- **Respect for HTTP 429**: Honors `Retry-After` header

### 3. GDPR Data Handling

The scrapers are designed to collect only public regulatory documents:

#### Data Collected
- Official government publications
- Court decisions (public record)
- Regulatory circulars and resolutions
- Official gazette entries

#### Data NOT Collected
- Personal identification information
- Private citizen data
- Authentication credentials
- Non-public documents

#### Data Protection Measures
- Content is hashed (SHA256) for deduplication
- No cookies are persisted
- No tracking of user behavior on scraped sites
- Session data is cleared after each scraping run

### 4. Access Control

#### Request Headers
```python
headers = {
    "User-Agent": "PratikoAI Legal Research Bot/1.0 (+https://pratiko.ai)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
}
```

#### Timeout Configuration
- **Request timeout**: 30 seconds
- **Connection timeout**: Configurable
- **Pool pre-ping**: Enabled to detect stale connections

### 5. Error Handling

#### Safe Error Logging
- Errors are logged without exposing sensitive data
- Stack traces are captured for debugging
- No credential information in logs

#### Graceful Degradation
- Failed requests don't crash the scraper
- Partial results are returned when possible
- Error statistics are tracked for monitoring

## Configuration Options

### GazzettaScraper

| Parameter | Default | Description |
|-----------|---------|-------------|
| `rate_limit_delay` | 2.0 | Seconds between requests |
| `max_retries` | 3 | Maximum retry attempts |
| `timeout_seconds` | 30 | Request timeout |
| `max_concurrent_requests` | 3 | Max parallel requests |
| `respect_robots_txt` | True | Honor robots.txt |

### CassazioneScraper

| Parameter | Default | Description |
|-----------|---------|-------------|
| `rate_limit_delay` | 2.0 | Seconds between requests |
| `max_retries` | 3 | Maximum retry attempts |
| `timeout_seconds` | 30 | Request timeout |
| `max_concurrent_requests` | 5 | Max parallel requests |
| `respect_robots_txt` | True | Honor robots.txt |

## Feed Processing Rate Limiting

The DynamicKnowledgeCollector implements additional rate limiting for RSS feeds:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_concurrent` | 5 | Max concurrent feed processing |
| `stagger_delay_min` | 1.0 | Min delay between feed starts |
| `stagger_delay_max` | 3.0 | Max delay between feed starts |

## Compliance Checklist

- [x] robots.txt parsing and compliance
- [x] Rate limiting (time-based and connection-based)
- [x] User-Agent identification
- [x] HTTP 429 (Too Many Requests) handling
- [x] Exponential backoff for retries
- [x] No PII collection
- [x] Public data only
- [x] Content hashing for deduplication
- [x] Safe error logging
- [x] Graceful error handling

## Audit Schedule

Security audits for scrapers should be conducted:
- **Weekly**: Automated rate limit compliance checks
- **Monthly**: Manual review of scraped content
- **Quarterly**: Full security audit by @severino

## Contact

For security concerns related to scraping, contact the DevOps team or @severino (Security Specialist).

---

**Last Updated**: 2025-12-05
**Author**: @ezio (Backend Developer)
**Reviewed By**: @severino (Security Specialist)
