# RAG STEP 25 — High confidence match? score at least 0.90 (RAG.golden.high.confidence.match.score.at.least.0.90)

**Type:** process  
**Category:** golden  
**Node ID:** `GoldenHit`

## Intent (Blueprint)
Evaluates the confidence score of a Golden Set match from Step 24 to determine routing. If the similarity score is >= 0.90 (high confidence), routes to Step 26 for KB freshness validation. Otherwise routes to Step 30 (ClassifyDomain) for standard RAG flow.

## Current Implementation (Repo)
- **Role:** Node
- **Paths / classes:** `app/orchestrators/golden.py:260` - `step_25__golden_hit()`
- **Status:** missing
- **Behavior notes:** Node orchestrator that performs threshold comparison (0.90) on `similarity_score` from Step 24. Routes to KB context check (Step 26) if high confidence, or ClassifyDomain (Step 30) if low confidence. Includes decision metadata for observability.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - simple threshold comparison with clear decision logic

## TDD Task List
- [x] Unit tests (high confidence, low confidence, exact threshold, no match, context preservation, decision metadata, logging, missing score)
- [x] Integration tests (Step 24→25→26 high confidence flow, Step 24→25→30 low confidence flow, Step 25→26 context preparation)
- [x] Implementation changes (async orchestrator with 0.90 threshold decision logic)
- [x] Observability: add structured log line
  `RAG STEP 25 (RAG.golden.high.confidence.match.score.at.least.0.90): High confidence match? score at least 0.90 | attrs={high_confidence_match, similarity_score, confidence_threshold, next_step}`
- [x] Feature flag / config if needed (none required - threshold hardcoded per Mermaid spec)
- [x] Rollout plan (implemented with comprehensive tests)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Node  |  Status: 🔌 (Implemented but Not Wired)  |  Confidence: 0.53

Top candidates:
1) app/api/v1/faq_automation.py:418 — app.api.v1.faq_automation.approve_faq (score 0.53)
   Evidence: Score 0.53, Approve, reject, or request revision for a generated FAQ
2) app/api/v1/faq_automation.py:460 — app.api.v1.faq_automation.publish_faq (score 0.53)
   Evidence: Score 0.53, Publish an approved FAQ to make it available to users
3) app/orchestrators/golden.py:690 — app.orchestrators.golden.step_117__faqfeedback (score 0.51)
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
- Node step requires LangGraph wiring to be considered fully implemented

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->