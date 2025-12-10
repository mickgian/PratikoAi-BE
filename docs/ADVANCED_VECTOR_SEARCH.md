# Advanced pgvector Search Patterns for PratikoAI

**Last Updated:** 2025-11-14
**Status:** Production
**Implementation:** `app/retrieval/postgres_retriever.py`

---

## Overview

This guide documents advanced usage patterns, optimization techniques, and best practices for PratikoAI's pgvector-based hybrid retrieval system. All examples are based on the actual production implementation.

**Prerequisites:**
- Read `docs/DATABASE_ARCHITECTURE.md` first for architecture overview
- PostgreSQL 15+ with pgvector extension installed
- OpenAI API key for embeddings (text-embedding-3-small)

---

## Why pgvector (Not Pinecone/Qdrant)?

**TL;DR:** pgvector was chosen for PratikoAI because it provides the best fit for our specific requirements: Italian language support, hybrid search, cost efficiency, and operational simplicity.

**Key Advantages for PratikoAI:**

1. **Native Italian Language Support**
   - PostgreSQL has built-in `italian` dictionary with morphology and stemming
   - External vector DBs require custom tokenization/preprocessing
   - Critical for accurate keyword matching on Italian regulatory documents

2. **Hybrid Search in Single Query**
   - Combine FTS + Vector Similarity + Recency in one SQL query
   - External vector DBs require app-level fusion of two separate systems
   - Simpler implementation, better performance, easier debugging

3. **Cost Savings**
   - pgvector-only: $90-265/month
   - With Pinecone: $240-560/month
   - **Savings: $150-295/month** (2-3x reduction)

4. **Operational Simplicity**
   - One PostgreSQL connection string vs. multiple services + API keys
   - Small team can manage single database system
   - No cross-system synchronization complexity

5. **Team Familiarity**
   - Team already knows SQL and PostgreSQL
   - No learning curve for new vector DB APIs/SDKs
   - Faster development and easier onboarding

6. **Performance**
   - <100ms p95 latency meets user experience requirements
   - Pinecone's theoretical 30-50ms improvement not worth 2-3x cost + complexity
   - Plenty of scaling headroom (excellent up to 1M vectors)

**When to Reconsider:**
Only if ALL THREE conditions are met: (1) >1M vectors + >2s latency, (2) Multi-region/sub-10ms SLA required, (3) Cost equation flips

**Full Comparison:** See `docs/DATABASE_ARCHITECTURE.md` Section 9.1 for detailed comparison table

---

## 1. Basic Usage

### 1.1 Simple Hybrid Query

```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.retrieval.postgres_retriever import hybrid_retrieve

# Basic usage with defaults (FTS 50%, Vector 35%, Recency 15%)
async def search_knowledge_base(session: AsyncSession, user_query: str):
    results = await hybrid_retrieve(
        session=session,
        query=user_query,
        top_k=14  # Returns top 14 results (default: CONTEXT_TOP_K from config)
    )

    for result in results:
        print(f"Score: {result['combined_score']:.3f}")
        print(f"Text: {result['chunk_text'][:200]}...")
        print(f"Source: {result['document_title']}")
        print("---")

    return results
```

### 1.2 FTS-Only Fallback

If embedding generation fails (API outage, network issue), the system automatically falls back to FTS-only:

```python
from app.retrieval.postgres_retriever import fts_only_retrieve

# Explicit FTS-only search (no vector similarity)
results = await fts_only_retrieve(
    session=session,
    query="contratti locazione commerciale",
    top_k=10
)
```

**When to use FTS-only:**
- Testing FTS performance separately
- Debugging vector search issues
- Emergency fallback during embedding service outage

---

## 2. Customizing Hybrid Weights

### 2.1 Adjust Scoring Weights

Tune the balance between FTS, vector similarity, and recency:

