# ADR-016: E2E Testing Strategy for RSS Feeds and Scrapers

**Status:** ACCEPTED
**Date:** 2025-12-09
**Decision Makers:** PratikoAI Architect (Egidio), Michele Giannone (Stakeholder)
**Context Review:** DEV-BE-69 - Expand RSS Feed Sources, Phase 6 (Testing)

---

## Context

**Current Testing Gap:**
- RSS feed ingestion tested only at unit level
- No validation of full RAG pipeline (ingest -> search -> LLM -> golden set)
- Document search bugs discovered only in production (e.g., "Messaggio 3585" bug)
- Golden set save/retrieval workflow untested end-to-end

**The Messaggio 3585 Bug (DEV-BE-69):**
- User query: "Di cosa parla il Messaggio numero 3585 dell'inps?"
- Document existed: "Messaggio numero 3585 del 27-11-2025"
- Bug: Query normalizer returned `{'type': 'DL', 'number': None}`
- Result: Search returned "Non ho trovato il testo specifico..."

**Root Cause:** No E2E tests validating the complete search flow from query to response.

---

## Decision

**Implement comprehensive E2E testing for all RSS feeds (13) and scrapers (2) with real LLM calls.**

### Test Architecture

```
tests/e2e/
├── conftest.py              # Shared fixtures (db, LLM tracker, expert profile)
├── feeds/
│   ├── __init__.py
│   ├── base_feed_test.py    # Base class with 4-step test flow
│   ├── test_inps_feeds.py   # 5 INPS feed tests
│   ├── test_agenzia_entrate_feeds.py  # 3 AE feed tests
│   └── test_other_feeds.py  # INAIL, MEF, Ministero, Gazzetta tests
└── scrapers/
    ├── __init__.py
    ├── test_gazzetta_scraper.py
    └── test_cassazione_scraper.py
```

### 4-Step Test Flow (BaseFeedTest)

Every E2E test validates the complete workflow:

1. **Ingest** - Documents from RSS feed exist in knowledge base
2. **Search** - Query returns relevant documents (BM25 + vector)
3. **Generate** - LLM generates response with context (real LLM call)
4. **Cache** - Golden set retrieval bypasses LLM (zero LLM calls)

```python
async def run_full_test_flow(self, query: str) -> FeedTestResult:
    # Step 1: Verify documents exist
    search_result = await self._search_for_documents(query)

    # Step 2: Generate LLM response
    llm_result = await self._generate_llm_response(query, search_result)

    # Step 3: Save as golden set
    golden_save = await self._save_as_golden_set(query, llm_result)

    # Step 4: Retrieve from golden set (MUST NOT call LLM)
    golden_retrieve = await self._retrieve_from_golden_set(query)
    assert golden_retrieve["llm_calls"] == 0  # Critical assertion
```

### Test Matrix

| Source            | Feeds | Tests | Query Variations |
|-------------------|-------|-------|------------------|
| INPS              | 5     | 15+   | 3 per feed       |
| Agenzia Entrate   | 3     | 9+    | 3 per feed       |
| INAIL             | 2     | 6+    | 3 per feed       |
| MEF               | 2     | 6+    | 3 per feed       |
| Ministero Lavoro  | 1     | 3+    | 3 per feed       |
| Gazzetta Ufficiale| 1     | 3+    | 3 per feed       |
| **Scrapers**      | 2     | 10+   | Integration tests|
| **Total**         | 16    | 52+   |                  |

### Cost Analysis

**Per CI Run (worst case - all 52 tests with LLM calls):**
- Tokens per test: ~2,000 (query + context + response)
- Total tokens: 52 × 2,000 = 104,000
- Cost at $0.75/M tokens: ~$0.08

**Monthly CI Cost (aggressive):**
- 10 runs/day × 30 days = 300 runs
- 300 × $0.10 = $30/month

**Annual Cost:** ~$360 (acceptable for quality assurance)

---

## Alternatives Considered

### 1. Mock LLM Responses
**Rejected:** Does not validate true integration. Would not catch the Messaggio 3585 bug.

### 2. Shared Test Database with Production
**Rejected:** Security risk, test pollution, GDPR concerns.

### 3. Manual Testing Only
**Rejected:** Not repeatable, not scalable, missed the original bug.

---

## Consequences

### Positive
- Catches integration bugs before production
- Documents expected behavior for all feeds
- Validates golden set caching works correctly
- Provides regression tests for query normalization

### Negative
- Small LLM cost per CI run (~$0.10)
- Tests take longer (LLM calls ~30s total)
- Requires separate test database

### Mitigations
- Use `@pytest.mark.slow` to skip in quick CI runs
- Rate limit external feed access
- Use test database with transaction rollback

---

## Implementation

### pytest Markers

```python
@pytest.mark.e2e        # End-to-end tests (require DB)
@pytest.mark.slow       # Tests that take >5s (LLM calls)
@pytest.mark.llm        # Tests that make real LLM calls
```

### CI Configuration

```yaml
# GitHub Actions
- name: Run E2E Tests
  run: |
    pytest tests/e2e/ -m "e2e" --tb=short
  env:
    DATABASE_URL: ${{ secrets.TEST_DATABASE_URL }}
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

### Database Setup

```sql
CREATE DATABASE pratiko_ai_test;
GRANT ALL PRIVILEGES ON DATABASE pratiko_ai_test TO aifinance;
```

---

## References

- DEV-BE-69: Expand RSS Feed Sources - ARCHITECTURE_ROADMAP.md
- ADR-013: TDD Methodology
- `tests/e2e/feeds/base_feed_test.py` - Base test class
- `tests/e2e/conftest.py` - Shared fixtures
