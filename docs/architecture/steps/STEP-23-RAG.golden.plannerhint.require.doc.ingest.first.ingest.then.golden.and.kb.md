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
Status: 🔌  |  Confidence: 0.52

Top candidates:
1) app/api/v1/faq_automation.py:418 — app.api.v1.faq_automation.approve_faq (score 0.52)
   Evidence: Score 0.52, Approve, reject, or request revision for a generated FAQ
2) app/api/v1/faq_automation.py:460 — app.api.v1.faq_automation.publish_faq (score 0.52)
   Evidence: Score 0.52, Publish an approved FAQ to make it available to users
3) app/orchestrators/golden.py:690 — app.orchestrators.golden.step_117__faqfeedback (score 0.50)
   Evidence: Score 0.50, RAG STEP 117 — POST /api/v1/faq/feedback.

ID: RAG.golden.post.api.v1.faq.feedba...
4) app/api/v1/faq.py:130 — app.api.v1.faq.query_faq (score 0.48)
   Evidence: Score 0.48, Query the FAQ system with semantic search and response variation.

This endpoint...
5) app/api/v1/faq.py:385 — app.api.v1.faq.create_faq (score 0.48)
   Evidence: Score 0.48, Create a new FAQ entry.

Requires admin privileges.

Notes:
- Implementation exists but may not be wired correctly

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->