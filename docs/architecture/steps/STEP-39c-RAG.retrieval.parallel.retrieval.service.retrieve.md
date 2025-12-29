# RAG STEP 39c — ParallelRetrievalService.retrieve (RAG.retrieval.parallel)

**Type:** process
**Category:** retrieval
**Node ID:** `step_039c_parallel_retrieval`

## Intent (Blueprint)
This step executes parallel hybrid retrieval with Reciprocal Rank Fusion (RRF) as part of the Agentic RAG pipeline (DEV-195). It combines results from multiple search strategies for improved recall and precision.

Key features:
- **Parallel execution:** BM25, vector, and HyDE searches run concurrently
- **RRF Fusion:** Combines rankings using formula `score = weight / (k + rank)` with k=60
- **Search weights:** BM25 (0.3), Vector (0.4), HyDE (0.3)
- **Source authority:** Boosts based on Italian legal hierarchy (Legge > Decreto > Circolare > FAQ)
- **Recency boost:** +50% for documents published within 12 months
- **Deduplication:** By document_id, keeping highest-scoring version

## Current Implementation (Repo)
- **Role:** Internal
- **Status:** Implemented
- **Paths / classes:** `app/core/langgraph/nodes/step_039c__parallel_retrieval.py` - `node_step_39c()`
- **Service:** `app/services/parallel_retrieval.py` - `ParallelRetrievalService`
- **Behavior notes:**
  - Skips when routing_decision.needs_retrieval is False
  - Returns empty result on any error
  - Reconstructs QueryVariants and HyDEResult from state dicts
  - Stores result in state["retrieval_result"] as serializable dict

## Source Authority Hierarchy (GERARCHIA_FONTI)
| Source Type | Boost Factor |
|-------------|--------------|
| legge       | 1.30         |
| decreto     | 1.25         |
| circolare   | 1.15         |
| risoluzione | 1.10         |
| interpello  | 1.05         |
| faq         | 1.00         |
| guida       | 0.95         |

## Differences (Blueprint vs Current)
- Search services (search_service, embedding_service) are passed as None for now
- Internal search methods return empty lists (placeholder implementation)
- Production implementation requires dependency injection of actual services

## Risks / Impact
- Low risk - graceful error handling returns empty result
- Placeholder implementation ready for real search service integration
- RRF fusion algorithm is fully implemented and tested

## TDD Task List
- [x] Unit tests for successful retrieval
- [x] Unit tests for skip logic (needs_retrieval=False)
- [x] Unit tests for error handling
- [x] Unit tests for missing query_variants handling
- [x] Observability: structured logging with rag_step_log
- [x] Integration test for full flow (39a -> 39b -> 39c)

## Done When
- All tests pass; RRF fusion correctly combines search results with authority/recency boosts

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
- DEV-195: Create Step 39 Query Expansion Nodes
- Related: DEV-190 (ParallelRetrieval service implementation)
- Reference: Section 13.7 - Parallel Hybrid Retrieval with RRF


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: Implemented  |  Registry: Pending

Notes:
- Internal step (no wiring required)
- Part of Agentic RAG Phase 7 pipeline
- Placeholder search methods - requires real service integration
<!-- AUTO-AUDIT:END -->
