# RAG STEP 123 — Create ExpertFeedback record (RAG.feedback.create.expertfeedback.record)

**Type:** process  
**Category:** feedback  
**Node ID:** `CreateFeedbackRec`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `CreateFeedbackRec` (Create ExpertFeedback record).

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
  `RAG STEP 123 (RAG.feedback.create.expertfeedback.record): Create ExpertFeedback record | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.42

Top candidates:
1) app/models/quality_analysis.py:105 — app.models.quality_analysis.ExpertFeedback (score 0.42)
   Evidence: Score 0.42, Expert feedback on AI-generated answers
2) app/services/expert_feedback_collector.py:1 — app.services.expert_feedback_collector (score 0.38)
   Evidence: Score 0.38, Expert Feedback Collection Service for Quality Analysis System.

Handles collect...
3) app/models/quality_analysis.py:27 — app.models.quality_analysis.FeedbackType (score 0.37)
   Evidence: Score 0.37, Types of expert feedback
4) app/models/quality_analysis.py:361 — app.models.quality_analysis.ExpertValidation (score 0.36)
   Evidence: Score 0.36, Expert validation records for complex queries
5) app/services/expert_feedback_collector.py:31 — app.services.expert_feedback_collector.ExpertFeedbackCollector (score 0.36)
   Evidence: Score 0.36, Service for collecting and processing expert feedback on AI responses.

Features...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->