```python
# Scenario 1: Emphasize keyword matching (legal compliance use case)
results = await hybrid_retrieve(
    session=session,
    query="IVA 22% fatturazione elettronica",
    fts_weight=0.70,      # 70% FTS (exact term matching important)
    vector_weight=0.20,   # 20% vector
    recency_weight=0.10   # 10% recency
)

# Scenario 2: Emphasize semantic similarity (user questions)
results = await hybrid_retrieve(
    session=session,
    query="come faccio a calcolare le tasse?",
    fts_weight=0.30,      # 30% FTS
    vector_weight=0.60,   # 60% vector (capture user intent)
    recency_weight=0.10   # 10% recency
)

# Scenario 3: Emphasize recency (breaking news, regulatory updates)
results = await hybrid_retrieve(
    session=session,
    query="nuova circolare agenzia entrate",
    fts_weight=0.30,      # 30% FTS
    vector_weight=0.20,   # 20% vector
    recency_weight=0.50   # 50% recency (recent docs heavily favored)
)
```

**Weight Tuning Guidelines:**
- **Sum must equal 1.0** (normalized weights)
- **FTS weight 0.4-0.7:** Good for exact term matching (legal, regulatory)
- **Vector weight 0.3-0.6:** Good for semantic understanding (user questions)
- **Recency weight 0.1-0.3:** Good for time-sensitive queries (news, updates)

### 2.2 Adjust Recency Decay

Control how quickly older documents lose relevance:

```python
# Fast decay: Recent docs strongly preferred
results = await hybrid_retrieve(
    session=session,
    query="circolare agenzia entrate",
    recency_days=90,  # Docs >90 days old decay rapidly
    recency_weight=0.30
)

# Slow decay: Older docs still relevant
results = await hybrid_retrieve(
    session=session,
    query="codice civile art 1571",
    recency_days=1825,  # 5 years (slow decay for legal texts)
    recency_weight=0.10
)
```

**Recency Decay Formula:**
```python
recency_score = EXP(-age_seconds / (recency_days * 86400))
```

**Examples:**
- Document age: 30 days, `recency_days=365` → score ≈ 0.92 (minimal decay)
- Document age: 180 days, `recency_days=90` → score ≈ 0.13 (significant decay)
- Document age: 1 year, `recency_days=1825` → score ≈ 0.80 (slow decay)

---

## 3. Italian Language Optimization

### 3.1 Full-Text Search Queries

**PostgreSQL FTS with Italian dictionary:**

```python
# Example user query: "contratti di locazione commerciale"
# PostgreSQL processes as:
#   websearch_to_tsquery('italian', 'contratti di locazione commerciale')
#   → 'contratt' & 'locaz' & 'commerc'
```

**Query Syntax:**

```python
# AND operator (default)
query = "contratti locazione"  # Both terms required

# OR operator
query = "IVA OR IRPEF"  # Either term matches

# Phrase search (with quotes)
query = '"locazione commerciale"'  # Exact phrase

# Negation
query = "IVA NOT 22%"  # IVA but not 22%

# Complex boolean
query = "(IVA OR imposta) NOT regime forfettario"
```

### 3.2 Common Italian Tax Terms

**Acronyms automatically stemmed:**
- "IVA" → matches "IVA", "imposta valore aggiunto"
- "IRPEF" → matches "IRPEF", "imposta reddito"
- "P.IVA" → matches "partita iva", "p.iva", "PIVA"

**Morphological variations handled:**
- "contratto" / "contratti" → same stem "contratt"
- "locazione" / "locazioni" → same stem "locaz"
- "fattura" / "fatture" / "fatturazione" → same stem "fattur"

**Accents normalized:**
- "è" / "e" → match
- "più" / "piu" → match

### 3.3 Boosting Specific Fields

The FTS search vector is weighted by field importance:

```sql
-- Defined in database schema
search_vector =
    setweight(to_tsvector('italian', title), 'A') ||      -- Highest weight
    setweight(to_tsvector('italian', chunk_text), 'B') || -- Medium weight
    setweight(to_tsvector('italian', category), 'C')      -- Lower weight
```

**Result:** Matches in title score higher than matches in body text.

---

