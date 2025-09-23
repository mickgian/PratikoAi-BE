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
Status: 🔌  |  Confidence: 0.50

Top candidates:
1) app/orchestrators/golden.py:140 — app.orchestrators.golden.step_117__faqfeedback (score 0.50)
   Evidence: Score 0.50, RAG STEP 117 — POST /api/v1/faq/feedback
ID: RAG.golden.post.api.v1.faq.feedback...
2) app/models/faq_automation.py:351 — app.models.faq_automation.GeneratedFAQ.should_auto_approve (score 0.46)
   Evidence: Score 0.46, Determine if FAQ should be auto-approved based on quality
3) app/api/v1/faq.py:1 — app.api.v1.faq (score 0.46)
   Evidence: Score 0.46, FAQ API endpoints for the Intelligent FAQ System.

This module provides REST API...
4) app/api/v1/faq_automation.py:1 — app.api.v1.faq_automation (score 0.45)
   Evidence: Score 0.45, FAQ Automation API Endpoints.

Admin dashboard and management endpoints for the ...
5) app/orchestrators/golden.py:122 — app.orchestrators.golden.step_83__faqquery (score 0.45)
   Evidence: Score 0.45, RAG STEP 83 — FAQTool.faq_query Query Golden Set
ID: RAG.golden.faqtool.faq.quer...

Notes:
- Implementation exists but may not be wired correctly

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->