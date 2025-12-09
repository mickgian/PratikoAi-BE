# E2E RSS Feed Testing Strategy

**Task:** DEV-BE-69 - Expand RSS Feed Sources (Phase 6: Testing)
**Date:** 2025-12-09
**Status:** Implemented

---

## Overview

This document describes the E2E testing strategy for RSS feeds and scrapers in PratikoAI. The strategy ensures that the complete RAG pipeline works correctly from document ingestion to user query response.

## Why E2E Tests?

### The Messaggio 3585 Bug

A user queried: "Di cosa parla il Messaggio numero 3585 dell'inps?"

Despite the document "Messaggio numero 3585 del 27-11-2025" existing in the database, the system returned "Non ho trovato il testo specifico..."

**Root Cause:** The query normalizer returned `{'type': 'DL', 'number': None}` for queries containing "DL" (decreto legge) patterns, even when the query was about an INPS messaggio. This triggered the document number search path with a null number, causing a silent failure.

**Lesson:** Unit tests passed, but the integration between components failed. E2E tests catch these integration bugs.

---

## Test Architecture

### Directory Structure

```
tests/e2e/
├── conftest.py                    # Shared fixtures
├── feeds/
│   ├── __init__.py
│   ├── base_feed_test.py          # Base class (4-step flow)
│   ├── test_inps_feeds.py         # 5 INPS feed tests
│   ├── test_agenzia_entrate_feeds.py  # 3 AE feed tests
│   └── test_other_feeds.py        # INAIL, MEF, etc.
└── scrapers/
    ├── __init__.py
    ├── test_gazzetta_scraper.py
    └── test_cassazione_scraper.py
```

### The 4-Step Test Flow

Every E2E test follows this flow:

```
┌─────────────────────────────────────────────────────────────┐
│                    E2E TEST FLOW                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Step 1: SEARCH                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Query: "Quali sono le ultime circolari INPS?"       │   │
│  │ → Knowledge Search Service                           │   │
│  │ → BM25 + Vector search                              │   │
│  │ → Returns top-k documents                           │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ▼                                 │
│  Step 2: GENERATE (Real LLM Call)                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Context: Retrieved documents                        │   │
│  │ → Query Service                                     │   │
│  │ → LLM generates response                            │   │
│  │ → Response with citations                           │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ▼                                 │
│  Step 3: SAVE AS GOLDEN SET                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Simulates "Corretta" button click                   │   │
│  │ → Intelligent FAQ Service                           │   │
│  │ → Expert approval (auto for high-trust)             │   │
│  │ → Cached in database                                │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ▼                                 │
│  Step 4: RETRIEVE FROM CACHE (NO LLM Call)                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Same query submitted again                          │   │
│  │ → Golden set lookup                                 │   │
│  │ → Returns cached response                           │   │
│  │ → LLM call count = 0  ← CRITICAL ASSERTION         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## RSS Feed Coverage

### INPS Feeds (5 total)

| Feed Type   | URL                                      | Query Examples |
|-------------|------------------------------------------|----------------|
| News        | `https://www.inps.it/it/it.rss.news.xml` | "Ultime novita INPS" |
| Circolari   | `https://www.inps.it/it/it.rss.circolari.xml` | "Circolare gestione separata" |
| Messaggi    | `https://www.inps.it/it/it.rss.messaggi.xml` | "Messaggio 3585" |
| Sentenze    | `https://www.inps.it/it/it.rss.sentenze.xml` | "Sentenze pensione invalidita" |
| Comunicati  | `https://www.inps.it/it/it.rss.comunicati.xml` | "Comunicati stampa INPS" |

### Agenzia Entrate Feeds (3 total)

| Feed Type    | URL                                                  | Query Examples |
|--------------|------------------------------------------------------|----------------|
| Circolari    | `https://www.agenziaentrate.gov.it/.../circolari.xml` | "Circolare IVA" |
| Risoluzioni  | `https://www.agenziaentrate.gov.it/.../risoluzioni.xml` | "Risoluzione 63" |
| Provvedimenti| `https://www.agenziaentrate.gov.it/.../provvedimenti.xml` | "Provvedimento fatturazione" |

### Other Feeds (5 total)

| Source            | Feeds | Feed Types |
|-------------------|-------|------------|
| INAIL             | 2     | news, eventi |
| MEF               | 2     | documenti, aggiornamenti |
| Ministero Lavoro  | 1     | news |

### Scrapers (2 total)