## 4. Vector Similarity Optimization

### 4.1 Embedding Generation

**Production implementation:**

```python
from app.core.embed import generate_embedding

# Generate embedding for query
embedding = await generate_embedding("contratti di locazione")
# Returns: List[float] of length 1536 (OpenAI text-embedding-3-small)
```

**Cost:** ~$0.000001 per query (50 tokens × $0.00002 / 1K tokens)

### 4.2 Distance Metrics

**Cosine distance (used in production):**

```sql
-- Raw distance (0.0 = identical, 2.0 = opposite)
kc.embedding <=> query_embedding

-- Convert to similarity (0.0 = opposite, 1.0 = identical)
1 - (kc.embedding <=> query_embedding) AS vector_score
```

**Filtering threshold:**

```sql
-- Only consider vectors within distance 1.0
WHERE (kc.embedding <=> CAST(:embedding AS vector)) < 1.0
```

**Threshold Guidelines:**
- **< 0.3:** Very similar (almost identical)
- **0.3 - 0.6:** Moderately similar (related concepts)
- **0.6 - 1.0:** Loosely similar (broad topic match)
- **> 1.0:** Not similar (filtered out)

### 4.3 Index Performance

**Current index (IVFFlat):**
```sql
CREATE INDEX idx_kc_embedding_ivfflat_1536
ON knowledge_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

**Performance characteristics:**
- Query time: 30-50ms (for 500K vectors)
- Recall: 85-90%
- Build time: ~30 minutes

**Future upgrade (HNSW - DEV-72):**
```sql
CREATE INDEX idx_kc_embedding_hnsw_1536
ON knowledge_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

**Expected improvements:**
- Query time: 20-30ms (20-30% faster)
- Recall: 90-95%
- Build time: ~2-4 hours (slower initial build, but worth it)

---

## 5. Performance Optimization

### 5.1 Query Diagnostics

```python
from app.retrieval.postgres_retriever import explain_hybrid_query

# Get EXPLAIN ANALYZE output
explain_output = await explain_hybrid_query(session, "contratti locazione")
print(explain_output)
```

**Example output:**
```
Index Scan using idx_kc_search_vector_gin on knowledge_chunks  (cost=...)
  Index Cond: (search_vector @@ websearch_to_tsquery('italian', 'contratti locazione'))
  Filter: ((embedding <=> '[0.123,...]'::vector) < 1.0)
  Rows Removed by Filter: 1523
  Buffers: shared hit=245 read=12
Planning Time: 2.341 ms
Execution Time: 47.892 ms
```

**What to look for:**
- "Index Scan" → Good (using indexes)
- "Seq Scan" → Bad (full table scan, need index)
- "Rows Removed by Filter" → High number OK (distance filter working)
- "Execution Time" → Target <100ms

### 5.2 Monitoring Query Performance

**Add timing to your queries:**

```python
import time

start = time.time()
results = await hybrid_retrieve(session, query)
duration_ms = (time.time() - start) * 1000

print(f"Query: {query}")
print(f"Results: {len(results)}")
print(f"Duration: {duration_ms:.1f}ms")
print(f"Avg score: {sum(r['combined_score'] for r in results) / len(results):.3f}")
```

**Target performance:**
- p50 latency: <50ms
- p95 latency: <100ms
- p99 latency: <300ms

### 5.3 Batch Queries

**Don't do this (slow):**
```python
# BAD: Sequential queries
for query in user_queries:
    results = await hybrid_retrieve(session, query)  # Waits for each
```

**Do this instead (fast):**
```python
import asyncio

# GOOD: Parallel queries
async def batch_search(session, queries):
    tasks = [hybrid_retrieve(session, q) for q in queries]
    all_results = await asyncio.gather(*tasks)
    return all_results

results = await batch_search(session, ["query1", "query2", "query3"])
```

**Improvement:** 3x-5x faster for multiple queries

---

## 6. Quality Filtering

### 6.1 Junk Detection

**Exclude low-quality chunks:**

