# RAG STEP 129 — GoldenSet.publish_or_update versioned entry (RAG.golden.goldenset.publish.or.update.versioned.entry)

**Type:** process  
**Category:** golden  
**Node ID:** `PublishGolden`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `PublishGolden` (GoldenSet.publish_or_update versioned entry).

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
  `RAG STEP 129 (RAG.golden.goldenset.publish.or.update.versioned.entry): GoldenSet.publish_or_update versioned entry | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🟡  |  Confidence: 0.57

Top candidates:
1) app/api/v1/faq_automation.py:460 — app.api.v1.faq_automation.publish_faq (score 0.57)
   Evidence: Score 0.57, Publish an approved FAQ to make it available to users
2) app/api/v1/faq_automation.py:418 — app.api.v1.faq_automation.approve_faq (score 0.54)
   Evidence: Score 0.54, Approve, reject, or request revision for a generated FAQ
3) app/api/v1/faq.py:431 — app.api.v1.faq.update_faq (score 0.53)
   Evidence: Score 0.53, Update an existing FAQ entry with versioning.

Requires admin privileges.
4) app/orchestrators/golden.py:140 — app.orchestrators.golden.step_117__faqfeedback (score 0.51)
   Evidence: Score 0.51, RAG STEP 117 — POST /api/v1/faq/feedback
ID: RAG.golden.post.api.v1.faq.feedback...
5) app/api/v1/faq.py:130 — app.api.v1.faq.query_faq (score 0.49)
   Evidence: Score 0.49, Query the FAQ system with semantic search and response variation.

This endpoint...

Notes:
- Partial implementation identified

Suggested next TDD actions:
- Complete partial implementation
- Add missing error handling
- Expand test coverage
- Add performance benchmarks if needed
<!-- AUTO-AUDIT:END -->