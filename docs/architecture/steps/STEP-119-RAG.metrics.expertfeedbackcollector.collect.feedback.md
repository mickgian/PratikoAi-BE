# RAG STEP 119 — ExpertFeedbackCollector.collect_feedback (RAG.metrics.expertfeedbackcollector.collect.feedback)

**Type:** process  
**Category:** metrics  
**Node ID:** `ExpertFeedbackCollector`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ExpertFeedbackCollector` (ExpertFeedbackCollector.collect_feedback).

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
  `RAG STEP 119 (RAG.metrics.expertfeedbackcollector.collect.feedback): ExpertFeedbackCollector.collect_feedback | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.34

Top candidates:
1) app/services/expert_feedback_collector.py:43 — app.services.expert_feedback_collector.ExpertFeedbackCollector.__init__ (score 0.34)
   Evidence: Score 0.34, method: __init__
2) app/services/expert_feedback_collector.py:149 — app.services.expert_feedback_collector.ExpertFeedbackCollector._validate_feedback_data (score 0.34)
   Evidence: Score 0.34, Validate feedback data structure and content
3) app/services/expert_feedback_collector.py:297 — app.services.expert_feedback_collector.ExpertFeedbackCollector._update_statistics (score 0.34)
   Evidence: Score 0.34, Update internal statistics tracking
4) app/services/expert_feedback_collector.py:515 — app.services.expert_feedback_collector.ExpertFeedbackCollector.get_statistics (score 0.34)
   Evidence: Score 0.34, Get current session statistics
5) app/services/expert_feedback_collector.py:31 — app.services.expert_feedback_collector.ExpertFeedbackCollector (score 0.30)
   Evidence: Score 0.30, Service for collecting and processing expert feedback on AI responses.

Features...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->