```sql
-- Built into hybrid_retrieve()
WHERE kc.junk = FALSE
```

**Manual quality filtering:**

```python
# Filter by text quality threshold
results = await hybrid_retrieve(session, query, top_k=30)
high_quality = [
    r for r in results
    if r.get('text_quality', 0) > 0.8
][:14]  # Take top 14 high-quality results
```

### 6.2 Source Filtering

**Filter by extraction method:**

```python
# Prefer specific extraction methods
results = await hybrid_retrieve(session, query, top_k=30)
preferred = [
    r for r in results
    if r['extraction_method'] in ['docling', 'pdfplumber']
]
```

**Filter by category:**

```python
# Only tax-related documents
from sqlalchemy import text

sql = text("""
    SELECT ... (hybrid query with WHERE ki.category = :category)
""")
result = await session.execute(sql, {"category": "IVA", ...})
```

---

## 7. Common Query Patterns

### 7.1 Regulatory Document Lookup

```python
# Find recent circulars from Agenzia delle Entrate
results = await hybrid_retrieve(
    session=session,
    query="circolare agenzia entrate",
    fts_weight=0.50,
    vector_weight=0.20,
    recency_weight=0.30,  # Emphasize recent circulars
    recency_days=180,     # 6 months
    top_k=10
)
```

### 7.2 Conceptual Search

```python
# User asks vague question - rely more on semantic understanding
results = await hybrid_retrieve(
    session=session,
    query="come calcolare le tasse per libero professionista",
    fts_weight=0.20,
    vector_weight=0.70,  # Emphasize semantic understanding
    recency_weight=0.10,
    top_k=14
)
```

### 7.3 Exact Legal Reference

```python
# User provides specific article number - emphasize FTS
results = await hybrid_retrieve(
    session=session,
    query="codice civile articolo 1571",
    fts_weight=0.80,  # Exact term matching critical
    vector_weight=0.10,
    recency_weight=0.10,
    recency_days=3650,  # 10 years (legal texts don't expire quickly)
    top_k=5
)
```

### 7.4 Recent News

```python
# User asks about recent changes
results = await hybrid_retrieve(
    session=session,
    query="nuove detrazioni fiscali 2024",
    fts_weight=0.40,
    vector_weight=0.20,
    recency_weight=0.40,  # Heavily favor recent documents
    recency_days=60,      # 2 months
    top_k=10
)
```

---

## 8. Troubleshooting

### 8.1 No Results Returned

**Problem:** `hybrid_retrieve()` returns empty list

**Diagnosis:**
```python
# Check FTS separately
results_fts = await fts_only_retrieve(session, query, top_k=10)
print(f"FTS results: {len(results_fts)}")

# Check if embedding generation failed
from app.core.embed import generate_embedding
embedding = await generate_embedding(query)
print(f"Embedding generated: {embedding is not None}")
```

**Common causes:**
1. **Query too specific:** No FTS matches found
   - Solution: Broaden query, use OR operators
2. **Embedding generation failed:** API outage
   - Solution: System auto-falls back to FTS-only
3. **All chunks marked as junk:** Quality filter too strict
   - Solution: Check `junk` flag distribution in database

### 8.2 Poor Result Relevance

**Problem:** Results don't match user intent

**Diagnosis:**
```python
# Inspect score breakdown
for result in results[:5]:
    print(f"Combined: {result['combined_score']:.3f}")
    print(f"  FTS: {result['fts_score']:.3f}")
    print(f"  Vector: {result['vector_score']:.3f}")
    print(f"  Recency: {result['recency_score']:.3f}")
    print(f"  Text: {result['chunk_text'][:100]}...")
    print("---")
```

**Common issues:**
1. **FTS score dominates, but wrong results:**
   - Solution: Lower `fts_weight`, increase `vector_weight`
2. **Recent but irrelevant docs ranking high:**
   - Solution: Lower `recency_weight`
3. **Vector similarity finding related but not exact matches:**
   - Solution: Increase `fts_weight` for exact term matching

### 8.3 Slow Queries

