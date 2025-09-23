# RAG STEP 27 — KB newer than Golden as of or conflicting tags? (RAG.golden.kb.newer.than.golden.as.of.or.conflicting.tags)

**Type:** process  
**Category:** golden  
**Node ID:** `KBDelta`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `KBDelta` (KB newer than Golden as of or conflicting tags?).

## Current Implementation (Repo)
- **Paths / classes:** `app/services/kb_delta_decision.py:KBDeltaDecision`, `tests/test_rag_step_27_kb_delta.py:TestRAGStep27KBDelta`
- **Status:** ✅ Implemented
- **Behavior notes:** Implemented KBDeltaDecision class that compares KB results from STEP 26 with Golden Set metadata to determine if KB has newer or conflicting information. Includes timestamp comparison, sophisticated conflict detection logic, and structured logging. Full test coverage with 8 passing tests covering all decision scenarios.

## Differences (Blueprint vs Current)
- _TBD_

## Risks / Impact
- _TBD_

## TDD Task List
- [x] Unit tests (newer KB decision, older KB decision, conflicting tags, empty results, missing metadata, mixed results, structured logging, edge cases)
- [x] Integration tests (full decision flow scenarios, error handling)
- [x] Implementation changes (KBDeltaDecision class, comparison logic, conflict detection, decision making)
- [x] Observability: add structured log line  
  `RAG STEP 27 (RAG.golden.kb.newer.than.golden.as.of.or.conflicting.tags): KB newer than Golden as of or conflicting tags? | attrs={decision, should_merge_context, newer_count, conflict_count, reason, processing_stage, golden_age_days, kb_newest_age_days, conflict_types}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.51

Top candidates:
1) app/orchestrators/golden.py:140 — app.orchestrators.golden.step_117__faqfeedback (score 0.51)
   Evidence: Score 0.51, RAG STEP 117 — POST /api/v1/faq/feedback
ID: RAG.golden.post.api.v1.faq.feedback...
2) app/api/v1/faq.py:1 — app.api.v1.faq (score 0.48)
   Evidence: Score 0.48, FAQ API endpoints for the Intelligent FAQ System.

This module provides REST API...
3) app/api/v1/faq_automation.py:1 — app.api.v1.faq_automation (score 0.47)
   Evidence: Score 0.47, FAQ Automation API Endpoints.

Admin dashboard and management endpoints for the ...
4) app/orchestrators/golden.py:122 — app.orchestrators.golden.step_83__faqquery (score 0.46)
   Evidence: Score 0.46, RAG STEP 83 — FAQTool.faq_query Query Golden Set
ID: RAG.golden.faqtool.faq.quer...
5) app/orchestrators/golden.py:176 — app.orchestrators.golden.step_128__golden_approval (score 0.46)
   Evidence: Score 0.46, RAG STEP 128 — Auto threshold met or manual approval?
ID: RAG.golden.auto.thresh...

Notes:
- Implementation exists but may not be wired correctly

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->