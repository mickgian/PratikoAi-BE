# RAG STEP 27 — KB newer than Golden as of or conflicting tags? (RAG.golden.kb.newer.than.golden.as.of.or.conflicting.tags)

**Type:** process  
**Category:** golden  
**Node ID:** `KBDelta`

## Intent (Blueprint)
Evaluates whether KB has newer content or conflicting tags compared to the Golden Set match. Routes to ServeGolden (Step 28) if no conflict, or to PreContextFromGolden (Step 29) if KB has updates that should be merged.

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/golden.py:step_27__kbdelta`
- **Status:** ✅ Implemented
- **Behavior notes:** Async orchestrator that evaluates KB delta/conflict using dual-check logic: (1) timestamp comparison for newer KB content, (2) tag-based conflict detection for supersedes/obsoletes/replaces/updated indicators. Routes to Step 28 (ServeGolden) if no delta, or Step 29 (PreContextFromGolden) if conflict detected. Preserves all context from Step 26.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - graceful degradation on missing timestamps/metadata

## TDD Task List
- [x] Unit tests (no changes→serve, newer KB→merge, conflicting tags→merge, context preservation, delta metadata, logging, missing timestamps, supersedes tag)
- [x] Parity tests (delta logic verification)
- [x] Integration tests (Step 26→27→28/29 flow, Step 27→28 context preparation)
- [x] Implementation changes (async orchestrator with timestamp + tag conflict checks)
- [x] Observability: add structured log line
  `RAG STEP 27 (RAG.golden.kb.newer.than.golden.as.of.or.conflicting.tags): KB newer than Golden as of or conflicting tags? | attrs={kb_has_delta, conflict_reason, next_step, processing_stage}`
- [x] Feature flag / config if needed (none required - uses Step 26 output)
- [x] Rollout plan (implemented with comprehensive tests)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.54

Top candidates:
1) app/api/v1/faq_automation.py:418 — app.api.v1.faq_automation.approve_faq (score 0.54)
   Evidence: Score 0.54, Approve, reject, or request revision for a generated FAQ
2) app/api/v1/faq_automation.py:460 — app.api.v1.faq_automation.publish_faq (score 0.54)
   Evidence: Score 0.54, Publish an approved FAQ to make it available to users
3) app/orchestrators/golden.py:534 — app.orchestrators.golden.step_117__faqfeedback (score 0.51)
   Evidence: Score 0.51, RAG STEP 117 — POST /api/v1/faq/feedback.

ID: RAG.golden.post.api.v1.faq.feedba...
4) app/api/v1/faq.py:130 — app.api.v1.faq.query_faq (score 0.49)
   Evidence: Score 0.49, Query the FAQ system with semantic search and response variation.

This endpoint...
5) app/api/v1/faq.py:385 — app.api.v1.faq.create_faq (score 0.49)
   Evidence: Score 0.49, Create a new FAQ entry.

Requires admin privileges.

Notes:
- Implementation exists but may not be wired correctly

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->