**Problem:** Latency >300ms consistently

**Diagnosis:**
```python
# Use EXPLAIN ANALYZE
explain = await explain_hybrid_query(session, query)
print(explain)
```

**Common causes:**
1. **Sequential scan instead of index scan:**
   - Solution: Check indexes exist, run `VACUUM ANALYZE`
2. **Too many vectors within distance threshold:**
   - Solution: Lower distance threshold from 1.0 to 0.8
3. **Large result set:**
   - Solution: Reduce `top_k`, add more specific filters

**Optimization checklist:**
- [ ] Indexes exist (`idx_kc_embedding_ivfflat_1536`, `idx_kc_search_vector_gin`)
- [ ] Database statistics up to date (`VACUUM ANALYZE knowledge_chunks`)
- [ ] Connection pool not exhausted
- [ ] Query uses prepared statements (SQLAlchemy does this automatically)

---

## 9. Advanced Techniques

### 9.1 Multi-Stage Retrieval

**Concept:** Retrieve more broadly, then rerank for precision

```python
# Stage 1: Hybrid retrieval (broad)
candidates = await hybrid_retrieve(
    session=session,
    query=query,
    top_k=30,  # Get 30 candidates
    fts_weight=0.50,
    vector_weight=0.35,
    recency_weight=0.15
)

# Stage 2: Custom reranking logic
def custom_rerank(candidates, query):
    # Example: Boost results with specific keywords in title
    for candidate in candidates:
        if "agenzia entrate" in candidate['document_title'].lower():
            candidate['combined_score'] *= 1.2  # 20% boost

    # Re-sort by adjusted score
    return sorted(candidates, key=lambda x: x['combined_score'], reverse=True)[:14]

final_results = custom_rerank(candidates, query)
```

**Note:** DEV-71 will add cross-encoder reranking to automate this.

### 9.2 Query Expansion

**Concept:** Expand user query with synonyms before searching

```python
# Example: User types "p.iva"
# Expand to: "p.iva OR partita iva OR codice iva"

italian_tax_synonyms = {
    "p.iva": ["partita iva", "codice iva", "numero iva"],
    "iva": ["imposta valore aggiunto"],
    "irpef": ["imposta reddito persone fisiche"],
}

def expand_query(query: str) -> str:
    for term, synonyms in italian_tax_synonyms.items():
        if term in query.lower():
            expanded = f"({term} OR {' OR '.join(synonyms)})"
            query = query.replace(term, expanded)
    return query

expanded_query = expand_query("calcolo p.iva")
# Result: "calcolo (p.iva OR partita iva OR codice iva OR numero iva)"

results = await hybrid_retrieve(session, expanded_query)
```

**Note:** DEV-73 will add Italian financial dictionary for automatic expansion.

### 9.3 Metadata Filtering

**Filter by document metadata before hybrid search:**

```python
from sqlalchemy import text

# Custom query with metadata filters
sql = text("""
    WITH ranked AS (
        SELECT
            kc.id, kc.chunk_text, kc.embedding, kc.search_vector,
            ki.category, ki.publication_date,
            ts_rank_cd(kc.search_vector, websearch_to_tsquery('italian', :query)) AS fts_score,
            1 - (kc.embedding <=> CAST(:embedding AS vector)) AS vector_score
        FROM knowledge_chunks kc
        INNER JOIN knowledge_items ki ON kc.knowledge_item_id = ki.id
        WHERE
            kc.junk = FALSE
            AND ki.category = :category  -- Metadata filter
            AND ki.publication_date > :min_date  -- Date filter
            AND kc.search_vector @@ websearch_to_tsquery('italian', :query)
    )
    SELECT *, (0.50 * fts_score + 0.50 * vector_score) AS combined_score
    FROM ranked
    ORDER BY combined_score DESC
    LIMIT :top_k;
""")

result = await session.execute(sql, {
    "query": "fatturazione elettronica",
    "embedding": embedding_str,
    "category": "IVA",
    "min_date": "2023-01-01",
    "top_k": 14
})
```

