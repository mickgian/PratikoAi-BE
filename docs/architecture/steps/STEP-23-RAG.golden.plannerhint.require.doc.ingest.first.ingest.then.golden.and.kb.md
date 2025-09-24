# RAG STEP 23 — PlannerHint.require_doc_ingest_first ingest then Golden and KB (RAG.golden.plannerhint.require.doc.ingest.first.ingest.then.golden.and.kb)

**Type:** process  
**Category:** golden  
**Node ID:** `RequireDocIngest`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `RequireDocIngest` (PlannerHint.require_doc_ingest_first ingest then Golden and KB).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/golden.py:step_23__require_doc_ingest`
- **Status:** ✅ Implemented
- **Behavior notes:** Async orchestrator that sets planning hints when documents need to be ingested before proceeding with Golden Set and KB queries. Sets workflow flags (requires_doc_ingest_first, defer_golden_lookup, defer_kb_search) to coordinate document-first processing. Routes to Step 31 (ClassifyDomain) to continue the workflow.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - pure coordination logic with no external dependencies

## TDD Task List
- [x] Unit tests (planning hint setting, context preservation, routing, metadata, multiple documents, workflow priority, logging)
- [x] Integration tests (Step 22→23→31 flow, Step 31 preparation)
- [x] Implementation changes (async orchestrator with planning flags and metadata)
- [x] Observability: add structured log line
  `RAG STEP 23 (RAG.golden.plannerhint.require.doc.ingest.first.ingest.then.golden.and.kb): PlannerHint.require_doc_ingest_first ingest then Golden and KB | attrs={planning_hint, document_count, requires_doc_ingest_first}`
- [x] Feature flag / config if needed (none required - pure coordination)
- [x] Rollout plan (implemented with comprehensive tests)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ✅  |  Confidence: 1.00

Top candidates:
1) app/orchestrators/golden.py:32 — app.orchestrators.golden.step_23__require_doc_ingest (score 1.00)
   Evidence: Score 1.00, RAG STEP 23 — PlannerHint.require_doc_ingest_first ingest then Golden and KB
ID: RAG.golden.plannerhint.require.doc.ingest.first.ingest.then.golden.and.kb
Type: process

Notes:
- ✅ Implementation complete and wired correctly
- ✅ Async orchestrator with planning coordination
- ✅ 10/10 tests passing
- ✅ Routes to Step 31 (ClassifyDomain) per Mermaid
- ✅ Sets workflow flags: requires_doc_ingest_first, defer_golden_lookup, defer_kb_search
- ✅ Pure coordination logic with no external service dependencies

Completed TDD actions:
- ✅ Created async orchestrator in app/orchestrators/golden.py
- ✅ Implemented planning hint coordination with workflow flags
- ✅ Implemented 10 comprehensive tests (unit + parity + integration)
- ✅ Added structured observability logging
- ✅ Verified Step 22→23→31 integration flow
<!-- AUTO-AUDIT:END -->