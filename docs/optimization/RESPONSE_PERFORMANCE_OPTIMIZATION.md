# Response Performance Optimization - Complete Analysis

**Last Updated:** 2026-03-04
**Scope:** End-to-end LangGraph RAG pipeline latency and cost optimization

---

## Executive Summary

Full analysis of the PratikoAI LangGraph pipeline identified **6 distinct LLM API call locations** and multiple sequential bottlenecks. Two rounds of optimization have been implemented:

- **Round 1** (Nov 2025): Eliminated duplicate classifier LLM calls (-25% API calls)
- **Round 2** (Mar 2026): Parallelized pipeline stages and added caching (-15-21s estimated)

**Combined Impact:**
- LLM API calls: 4 -> 2-3 per query
- Estimated latency reduction: 15-21s per request
- Embedding API cost savings via caching

---

## Pipeline Architecture

### LLM Call Inventory

| # | Step | LLM Call | Model Tier | Purpose |
|---|------|----------|------------|---------|
| 1 | 12 | `step_012__extract_query` | BASIC (gpt-4o-mini) | Query extraction from conversation |
| 2 | 25 | `node_step_25__llm_router` | BASIC (gpt-4o-mini) | Intent routing (chitchat/research/calc) |
| 3 | 39a | `_run_multi_query` | BASIC (gpt-4o-mini) | Multi-query expansion (BM25/vector/entity variants) |
| 4 | 39a | `reformulate_short_query_llm` | BASIC (gpt-4o-mini) | Short query expansion with context |
| 5 | 39b | `_run_hyde` | BASIC (gpt-4o-mini) | Hypothetical Document Embedding generation |
| 6 | 64 | `node_step_64` | PREMIUM (gpt-4o) / configurable | Final answer generation with Tree-of-Thoughts |

### LangGraph Node Flow (After Optimization)

```
ExtractQuery(12) -> LLMRouter(25) -> ParallelExpansion(39ab) -> ParallelRetrieval(39c) -> BuildContext
    -> ClassifyAndScore(31-32) -> ConfidenceCheck(33)
        -> TrackMetrics(34)
        -> LLMFallbackResolve(35-38) -> TrackMetrics(34)
    -> LLMCall(64) -> Response
```

---

## Round 1: LLM Call Reduction (Nov 2025)

### Problem
Query "Cosa dice la risoluzione 64?" triggered 4 LLM API calls instead of expected 3. The `DomainActionClassifier.classify()` automatically triggered an LLM fallback when rule-based confidence fell below threshold, causing duplicate classification calls.

### Changes
1. **Disabled automatic LLM fallback** in `domain_action_classifier.py` - Rule-based classifier achieves 95%+ accuracy for tax/legal domains
2. **Hardcoded gpt-4o-mini** for classification - Bypasses provider selection overhead

### Results
| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| LLM API Calls | 4 | 3 | -25% |
| Classifier LLM Calls | 2 | 0 | -100% |
| Response Latency | ~2.5s | ~2.3s | -8% |
| Cost per Query | ~$0.0020 | ~$0.0017 | -15% |

---

## Round 2: Pipeline Parallelization (Mar 2026)

### S1: Parallelize MultiQuery + HyDE (~4-5s saving)

**Problem:** MultiQuery expansion (step 39a) and HyDE generation (step 39b) ran as separate sequential LangGraph nodes. Both are independent LLM calls that only depend on `user_query` and `routing_decision`.

**Solution:** Combined into single node `step_039ab__parallel_expansion` using `asyncio.gather()`.

**Files:**
- `app/core/langgraph/nodes/step_039ab__parallel_expansion.py` (NEW)
- `app/core/langgraph/graph.py` (MODIFIED - wiring)

**Key Code:**
```python
async def node_step_39ab(state: RAGState) -> RAGState:
    query_variants, hyde_result = await asyncio.gather(
        _run_multi_query(user_query, route, routing_decision, messages),
        _run_hyde(user_query, route),
    )
    return {**state, "query_variants": query_variants, "hyde_result": hyde_result}
```

**Impact:** ~4-5s saved by overlapping two LLM API calls.

---

### S2: Separate DB Sessions for Parallel Retrieval (~8-12s saving)

**Problem:** KB searches (BM25, vector, HyDE, authority) in `ParallelRetrievalService` ran sequentially because they shared one `AsyncSession`. SQLAlchemy's `AsyncSession` doesn't support concurrent operations.

**Solution:** Added `session_factory` parameter that creates independent DB sessions per search task, enabling true `asyncio.gather()` parallelism.

**Files:**
- `app/services/parallel_retrieval.py` (MODIFIED)
- `app/core/langgraph/nodes/step_039c__parallel_retrieval.py` (MODIFIED)

**Key Code:**
```python
class ParallelRetrievalService:
    def __init__(self, search_service, embedding_service, session_factory=None):
        self._session_factory = session_factory

    async def _execute_parallel_searches_with_sessions(self, ...):
        async def _kb_search_with_session(search_type, search_fn, *args, **kwargs):
            async with self._session_factory() as session:
                svc = SearchService(db_session=session)
                temp_service = ParallelRetrievalService(search_service=svc, ...)
                return await search_fn(temp_service, *args, **kwargs)

        results = await asyncio.gather(
            _safe_search("bm25", _kb_search_with_session(...)),
            _safe_search("vector", _kb_search_with_session(...)),
            _safe_search("hyde", _kb_search_with_session(...)),
            _safe_search("authority", _kb_search_with_session(...)),
            _safe_search("brave", self._search_brave(...)),
        )
```