---

## 10. Testing & Validation

### 10.1 Unit Testing

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_hybrid_retrieve_returns_results(db_session: AsyncSession):
    """Test that hybrid_retrieve returns results for common query"""
    results = await hybrid_retrieve(
        session=db_session,
        query="contratti locazione",
        top_k=10
    )

    assert len(results) > 0
    assert all('combined_score' in r for r in results)
    assert results[0]['combined_score'] >= results[-1]['combined_score']  # Sorted

@pytest.mark.asyncio
async def test_custom_weights_affect_ranking(db_session: AsyncSession):
    """Test that changing weights affects result order"""
    query = "IVA fatturazione"

    # FTS-heavy
    results_fts = await hybrid_retrieve(
        session=db_session,
        query=query,
        fts_weight=0.90,
        vector_weight=0.10,
        top_k=5
    )

    # Vector-heavy
    results_vector = await hybrid_retrieve(
        session=db_session,
        query=query,
        fts_weight=0.10,
        vector_weight=0.90,
        top_k=5
    )

    # Different weights should produce different top results
    assert results_fts[0]['chunk_id'] != results_vector[0]['chunk_id']
```

### 10.2 Precision/Recall Evaluation

```python
# Create test set with manually labeled relevance
test_queries = [
    ("contratti locazione commerciale", ["doc_123", "doc_456"]),  # Relevant doc IDs
    ("calcolo IVA 22%", ["doc_789"]),
    # ... 50+ test queries
]

async def evaluate_precision_recall(session, test_queries):
    total_precision = 0
    total_recall = 0

    for query, relevant_ids in test_queries:
        results = await hybrid_retrieve(session, query, top_k=14)
        retrieved_ids = [r['knowledge_item_id'] for r in results]

        # Precision: How many retrieved are relevant?
        relevant_retrieved = set(retrieved_ids) & set(relevant_ids)
        precision = len(relevant_retrieved) / len(retrieved_ids) if retrieved_ids else 0

        # Recall: How many relevant were retrieved?
        recall = len(relevant_retrieved) / len(relevant_ids) if relevant_ids else 0

        total_precision += precision
        total_recall += recall

    avg_precision = total_precision / len(test_queries)
    avg_recall = total_recall / len(test_queries)

    print(f"Average Precision@14: {avg_precision:.2%}")
    print(f"Average Recall@14: {avg_recall:.2%}")

    return avg_precision, avg_recall
```

---

## 11. Migration Path

### 11.1 From Pinecone to pgvector (If Needed)

**For FAQs (DEV-67):**

```python
# Export from Pinecone
pinecone_index = pinecone.Index("pratikoai-vectors")
vectors = pinecone_index.query(
    namespace="faq_embeddings",
    top_k=10000,  # All FAQs
    include_metadata=True,
    include_values=True
)

# Import to PostgreSQL
for vector in vectors['matches']:
    await session.execute(
        text("""
            INSERT INTO faq_embeddings (faq_id, question, answer, embedding, metadata)
            VALUES (:faq_id, :question, :answer, :embedding::vector, :metadata)
        """),
        {
            "faq_id": vector['id'],
            "question": vector['metadata']['question'],
            "answer": vector['metadata']['answer'],
            "embedding": str(vector['values']),  # Convert to pgvector format
            "metadata": json.dumps(vector['metadata'])
        }
    )
