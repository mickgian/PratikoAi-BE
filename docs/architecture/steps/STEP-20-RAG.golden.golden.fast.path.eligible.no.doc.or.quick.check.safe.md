# RAG STEP 20 — Golden fast-path eligible? no doc or quick check safe (RAG.golden.golden.fast.path.eligible.no.doc.or.quick.check.safe)

**Type:** process  
**Category:** golden  
**Node ID:** `GoldenFastGate`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `GoldenFastGate` (Golden fast-path eligible? no doc or quick check safe).

## Current Implementation (Repo)
- **Role:** Node
- **Paths / classes:** `app/core/langgraph/nodes/step_020__golden_fast_gate.py` - `node_step_20`, `app/orchestrators/golden.py:14` - `step_20__golden_fast_gate()`
- **Status:** ✅ Implemented
- **Behavior notes:** Node orchestrator using GoldenFastPathService to determine eligibility for golden fast-path. Checks for document-dependent queries, safe factual queries, and complexity indicators. Routes to Step 24 (GoldenLookup) if eligible or Step 31 (ClassifyDomain) if not eligible.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing Golden Set infrastructure

## TDD Task List
- [x] Unit tests (Golden Set operations, FAQ management, confidence matching)
- [x] Integration tests (Golden Set matching and FAQ retrieval flow)
- [x] Implementation changes (async orchestrator with Golden Set operations, FAQ management, confidence matching)
- [x] Observability: add structured log line
  `RAG STEP 20 (...): ... | attrs={match_confidence, golden_set_id, faq_version}`
- [x] Feature flag / config if needed (Golden Set thresholds and matching parameters)
- [x] Rollout plan (implemented with Golden Set accuracy and cache performance safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Node  |  Status: ✅ (Implemented & Wired)  |  Confidence: 0.51

Top candidates:
1) app/api/v1/faq_automation.py:418 — app.api.v1.faq_automation.approve_faq (score 0.51)
   Evidence: Score 0.51, Approve, reject, or request revision for a generated FAQ
2) app/api/v1/faq_automation.py:460 — app.api.v1.faq_automation.publish_faq (score 0.51)
   Evidence: Score 0.51, Publish an approved FAQ to make it available to users
3) app/orchestrators/golden.py:690 — app.orchestrators.golden.step_117__faqfeedback (score 0.50)
   Evidence: Score 0.50, RAG STEP 117 — POST /api/v1/faq/feedback.

ID: RAG.golden.post.api.v1.faq.feedba...
4) app/api/v1/faq.py:645 — app.api.v1.faq.health_check (score 0.48)
   Evidence: Score 0.48, FAQ system health check.
5) app/api/v1/faq.py:40 — app.api.v1.faq.FAQQueryRequest (score 0.47)
   Evidence: Score 0.47, Request model for FAQ queries.

Notes:
- Strong implementation match found
- Wired via graph registry ✅
- Incoming: [], Outgoing: [24]

Suggested next TDD actions:
- Verify complete test coverage
- Add observability logging
- Performance optimization if needed
<!-- AUTO-AUDIT:END -->