# RAG STEP 39b — HyDEGeneratorService.generate (RAG.query.hyde)

**Type:** process
**Category:** query
**Node ID:** `step_039b_hyde`

## Intent (Blueprint)
This step implements Hypothetical Document Embeddings (HyDE) as part of the Agentic RAG pipeline (DEV-195). HyDE generates a hypothetical answer document in Italian bureaucratic style, which when embedded, is closer to real documents than the original query embedding.

Key features:
- Generates 150-250 word documents in Italian bureaucratic style
- Includes legal references (Leggi, Decreti, Circolari)
- Uses formal administrative language
- Skips generation for CHITCHAT and CALCULATOR routes

## Current Implementation (Repo)
- **Role:** Internal
- **Status:** Implemented
- **Paths / classes:** `app/core/langgraph/nodes/step_039b__hyde.py` - `node_step_39b()`
- **Service:** `app/services/hyde_generator.py` - `HyDEGeneratorService`
- **Behavior notes:**
  - Skips for chitchat/calculator routes (set by service)
  - Returns skip result with reason on timeout or error
  - Stores result in state["hyde_result"] as serializable dict

## Differences (Blueprint vs Current)
- None - implementation matches DEV-195 specification

## Risks / Impact
- Low risk - graceful skip on any error (no fallback document)
- Uses GPT-4o-mini (BASIC tier) for low latency and cost
- HyDE improves recall for technical queries but adds ~200ms latency

## TDD Task List
- [x] Unit tests for successful generation
- [x] Unit tests for skip logic (chitchat, calculator)
- [x] Unit tests for error handling (returns skipped result)
- [x] Unit tests for state preservation
- [x] Observability: structured logging with rag_step_log
- [x] Integration test for full flow (39a -> 39b -> 39c)

## Done When
- All tests pass; HyDE documents generated in Italian bureaucratic style

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
- DEV-195: Create Step 39 Query Expansion Nodes
- Related: DEV-189 (HyDEGenerator service implementation)
- Reference: Section 13.6 - Hypothetical Document Embeddings


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: Implemented  |  Registry: Pending

Notes:
- Internal step (no wiring required)
- Part of Agentic RAG Phase 7 pipeline
<!-- AUTO-AUDIT:END -->
