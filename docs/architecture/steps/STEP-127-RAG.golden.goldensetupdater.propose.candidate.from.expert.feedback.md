# RAG STEP 127 — GoldenSetUpdater.propose_candidate from expert feedback (RAG.golden.goldensetupdater.propose.candidate.from.expert.feedback)

**Type:** process  
**Category:** golden  
**Node ID:** `GoldenCandidate`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `GoldenCandidate` (GoldenSetUpdater.propose_candidate from expert feedback).

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
  `RAG STEP 127 (RAG.golden.goldensetupdater.propose.candidate.from.expert.feedback): GoldenSetUpdater.propose_candidate from expert feedback | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.50

Top candidates:
1) app/orchestrators/golden.py:140 — app.orchestrators.golden.step_117__faqfeedback (score 0.50)
   Evidence: Score 0.50, RAG STEP 117 — POST /api/v1/faq/feedback
ID: RAG.golden.post.api.v1.faq.feedback...
2) app/api/v1/faq.py:1 — app.api.v1.faq (score 0.47)
   Evidence: Score 0.47, FAQ API endpoints for the Intelligent FAQ System.

This module provides REST API...
3) app/api/v1/faq_automation.py:1 — app.api.v1.faq_automation (score 0.46)
   Evidence: Score 0.46, FAQ Automation API Endpoints.

Admin dashboard and management endpoints for the ...
4) app/orchestrators/golden.py:122 — app.orchestrators.golden.step_83__faqquery (score 0.46)
   Evidence: Score 0.46, RAG STEP 83 — FAQTool.faq_query Query Golden Set
ID: RAG.golden.faqtool.faq.quer...
5) app/orchestrators/golden.py:176 — app.orchestrators.golden.step_128__golden_approval (score 0.45)
   Evidence: Score 0.45, RAG STEP 128 — Auto threshold met or manual approval?
ID: RAG.golden.auto.thresh...

Notes:
- Implementation exists but may not be wired correctly

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->