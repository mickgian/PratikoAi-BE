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

### LLM Call Inventory (Updated Mar 2026)

| # | Step | LLM Call | Model Tier | Purpose | Conditional? |
|---|------|----------|------------|---------|--------------|
| 1 | 12 | `step_012__extract_query` | **None** (rule-based) | Query extraction from conversation | N/A — no LLM call |
| 2 | 34a | `node_step_34a` (HF classifier) | **$0** (local HuggingFace mDeBERTa) | Intent routing — primary path | Always runs (<100ms) |
| 2b | 34a | `LLMRouterService.route()` | BASIC (gpt-4o-mini) | Intent routing — GPT fallback | Only when HF confidence < 0.5 |
| 3 | 39ab | `reformulate_short_query_llm` | BASIC (gpt-4o-mini) | Short query expansion with context | Only when query < 5 words |
| 4 | 39ab | `MultiQueryGeneratorService` | BASIC (gpt-4o-mini) | Multi-query expansion (BM25/vector/entity) | Skipped for chitchat; cached by MD5 |
| 5 | 39ab | `HyDEGeneratorService` | BASIC (gpt-4o-mini) | Hypothetical Document Embedding generation | Parallel with #4 (S1 optimization) |
| 6 | 64 | `node_step_64` | PREMIUM (gpt-4o) / configurable | Final answer generation with Tree-of-Thoughts | Always |

**Typical query (5+ words, HF confident):** 3 LLM calls — MultiQuery + HyDE (parallel) + Final Answer
**Short follow-up (HF confident):** 4 LLM calls — reformulate + MultiQuery + HyDE (parallel) + Final Answer
**HF uncertain:** +1 GPT-4o-mini fallback call for routing

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

### ~~1. Unified Query Analyzer~~ — REJECTED (Mar 2026)

**Original Proposal:** Merge `QueryExtraction` + `LLMRouter` + `MultiQuery` into single LLM call with structured output. Claimed to reduce 4 BASIC-tier LLM calls to 1.

**Analysis Result: Not Recommended.** The original claim was based on outdated pipeline data. Detailed code review reveals:

| Component | Actual LLM Call? | When? |
|-----------|-----------------|-------|
| `ExtractQuery` (step 12) | **No** — pure rule-based message parsing | Never |
| `LLMRouter` (step 34a) | **Rarely** — HF classifier handles most queries locally for $0 | Only when HF confidence < 0.5 |
| `reformulate_short_query` | **Sometimes** | Only when query < 5 words |
| `MultiQuery` + `HyDE` | **Yes** — but already parallelized (S1) | Always (non-chitchat) |

**Best case (happy path):** 2 parallel LLM calls (MultiQuery + HyDE) — nothing to merge.
**Worst case:** 4 calls, but merging saves only ~1-2s (router fallback + reformulation are sequential before expansion).

**Reasons for rejection:**
1. **Would bypass the free HF classifier** — the routing happy path costs $0 and runs in <100ms locally. A merged LLM call would replace this with a paid GPT-4o-mini call on every query.
2. **Sequential dependency is architectural** — MultiQuery needs routing decision to skip expansion for chitchat/calculator routes. Merging requires either wasting tokens on unnecessary variants or cramming routing + generation into one fragile prompt.
3. **Short query reformulation depends on conversation context** — it reformulates "e l'IRAP?" using the last assistant response. MultiQuery then works on the reformulated text. One merged call must do reformulation AND variant generation — a harder task that reduces output quality.
4. **Independent failure domains** — routing fallback (→ TECHNICAL_RESEARCH) and MultiQuery fallback (→ original query) are separate recovery paths. One merged call means one failure breaks everything.
5. **Industry consensus** — Google, Perplexity, and production RAG systems use staged processing when tasks have sequential dependencies and conditional execution paths.

### 2. Streaming Answer Generation
Stream the final answer (step 64) to reduce time-to-first-token. Perceived latency drops ~60% even if total time is unchanged. **Low risk, high impact.**

### 3. Speculative Retrieval
Start retrieval before routing completes for likely-research queries. Saves ~1-2s but wastes DB resources on chitchat queries. **Medium risk.**

### 4. Classification Caching
Cache classification results by normalized query hash (similar to S3 embedding cache). Saves ~1-2s on repeated routing patterns. **Very low risk.**

### 5. HF Classifier Fine-Tuning (NEW)
Fine-tune the HuggingFace intent classifier on captured low-confidence predictions (DEV-253 labeling data) to reduce GPT-4o-mini fallback rate. Saves ~1-2s on queries that currently trigger fallback. **Low risk, reduces cost.**
