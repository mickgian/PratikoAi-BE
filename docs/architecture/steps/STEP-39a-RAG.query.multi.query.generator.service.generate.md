# RAG STEP 39a — MultiQueryGeneratorService.generate (RAG.query.multi_query)

**Type:** process
**Category:** query
**Node ID:** `step_039a_multi_query`

## Intent (Blueprint)
This step generates optimized query variants for different search types as part of the Agentic RAG pipeline (DEV-195). It creates three query variants:
- **BM25 query:** Keywords optimized for lexical/BM25 search
- **Vector query:** Semantically expanded for embedding-based search
- **Entity query:** Focused on legal references and entities (INPS, Legge, etc.)

The step skips expansion for CHITCHAT and THEORETICAL_DEFINITION routes where multi-query adds no value.

## Current Implementation (Repo)
- **Role:** Internal
- **Status:** Implemented
- **Paths / classes:** `app/core/langgraph/nodes/step_039a__multi_query.py` - `node_step_39a()`
- **Service:** `app/services/multi_query_generator.py` - `MultiQueryGeneratorService`
- **Behavior notes:**
  - Skips for chitchat/theoretical_definition routes
  - Falls back to original query on any error
  - Stores result in state["query_variants"] as serializable dict

## Differences (Blueprint vs Current)
- None - implementation matches DEV-195 specification

## Risks / Impact
- Low risk - graceful fallback to original query on any service error
- Uses GPT-4o-mini (BASIC tier) for low latency and cost

## TDD Task List
- [x] Unit tests for successful generation
- [x] Unit tests for skip logic (chitchat, theoretical_definition)
- [x] Unit tests for error fallback behavior
- [x] Unit tests for state preservation
- [x] Observability: structured logging with rag_step_log
- [x] Integration test for full flow (39a -> 39b -> 39c)

## Done When
- All 15 tests pass; service integrates with LLM Router output

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
- DEV-195: Create Step 39 Query Expansion Nodes
- Related: DEV-188 (MultiQueryGenerator service implementation)


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: Implemented  |  Registry: Pending

Notes:
- Internal step (no wiring required)
- Part of Agentic RAG Phase 7 pipeline
<!-- AUTO-AUDIT:END -->
