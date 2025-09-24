# RAG STEP 128 — Auto threshold met or manual approval? (RAG.golden.auto.threshold.met.or.manual.approval)

**Type:** decision  
**Category:** golden  
**Node ID:** `GoldenApproval`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `GoldenApproval` (Auto threshold met or manual approval?).

## Current Implementation (Repo)
- **Paths / classes:** _TBD during audit_
- **Status:** ❓ Pending review (✅ Implemented / 🟡 Partial / ❌ Missing / 🔌 Not wired)
- **Behavior notes:** _TBD_

## Differences (Blueprint vs Current)
- _TBD_

## Risks / Impact
- _TBD_

## TDD Task List
- [ ] Unit tests (list specific cases)
- [ ] Integration tests (list cases)
- [ ] Implementation changes (bullets)
- [ ] Observability: add structured log line  
  `RAG STEP 128 (RAG.golden.auto.threshold.met.or.manual.approval): Auto threshold met or manual approval? | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

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
3) app/orchestrators/golden.py:140 — app.orchestrators.golden.step_117__faqfeedback (score 0.51)
   Evidence: Score 0.51, RAG STEP 117 — POST /api/v1/faq/feedback
ID: RAG.golden.post.api.v1.faq.feedback...
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