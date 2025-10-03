# RAG STEP 28 — Serve Golden answer with citations (RAG.golden.serve.golden.answer.with.citations)

**Type:** process  
**Category:** golden  
**Node ID:** `ServeGolden`

## Intent (Blueprint)
Formats the Golden Set match into a ChatResponse with proper citations and metadata. This is the final step for high-confidence FAQ matches, bypassing LLM generation and serving pre-approved answers directly.

## Current Implementation (Repo)
- **Role:** Node
- **Paths / classes:** `app/orchestrators/golden.py:413` - `step_28__serve_golden()`
- **Status:** missing
- **Behavior notes:** Node orchestrator that formats Golden Set answer with citations, metadata, and timing information. Bypasses LLM when high-confidence FAQ match exists and KB has no conflicting updates. Routes to ReturnComplete with formatted response.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - simple response formatting with graceful handling of missing fields

## TDD Task List
- [x] Unit tests (serve with citations, FAQ metadata, citation formatting, context preservation, logging, missing metadata, timing)
- [x] Parity tests (response format verification)
- [x] Integration tests (Step 27→28→ReturnComplete flow)
- [x] Implementation changes (async orchestrator with response formatting)
- [x] Observability: add structured log line
  `RAG STEP 28 (RAG.golden.serve.golden.answer.with.citations): Serve Golden answer with citations | attrs={faq_id, answer_length, next_step, processing_stage}`
- [x] Feature flag / config if needed (none required - formats output from Step 27)
- [x] Rollout plan (implemented with comprehensive tests)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Node  |  Status: 🔌 (Implemented but Not Wired)  |  Confidence: 0.54

Top candidates:
1) app/api/v1/faq_automation.py:418 — app.api.v1.faq_automation.approve_faq (score 0.54)
   Evidence: Score 0.54, Approve, reject, or request revision for a generated FAQ
2) app/api/v1/faq_automation.py:460 — app.api.v1.faq_automation.publish_faq (score 0.54)
   Evidence: Score 0.54, Publish an approved FAQ to make it available to users
3) app/orchestrators/golden.py:690 — app.orchestrators.golden.step_117__faqfeedback (score 0.51)
   Evidence: Score 0.51, RAG STEP 117 — POST /api/v1/faq/feedback.

ID: RAG.golden.post.api.v1.faq.feedba...
4) app/api/v1/faq.py:130 — app.api.v1.faq.query_faq (score 0.50)
   Evidence: Score 0.50, Query the FAQ system with semantic search and response variation.

This endpoint...
5) app/api/v1/faq.py:385 — app.api.v1.faq.create_faq (score 0.50)
   Evidence: Score 0.50, Create a new FAQ entry.

Requires admin privileges.

Notes:
- Implementation exists but may not be wired correctly
- Detected Node but not in runtime registry

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->