# RAG STEP 23 — PlannerHint.require_doc_ingest_first ingest then Golden and KB (RAG.golden.plannerhint.require.doc.ingest.first.ingest.then.golden.and.kb)

**Type:** process  
**Category:** golden  
**Node ID:** `RequireDocIngest`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `RequireDocIngest` (PlannerHint.require_doc_ingest_first ingest then Golden and KB).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/golden.py:step_23__require_doc_ingest`
- **Role:** Internal
- **Status:** 🔌
- **Behavior notes:** Internal transform within parent node; [processing description].
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
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: 🔌 (Implemented (internal))  |  Registry: ❌ Not in registry

Notes:
- ✅ Internal step (no wiring required)
<!-- AUTO-AUDIT:END -->