| Scraper            | Documents | Topics |
|--------------------|-----------|--------|
| Gazzetta Ufficiale | Laws, Decrees | Tax, Labor |
| Cassazione         | Court Decisions | Tax, Labor |

---

## Running E2E Tests

### Prerequisites

1. **Test Database:**
   ```sql
   CREATE DATABASE pratiko_ai_test;
   ```

2. **Environment Variables:**
   ```bash
   # pragma: allowlist secret
   export TEST_DATABASE_URL="postgresql://user:password@localhost:5432/pratiko_ai_test"
   export OPENAI_API_KEY="your-api-key-here"
   ```

### Commands

```bash
# Run all E2E tests
pytest tests/e2e/ -m "e2e" -v

# Run only feed tests
pytest tests/e2e/feeds/ -v

# Run only scraper tests
pytest tests/e2e/scrapers/ -v

# Skip slow tests (with LLM calls)
pytest tests/e2e/ -m "e2e and not slow"

# Run specific feed tests
pytest tests/e2e/feeds/test_inps_feeds.py -v
```

---

## Cost Analysis

### Per Test Cost

- Average tokens per test: ~2,000 (query + context + response)
- Cost at $0.75/M tokens: ~$0.0015 per test

### CI Run Cost

| Scenario | Tests | Cost |
|----------|-------|------|
| Quick (no LLM) | 30 | $0.00 |
| Full (with LLM) | 52 | ~$0.08 |
| With retries | 60 | ~$0.10 |

### Monthly Cost

| Runs/Day | Monthly Cost |
|----------|--------------|
| 5        | ~$15 |
| 10       | ~$30 |
| 20       | ~$60 |

### Annual Cost

~$180-360 depending on CI frequency (acceptable for quality assurance).

---

## Fixtures

### LLM Call Tracker

```python
@pytest.fixture
def llm_call_tracker():
    """Track LLM API calls to verify golden set bypass."""
    class LLMCallTracker:
        def __init__(self):
            self.calls = []

        def record(self, query, response, model="unknown"):
            self.calls.append({...})

        @property
        def call_count(self):
            return len(self.calls)

    return LLMCallTracker()
```

### Test Expert Profile

```python
@pytest.fixture
async def test_expert_profile(db_session):
    """High-trust expert for auto-approval testing."""
    # Creates expert with trust_score=0.95
    # Auto-approves golden set entries
```

### Rate Limit Delay

```python
@pytest.fixture
def rate_limit_delay():
    """Configurable delay between RSS requests."""
    return float(os.environ.get("E2E_RATE_LIMIT_DELAY", "1.0"))
```

---

## Best Practices

### 1. Test Isolation

Each test runs in a database transaction that rolls back:

```python
@pytest.fixture
async def db_session(test_engine):
    async with session.begin():
        yield session
        await session.rollback()  # Automatic cleanup
```

### 2. Query Variations

Each feed should have at least 3 semantic query variations:

```python
QUERY_VARIATIONS = [
    "Quali sono le ultime circolari INPS?",    # Direct question
    "Aggiornamenti INPS per lavoratori",       # Topic-based
    "Novita circolari previdenziali",          # Synonym-based
]
```

### 3. Assertions

Critical assertions for every test:

```python
# Step 2: Documents found
assert result.documents_found > 0

# Step 3: LLM responded
assert result.llm_response_generated

# Step 4: Golden set cached
assert result.golden_set_saved

# Step 5: NO LLM call on retrieval
assert result.llm_calls_on_retrieval == 0  # CRITICAL
```

---

## Troubleshooting

### "No documents found" Error

1. Check if database has documents:
   ```sql
   SELECT COUNT(*) FROM knowledge_items WHERE source = 'inps';
   ```

2. Run RSS ingestion:
   ```bash
   python scripts/run_full_ingestion.py
   ```

### "LLM call on retrieval" Error

1. Check golden set was saved:
   ```sql
   SELECT * FROM intelligent_faqs WHERE question ILIKE '%query%';
   ```

2. Verify semantic similarity threshold (default: 0.85)

### Rate Limiting Errors

1. Increase delay:
   ```bash
   export E2E_RATE_LIMIT_DELAY=2.0
   ```

2. Use fewer parallel tests

---

## References

- ADR-016: E2E RSS Testing Strategy
- DEV-BE-69: Expand RSS Feed Sources
- `tests/e2e/feeds/base_feed_test.py` - Base test class