**Backward Compatibility:** Falls back to sequential execution when no `session_factory` provided.

**Impact:** ~8-12s saved by running 4 sequential DB queries + 1 HTTP call concurrently.

---

### S3: Cache Embeddings by Content Hash (~0.5-1s saving)

**Problem:** The same text frequently gets re-embedded across requests (e.g., identical queries, repeated document chunks). Each call to `generate_embedding()` hits the OpenAI API.

**Solution:** Redis cache with SHA-256 content hashing. Embeddings are deterministic for the same input, so caching is safe with a 24-hour TTL.

**Files:**
- `app/core/embed.py` (MODIFIED)

**Key Code:**
```python
def _embedding_cache_key(text: str) -> str:
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"embed:{EMBED_MODEL}:{text_hash}"

async def generate_embedding(text: str) -> list[float] | None:
    cache_key = _embedding_cache_key(text)
    cached = await _get_cached_embedding(cache_key)
    if cached is not None:
        return cached
    # ... API call, then cache result
```

**Impact:** ~0.5-1s saved per cache hit + API cost savings.

---

### S4: Consolidate Classification Nodes (~2-3s saving)

**Problem:** The classification pipeline used 6 separate LangGraph nodes with 5 edges and 2 conditional routing decisions:
```
ClassifyDomain -> CalcScores -> ConfidenceCheck -> LLMFallback -> LLMBetter -> UseLLM/UseRuleBased -> TrackMetrics
```

Each node transition adds ~200-500ms overhead.

**Solution:** Consolidated into 2 nodes:
1. `ClassifyAndScore` (steps 31+32) - sequential dependency, same node
2. `LLMFallbackResolve` (steps 35+36+37+38) - complete fallback logic in one node

**Files:**
- `app/core/langgraph/nodes/step_031_032__classify_and_score.py` (NEW)
- `app/core/langgraph/nodes/step_035_038__llm_fallback_resolve.py` (NEW)
- `app/core/langgraph/graph.py` (MODIFIED - wiring)

**New Flow:**
```
ClassifyAndScore -> ConfidenceCheck -> {TrackMetrics, LLMFallbackResolve -> TrackMetrics}
```

**Impact:** ~2-3s saved by eliminating 4 node transitions.

---

## Test Coverage

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `tests/core/langgraph/nodes/test_step_039ab__parallel_expansion.py` | 10 | Concurrent execution, error handling, chitchat skip |
| `tests/core/langgraph/nodes/test_step_031_032__classify_and_score.py` | 3 | Classification + scores, state preservation |
| `tests/core/langgraph/nodes/test_step_035_038__llm_fallback_resolve.py` | 4 | LLM better/worse, error fallback, comparison data |
| `tests/services/test_parallel_retrieval_sessions.py` | 4 | Concurrent execution, sequential fallback, error isolation |
| `tests/core/test_embed_cache.py` | 7 | Cache key generation, hit/miss, disabled cache |

---

## Estimated Combined Impact

| Optimization | Latency Saving | Cost Impact |
|-------------|----------------|-------------|
| S1: Parallel MultiQuery+HyDE | ~4-5s | Neutral |
| S2: Parallel DB sessions | ~8-12s | Neutral |
| S3: Embedding cache | ~0.5-1s per hit | -API calls |
| S4: Node consolidation | ~2-3s | Neutral |
| **Total** | **~15-21s** | **Reduced** |

---

## Model Tier Strategy

| Tier | Model | Cost | Used By |
|------|-------|------|---------|
| BASIC | gpt-4o-mini | $0.15/1M input | Query extraction, routing, multi-query, HyDE |
| PREMIUM | gpt-4o | $2.50/1M input | Final answer generation (Tree-of-Thoughts) |
| PRODUCTION | mistral-large-latest | $2.00/1M input | Alternative for final answers |

All utility LLM calls (steps 12, 25, 39a, 39b) use BASIC tier. Only the final answer generation (step 64) uses PREMIUM tier.

---

## Original Nodes Preserved

The original separate node files are preserved for reference/rollback:
- `step_039a__multi_query.py` - Original standalone MultiQuery node
- `step_039b__hyde.py` - Original standalone HyDE node
- `step_031__classify_domain.py` - Original ClassifyDomain node
- `step_032__calc_scores.py` - Original CalcScores node
- `step_035__llm_fallback.py` - Original LLMFallback node
- (etc.)

These are no longer wired in `graph.py` but remain importable for backward compatibility.

---

## Future Optimizations

### 1. Unified Query Analyzer
Merge `QueryExtraction` + `LLMRouter` + `MultiQuery` into single LLM call with structured output. Would reduce 4 BASIC-tier LLM calls to 1.

### 2. Streaming Answer Generation
Stream the final answer (step 64) to reduce time-to-first-token.

### 3. Speculative Retrieval
Start retrieval before routing completes for likely-research queries.

### 4. Classification Caching
Cache classification results by normalized query hash (similar to S3 embedding cache).
