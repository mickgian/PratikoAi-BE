# RAG STEP 116 — Feedback type selected (RAG.feedback.feedback.type.selected)

**Type:** process  
**Category:** feedback  
**Node ID:** `FeedbackTypeSel`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `FeedbackTypeSel` (Feedback type selected).

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
  `RAG STEP 116 (RAG.feedback.feedback.type.selected): Feedback type selected | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.38

Top candidates:
1) app/models/quality_analysis.py:27 — app.models.quality_analysis.FeedbackType (score 0.38)
   Evidence: Score 0.38, Types of expert feedback
2) app/models/quality_analysis.py:361 — app.models.quality_analysis.ExpertValidation (score 0.36)
   Evidence: Score 0.36, Expert validation records for complex queries
3) app/models/quality_analysis.py:105 — app.models.quality_analysis.ExpertFeedback (score 0.36)
   Evidence: Score 0.36, Expert feedback on AI-generated answers
4) app/services/expert_feedback_collector.py:1 — app.services.expert_feedback_collector (score 0.35)
   Evidence: Score 0.35, Expert Feedback Collection Service for Quality Analysis System.

Handles collect...
5) app/models/quality_analysis.py:60 — app.models.quality_analysis.ExpertProfile (score 0.35)
   Evidence: Score 0.35, Expert profiles for validation and trust scoring

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->