await session.commit()
```

---

## 12. Production Checklist

**Before deploying hybrid search changes:**

- [ ] Indexes exist and are up-to-date
  ```sql
  SELECT indexname, idx_scan FROM pg_stat_user_indexes WHERE tablename = 'knowledge_chunks';
  ```

- [ ] Database statistics current
  ```sql
  VACUUM ANALYZE knowledge_chunks;
  VACUUM ANALYZE knowledge_items;
  ```

- [ ] Test on staging with production-like data volume

- [ ] Benchmark latency (p50, p95, p99)

- [ ] Monitor embedding API cost (should be <$10/month)

- [ ] Set up alerts for query latency >300ms (DEV-69 will add Prometheus/Grafana)

- [ ] Document any custom weight configurations

- [ ] Have rollback plan (revert to default weights)

---

## 13. Related Documentation

**Core Implementation:**
- `app/retrieval/postgres_retriever.py` - Production code (this guide)
- `app/core/embed.py` - Embedding generation
- `app/core/config.py` - Default weights configuration

**Database Schema:**
- `docs/DATABASE_ARCHITECTURE.md` - Full architecture documentation
- `alembic/versions/` - Database migrations

**Roadmap:**
- `ARCHITECTURE_ROADMAP.md` - Future enhancements (cross-encoder reranking, HNSW index)

---

## 14. E2E Testing for RSS Feeds (DEV-BE-69)

### 14.1 Why E2E Tests?

**The Messaggio 3585 Bug:**
- User query: "Di cosa parla il Messaggio numero 3585 dell'inps?"
- Document existed: "Messaggio numero 3585 del 27-11-2025"
- Bug: Query normalizer returned `{'type': 'DL', 'number': None}`
- Result: Search returned empty, despite document existing

**Root Cause:** Unit tests passed, but integration between components failed.

### 14.2 E2E Test Architecture

```
tests/e2e/
├── conftest.py              # Shared fixtures
├── feeds/
│   ├── base_feed_test.py    # Base class (4-step flow)
│   ├── test_inps_feeds.py   # 5 INPS feeds
│   ├── test_agenzia_entrate_feeds.py  # 3 AE feeds
│   └── test_other_feeds.py  # INAIL, MEF, etc.
└── scrapers/
    ├── test_gazzetta_scraper.py
    └── test_cassazione_scraper.py
```

### 14.3 The 4-Step Test Flow

Every feed test validates the complete RAG pipeline:

```python
async def run_full_test_flow(self, query: str):
    # Step 1: Search - Documents found via hybrid search
    search_result = await self._search_for_documents(query)
    assert search_result["count"] > 0

    # Step 2: Generate - LLM generates response with context
    llm_result = await self._generate_llm_response(query, search_result)
    assert llm_result["llm_calls"] > 0

    # Step 3: Save - Golden set created (simulates "Corretta" button)
    golden_save = await self._save_as_golden_set(query, llm_result)
    assert golden_save["saved"]

    # Step 4: Cache - Retrieval bypasses LLM (CRITICAL)
    golden_retrieve = await self._retrieve_from_golden_set(query)
    assert golden_retrieve["llm_calls"] == 0  # Must not call LLM
```

### 14.4 Running E2E Tests

```bash
# Run all E2E tests
pytest tests/e2e/ -m "e2e" -v

# Run only feed tests
pytest tests/e2e/feeds/ -v

# Skip slow tests (with LLM calls)
pytest tests/e2e/ -m "e2e and not slow"

# Run specific feed
pytest tests/e2e/feeds/test_inps_feeds.py -v
```

### 14.5 Cost Analysis

| Scenario | Tests | Cost/Run |
|----------|-------|----------|
| Quick (no LLM) | 30 | $0.00 |
| Full (with LLM) | 52 | ~$0.08 |

**Annual cost:** ~$360 (10 runs/day × 30 days × $0.10/run × 12 months)

### 14.6 Test Coverage Matrix

| Source | Feeds | Query Variations |
|--------|-------|------------------|
| INPS | 5 | 3 per feed |
| Agenzia Entrate | 3 | 3 per feed |
| INAIL | 2 | 3 per feed |
| MEF | 2 | 3 per feed |
| Ministero Lavoro | 1 | 3 per feed |
| Gazzetta Ufficiale | 1 | 3 per feed |
| **Total** | 14 | 42+ tests |

**Full documentation:** See `docs/E2E_RSS_TESTING_STRATEGY.md`

---

**Document Maintained By:** Engineering Team
**Review Cycle:** Quarterly (Jan, Apr, Jul, Oct)
**Next Review:** 2025-01-15
