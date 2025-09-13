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
Status: 🔌  |  Confidence: 0.41

Top candidates:
1) app/services/expert_feedback_collector.py:31 — app.services.expert_feedback_collector.ExpertFeedbackCollector (score 0.41)
   Evidence: Score 0.41, Service for collecting and processing expert feedback on AI responses.

Features...
2) app/services/expert_feedback_collector.py:149 — app.services.expert_feedback_collector.ExpertFeedbackCollector._validate_feedback_data (score 0.40)
   Evidence: Score 0.40, Validate feedback data structure and content
3) app/services/automatic_improvement_engine.py:662 — app.services.automatic_improvement_engine.AutomaticImprovementEngine._initialize_improvement_strategies (score 0.38)
   Evidence: Score 0.38, Initialize improvement strategies for different pattern types
4) app/services/automatic_improvement_engine.py:1 — app.services.automatic_improvement_engine (score 0.37)
   Evidence: Score 0.37, Automatic Improvement Engine for Quality Analysis System.

Automatically generat...
5) app/models/quality_analysis.py:105 — app.models.quality_analysis.ExpertFeedback (score 0.37)
   Evidence: Score 0.37, Expert feedback on AI-generated answers

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->