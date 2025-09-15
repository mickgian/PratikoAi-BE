# RAG STEP 135 — GoldenSetUpdater.auto_rule_eval new or obsolete candidates (RAG.golden.goldensetupdater.auto.rule.eval.new.or.obsolete.candidates)

**Type:** process  
**Category:** golden  
**Node ID:** `GoldenRules`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `GoldenRules` (GoldenSetUpdater.auto_rule_eval new or obsolete candidates).

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
  `RAG STEP 135 (RAG.golden.goldensetupdater.auto.rule.eval.new.or.obsolete.candidates): GoldenSetUpdater.auto_rule_eval new or obsolete candidates | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.47

Top candidates:
1) app/api/v1/faq.py:1 — app.api.v1.faq (score 0.47)
   Evidence: Score 0.47, FAQ API endpoints for the Intelligent FAQ System.

This module provides REST API...
2) app/api/v1/faq.py:40 — app.api.v1.faq.FAQQueryRequest (score 0.46)
   Evidence: Score 0.46, Request model for FAQ queries.
3) app/api/v1/faq.py:47 — app.api.v1.faq.FAQQueryResponse (score 0.46)
   Evidence: Score 0.46, Response model for FAQ queries.
4) app/api/v1/faq.py:60 — app.api.v1.faq.FAQCreateRequest (score 0.46)
   Evidence: Score 0.46, Request model for creating FAQ entries.
5) app/api/v1/faq.py:69 — app.api.v1.faq.FAQUpdateRequest (score 0.46)
   Evidence: Score 0.46, Request model for updating FAQ entries.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->